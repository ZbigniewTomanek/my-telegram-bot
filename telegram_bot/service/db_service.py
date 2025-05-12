import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from loguru import logger


@dataclass
class FoodLogEntry:
    name: str
    protein: str
    carbs: str
    fats: str
    comment: str
    datetime: Optional[str] = None


@dataclass
class DrugLogEntry:
    drug_name: str
    dosage: int
    datetime: Optional[str] = None


class MessageType(Enum):
    TEXT = "text"
    VOICE = "voice"


@dataclass
class MessageEntry:
    user_id: int
    message_type: MessageType
    content: str
    response: str
    datetime: Optional[str] = None


class DBService:
    _FOOD_LOG_TABLE_NAME = "food_log"
    _DRUG_LOG_TABLE_NAME = "drug_log"
    _MESSAGE_LOG_TABLE_NAME = "message_log"

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self._initialize_tables()

    def _initialize_tables(self) -> None:
        """Initialize all database tables on service creation."""
        logger.info("Initializing database tables")
        with self._db as conn:
            # Initialize food log table
            create_food_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self._FOOD_LOG_TABLE_NAME} (
                name VARCHAR,
                protein VARCHAR,
                carbs VARCHAR,
                fats VARCHAR,
                comment VARCHAR,
                datetime TIMESTAMP
            )
            """
            # Initialize drug log table
            create_drug_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self._DRUG_LOG_TABLE_NAME} (
                name VARCHAR,
                dosage INT,
                datetime TIMESTAMP
            )
            """
            # Initialize message log table
            create_message_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self._MESSAGE_LOG_TABLE_NAME} (
                user_id INT,
                message_type VARCHAR,
                content TEXT,
                response TEXT,
                datetime TIMESTAMP
            )
            """
            conn.execute(create_food_table_query)
            conn.execute(create_drug_table_query)
            conn.execute(create_message_table_query)
            conn.commit()

    def add_food_log_entry(self, entry: FoodLogEntry) -> None:
        logger.info(f"Adding food log entry: {entry}")
        with self._db as conn:
            insert_query = f"""
            INSERT INTO {self._FOOD_LOG_TABLE_NAME} (name, protein, carbs, fats, comment, datetime)
            VALUES (
                '{entry.name}',
                '{entry.protein}',
                '{entry.carbs}',
                '{entry.fats}',
                '{entry.comment}',
                CURRENT_TIMESTAMP
            )
            """
            conn.execute(insert_query)
            conn.commit()

    def add_drug_log_entry(self, entry: DrugLogEntry) -> None:
        logger.info(f"Adding drug log entry: {entry}")
        with self._db as conn:
            insert_query = f"""
            INSERT INTO {self._DRUG_LOG_TABLE_NAME} (name, dosage, datetime)
            VALUES ('{entry.drug_name}', {entry.dosage}, CURRENT_TIMESTAMP)
            """
            conn.execute(insert_query)
            conn.commit()

    def list_food_logs(self, limit: Optional[int] = None) -> list[FoodLogEntry]:
        logger.info("Listing food logs")
        with self._db as conn:
            query = f"""SELECT
             name, protein, carbs, fats, comment, datetime
            FROM {self._FOOD_LOG_TABLE_NAME} ORDER BY datetime DESC"""
            if limit is not None:
                query += f" LIMIT {limit}"
            for row in conn.execute(query).fetchall():
                yield FoodLogEntry(*row)

    def list_drug_logs(self, limit: Optional[int] = None) -> list[DrugLogEntry]:
        logger.info("Listing drug logs")
        with self._db as conn:
            query = f"""SELECT
             name, dosage, datetime
            FROM {self._DRUG_LOG_TABLE_NAME} ORDER BY datetime DESC"""
            if limit is not None:
                query += f" LIMIT {limit}"
            for row in conn.execute(query).fetchall():
                yield DrugLogEntry(*row)

    def add_message_entry(self, entry: MessageEntry) -> None:
        logger.info(f"Adding message log entry: {entry}")
        with self._db as conn:
            insert_query = f"""
            INSERT INTO {self._MESSAGE_LOG_TABLE_NAME} (user_id, message_type, content, response, datetime)
            VALUES (
                {entry.user_id},
                '{entry.message_type.value}',
                ?,
                ?,
                CURRENT_TIMESTAMP
            )
            """
            conn.execute(insert_query, (entry.content, entry.response))
            conn.commit()

    def list_message_logs(self, user_id: Optional[int] = None, limit: Optional[int] = None) -> list[MessageEntry]:
        logger.info(f"Listing message logs for user_id: {user_id}")
        with self._db as conn:
            query = f"""SELECT
             user_id, message_type, content, response, datetime
            FROM {self._MESSAGE_LOG_TABLE_NAME}"""

            conditions = []
            if user_id is not None:
                conditions.append(f"user_id = {user_id}")

            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"

            query += " ORDER BY datetime DESC"

            if limit is not None:
                query += f" LIMIT {limit}"

            for row in conn.execute(query).fetchall():
                user_id, message_type_str, content, response, datetime_str = row
                message_type = MessageType(message_type_str)
                yield MessageEntry(user_id, message_type, content, response, datetime_str)

    @property
    def _db(self) -> sqlite3.Connection:
        db_file = self.out_dir / "bot.db"
        return sqlite3.connect(db_file.as_posix())
