from functools import cached_property

from telegram_bot.config import BotSettings
from telegram_bot.service.background_task_executor import BackgroundTaskExecutor
from telegram_bot.service.db_service import DBService
from telegram_bot.service.garmin_connect_service import GarminConnectService
from telegram_bot.service.message_transcription_service import MessageTranscriptionService


class ServiceFactory:
    def __init__(self, bot_settings: BotSettings):
        self.bot_settings = bot_settings

    @cached_property
    def db_service(self) -> DBService:
        return DBService(self.bot_settings.out_dir)

    @cached_property
    def garmin_connect_service(self) -> GarminConnectService:
        return GarminConnectService(
            self.bot_settings.garmin_token_dir,
        )

    @cached_property
    def background_task_executor(self) -> BackgroundTaskExecutor:
        return BackgroundTaskExecutor(
            num_async_workers=self.bot_settings.executor_num_async_workers,
            num_cpu_workers=self.bot_settings.executor_num_cpu_workers,
        )

    @cached_property
    def message_transcription_service(self) -> MessageTranscriptionService:
        return MessageTranscriptionService(
            background_task_executor=self.background_task_executor, whisper_settings=self.bot_settings.whisper
        )
