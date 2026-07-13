"""Test dashboard client safety, timeout policy, and pure formatting helpers."""

import unittest

import requests

from dashboard.api_client import ApiClientError, BackendUnavailable, check_health, request_analysis
from dashboard.streamlit_app import DASHBOARD_CSS, metric_values, rating_rows, sentiment_rows


class FakeResponse:
    """Simulate the JSON-capable subset of backend HTTP responses."""

    def __init__(self, payload, *, status_code=200, content_type="application/json"):
        """Configure response payload, status, and declared media type."""

        self.payload = payload
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def json(self):
        """Return the configured decoded backend payload."""

        return self.payload


class FakeSession:
    """Simulate healthy backend calls while recording timeout and payload choices."""

    def __init__(self, *, get_response=None, post_status=200, post_json=None):
        """Configure health and analysis responses for client tests."""

        self.get_response = get_response or {"status": "ok"}
        self.post_status = post_status
        self.post_json = post_json or sample_report()
        self.get_call = None
        self.post_call = None

    def get(self, url, timeout):
        """Record and answer a health request."""

        self.get_call = (url, timeout)
        return FakeResponse(self.get_response)

    def post(self, url, json, timeout):
        """Record and answer an analysis request."""

        self.post_call = (url, json, timeout)
        return FakeResponse(self.post_json, status_code=self.post_status)


class FailingSession:
    """Simulate transport failures at either dashboard client endpoint."""

    def __init__(self, error):
        """Store the transport exception raised by all requests."""

        self.error = error

    def get(self, url, timeout):
        """Raise the configured health transport failure."""

        raise self.error

    def post(self, url, json, timeout):
        """Raise the configured analysis transport failure."""

        raise self.error


def sample_report():
    """Build a representative backend report for client and formatting tests."""

    return {
        "source": {
            "url": "https://example.com/product",
            "title": "Everyday Headphones",
            "extractor": "json_ld",
        },
        "metrics": {
            "review_count": 3,
            "rated_count": 2,
            "average_rating": 4.0,
            "positive_percentage": 66.7,
            "sentiment_counts": {"positive": 2, "neutral": 0, "negative": 1},
            "rating_distribution": {"1": 0, "2": 0, "3": 1, "4": 0, "5": 1},
        },
        "insights": {
            "summary": "Customers value sound and comfort while noting microphone limitations.",
            "overall_sentiment": "positive",
            "themes": [
                {
                    "name": "Daily performance",
                    "description": "Sound, comfort, and microphone quality shape the feedback.",
                    "mentions": 3,
                }
            ],
            "strengths": ["Clear sound", "Comfortable fit"],
            "weaknesses": ["Microphone quality"],
            "actions": ["Improve microphone noise handling"],
            "review_sentiments": [
                {"review_id": "r1", "sentiment": "positive"},
                {"review_id": "r2", "sentiment": "positive"},
                {"review_id": "r3", "sentiment": "negative"},
            ],
        },
        "reviews": [
            {"id": "r1", "text": "Clear sound and comfortable fit.", "rating": 5},
            {"id": "r2", "text": "Battery is adequate for a normal day.", "rating": 3},
            {"id": "r3", "text": "Microphone quality needs meaningful improvement.", "rating": None},
        ],
    }


