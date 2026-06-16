import unittest
import warnings

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)
from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


class ReviewInsightApiTests(unittest.TestCase):
    def test_health_check_returns_project_status(self) -> None:
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "project": "ReviewInsight", "version": "0.1.0"},
        )

    def test_single_review_input_cleans_review_text(self) -> None:
        response = client.post(
            "/reviews",
            json={"text": "  The product is great, but shipping was slow.  "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reviews"][0]["text"], "The product is great, but shipping was slow.")
        self.assertEqual(response.json()["count"], 1)

    def test_multiple_review_input_removes_empty_and_duplicate_reviews(self) -> None:
        response = client.post(
            "/reviews/batch",
            json={
                "reviews": [
                    {"text": "Great product!"},
                    {"text": "   "},
                    {"text": "Great product!"},
                    {"text": "Support was slow."},
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(
            [review["text"] for review in response.json()["reviews"]],
            ["Great product!", "Support was slow."],
        )

    def test_empty_review_batch_returns_validation_error(self) -> None:
        response = client.post("/reviews/batch", json={"reviews": [{"text": "   "}]})

        self.assertEqual(response.status_code, 422)
        self.assertIn("At least one non-empty review is required.", response.text)

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

    def test_existing_analyze_endpoint_still_returns_legacy_shape(self) -> None:
        response = client.post("/analyze", json={"text": "Shipping was slow but support was helpful."})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json().keys()),
            {"sentiment", "topic", "urgency", "summary"},
        )

    def test_api_analyze_single_returns_high_urgency_structured_review_result(self) -> None:
        response = client.post(
            "/api/analyze/single",
            json={
                "text": "The app crashes every time I log in, payment failed, and I urgently need help."
            },
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(body.keys()),
            {"text", "sentiment", "topics", "urgency_score", "urgency_label", "summary"},
        )
        self.assertEqual(body["text"], "The app crashes every time I log in, payment failed, and I urgently need help.")
        self.assertEqual(body["sentiment"], "negative")
        self.assertIn("bugs/crashes", body["topics"])
        self.assertIn("login/auth", body["topics"])
        self.assertIn("pricing", body["topics"])
        self.assertGreaterEqual(body["urgency_score"], 0.67)
        self.assertLessEqual(body["urgency_score"], 1.0)
        self.assertEqual(body["urgency_label"], "high")
        self.assertTrue(body["summary"].endswith("."))

    def test_api_analyze_single_returns_low_urgency_positive_result(self) -> None:
        response = client.post(
            "/api/analyze/single",
            json={"text": "The interface is easy to use and support was helpful."},
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["sentiment"], "positive")
        self.assertIn("UI/UX", body["topics"])
        self.assertIn("support", body["topics"])
        self.assertEqual(body["urgency_label"], "low")
        self.assertGreaterEqual(body["urgency_score"], 0.0)
        self.assertLess(body["urgency_score"], 0.34)

    def test_api_analyze_single_rejects_empty_text(self) -> None:
        response = client.post("/api/analyze/single", json={"text": "   "})

        self.assertEqual(response.status_code, 422)
        self.assertIn("At least one non-empty review is required.", response.text)

    def test_analysis_review_endpoint_returns_full_analysis_and_saves_history(self) -> None:
        response = client.post(
            "/analysis/review",
            json={
                "text": "The product quality is great but shipping was late.",
                "source": "manual",
            },
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["source"], "manual")
        self.assertEqual(body["review_count"], 1)
        self.assertEqual(body["reviews"][0]["text"], "The product quality is great but shipping was late.")
        self.assertIn(body["reviews"][0]["sentiment"], {"positive", "neutral", "negative"})
        self.assertIn(body["reviews"][0]["urgency"], {"low", "medium", "high"})
        self.assertIn("summary", body)
        self.assertIn("metrics", body)
        self.assertIn("id", body)

        history_response = client.get("/history?limit=5")
        self.assertEqual(history_response.status_code, 200)
        self.assertTrue(
            any(item["id"] == body["id"] for item in history_response.json()["items"])
        )

    def test_analysis_reviews_endpoint_accepts_api_batch_payload(self) -> None:
        response = client.post(
            "/analysis/reviews",
            json={
                "source": "api",
                "reviews": [
                    {"text": "Support was helpful and fast."},
                    {"text": "The setup was confusing and difficult."},
                ],
            },
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["source"], "api")
        self.assertEqual(body["review_count"], 2)
        self.assertEqual(len(body["reviews"]), 2)
        self.assertEqual(
            sum(body["metrics"]["sentiment_breakdown"].values()),
            2,
        )
        self.assertIn("average_urgency", body["metrics"])
        self.assertGreaterEqual(body["metrics"]["average_urgency"], 1.0)
        self.assertIn("most_urgent_reviews", body)
        self.assertGreaterEqual(len(body["most_urgent_reviews"]), 1)

    def test_analysis_csv_endpoint_extracts_review_column(self) -> None:
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

    def test_analysis_run_detail_and_review_detail_can_be_loaded_from_history(self) -> None:
        create_response = client.post(
            "/analysis/reviews",
            json={
                "source": "api",
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
            "/analysis/review",
            json={"text": "Helpful support and fast delivery.", "source": "manual"},
        )
        created_run = create_response.json()

        latest_response = client.get("/analysis/latest")

        self.assertEqual(latest_response.status_code, 200)
        self.assertEqual(latest_response.json()["id"], created_run["id"])

    def test_dashboard_metrics_endpoint_returns_history_rollup(self) -> None:
        client.post("/analysis/review", json={"text": "Excellent support and easy setup."})

        response = client.get("/dashboard/metrics")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(body["total_runs"], 1)
        self.assertGreaterEqual(body["total_reviews"], 1)
        self.assertIn("sentiment_breakdown", body)
        self.assertIn("urgency_breakdown", body)


if __name__ == "__main__":
    unittest.main()
