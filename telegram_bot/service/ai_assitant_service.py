from datetime import datetime

from agents import Runner
from loguru import logger

from telegram_bot.ai_assistant.ai_assitant_agent import get_ai_assistant_agent
from telegram_bot.config import BotSettings
from telegram_bot.service.db_service import DBService, MessageEntry, MessageType


class AIAssistantService:
    def __init__(self, db_service: DBService, bot_settings: BotSettings) -> None:
        self.db_service = db_service
        self.bot_settings = bot_settings
        self.ai_assistant_agent = None

    async def run_ai_assistant(self, user_id: int, query: str, message_type: MessageType = MessageType.TEXT) -> str:
        if self.ai_assistant_agent is None:
            logger.info(f"Initializing AI Assistant agent for user {user_id}")
            self.ai_assistant_agent = await get_ai_assistant_agent(
                self.bot_settings.ai_assistant,
                log_file_path=self.bot_settings.out_dir / self.bot_settings.ai_assistant.relative_log_dir,
            )

        # Get the 3 most recent conversation entries for context
        recent_messages = list(self.db_service.list_message_logs(user_id=user_id, limit=3))

        # Build context from previous messages if available
        context = ""
        if recent_messages:
            context = "Previous conversation:\n"
            for msg in reversed(recent_messages):  # Display oldest to newest
                context += f"User: {msg.content}\n"
                context += f"Assistant: {msg.response}\n\n"
            context += "Current message:\n"

        # Build the complete query with context and timestamp
        full_query = f"{context}{query}\n\nToday is {datetime.now().isoformat()}"

        logger.debug(f"Running AI Assistant for user {user_id} with query including context")
        result = await Runner.run(self.ai_assistant_agent, input=full_query)
        final_output = result.final_output
        logger.debug(f"AI Assistant response: {final_output}")

        # Save just the original query in the database, not the full context
        message_entry = MessageEntry(user_id=user_id, message_type=message_type, content=query, response=final_output)
        self.db_service.add_message_entry(message_entry)
        return final_output
