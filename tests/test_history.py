import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from tests.factories import complete_response


class WebsiteHistoryTests(unittest.TestCase):
    def test_fresh_database_creates_only_active_website_table(self) -> None:
        from backend.app.services.db import connect

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            with closing(connect(path)) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }

        self.assertIn("website_analysis_runs", tables)
        self.assertNotIn("analysis_runs", tables)

    def test_save_list_and_get_round_trip_complete_validated_payload(self) -> None:
        from backend.app.services.history import (
            get_website_analysis,
            list_website_analyses,
            save_website_analysis,
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            older = complete_response(run_id="older", completed_at="2026-07-10T14:00:00Z")
            newer = complete_response(run_id="newer", completed_at="2026-07-10T15:00:00Z")
            save_website_analysis(older, path)
            save_website_analysis(newer, path)

            history = list_website_analyses(limit=1, path=path)
            stored = get_website_analysis("newer", path)

        self.assertEqual([item.id for item in history.items], ["newer"])
        self.assertEqual(history.items[0].entity_name, "Example Product")
        self.assertEqual(history.items[0].review_count, 2)
        self.assertEqual(stored, newer)

    def test_existing_legacy_table_and_rows_are_left_untouched(self) -> None:
        from backend.app.services.db import connect

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            legacy = sqlite3.connect(path)
            legacy.execute("CREATE TABLE analysis_runs (id TEXT PRIMARY KEY, payload_json TEXT)")
            legacy.execute("INSERT INTO analysis_runs VALUES ('legacy', '{}')")
            legacy.commit()
            legacy.close()

            with closing(connect(path)) as connection:
                legacy_rows = connection.execute("SELECT id FROM analysis_runs").fetchall()
                active_table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='website_analysis_runs'"
                ).fetchone()

        self.assertEqual([row[0] for row in legacy_rows], ["legacy"])
        self.assertIsNotNone(active_table)

    def test_duplicate_run_is_not_silently_replaced(self) -> None:
        from backend.app.services.history import save_website_analysis

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            response = complete_response()
            save_website_analysis(response, path)
            with self.assertRaises(sqlite3.IntegrityError):
                save_website_analysis(response, path)


if __name__ == "__main__":
    unittest.main()
