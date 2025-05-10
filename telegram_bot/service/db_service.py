import sqlite3
from dataclasses import dataclass
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


class DBService:
    _FOOD_LOG_TABLE_NAME = "food_log"
    _DRUG_LOG_TABLE_NAME = "drug_log"

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir

    def add_food_log_entry(self, entry: FoodLogEntry) -> None:
        logger.info(f"Adding food log entry: {entry}")
        with self._db as conn:
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self._FOOD_LOG_TABLE_NAME} (
                name VARCHAR,
                protein VARCHAR,
                carbs VARCHAR,
                fats VARCHAR,
                comment VARCHAR,
                datetime TIMESTAMP
            )
            """
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
            conn.execute(create_table_query)
            conn.execute(insert_query)
            conn.commit()

    def add_drug_log_entry(self, entry: DrugLogEntry) -> None:
        logger.info(f"Adding drug log entry: {entry}")
        with self._db as conn:
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self._DRUG_LOG_TABLE_NAME} (
                name VARCHAR,
                dosage INT,
                datetime TIMESTAMP
            )
            """
            insert_query = f"""
            INSERT INTO {self._DRUG_LOG_TABLE_NAME} (name, dosage, datetime)
            VALUES ('{entry.drug_name}', {entry.dosage}, CURRENT_TIMESTAMP)
            """
            conn.execute(create_table_query)
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

    @property
    def _db(self) -> sqlite3.Connection:
        db_file = self.out_dir / "bot.db"
        return sqlite3.connect(db_file.as_posix())
