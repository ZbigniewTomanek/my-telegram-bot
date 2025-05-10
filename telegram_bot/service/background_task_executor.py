import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger


@dataclass
class TaskJob:
    target_fn: Callable[..., Any]
    target_args: tuple[Any, ...] = field(default_factory=tuple)
    target_kwargs: dict[str, Any] = field(default_factory=dict)

    callback_fn: Optional[Callable[..., Awaitable[None]]] = None


class BackgroundTaskExecutor:
    """
    Manages a queue and worker pool for executing generic background tasks.
    CPU-bound tasks are run in a ProcessPoolExecutor, and their results (or exceptions)
    are passed to an asyncio callback function.
    """

    def __init__(self, num_async_workers: int = 2, num_cpu_workers: int = 1):
        """
        Initializes the BackgroundTaskExecutor.

        Args:
            num_async_workers: Number of asyncio tasks pulling from the queue to dispatch jobs.
            num_cpu_workers: Number of worker processes in the ProcessPoolExecutor
                             for CPU-bound tasks. This is the primary concurrency limit
                             for the actual heavy computation.
        """
        self._queue: asyncio.Queue[TaskJob] = asyncio.Queue()
        self._num_async_workers = num_async_workers

        # Ensure num_cpu_workers is at least 1
        if num_cpu_workers < 1:
            logger.warning(f"num_cpu_workers was {num_cpu_workers}, defaulting to 1.")
            num_cpu_workers = 1

        self._process_pool = ProcessPoolExecutor(max_workers=num_cpu_workers)
        self._worker_tasks: list[asyncio.Task] = []
        self._is_running = False

        logger.info(
            f"BackgroundTaskExecutor initialized with {num_async_workers} async workers "
            f"and {num_cpu_workers} CPU workers."
        )

    async def _worker(self, worker_id: int):
        """
        An asyncio worker task that pulls jobs from the queue,
        executes them via the process pool, and then calls the callback.
        """
        logger.info(f"Async worker {worker_id} started.")
        loop = asyncio.get_running_loop()

        while self._is_running:
            try:
                # Wait for a job with a timeout to allow checking self._is_running
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue  # Check self._is_running again
            except asyncio.CancelledError:
                logger.info(f"Async worker {worker_id} received cancellation request during queue.get().")
                break  # Exit if cancelled

            if not job:  # Should not happen if queue is managed properly, but as a safeguard
                self._queue.task_done()
                continue

            logger.info(f"Async worker {worker_id} picked up job for target: {job.target_fn.__name__}")

            task_result: Any = None
            task_exception: Optional[Exception] = None

            try:
                # Execute the CPU-bound target function in the process pool
                task_result = await loop.run_in_executor(
                    self._process_pool, job.target_fn, *job.target_args, **job.target_kwargs
                )
                logger.debug(f"Target function {job.target_fn.__name__} completed successfully for worker {worker_id}.")
            except Exception as e:
                logger.exception(f"Exception in target_fn {job.target_fn.__name__} (worker {worker_id}): {e}")
                task_exception = e

            # If a callback is provided, execute it
            if job.callback_fn:
                try:
                    logger.debug(f"Executing callback {job.callback_fn.__name__} for worker {worker_id}.")
                    # The callback receives the result, any exception, and its own pre-configured args
                    await job.callback_fn(task_result, task_exception, *job.callback_args, **job.callback_kwargs)
                except Exception as ce:
                    logger.exception(
                        f"Exception in callback_fn {job.callback_fn.__name__} "
                        f"for target {job.target_fn.__name__} (worker {worker_id}): {ce}"
                    )

            self._queue.task_done()
            logger.info(f"Async worker {worker_id} finished job for target: {job.target_fn.__name__}")

        logger.info(f"Async worker {worker_id} stopped.")

    async def add_task(
        self,
        target_fn: Callable[..., Any],
        target_args: tuple[Any, ...] = (),
        target_kwargs: Optional[dict[str, Any]] = None,
        callback_fn: Optional[Callable[..., Awaitable[None]]] = None,
    ) -> None:
        """
        Adds a new task to the processing queue.

        Args:
            target_fn: The CPU-bound function to execute.
            target_args: Positional arguments for target_fn.
            target_kwargs: Keyword arguments for target_fn.
            callback_fn: The async function to call with the result of target_fn.
                         Signature: async def my_callback(result, exception, *cb_args, **cb_kwargs)
        """
        if not self._is_running:
            raise RuntimeError("BackgroundTaskExecutor is not running. Please start it before adding tasks.")

        job = TaskJob(
            target_fn=target_fn,
            target_args=target_args,
            target_kwargs=target_kwargs if target_kwargs is not None else {},
            callback_fn=callback_fn,
        )
        await self._queue.put(job)
        logger.info(f"Added task for target {target_fn.__name__} to queue. Queue size: {self._queue.qsize()}")

    async def start_workers(self):
        """
        Starts the asyncio worker tasks.
        """
        if self._is_running:
            logger.info("Workers are already running.")
            return

        self._is_running = True
        self._worker_tasks.clear()  # Clear any old tasks if restart is attempted (though not typical)
        for i in range(self._num_async_workers):
            task = asyncio.create_task(self._worker(i))
            self._worker_tasks.append(task)
        logger.info(f"Started {self._num_async_workers} async workers for BackgroundTaskExecutor.")

    async def stop_workers(self, wait_for_queue: bool = True):
        """
        Stops the asyncio worker tasks and shuts down the process pool.

        Args:
            wait_for_queue: If True, waits for all items currently in the queue
                            to be processed before stopping workers.
        """
        if not self._is_running:
            logger.info("Workers are not running.")
            return

        logger.info("Stopping BackgroundTaskExecutor workers...")

        if wait_for_queue and not self._queue.empty():
            logger.info(f"Waiting for {self._queue.qsize()} items in queue to be processed...")
            await self._queue.join()  # Wait for all queue items to be processed

        self._is_running = False  # Signal workers to stop

        # Wait for worker tasks to complete
        if self._worker_tasks:
            logger.info("Cancelling and gathering worker tasks...")
            for task in self._worker_tasks:
                task.cancel()
            # Wait for all tasks to acknowledge cancellation and finish
            results = await asyncio.gather(*self._worker_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, asyncio.CancelledError):
                    logger.debug(f"Worker task {i} cancelled successfully.")
                elif isinstance(result, Exception):
                    logger.error(f"Worker task {i} raised an exception during shutdown: {result}")
            self._worker_tasks.clear()
            logger.info("All async worker tasks have been stopped.")

        # Shutdown the process pool
        logger.info("Shutting down process pool...")
        self._process_pool.shutdown(wait=True)  # wait=True ensures all child processes finish
        logger.info("Process pool shut down.")
        logger.info("BackgroundTaskExecutor workers stopped.")
