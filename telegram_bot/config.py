from pathlib import Path

from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    telegram_bot_api_key: str
    my_telegram_user_id: int
    read_timeout_s: int = 30
    write_timeout_s: int = 30
    out_dir: Path = "./out"
    garmin_token_dir: Path = "./out/garmin_tokens"
    executor_num_async_workers: int = 4
    executor_num_cpu_workers: int = 2
