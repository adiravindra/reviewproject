"""Test FastAPI routes, validation, and safe public failure envelopes."""

import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from backend.app.collector import CollectionError
from backend.app.errors import AnalysisError
from backend.app.main import create_app
from backend.app.models import AnalysisResponse, PublicError


def sample_response():
    """Build a fully validated response returned by API service fakes."""

    return AnalysisResponse.model_validate(
        {
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
                {"id": "r3", "text": "Microphone quality needs meaningful improvement."},
            ],
        }
    )


class ApiTests(unittest.TestCase):
    """Group regression contracts at the public HTTP boundary."""

    def test_only_health_and_analyze_are_active(self):
        """Keep the MVP surface limited to readiness and analysis routes."""

        client = TestClient(create_app(analysis_service=lambda url, provider: sample_response()))
        self.assertEqual(client.get("/health").json(), {"status": "ok"})
        paths = set(client.get("/openapi.json").json()["paths"])
        self.assertEqual(paths, {"/health", "/api/analyze"})

    def test_analyze_returns_the_validated_response(self):
        """Pass validated input to the service and serialize its response contract."""

        service = Mock(return_value=sample_response())
        client = TestClient(create_app(analysis_service=service))
        response = client.post(
            "/api/analyze",
            json={"url": "https://example.com/product", "provider": "groq"},
        )
        self.assertEqual(response.status_code, 200)
        service.assert_called_once_with("https://example.com/product", "groq")
        self.assertEqual(response.json()["metrics"]["review_count"], 3)

    def test_known_failures_have_small_safe_envelopes(self):
        """Expose collection failures only through the documented detail shape."""

        def fail(url, provider):
            """Simulate a known insufficient-review collection failure."""

            raise CollectionError("no_reviews", "At least two public reviews are required.")

        response = TestClient(create_app(analysis_service=fail)).post(
            "/api/analyze",
            json={"url": "https://example.com/product", "provider": "google"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "no_reviews",
                    "message": "At least two public reviews are required.",
                }
            },
        )

    def test_collection_and_provider_failures_map_to_public_statuses(self):
        """Map domain codes stably while excluding chained provider secrets."""

        invalid_key = AnalysisError(
            "invalid_api_key",
            "The selected credential is invalid.",
        )
        invalid_key.__cause__ = RuntimeError(
            "Authorization: Bearer fake-secret-key; raw provider rejection"
        )
        unavailable = AnalysisError(
            "provider_unavailable",
            "The selected provider is temporarily unavailable.",
        )
        unavailable.__cause__ = RuntimeError(
            "x-goog-api-key: fake-google-key; raw provider timeout details"
        )
        cases = [
            (CollectionError("invalid_url", "Use a public URL."), 422, ()),
            (CollectionError("collection_failed", "The page could not be read."), 502, ()),
            (AnalysisError("missing_api_key", "Set the provider key."), 400, ()),
            (
                invalid_key,
                401,
                ("fake-secret-key", "raw provider rejection"),
            ),
            (
                unavailable,
                503,
                ("fake-google-key", "raw provider timeout details"),
            ),
            (AnalysisError("analysis_failed", "The analysis failed."), 502, ()),
        ]
        for error, expected_status, private_details in cases:
            with self.subTest(code=error.code):
                def fail(url, provider, raised=error):
                    """Raise the current table-driven domain failure."""

                    raise raised

                response = TestClient(create_app(analysis_service=fail)).post(
                    "/api/analyze",
                    json={"url": "https://example.com/product", "provider": "google"},
                )
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], error.code)
                for detail in private_details:
                    self.assertNotIn(detail, response.text)

    def test_public_error_accepts_credential_codes(self):
        """Keep credential preflight codes inside the declared public schema."""

        for code in ("invalid_api_key", "provider_unavailable"):
            with self.subTest(code=code):
                error = PublicError(code=code, message="Safe credential message.")
                self.assertEqual(error.code, code)

    def test_malformed_url_does_not_call_service(self):
        """Reject malformed URLs during request validation before service work."""

        service = Mock(return_value=sample_response())
        response = TestClient(create_app(analysis_service=service)).post(
            "/api/analyze",
            json={"url": "not a url", "provider": "google"},
        )
        self.assertEqual(response.status_code, 422)
        service.assert_not_called()

    def test_unexpected_exception_is_generic(self):
        """Convert unknown exceptions to a generic non-leaking server error."""

        def fail(url, provider):
            """Simulate an unexpected internal failure carrying private details."""

            raise RuntimeError("database password and provider internals")

        response = TestClient(create_app(analysis_service=fail)).post(
            "/api/analyze",
            json={"url": "https://example.com/product", "provider": "google"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "analysis_failed",
                    "message": "The analysis could not be completed.",
                }
            },
        )
        self.assertNotIn("password", response.text)


if __name__ == "__main__":
    unittest.main()
