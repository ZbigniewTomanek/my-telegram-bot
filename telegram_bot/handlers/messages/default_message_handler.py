import random
from typing import Any

from fortune import fortune
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, MessageHandler, filters

from telegram_bot.handlers.base.public_handler import PublicHandler


class DefaultMessageHandler(PublicHandler):
    # Emojis to make messages more visually appealing
    FORTUNE_EMOJIS = ["🔮", "✨", "🌟", "💫", "🧙", "🎯", "🧠", "💭", "📜", "⚡️"]

    async def _handle(self, update: Update, context: CallbackContext) -> Any:
        fortune_text = fortune()
        emoji = random.choice(self.FORTUNE_EMOJIS)

        formatted_message = f"{emoji} *Fortune Cookie* {emoji}\n\n_{fortune_text}_"
        await update.message.reply_text(formatted_message, parse_mode=ParseMode.MARKDOWN)


def get_default_message_handler() -> MessageHandler:
    return MessageHandler(filters.TEXT & ~filters.COMMAND, DefaultMessageHandler().handle)
