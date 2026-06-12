import unittest

from dashboard.api_client import ApiClientError, fetch_review_insights


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict[str, object]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class DashboardApiClientTests(unittest.TestCase):
    def test_fetch_review_insights_posts_non_empty_reviews(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(
                200,
                {
                    "review_count": 1,
                    "overall_sentiment": "positive",
                    "sentiment_breakdown": {"positive": 1, "neutral": 0, "negative": 0},
                    "positive_themes": ["quality"],
                    "negative_themes": [],
                    "common_complaints": [],
                    "summary": "A useful summary.",
                    "suggested_action_items": ["Keep monitoring reviews."],
                },
            )

        result = fetch_review_insights(
            [" Great product! ", "", "   "],
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["overall_sentiment"], "positive")
        self.assertEqual(
            calls,
            [
                {
                    "url": "http://localhost:8000/insights",
                    "json": {"reviews": [{"text": "Great product!"}]},
                    "timeout": 10,
                }
            ],
        )

    def test_fetch_review_insights_rejects_empty_input(self) -> None:
        with self.assertRaisesRegex(ApiClientError, "Enter at least one review"):
            fetch_review_insights([" ", ""], post=lambda **_: FakeResponse(200, {}))

    def test_fetch_review_insights_wraps_backend_errors(self) -> None:
        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            return FakeResponse(500, {"detail": "Server error"})

        with self.assertRaisesRegex(ApiClientError, "Could not analyze reviews"):
            fetch_review_insights(["Good product"], post=fake_post)


if __name__ == "__main__":
    unittest.main()
