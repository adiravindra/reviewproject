import os
import sqlite3
import tempfile
import unittest
import warnings
from contextlib import closing

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)
from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


class ReviewInsightApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "reviewinsight.db")
        self.previous_db_path = os.environ.get("REVIEWINSIGHT_DB_PATH")
        os.environ["REVIEWINSIGHT_DB_PATH"] = self.db_path

    def tearDown(self) -> None:
        if self.previous_db_path is None:
            os.environ.pop("REVIEWINSIGHT_DB_PATH", None)
        else:
            os.environ["REVIEWINSIGHT_DB_PATH"] = self.previous_db_path
        self.temp_dir.cleanup()

    def test_health_check_returns_project_status(self) -> None:
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "project": "ReviewInsight", "version": "0.1.0"},
        )

    def test_sentiment_endpoint_returns_rule_based_sentiment(self) -> None:
        response = client.post("/sentiment", json={"text": "I love the fast delivery and excellent quality."})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sentiment"], "positive")
        self.assertGreater(response.json()["score"], 0)

    def test_keywords_endpoint_extracts_recurring_themes(self) -> None:
        response = client.post(
            "/keywords",
            json={
                "reviews": [
                    {"text": "Shipping was slow and the package arrived late."},
                    {"text": "Slow shipping, but the package quality was good."},
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        keywords = [item["keyword"] for item in response.json()["keywords"]]
        self.assertIn("shipping", keywords)
        self.assertIn("slow", keywords)

    def test_summarize_endpoint_summarizes_multiple_reviews(self) -> None:
        response = client.post(
            "/summarize",
            json={
                "reviews": [
                    {"text": "The app is easy to use."},
                    {"text": "Support answered slowly."},
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["review_count"], 2)
        self.assertIn("2 reviews", response.json()["summary"])

    def test_insights_endpoint_returns_business_insights(self) -> None:
        response = client.post(
            "/insights",
            json={
                "reviews": [
                    {"text": "I love the product quality and fast delivery."},
                    {"text": "Shipping was slow and support did not respond."},
                    {"text": "The price is fair and setup is easy."},
                ]
            },
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn(body["overall_sentiment"], {"positive", "neutral", "negative", "mixed"})
        self.assertIsInstance(body["positive_themes"], list)
        self.assertIsInstance(body["negative_themes"], list)
        self.assertIsInstance(body["common_complaints"], list)
        self.assertIsInstance(body["suggested_action_items"], list)
        self.assertGreaterEqual(body["review_count"], 1)

    def test_analysis_single_returns_unsaved_single_review_result_by_default(self) -> None:
        response = client.post(
            "/analysis/single",
            json={"text": "The interface is easy to use and support was helpful."},
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(body.keys()),
            {
                "text",
                "sentiment",
                "topics",
                "urgency_score",
                "urgency_label",
                "summary",
                "saved_to_history",
                "run_id",
                "run",
            },
        )
        self.assertEqual(body["sentiment"], "positive")
        self.assertIn("UI/UX", body["topics"])
        self.assertIn("support", body["topics"])
        self.assertEqual(body["urgency_label"], "low")
        self.assertFalse(body["saved_to_history"])
        self.assertIsNone(body["run_id"])
        self.assertIsNone(body["run"])
        self.assertEqual(client.get("/analysis/runs").json()["items"], [])

    def test_analysis_single_can_save_review_to_sqlite_history(self) -> None:
        response = client.post(
            "/analysis/single",
            json={
                "text": "The app crashes every time I log in, payment failed, and I urgently need help.",
                "save_to_history": True,
            },
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["saved_to_history"])
        self.assertIsInstance(body["run_id"], str)
        self.assertEqual(body["run"]["id"], body["run_id"])
        self.assertEqual(body["run"]["source"], "single")
        self.assertEqual(body["run"]["review_count"], 1)
        self.assertEqual(body["run"]["reviews"][0]["urgency"], "high")

        runs_response = client.get("/analysis/runs")
        self.assertEqual(runs_response.status_code, 200)
        self.assertEqual(runs_response.json()["items"][0]["id"], body["run_id"])
        self.assertEqual(runs_response.json()["items"][0]["input_type"], "single")

        with closing(sqlite3.connect(self.db_path)) as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'analysis_runs'"
            ).fetchall()
            row_count = connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]

        self.assertEqual(tables, [("analysis_runs",)])
        self.assertEqual(row_count, 1)

    def test_analysis_single_rejects_empty_text(self) -> None:
        response = client.post("/analysis/single", json={"text": "   "})

        self.assertEqual(response.status_code, 422)
        self.assertIn("At least one non-empty review is required.", response.text)

    def test_analysis_batch_saves_full_run_to_sqlite_history(self) -> None:
        response = client.post(
            "/analysis/batch",
            json={
                "reviews": [
                    {"text": "Support was helpful and fast."},
                    {"text": "The setup was confusing and difficult."},
                ],
            },
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["source"], "batch")
        self.assertEqual(body["review_count"], 2)
        self.assertEqual(len(body["reviews"]), 2)
        self.assertEqual(sum(body["metrics"]["sentiment_breakdown"].values()), 2)
        self.assertIn("average_urgency", body["metrics"])
        self.assertIn("most_urgent_reviews", body)

        runs_response = client.get("/analysis/runs")
        self.assertEqual(runs_response.status_code, 200)
        self.assertEqual(runs_response.json()["items"][0]["id"], body["id"])
        self.assertEqual(runs_response.json()["items"][0]["input_type"], "batch")

    def test_analysis_csv_endpoint_extracts_review_column_and_saves_run(self) -> None:
        csv_content = "review,rating\nFast delivery and great quality,5\nShipping was late and slow,2\n"

        response = client.post(
            "/analysis/csv",
            files={"file": ("reviews.csv", csv_content, "text/csv")},
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["source"], "csv")
        self.assertEqual(body["review_count"], 2)
        self.assertEqual(len(body["reviews"]), 2)
        self.assertEqual(client.get("/analysis/runs").json()["items"][0]["id"], body["id"])

    def test_analysis_run_detail_and_review_detail_can_be_loaded_from_sqlite(self) -> None:
        create_response = client.post(
            "/analysis/batch",
            json={
                "reviews": [
                    {"text": "Excellent support and easy setup."},
                    {"text": "The package arrived broken and I need an urgent refund."},
                ],
            },
        )
        created_run = create_response.json()

        run_response = client.get(f"/analysis/runs/{created_run['id']}")
        self.assertEqual(run_response.status_code, 200)
        self.assertEqual(run_response.json()["id"], created_run["id"])

        detail_response = client.get(f"/analysis/runs/{created_run['id']}/reviews/1")
        detail_body = detail_response.json()
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_body["run_id"], created_run["id"])
        self.assertEqual(detail_body["review_index"], 1)
        self.assertEqual(detail_body["review"]["urgency"], "high")

    def test_latest_analysis_run_returns_most_recent_saved_run(self) -> None:
        create_response = client.post(
            "/analysis/single",
            json={"text": "Helpful support and fast delivery.", "save_to_history": True},
        )
        created_run = create_response.json()["run"]

        latest_response = client.get("/analysis/latest")

        self.assertEqual(latest_response.status_code, 200)
        self.assertEqual(latest_response.json()["id"], created_run["id"])

    def test_old_duplicate_routes_are_no_longer_registered(self) -> None:
        old_post_routes = [
            "/reviews",
            "/reviews/batch",
            "/analyze",
            "/api/analyze/single",
            "/analysis/review",
            "/analysis/reviews",
        ]

        for route in old_post_routes:
            with self.subTest(route=route):
                self.assertEqual(client.post(route, json={"text": "Great product"}).status_code, 404)

        self.assertEqual(client.get("/history").status_code, 404)
        self.assertEqual(client.get("/dashboard/metrics").status_code, 404)


if __name__ == "__main__":
    unittest.main()