class DashboardClientTests(unittest.TestCase):
    """Group HTTP-client timeout, decoding, and safe-error contracts."""

    def test_health_uses_a_short_timeout(self):
        """Keep readiness probing on its dedicated short timeout."""

        session = FakeSession(get_response={"status": "ok"})
        self.assertTrue(check_health("http://127.0.0.1:8000", session=session))
        self.assertEqual(session.get_call, ("http://127.0.0.1:8000/health", 2))

    def test_health_failure_returns_false_without_os_details(self):
        """Reduce health transport failures to false without leaking OS details."""

        session = FailingSession(requests.ConnectionError("OS detail"))
        self.assertFalse(check_health("http://127.0.0.1:8000", session=session))

    def test_connection_failure_is_backend_unavailable(self):
        """Raise the curated backend-unavailable error for analysis connection loss."""

        session = FailingSession(requests.ConnectionError("OS detail"))
        with self.assertRaises(BackendUnavailable) as raised:
            request_analysis(
                "https://example.com",
                "google",
                "http://127.0.0.1:8000",
                session=session,
            )
        self.assertNotIn("OS detail", str(raised.exception))

    def test_structured_api_error_is_preserved(self):
        """Preserve documented error code and message from JSON detail."""

        session = FakeSession(
            post_status=422,
            post_json={
                "detail": {
                    "code": "no_reviews",
                    "message": "At least two public reviews are required.",
                }
            },
        )
        with self.assertRaises(ApiClientError) as raised:
            request_analysis(
                "https://example.com",
                "google",
                "http://127.0.0.1:8000",
                session=session,
            )
        self.assertEqual(raised.exception.code, "no_reviews")
        self.assertEqual(str(raised.exception), "At least two public reviews are required.")

    def test_structured_credential_errors_preserve_only_safe_fields(self):
        """Discard extra provider and authorization fields from credential errors."""

        cases = [
            (
                401,
                "invalid_api_key",
                "The selected credential is invalid.",
            ),
            (
                503,
                "provider_unavailable",
                "The selected provider is temporarily unavailable.",
            ),
        ]
        for status, code, safe_message in cases:
            with self.subTest(code=code):
                session = FakeSession(
                    post_status=status,
                    post_json={
                        "detail": {
                            "code": code,
                            "message": safe_message,
                            "provider_body": "raw provider body details",
                            "authorization": "Bearer fake-secret-key",
                            "provider_header": "x-goog-api-key: fake-google-key",
                        }
                    },
                )
                with self.assertRaises(ApiClientError) as raised:
                    request_analysis(
                        "https://example.com",
                        "google",
                        "http://127.0.0.1:8000",
                        session=session,
                    )
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(str(raised.exception), safe_message)
                message = str(raised.exception)
                self.assertNotIn("fake-secret-key", message)
                self.assertNotIn("fake-google-key", message)
                self.assertNotIn("Bearer", message)
                self.assertNotIn("x-goog-api-key", message)
                self.assertNotIn("raw provider body", message)

    def test_analysis_uses_the_mvp_endpoint_and_long_timeout(self):
        """Send the MVP payload with the longer end-to-end analysis timeout."""

        session = FakeSession()
        report = request_analysis(
            "https://example.com/product",
            "groq",
            "http://127.0.0.1:8000/",
            session=session,
        )
        self.assertEqual(report["metrics"]["review_count"], 3)
        self.assertEqual(
            session.post_call,
            (
                "http://127.0.0.1:8000/api/analyze",
                {"url": "https://example.com/product", "provider": "groq"},
                45,
            ),
        )


class DashboardFormattingTests(unittest.TestCase):
    """Group visual-token and report-formatting regression contracts."""

    def test_primary_controls_keep_the_blue_design_token(self):
        """Keep primary form, radio, and toolbar CSS selectors on the blue token."""

        self.assertIn('[data-testid="stBaseButton-primaryFormSubmit"]', DASHBOARD_CSS)
        self.assertIn(":has(input:checked)", DASHBOARD_CSS)
        self.assertIn('[data-testid="stToolbar"]', DASHBOARD_CSS)
        self.assertIn("#2563eb", DASHBOARD_CSS)

    def test_metrics_and_charts_use_response_values(self):
        """Transform report values into deterministic metric and chart displays."""

        report = sample_report()
        self.assertEqual(metric_values(report), ("3", "4.0 / 5", "66.7%", "Positive"))
        self.assertEqual(sentiment_rows(report)[0], {"Sentiment": "Positive", "Reviews": 2})
        self.assertEqual(rating_rows(report)[4], {"Rating": "5 star", "Reviews": 1})

    def test_missing_average_rating_has_a_clear_display(self):
        """Render unrated reports with an explicit nonnumeric label."""

        report = sample_report()
        report["metrics"]["average_rating"] = None
        self.assertEqual(metric_values(report)[1], "Not rated")


if __name__ == "__main__":
    unittest.main()
