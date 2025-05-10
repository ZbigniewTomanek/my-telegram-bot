from pathlib import Path
from typing import Union

from pydantic_settings import BaseSettings, SettingsConfigDict


class WhisperSettings(BaseSettings):
    model_size: str
    device: str = "auto"
    device_index: Union[int, list[int]] = 0
    compute_type: str = "default"
    cpu_threads: int = 0
    num_workers: int = 1
    download_root: Path = Path("/cache/whisper")
    local_files_only: bool = False


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    telegram_bot_api_key: str
    my_telegram_user_id: int
    read_timeout_s: int = 30
    write_timeout_s: int = 30
    out_dir: Path = "./out"
    garmin_token_dir: Path = "./out/garmin_tokens"
    executor_num_async_workers: int = 4
    executor_num_cpu_workers: int = 2
    whisper: WhisperSettings
