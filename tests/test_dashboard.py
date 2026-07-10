import unittest
from typing import Any
from unittest.mock import ANY, patch

import requests

from dashboard.api_client import ApiClientError
from tests.factories import complete_response


class FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class DashboardApiClientTests(unittest.TestCase):
    def test_analyze_posts_url_with_backend_plus_deadline_timeout(self) -> None:
        from dashboard.api_client import analyze_website

        payload = complete_response().model_dump(mode="json")
        with patch("dashboard.api_client.requests.post", return_value=FakeResponse(200, payload)) as post:
            result = analyze_website(
                " https://public.example/reviews ",
                api_base_url="http://backend.test/",
            )

        self.assertEqual(result, payload)
        post.assert_called_once_with(
            "http://backend.test/analysis/website",
            json={"url": "https://public.example/reviews"},
            timeout=130,
        )

    def test_structured_backend_error_is_preserved(self) -> None:
        from dashboard.api_client import analyze_website

        response = FakeResponse(
            403,
            {
                "error": {
                    "code": "blocked_source",
                    "message": "The website blocked automated access.",
                    "stage": "scraping",
                    "retryable": False,
                    "details": {"url": "https://public.example/reviews"},
                }
            },
        )
        with (
            patch("dashboard.api_client.requests.post", return_value=response),
            self.assertRaises(ApiClientError) as raised,
        ):
            analyze_website("https://public.example/reviews")

        self.assertEqual(raised.exception.code, "blocked_source")
        self.assertEqual(raised.exception.stage, "scraping")
        self.assertFalse(raised.exception.retryable)
        self.assertEqual(raised.exception.details["url"], "https://public.example/reviews")

    def test_network_timeout_has_honest_retryable_state(self) -> None:
        from dashboard.api_client import analyze_website

        with (
            patch("dashboard.api_client.requests.post", side_effect=requests.Timeout),
            self.assertRaises(ApiClientError) as raised,
        ):
            analyze_website("https://public.example/reviews")

        self.assertEqual(raised.exception.code, "request_timeout")
        self.assertEqual(raised.exception.stage, "request")
        self.assertTrue(raised.exception.retryable)

    def test_history_summary_and_complete_item_use_separate_routes(self) -> None:
        from dashboard.api_client import fetch_history, fetch_history_item

        responses = [
            FakeResponse(200, {"items": []}),
            FakeResponse(200, complete_response().model_dump(mode="json")),
        ]
        with patch("dashboard.api_client.requests.get", side_effect=responses) as get:
            self.assertEqual(fetch_history("http://backend.test"), {"items": []})
            self.assertEqual(fetch_history_item("run 1", "http://backend.test")["id"], "run_test")

        self.assertEqual(get.call_args_list[0].args[0], "http://backend.test/analysis/history")
        self.assertEqual(get.call_args_list[1].args[0], "http://backend.test/analysis/history/run%201")


class DashboardFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = complete_response().model_dump(mode="json")

    def test_metric_and_chart_helpers_use_deterministic_payload_fields(self) -> None:
        from dashboard.ui import dashboard_metrics, rating_chart_data, sentiment_chart_data

        self.assertEqual(
            dashboard_metrics(self.payload),
            {
                "Reviews": "2 analyzed / 2 found",
                "Average rating": "3.5 / 5",
                "Rated reviews": "2",
                "Overall sentiment": "Mixed",
            },
        )
        self.assertEqual(
            rating_chart_data(self.payload),
            [
                {"Rating": "1 star", "Reviews": 0},
                {"Rating": "2 stars", "Reviews": 1},
                {"Rating": "3 stars", "Reviews": 0},
                {"Rating": "4 stars", "Reviews": 0},
                {"Rating": "5 stars", "Reviews": 1},
            ],
        )
        self.assertEqual(
            sentiment_chart_data(self.payload),
            [
                {"Sentiment": "Positive", "Reviews": 1},
                {"Sentiment": "Neutral", "Reviews": 0},
                {"Sentiment": "Negative", "Reviews": 1},
            ],
        )

    def test_history_rows_format_website_level_summaries(self) -> None:
        from dashboard.ui import history_rows

        history = {
            "items": [
                {
                    "id": "run_test",
                    "completed_at": "2026-07-10T15:00:00Z",
                    "source_url": "https://public.example/reviews",
                    "entity_name": "Example Product",
                    "review_count": 2,
                    "average_rating": 3.5,
                    "overall_sentiment": "mixed",
                    "executive_summary": "Customers see clear strengths and concerns.",
                    "provider": "google",
                    "model": "gemini-2.5-flash-lite",
                }
            ]
        }

        rows = history_rows(history)

        self.assertEqual(rows[0]["ID"], "run_test")
        self.assertEqual(rows[0]["Source"], "Example Product")
        self.assertEqual(rows[0]["Reviews"], "2")
        self.assertEqual(rows[0]["Average rating"], "3.5")
        self.assertEqual(rows[0]["Sentiment"], "Mixed")


if __name__ == "__main__":
    unittest.main()
