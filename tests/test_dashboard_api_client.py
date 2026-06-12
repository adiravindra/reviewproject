import unittest

from dashboard.api_client import (
    ApiClientError,
    fetch_health,
    fetch_keywords,
    fetch_review_insights,
    fetch_sentiment,
    fetch_summary,
    submit_review_batch,
    submit_single_review,
)


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
    def test_fetch_health_calls_health_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_get(url: str, timeout: int) -> FakeResponse:
            calls.append({"url": url, "timeout": timeout})
            return FakeResponse(200, {"status": "ok", "project": "ReviewInsight", "version": "0.1.0"})

        result = fetch_health(api_base_url="http://localhost:8000/", get=fake_get)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(calls, [{"url": "http://localhost:8000/health", "timeout": 10}])

    def test_submit_single_review_posts_to_reviews_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(200, {"count": 1, "reviews": [{"text": "Great product!"}]})

        result = submit_single_review(
            "  Great product!  ",
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["count"], 1)
        self.assertEqual(
            calls,
            [{"url": "http://localhost:8000/reviews", "json": {"text": "Great product!"}, "timeout": 10}],
        )

    def test_submit_review_batch_posts_to_reviews_batch_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(200, {"count": 2, "reviews": [{"text": "Great"}, {"text": "Slow shipping"}]})

        result = submit_review_batch(
            [" Great ", "", "Slow shipping"],
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["count"], 2)
        self.assertEqual(
            calls,
            [
                {
                    "url": "http://localhost:8000/reviews/batch",
                    "json": {"reviews": [{"text": "Great"}, {"text": "Slow shipping"}]},
                    "timeout": 10,
                }
            ],
        )

    def test_fetch_sentiment_posts_to_sentiment_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(200, {"text": "Helpful support", "sentiment": "positive", "score": 1})

        result = fetch_sentiment(
            " Helpful support ",
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["sentiment"], "positive")
        self.assertEqual(
            calls,
            [{"url": "http://localhost:8000/sentiment", "json": {"text": "Helpful support"}, "timeout": 10}],
        )

    def test_fetch_keywords_posts_to_keywords_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(200, {"keywords": [{"keyword": "shipping", "count": 2}], "themes": []})

        result = fetch_keywords(
            ["Shipping was slow", "Shipping improved"],
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["keywords"][0]["keyword"], "shipping")
        self.assertEqual(calls[0]["url"], "http://localhost:8000/keywords")

    def test_fetch_summary_posts_to_summarize_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(200, {"summary": "Summary of 2 reviews.", "review_count": 2})

        result = fetch_summary(
            ["Easy setup", "Slow support"],
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["review_count"], 2)
        self.assertEqual(calls[0]["url"], "http://localhost:8000/summarize")

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

    def test_batch_helpers_reject_empty_input(self) -> None:
        with self.assertRaisesRegex(ApiClientError, "Enter at least one review"):
            fetch_review_insights([" ", ""], post=lambda **_: FakeResponse(200, {}))

    def test_fetch_review_insights_wraps_backend_errors(self) -> None:
        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            return FakeResponse(500, {"detail": "Server error"})

        with self.assertRaisesRegex(ApiClientError, "Could not analyze reviews"):
            fetch_review_insights(["Good product"], post=fake_post)


if __name__ == "__main__":
    unittest.main()
