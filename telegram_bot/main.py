from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Tuple

from loguru import logger
from telegram import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, BotCommandScopeDefault
from telegram.ext import Application, ApplicationBuilder

# --- project‑specific imports -------------------------------------------------
from telegram_bot.handlers.commands.garmin_commands import get_garmin_disconnect_command, get_garmin_status_command
from telegram_bot.handlers.commands.list_drug_command import get_list_drugs_command
from telegram_bot.handlers.commands.list_food_command import get_list_food_command
from telegram_bot.handlers.conversations.garmin_auth_conversation import get_garmin_auth_handler
from telegram_bot.handlers.conversations.garmin_export_conversation import get_garmin_export_handler
from telegram_bot.handlers.conversations.log_drug_conversation import get_drug_log_handler
from telegram_bot.handlers.conversations.log_food_conversation import get_food_log_handler
from telegram_bot.handlers.messages.default_message_handler import get_default_message_handler
from telegram_bot.service.db_service import DBService
from telegram_bot.service.garmin_connect_service import GarminConnectService

# ---------------------------------------------------------------------------

OUT_DIR = Path(__file__).parent.parent / "out"


def setup_logger() -> None:
    log_dir = OUT_DIR / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(log_dir / "debug.log", rotation="100 MB", retention="7 days", level="DEBUG")
    logger.add(log_dir / "error.log", rotation="100 MB", retention="7 days", level="ERROR")
    logger.info("logger initialised")


# ---------------------------------------------------------------------------#
# Commands                                                                   #
# ---------------------------------------------------------------------------#


def _build_commands() -> Dict[str, List[BotCommand]]:
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

    german = [
        BotCommand("log_food", "Lebensmittel protokollieren"),
        BotCommand("list_food", "Lebensmittelprotokolle anzeigen"),
        BotCommand("log_drug", "Medikamente protokollieren"),
        BotCommand("list_drugs", "Medikamentenprotokolle anzeigen"),
        BotCommand("connect_garmin", "Garmin‑Konto verbinden"),
        BotCommand("garmin_export", "Daten aus Garmin Connect exportieren"),
        BotCommand("garmin_status", "Garmin‑Status prüfen"),
        BotCommand("disconnect_garmin", "Garmin‑Konto trennen"),
        BotCommand("cancel", "Konversation abbrechen"),
    ]

    return {
        "default": common + garmin,
        "private": common + garmin,
        "group": common,
        "german": german,
    }


async def _post_init(application: Application) -> None:
    commands = _build_commands()

    matrix: List[Tuple[List[BotCommand], object, str | None]] = [
        (commands["private"], BotCommandScopeAllPrivateChats(), None),
        (commands["group"], BotCommandScopeAllGroupChats(), None),
        (commands["default"], BotCommandScopeDefault(), None),
        (commands["default"], BotCommandScopeDefault(), "en"),
        (commands["german"], BotCommandScopeDefault(), "de"),
    ]

    await asyncio.gather(
        *(application.bot.set_my_commands(cmds, scope=scope, language_code=lang) for cmds, scope, lang in matrix)
    )
    logger.info("Bot commands registered.")


# ---------------------------------------------------------------------------#
# Application setup                                                          #
# ---------------------------------------------------------------------------#


def _build_app() -> Application:
    token = os.getenv("TELEGRAM_BOT_API_KEY")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_API_KEY env var not set")

    application = (
        ApplicationBuilder()
        .token(token)
        .concurrent_updates(True)
        .read_timeout(int(os.getenv("READ_TIMEOUT_S", 30)))
        .write_timeout(int(os.getenv("WRITE_TIMEOUT_S", 30)))
        .post_init(_post_init)
        .build()
    )
    return application


def _initialise_services() -> tuple[DBService, GarminConnectService]:
    db_service = DBService(out_dir=OUT_DIR)

    token_dir = OUT_DIR / "garmin_tokens"
    token_dir.mkdir(parents=True, exist_ok=True)
    garmin_service = GarminConnectService(token_store_dir=token_dir)

    return db_service, garmin_service


def _setup_handlers(app: Application, db: DBService, garmin: GarminConnectService) -> None:
    app.add_handler(get_food_log_handler(db))
    app.add_handler(get_drug_log_handler(db))
    app.add_handler(get_list_food_command(db))
    app.add_handler(get_list_drugs_command(db))

    app.add_handler(get_garmin_auth_handler(garmin))
    app.add_handler(get_garmin_export_handler(garmin))
    app.add_handler(get_garmin_status_command(garmin))
    app.add_handler(get_garmin_disconnect_command(garmin))

    app.add_handler(get_default_message_handler())


def build_configured_application() -> Application:
    setup_logger()
    application = _build_app()
    db, garmin = _initialise_services()
    _setup_handlers(application, db, garmin)
    return application


def main() -> None:  # pragma: no cover
    application = build_configured_application()
    logger.info("Starting polling …")
    application.run_polling(allowed_updates="*")


if __name__ == "__main__":
    main()
