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


if __name__ == "__main__":
    unittest.main()
