"""Exercise local SQLite history persistence with isolated real databases."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import backend.app.history as history_module
from backend.app.errors import AnalysisError
from backend.app.history import HistoryStore
from backend.app.models import AnalysisResponse, AgentInsights, Metrics, Review, SourceInfo


def make_report(*, demo: bool = False, title: str = "Product reviews") -> AnalysisResponse:
    """Build a complete validated report suitable for repository behavior tests."""

    source = SourceInfo(
        url=None if demo else "https://example.test/products/widget",
        title=title,
        extractor="demo" if demo else "json_ld",
        is_demo=demo,
    )
    return AnalysisResponse(
        source=source,
        metrics=Metrics(
            review_count=2,
            rated_count=2,
            average_rating=4.0,
            positive_percentage=50.0,
            sentiment_counts={"positive": 1, "neutral": 1, "negative": 0},
            rating_distribution={"1": 0, "2": 0, "3": 1, "4": 0, "5": 1},
        ),
        insights=AgentInsights(
            summary="Customers appreciate the product while noting one small concern.",
            overall_sentiment="mixed",
            themes=[
                {
                    "name": "Usability",
                    "description": "Customers discuss straightforward daily use.",
                    "mentions": 2,
                    "sentiment": "positive",
                }
            ],
            strengths=["Easy to use"],
            weaknesses=["Needs more polish"],
            actions=["Improve the setup guidance"],
            review_sentiments=[
                {"review_id": "r1", "sentiment": "positive"},
                {"review_id": "r2", "sentiment": "neutral"},
            ],
        ),
        reviews=[
            Review(id="r1", text="Very easy to use.", rating=5, date="2026-07-01"),
            Review(id="r2", text="Good, but setup took time.", rating=3, date=None),
        ],
    )


class HistoryStoreTests(unittest.TestCase):
    """Verify persisted reports and their deliberately limited history summaries."""

    def setUp(self):
        """Create an isolated database path for every real SQLite test."""

        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "nested" / "history.db"
        self.store = HistoryStore(self.db_path)

    def tearDown(self):
        """Remove the temporary database and its parent directories."""

        self.temporary_directory.cleanup()

    def test_first_operation_creates_parent_database_and_schema(self):
        """Initialize storage lazily when a public read operation is first used."""

        self.assertFalse(self.db_path.parent.exists())

        self.assertEqual(self.store.list_runs(), [])

        self.assertTrue(self.db_path.is_file())
        with closing(sqlite3.connect(self.db_path)) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(analysis_history)").fetchall()
            }
        self.assertEqual(
            columns,
            {
                "id",
                "created_at",
                "source_url",
                "source_title",
                "extractor",
                "is_demo",
                "review_count",
                "overall_sentiment",
                "report_json",
            },
        )

    def test_live_report_round_trips_and_restores_history_id(self):
        """Persist a validated live report and identify the restored saved row."""

        report = make_report()
        run_id = self.store.save(report)

        restored = self.store.get(run_id)

        self.assertIsNotNone(restored)
        self.assertEqual(restored.history_id, run_id)
        self.assertEqual(restored.model_copy(update={"history_id": None}), report)

    def test_demo_report_preserves_url_less_demo_provenance(self):
        """Keep the demo source properties valid after persistence and restoration."""

        run_id = self.store.save(make_report(demo=True))

        restored = self.store.get(run_id)

        self.assertIsNotNone(restored)
        self.assertIsNone(restored.source.url)
        self.assertEqual(restored.source.extractor, "demo")
        self.assertTrue(restored.source.is_demo)

    def test_two_saves_list_newest_first_with_safe_summary_values(self):
        """Expose newest-first rows containing only the history-list summary data."""

        first_id = self.store.save(make_report(title="First report"))
        second_id = self.store.save(make_report(demo=True, title="Demo report"))

        items = self.store.list_runs()

        self.assertEqual([item.id for item in items], [second_id, first_id])
        self.assertEqual(items[0].source_title, "Demo report")
        self.assertIsNone(items[0].source_url)
        self.assertEqual(items[0].extractor, "demo")
        self.assertTrue(items[0].is_demo)
        self.assertEqual(items[0].review_count, 2)
        self.assertEqual(items[0].overall_sentiment, "mixed")
        self.assertEqual(items[1].source_url, "https://example.test/products/widget")

    def test_list_runs_honors_a_bounded_limit(self):
        """Return only the requested number of newest history summary rows."""

        self.store.save(make_report(title="First report"))
        latest_id = self.store.save(make_report(title="Latest report"))

        items = self.store.list_runs(limit=1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, latest_id)

    def test_missing_id_returns_none(self):
        """Treat a missing local history row as an ordinary absent result."""

        self.assertIsNone(self.store.get(404))

    def test_malformed_stored_json_maps_to_a_safe_history_error(self):
        """Hide corrupt local storage details when a saved report cannot validate."""

        self.store.list_runs()
        marker = "raw-corrupt-json-marker"
        with closing(sqlite3.connect(self.db_path)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO analysis_history (
                        created_at, source_url, source_title, extractor, is_demo,
                        review_count, overall_sentiment, report_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("2026-07-17T00:00:00+00:00", None, "Bad", "demo", 1, 2, "mixed", marker),
                )
                run_id = cursor.lastrowid

        with self.assertRaises(AnalysisError) as raised:
            self.store.get(run_id)

        self.assertEqual(raised.exception.code, "history_failed")
        self.assertEqual(
            raised.exception.public_message, "Local analysis history could not be updated."
        )
        self.assertNotIn(marker, str(raised.exception))

    def test_insert_failure_is_safe_and_rolls_back_without_partial_row(self):
        """Map a SQLite insert failure and leave the prior committed history intact."""

        existing_id = self.store.save(make_report(title="Committed report"))
        original_connect = sqlite3.connect

        def deny_insert_connection(*args, **kwargs):
            """Return a real connection that refuses only row insertion."""

            connection = original_connect(*args, **kwargs)

            def deny_inserts(action, _arg1, _arg2, _database, _trigger):
                """Reject SQLite INSERT operations while allowing schema checks."""

                return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_INSERT else sqlite3.SQLITE_OK

            connection.set_authorizer(deny_inserts)
            return connection

        with patch.object(history_module.sqlite3, "connect", side_effect=deny_insert_connection):
            with self.assertRaises(AnalysisError) as raised:
                self.store.save(make_report(title="Rejected report"))

        self.assertEqual(raised.exception.code, "history_failed")
        self.assertNotIn("not authorized", str(raised.exception))
        self.assertEqual([item.id for item in self.store.list_runs()], [existing_id])

    def test_stored_json_clears_history_id_and_contains_no_secret_marker(self):
        """Persist only report data, resetting the storage-specific row identifier."""

        report = make_report().model_copy(update={"history_id": 9182})
        run_id = self.store.save(report)
        marker = "groq-secret-marker"

        with closing(sqlite3.connect(self.db_path)) as connection:
            stored_json = connection.execute(
                "SELECT report_json FROM analysis_history WHERE id = ?", (run_id,)
            ).fetchone()[0]

        self.assertIn('"history_id":null', stored_json)
        self.assertNotIn(marker, stored_json)


if __name__ == "__main__":
    unittest.main()
