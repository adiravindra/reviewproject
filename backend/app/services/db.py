import os
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path("data/reviewinsight.db")


# The database path can be changed with REVIEWINSIGHT_DB_PATH.
def db_path() -> Path:
    configured_path = os.getenv("REVIEWINSIGHT_DB_PATH")
    return Path(configured_path) if configured_path else DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    # Row objects let the history code read columns by name.
    connection.row_factory = sqlite3.Row
    initialize(connection)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            input_type TEXT NOT NULL,
            review_count INTEGER NOT NULL,
            sentiment_counts_json TEXT NOT NULL,
            topic_counts_json TEXT NOT NULL,
            urgency_counts_json TEXT NOT NULL,
            average_urgency REAL NOT NULL,
            overall_summary TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.commit()
