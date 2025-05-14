"""Utility functions for the Telegram bot."""

from pathlib import Path
from typing import Union


def get_user_directory(base_dir: Union[str, Path], user_id: Union[int, str], subdir: str = None) -> Path:
    """
    Get a user-specific directory path, creating it if it doesn't exist.

    Args:
        base_dir: Base directory path
        user_id: Telegram user ID
        subdir: Optional subdirectory within the user directory

    Returns:
        Path object for the user directory
    """
    # Ensure base_dir is a Path object
    if isinstance(base_dir, str):
        base_dir = Path(base_dir)

    # Convert user_id to string if it's an integer
    user_id_str = str(user_id)

    # Create the user directory path
    user_dir = base_dir / "user" / user_id_str

    # Add subdirectory if specified
    if subdir:
        user_dir = user_dir / subdir

    # Ensure the directory exists
    user_dir.mkdir(parents=True, exist_ok=True)

    return user_dir
