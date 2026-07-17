"""Persist validated analysis reports in local SQLite history storage."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from backend.app.errors import AnalysisError
from backend.app.models import AnalysisResponse, HistoryItem


DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "review_history.db"
"""Locate the git-ignored local database used for saved analysis history."""

_MAX_HISTORY_LIMIT = 50
_HISTORY_ERROR_MESSAGE = "Local analysis history could not be updated."
_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source_url TEXT,
    source_title TEXT NOT NULL,
    extractor TEXT NOT NULL,
    is_demo INTEGER NOT NULL,
    review_count INTEGER NOT NULL,
    overall_sentiment TEXT NOT NULL,
    report_json TEXT NOT NULL
)
"""


class HistoryStore:
    """Store and retrieve validated analysis reports using local SQLite transactions."""

    def __init__(self, db_path: Path = DEFAULT_HISTORY_PATH):
        """Remember the database path without touching the filesystem yet."""

        self.db_path = Path(db_path)

    def save(self, report: AnalysisResponse) -> int:
        """Atomically save one validated report and return its generated row identifier."""

        try:
            report_json = report.model_copy(update={"history_id": None}).model_dump_json()
            created_at = datetime.now(timezone.utc).isoformat()
            source_url = str(report.source.url) if report.source.url is not None else None
            with self._connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO analysis_history (
                        created_at, source_url, source_title, extractor, is_demo,
                        review_count, overall_sentiment, report_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at,
                        source_url,
                        report.source.title,
                        report.source.extractor,
                        int(report.source.is_demo),
                        report.metrics.review_count,
                        report.insights.overall_sentiment,
                        report_json,
                    ),
                )
                return cursor.lastrowid
        except (OSError, sqlite3.Error, TypeError, ValueError, ValidationError):
            raise AnalysisError("history_failed", _HISTORY_ERROR_MESSAGE) from None

    def list_runs(self, limit: int = _MAX_HISTORY_LIMIT) -> list[HistoryItem]:
        """Return newest-first safe summaries of the locally saved analysis runs."""

        try:
            bounded_limit = max(0, min(limit, _MAX_HISTORY_LIMIT))
            with self._connection() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        id, created_at, source_title, source_url, extractor, is_demo,
                        review_count, overall_sentiment
                    FROM analysis_history
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (bounded_limit,),
                ).fetchall()
            return [
                HistoryItem(
                    id=row[0],
                    created_at=row[1],
                    source_title=row[2],
                    source_url=row[3],
                    extractor=row[4],
                    is_demo=bool(row[5]),
                    review_count=row[6],
                    overall_sentiment=row[7],
                )
                for row in rows
            ]
        except (OSError, sqlite3.Error, TypeError, ValueError, ValidationError):
            raise AnalysisError("history_failed", _HISTORY_ERROR_MESSAGE) from None

    def get(self, run_id: int) -> AnalysisResponse | None:
        """Restore one validated report, or return ``None`` when its row is absent."""

        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT report_json FROM analysis_history WHERE id = ?", (run_id,)
                ).fetchone()
            if row is None:
                return None
            report = AnalysisResponse.model_validate_json(row[0])
            return report.model_copy(update={"history_id": run_id})
        except (OSError, sqlite3.Error, TypeError, ValueError, ValidationError):
            raise AnalysisError("history_failed", _HISTORY_ERROR_MESSAGE) from None

    def _ensure_parent_directory(self) -> None:
        """Create the local database directory only when an operation needs it."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connection(self):
        """Yield one initialized transactional connection and always close it afterward."""

        self._ensure_parent_directory()
        connection = sqlite3.connect(self.db_path)
        try:
            with connection:
                connection.execute(_SCHEMA)
                yield connection
        finally:
            connection.close()
