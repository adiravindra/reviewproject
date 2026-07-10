import sqlite3
from pathlib import Path

from backend.app.settings import Settings


def connect(path: Path | None = None) -> sqlite3.Connection:
    database_path = path or Settings.from_env().db_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    initialize(connection)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS website_analysis_runs (
            id TEXT PRIMARY KEY,
            completed_at TEXT NOT NULL,
            source_url TEXT NOT NULL,
            entity_name TEXT,
            review_count INTEGER NOT NULL CHECK (review_count >= 0),
            average_rating REAL,
            overall_sentiment TEXT NOT NULL,
            executive_summary TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_website_analysis_runs_completed_at
        ON website_analysis_runs (completed_at DESC)
        """
    )
    connection.commit()
