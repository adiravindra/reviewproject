"""Exercise provider-neutral import API routes and safe error envelopes."""

import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from backend.app.imports.contracts import ReviewImportError
from backend.app.main import create_app
from backend.app.models import (
    CollectionResult,
    ImportOptions,
    ImportPlatformOption,
    Review,
    SourceInfo,
)


class FakeHistoryStore:
    """Provide inert history methods for route-isolated API tests."""

    def save(self, report):
        """Reject unexpected history writes."""

        raise AssertionError("history must not be called")

    def list_runs(self):
        """Return an empty history list."""

        return []

    def get(self, run_id):
        """Return no stored report."""

        return None


def imported_collection():
    """Build one valid provider collection returned by a fake service."""

    return CollectionResult(
        source=SourceInfo(
            url="https://www.amazon.com/dp/B000000000",
            title="Amazon product B000000000",
            extractor="provider_api",
            is_demo=False,
            platform="amazon",
            provider="Outscraper",
            requested_count=5,
            retrieved_count=2,
            retrieved_at="2026-07-22T12:00:00+00:00",
            cache_status="miss",
        ),
        reviews=[
            Review(id="r1", text="First useful imported review."),
            Review(id="r2", text="Second useful imported review."),
        ],
    )


class ImportApiTests(unittest.TestCase):
    """Verify import routing without providers, analysis, or history."""

    def test_options_and_import_call_only_the_injected_service(self):
        """Expose registry choices and pass one exact validated request."""

        service = Mock()
        service.options.return_value = ImportOptions(
            platforms=[
                ImportPlatformOption(key="amazon", label="Amazon product", limits=[5, 10, 12])
            ]
        )
        service.import_reviews.return_value = imported_collection()
        client = TestClient(create_app(import_service=service, history_store=FakeHistoryStore()))

        options = client.get("/api/import/options")
        response = client.post(
            "/api/import",
            json={
                "platform": "amazon",
                "url": "https://www.amazon.com/dp/B000000000",
                "limit": 5,
                "refresh": False,
            },
        )

        self.assertEqual(options.status_code, 200)
        self.assertEqual(options.json()["platforms"][0]["limits"], [5, 10, 12])
        self.assertEqual(response.status_code, 200)
        submitted = service.import_reviews.call_args.args[0]
        self.assertEqual(submitted.platform, "amazon")
        self.assertEqual(submitted.limit, 5)
        self.assertFalse(submitted.refresh)
        service.options.assert_called_once_with()
        service.import_reviews.assert_called_once()

    def test_default_options_need_no_credentials_or_provider_request(self):
        """List sources safely before accounts or environment values exist."""

        response = TestClient(
            create_app(history_store=FakeHistoryStore())
        ).get("/api/import/options")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["key"] for item in response.json()["platforms"]],
            ["amazon", "google_maps"],
        )

    def test_validation_errors_stop_before_service_with_specific_codes(self):
        """Classify platform, limit, and URL request validation safely."""

        cases = (
            ({"platform": "other", "url": "https://example.com", "limit": 5}, "unsupported_import_platform"),
            ({"platform": "amazon", "url": "https://example.com", "limit": 0}, "unsupported_import_limit"),
            ({"platform": "amazon", "url": "not-a-url", "limit": 5}, "invalid_import_url"),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected):
                service = Mock()
                response = TestClient(
                    create_app(import_service=service, history_store=FakeHistoryStore())
                ).post("/api/import", json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["detail"]["code"], expected)
                service.import_reviews.assert_not_called()

    def test_all_import_failures_have_exact_safe_statuses(self):
        """Map approved import errors without exposing provider details."""

        cases = {
            "invalid_import_url": 422,
            "unsupported_import_platform": 422,
            "unsupported_import_limit": 422,
            "missing_provider_key": 400,
            "provider_auth_failed": 401,
            "provider_quota_exhausted": 429,
            "no_reviews": 422,
            "provider_response_invalid": 502,
            "import_failed": 502,
            "provider_unavailable": 503,
            "import_timeout": 504,
            "cache_failed": 500,
        }
        marker = "secret-token raw-provider-body"
        payload = {
            "platform": "amazon",
            "url": "https://www.amazon.com/dp/B000000000",
            "limit": 5,
        }
        for code, status in cases.items():
            with self.subTest(code=code):
                service = Mock()
                service.import_reviews.side_effect = ReviewImportError(code, marker)
                response = TestClient(
                    create_app(import_service=service, history_store=FakeHistoryStore())
                ).post("/api/import", json=payload)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["detail"]["code"], code)
                self.assertNotIn(marker, response.text)

    def test_unknown_import_failures_use_generic_import_envelope(self):
        """Hide unknown exception text behind the approved import failure."""

        marker = "secret traceback"
        service = Mock()
        service.import_reviews.side_effect = RuntimeError(marker)
        response = TestClient(
            create_app(import_service=service, history_store=FakeHistoryStore())
        ).post(
            "/api/import",
            json={
                "platform": "amazon",
                "url": "https://www.amazon.com/dp/B000000000",
                "limit": 5,
            },
        )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"]["code"], "import_failed")
        self.assertNotIn(marker, response.text)


if __name__ == "__main__":
    unittest.main()
