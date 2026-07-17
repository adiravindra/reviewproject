"""Test dashboard client safety, timeout policy, and pure formatting helpers."""

import unittest

import requests

import dashboard.streamlit_app as streamlit_app
from dashboard.api_client import (
    ApiClientError,
    BackendUnavailable,
    check_health,
    request_analysis,
    request_collection,
    request_demo,
    request_history,
    request_history_report,
)
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


class MalformedResponse(FakeResponse):
    """Simulate a response whose body cannot be decoded as JSON."""

    def json(self):
        """Raise the same safe-to-handle decode error as a malformed body."""

        raise ValueError("invalid JSON")


class FakeSession:
    """Simulate HTTP calls while recording their public client contract."""

    def __init__(self, *, get_responses=None, post_responses=None, error=None):
        """Configure route responses or one transport error for every request."""

        self.get_responses = get_responses or {}
        self.post_responses = post_responses or {}
        self.error = error
        self.calls = []

    def get(self, url, timeout):
        """Record and answer a GET request."""

        self.calls.append(("get", url, timeout))
        if self.error:
            raise self.error
        return self.get_responses[url]

    def post(self, url, json, timeout):
        """Record and answer a POST request."""

        self.calls.append(("post", url, json, timeout))
        if self.error:
            raise self.error
        return self.post_responses[url]


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

        session = FakeSession(
            get_responses={
                "http://127.0.0.1:8000/health": FakeResponse({"status": "ok"})
            }
        )
        self.assertTrue(check_health("http://127.0.0.1:8000", session=session))
        self.assertEqual(session.calls, [("get", "http://127.0.0.1:8000/health", 2)])

    def test_health_failure_returns_false_without_os_details(self):
        """Reduce health transport failures to false without leaking OS details."""

        session = FailingSession(requests.ConnectionError("OS detail"))
        self.assertFalse(check_health("http://127.0.0.1:8000", session=session))

    def test_connection_failure_is_backend_unavailable(self):
        """Reduce every stage's connection failure to the safe unavailable error."""

        for request in (
            lambda session: request_collection("https://example.com", "http://127.0.0.1:8000", session=session),
            lambda session: request_demo("http://127.0.0.1:8000", session=session),
            lambda session: request_analysis({"source": {}, "reviews": []}, "http://127.0.0.1:8000", session=session),
            lambda session: request_history("http://127.0.0.1:8000", session=session),
            lambda session: request_history_report(1, "http://127.0.0.1:8000", session=session),
        ):
            with self.subTest(request=request):
                with self.assertRaises(BackendUnavailable) as raised:
                    request(FailingSession(requests.ConnectionError("OS detail")))
                self.assertEqual(str(raised.exception), "The FastAPI backend is not reachable.")

    def test_timeout_failure_is_backend_unavailable_for_every_stage(self):
        """Reduce every stage's timeout failure to the safe unavailable error."""

        for request in (
            lambda session: request_collection("https://example.com", "http://127.0.0.1:8000", session=session),
            lambda session: request_demo("http://127.0.0.1:8000", session=session),
            lambda session: request_analysis({"source": {}, "reviews": []}, "http://127.0.0.1:8000", session=session),
            lambda session: request_history("http://127.0.0.1:8000", session=session),
            lambda session: request_history_report(1, "http://127.0.0.1:8000", session=session),
        ):
            with self.subTest(request=request):
                with self.assertRaises(BackendUnavailable):
                    request(FailingSession(requests.Timeout("network detail")))

    def test_structured_api_error_is_preserved(self):
        """Preserve documented error code and message from JSON detail."""

        session = FakeSession(post_responses={
            "http://127.0.0.1:8000/api/collect": FakeResponse(
                {"detail": {"code": "no_reviews", "message": "At least two public reviews are required."}},
                status_code=422,
            )
        })
        with self.assertRaises(ApiClientError) as raised:
            request_collection("https://example.com", "http://127.0.0.1:8000", session=session)
        self.assertEqual(raised.exception.code, "no_reviews")
        self.assertEqual(str(raised.exception), "At least two public reviews are required.")

    def test_structured_api_error_discards_sensitive_extra_fields(self):
        """Preserve exactly safe nested fields and discard untrusted extras."""

        session = FakeSession(post_responses={
            "http://127.0.0.1:8000/api/collect": FakeResponse(
                {"detail": {"code": "no_reviews", "message": "At least two reviews are required.", "token": "secret-value", "raw_body": "private details"}},
                status_code=422,
            )
        })
        with self.assertRaises(ApiClientError) as raised:
            request_collection("https://example.com", "http://127.0.0.1:8000", session=session)
        self.assertEqual(raised.exception.code, "no_reviews")
        self.assertEqual(str(raised.exception), "At least two reviews are required.")
        self.assertNotIn("secret-value", str(raised.exception))
        self.assertNotIn("private details", str(raised.exception))

    def test_collection_uses_staged_endpoint_payload_and_timeout(self):
        """Collect a URL before analysis with its dedicated timeout budget."""

        collection = {"source": {"url": "https://example.com"}, "reviews": []}
        session = FakeSession(post_responses={"http://127.0.0.1:8000/api/collect": FakeResponse(collection)})
        self.assertEqual(request_collection("https://example.com", "http://127.0.0.1:8000/", session=session), collection)
        self.assertEqual(session.calls, [("post", "http://127.0.0.1:8000/api/collect", {"url": "https://example.com"}, 15)])

    def test_demo_uses_staged_endpoint_and_timeout(self):
        """Load deterministic demo collection data with its short work budget."""

        collection = {"source": {"url": "demo"}, "reviews": []}
        session = FakeSession(get_responses={"http://127.0.0.1:8000/api/demo": FakeResponse(collection)})
        self.assertEqual(request_demo("http://127.0.0.1:8000/", session=session), collection)
        self.assertEqual(session.calls, [("get", "http://127.0.0.1:8000/api/demo", 15)])

    def test_analysis_sends_only_collection_source_and_reviews(self):
        """Analyze an already collected payload using only its required fields."""

        collection = {"source": {"url": "https://example.com"}, "reviews": [{"text": "Good"}], "unused": "discarded"}
        session = FakeSession(post_responses={"http://127.0.0.1:8000/api/analyze": FakeResponse(sample_report())})
        self.assertEqual(request_analysis(collection, "http://127.0.0.1:8000/", session=session), sample_report())
        self.assertEqual(session.calls, [("post", "http://127.0.0.1:8000/api/analyze", {"source": collection["source"], "reviews": collection["reviews"]}, 45)])

    def test_history_uses_list_endpoint_and_timeout(self):
        """Request run history with its own response shape and timeout."""

        history = [{"id": 1, "source": "Demo"}]
        session = FakeSession(get_responses={"http://127.0.0.1:8000/api/history": FakeResponse(history)})
        self.assertEqual(request_history("http://127.0.0.1:8000/", session=session), history)
        self.assertEqual(session.calls, [("get", "http://127.0.0.1:8000/api/history", 5)])

    def test_history_report_uses_object_endpoint_and_timeout(self):
        """Request one stored report with its own response shape and timeout."""

        report = sample_report()
        session = FakeSession(get_responses={"http://127.0.0.1:8000/api/history/7": FakeResponse(report)})
        self.assertEqual(request_history_report(7, "http://127.0.0.1:8000/", session=session), report)
        self.assertEqual(session.calls, [("get", "http://127.0.0.1:8000/api/history/7", 5)])

    def test_invalid_history_id_is_rejected_without_a_request(self):
        """Reject locally invalid history IDs without reaching the backend."""

        for run_id in (0, -1, True, "1"):
            with self.subTest(run_id=run_id):
                session = FakeSession()
                with self.assertRaises(ApiClientError) as raised:
                    request_history_report(run_id, "http://127.0.0.1:8000", session=session)
                self.assertEqual(raised.exception.code, "history_not_found")
                self.assertEqual(str(raised.exception), "That history entry was not found.")
                self.assertEqual(session.calls, [])

    def test_malformed_error_response_uses_the_generic_safe_error(self):
        """Never surface an untrusted error response payload to the dashboard."""

        session = FakeSession(post_responses={
            "http://127.0.0.1:8000/api/collect": MalformedResponse(None, status_code=500, content_type="text/html")
        })
        with self.assertRaises(ApiClientError) as raised:
            request_collection("https://example.com", "http://127.0.0.1:8000", session=session)
        self.assertEqual(raised.exception.code, "analysis_failed")
        self.assertEqual(str(raised.exception), "The request could not be completed.")

    def test_success_shape_mismatch_uses_the_generic_invalid_response_error(self):
        """Reject successful payloads that do not match each endpoint contract."""

        cases = (
            (lambda session: request_collection("https://example.com", "http://127.0.0.1:8000", session=session), FakeSession(post_responses={"http://127.0.0.1:8000/api/collect": FakeResponse([])})),
            (lambda session: request_demo("http://127.0.0.1:8000", session=session), FakeSession(get_responses={"http://127.0.0.1:8000/api/demo": FakeResponse([])})),
            (lambda session: request_analysis({"source": {}, "reviews": []}, "http://127.0.0.1:8000", session=session), FakeSession(post_responses={"http://127.0.0.1:8000/api/analyze": FakeResponse([])})),
            (lambda session: request_history("http://127.0.0.1:8000", session=session), FakeSession(get_responses={"http://127.0.0.1:8000/api/history": FakeResponse(["not-an-object"])})),
            (lambda session: request_history_report(1, "http://127.0.0.1:8000", session=session), FakeSession(get_responses={"http://127.0.0.1:8000/api/history/1": FakeResponse([])})),
        )
        for request, session in cases:
            with self.subTest(request=request):
                with self.assertRaises(ApiClientError) as raised:
                    request(session)
                self.assertEqual(raised.exception.code, "analysis_failed")
                self.assertEqual(str(raised.exception), "The backend returned an invalid response.")


class DashboardFormattingTests(unittest.TestCase):
    """Group visual-token and report-formatting regression contracts."""

    def test_primary_controls_keep_the_blue_design_token(self):
        """Keep primary form, radio, and toolbar CSS selectors on the blue token."""

        self.assertIn('[data-testid="stBaseButton-primaryFormSubmit"]', DASHBOARD_CSS)
        self.assertIn(":has(input:checked)", DASHBOARD_CSS)
        self.assertIn('[data-testid="stToolbar"]', DASHBOARD_CSS)
        self.assertIn("#2563eb", DASHBOARD_CSS)

    def test_recovery_guidance_uses_supported_full_application_command(self):
        """Direct recovery through the supported supervisor entry point."""

        self.assertTrue(hasattr(streamlit_app, "APP_COMMAND"))
        self.assertEqual(
            streamlit_app.APP_COMMAND,
            r".\.venv\Scripts\python.exe run_app.py",
        )
        self.assertNotIn("uvicorn", streamlit_app.APP_COMMAND.lower())

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
