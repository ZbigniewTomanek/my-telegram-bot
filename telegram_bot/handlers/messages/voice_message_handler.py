import tempfile
from pathlib import Path
from typing import Any

from loguru import logger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, MessageHandler, filters

from telegram_bot.handlers.base.public_handler import PublicHandler
from telegram_bot.service.background_task_executor import TaskResult
from telegram_bot.service.message_transcription_service import MessageTranscriptionService, TranscriptionResult


class VoiceMessageHandler(PublicHandler):
    def __init__(self, message_transcription_service: MessageTranscriptionService):
        self.message_transcription_service = message_transcription_service

    async def _handle(self, update: Update, context: CallbackContext) -> Any:
        await update.message.reply_text("🎙️ Transcribing your voice message...")
        voice_file = await update.message.voice.get_file()

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
            await voice_file.download_to_drive(custom_path=tmp_file.name)
            temp_path = Path(tmp_file.name)

        async def on_transcription_complete(task_result: TaskResult) -> None:
            if task_result.exception:
                logger.error(f"Error during transcription: {task_result.exception}")
                await update.message.reply_text("❌ An error occurred during transcription.")
                return

            result: TranscriptionResult = task_result.result
            transcript = " ".join([segment.text for segment in result.segments])
            transcription_time = round(result.duration.total_seconds(), 2)
            response = "🎙️ *Voice Message Transcript*\n\n"
            response += f"_{transcript}_\n\n"
            response += f"_(Transcribed in {transcription_time}s)_"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            await update.message.reply_text(result.llm_response.message.content, parse_mode=ParseMode.MARKDOWN)
            temp_path.unlink(missing_ok=True)

        await self.message_transcription_service.transcribe_message(
            tmp_audio_file=temp_path, callback=on_transcription_complete
        )


def get_voice_message_handler(message_transcription_service: MessageTranscriptionService) -> MessageHandler:
    return MessageHandler(filters.VOICE & ~filters.COMMAND, VoiceMessageHandler(message_transcription_service).handle)
