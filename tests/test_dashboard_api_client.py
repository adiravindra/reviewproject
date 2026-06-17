import unittest

from dashboard.api_client import (
    ApiClientError,
    analyze_reviews_csv,
    analyze_reviews_from_api_payload,
    analyze_single_review,
    fetch_analysis_run,
    fetch_analysis_runs,
    fetch_health,
    fetch_keywords,
    fetch_latest_analysis,
    fetch_review_detail,
    fetch_review_insights,
    fetch_sentiment,
    fetch_summary,
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

    def test_analyze_single_review_posts_to_analysis_single_without_save_by_default(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(
                200,
                {
                    "text": "Great quality",
                    "sentiment": "positive",
                    "topics": [],
                    "urgency_score": 0.0,
                    "urgency_label": "low",
                    "summary": "This review says: Great quality.",
                    "saved_to_history": False,
                    "run_id": None,
                    "run": None,
                },
            )

        result = analyze_single_review(
            " Great quality ",
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["sentiment"], "positive")
        self.assertEqual(
            calls,
            [
                {
                    "url": "http://localhost:8000/analysis/single",
                    "json": {"text": "Great quality", "save_to_history": False},
                    "timeout": 10,
                }
            ],
        )

    def test_analyze_single_review_can_request_history_save(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(
                200,
                {
                    "text": "Great quality",
                    "sentiment": "positive",
                    "topics": [],
                    "urgency_score": 0.0,
                    "urgency_label": "low",
                    "summary": "This review says: Great quality.",
                    "saved_to_history": True,
                    "run_id": "run-1",
                    "run": {"id": "run-1"},
                },
            )

        result = analyze_single_review(
            "Great quality",
            save_to_history=True,
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["run_id"], "run-1")
        self.assertEqual(calls[0]["url"], "http://localhost:8000/analysis/single")
        self.assertEqual(calls[0]["json"]["save_to_history"], True)

    def test_analyze_reviews_from_api_payload_posts_to_analysis_batch_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse(200, {"id": "run-2", "review_count": 2, "reviews": [], "metrics": {}})

        result = analyze_reviews_from_api_payload(
            ["Helpful support", "Slow shipping"],
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["id"], "run-2")
        self.assertEqual(calls[0]["url"], "http://localhost:8000/analysis/batch")
        self.assertEqual(calls[0]["json"], {"reviews": [{"text": "Helpful support"}, {"text": "Slow shipping"}]})

    def test_analyze_reviews_csv_posts_file_to_analysis_csv_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, files: dict[str, object], timeout: int) -> FakeResponse:
            calls.append({"url": url, "files": files, "timeout": timeout})
            return FakeResponse(200, {"id": "run-3", "review_count": 2, "reviews": [], "metrics": {}})

        result = analyze_reviews_csv(
            "reviews.csv",
            b"review\nGreat product\nSlow shipping\n",
            api_base_url="http://localhost:8000/",
            post=fake_post,
        )

        self.assertEqual(result["id"], "run-3")
        self.assertEqual(calls[0]["url"], "http://localhost:8000/analysis/csv")
        self.assertEqual(calls[0]["files"]["file"][0], "reviews.csv")

    def test_fetch_analysis_runs_calls_analysis_runs_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_get(url: str, timeout: int) -> FakeResponse:
            calls.append({"url": url, "timeout": timeout})
            return FakeResponse(200, {"items": []})

        result = fetch_analysis_runs(api_base_url="http://localhost:8000/", get=fake_get)

        self.assertEqual(result["items"], [])
        self.assertEqual(calls, [{"url": "http://localhost:8000/analysis/runs", "timeout": 10}])

    def test_fetch_analysis_run_calls_run_detail_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_get(url: str, timeout: int) -> FakeResponse:
            calls.append({"url": url, "timeout": timeout})
            return FakeResponse(200, {"id": "run-1"})

        result = fetch_analysis_run("run-1", api_base_url="http://localhost:8000/", get=fake_get)

        self.assertEqual(result["id"], "run-1")
        self.assertEqual(calls, [{"url": "http://localhost:8000/analysis/runs/run-1", "timeout": 10}])

    def test_fetch_review_detail_calls_run_review_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_get(url: str, timeout: int) -> FakeResponse:
            calls.append({"url": url, "timeout": timeout})
            return FakeResponse(
                200,
                {
                    "run_id": "run-1",
                    "review_index": 2,
                    "review": {"text": "Helpful support", "sentiment": "positive"},
                },
            )

        result = fetch_review_detail(
            "run-1",
            2,
            api_base_url="http://localhost:8000/",
            get=fake_get,
        )

        self.assertEqual(result["review_index"], 2)
        self.assertEqual(
            calls,
            [{"url": "http://localhost:8000/analysis/runs/run-1/reviews/2", "timeout": 10}],
        )

    def test_fetch_latest_analysis_calls_latest_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_get(url: str, timeout: int) -> FakeResponse:
            calls.append({"url": url, "timeout": timeout})
            return FakeResponse(200, {"id": "run-latest", "reviews": [], "metrics": {}})

        result = fetch_latest_analysis(api_base_url="http://localhost:8000/", get=fake_get)

        self.assertEqual(result["id"], "run-latest")
        self.assertEqual(calls, [{"url": "http://localhost:8000/analysis/latest", "timeout": 10}])


if __name__ == "__main__":
    unittest.main()
