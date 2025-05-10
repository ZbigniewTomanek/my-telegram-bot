from __future__ import annotations

import asyncio
import atexit
from pathlib import Path

from loguru import logger
from telegram import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, BotCommandScopeDefault
from telegram.ext import Application, ApplicationBuilder

from telegram_bot.config import BotSettings
from telegram_bot.handlers.commands.garmin_commands import get_garmin_disconnect_command, get_garmin_status_command
from telegram_bot.handlers.commands.list_drug_command import get_list_drugs_command
from telegram_bot.handlers.commands.list_food_command import get_list_food_command
from telegram_bot.handlers.conversations.garmin_auth_conversation import get_garmin_auth_handler
from telegram_bot.handlers.conversations.garmin_export_conversation import get_garmin_export_handler
from telegram_bot.handlers.conversations.log_drug_conversation import get_drug_log_handler
from telegram_bot.handlers.conversations.log_food_conversation import get_food_log_handler
from telegram_bot.handlers.messages import get_default_message_handler, get_voice_message_handler
from telegram_bot.service_factory import ServiceFactory

BOT_SETTINGS = BotSettings()
SERVICE_FACTORY = ServiceFactory(BOT_SETTINGS)


def setup_logger(out_dir: Path) -> None:
    log_dir = out_dir / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(log_dir / "debug.log", rotation="100 MB", retention="7 days", level="DEBUG")
    logger.add(log_dir / "error.log", rotation="100 MB", retention="7 days", level="ERROR")
    logger.info("logger initialised")


def _build_commands() -> dict[str, list[BotCommand]]:
    common = [
        BotCommand("log_food", "Log your food consumption"),
        BotCommand("list_food", "View your food logs"),
        BotCommand("log_drug", "Log drug usage"),
        BotCommand("list_drugs", "View your drug logs"),
        BotCommand("cancel", "Cancel current conversation"),
    ]

    garmin = [
        BotCommand("connect_garmin", "Connect your Garmin account"),
        BotCommand("garmin_export", "Export data from Garmin Connect"),
        BotCommand("garmin_status", "Check Garmin Connect status"),
        BotCommand("disconnect_garmin", "Disconnect your Garmin account"),
    ]

    return {
        "default": common + garmin,
        "private": common + garmin,
        "group": common,
    }


async def _post_init(application: Application) -> None:
    commands = _build_commands()

    await SERVICE_FACTORY.background_task_executor.start_workers()

    async def stop_workers() -> None:
        await SERVICE_FACTORY.background_task_executor.stop_workers(False)

    atexit.register(stop_workers)

    matrix: list[tuple[list[BotCommand], object, str | None]] = [
        (commands["private"], BotCommandScopeAllPrivateChats(), None),
        (commands["group"], BotCommandScopeAllGroupChats(), None),
        (commands["default"], BotCommandScopeDefault(), None),
        (commands["default"], BotCommandScopeDefault(), "en"),
    ]

    await asyncio.gather(
        *(application.bot.set_my_commands(cmds, scope=scope, language_code=lang) for cmds, scope, lang in matrix)
    )
    logger.info("Bot commands registered.")


def _build_app(bot_settings: BotSettings) -> Application:
    application = (
        ApplicationBuilder()
        .token(bot_settings.telegram_bot_api_key)
        .concurrent_updates(True)
        .read_timeout(bot_settings.read_timeout_s)
        .write_timeout(bot_settings.write_timeout_s)
        .post_init(_post_init)
        .build()
    )
    return application


def _setup_handlers(app: Application) -> None:
    app.add_handler(get_food_log_handler(SERVICE_FACTORY.db_service))
    app.add_handler(get_drug_log_handler(SERVICE_FACTORY.db_service))
    app.add_handler(get_list_food_command(SERVICE_FACTORY.db_service))
    app.add_handler(get_list_drugs_command(SERVICE_FACTORY.db_service))

    app.add_handler(get_garmin_auth_handler(SERVICE_FACTORY.garmin_connect_service))
    app.add_handler(get_garmin_export_handler(SERVICE_FACTORY.garmin_connect_service))
    app.add_handler(get_garmin_status_command(SERVICE_FACTORY.garmin_connect_service))
    app.add_handler(get_garmin_disconnect_command(SERVICE_FACTORY.garmin_connect_service))

    app.add_handler(get_voice_message_handler(SERVICE_FACTORY.message_transcription_service))
    app.add_handler(get_default_message_handler())


def build_configured_application() -> Application:
    if not BOT_SETTINGS.out_dir.exists():
        BOT_SETTINGS.out_dir.mkdir(parents=True)
    setup_logger(BOT_SETTINGS.out_dir)
    application = _build_app(BOT_SETTINGS)

    _setup_handlers(application)
    return application


def main() -> None:  # pragma: no cover
    application = build_configured_application()
    logger.info("Starting polling …")
    application.run_polling(allowed_updates="*")


if __name__ == "__main__":
    main()
