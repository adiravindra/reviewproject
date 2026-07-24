"""Contract-test provider adapters with saved fixtures and fake HTTP only."""

import json
import logging
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from backend.app.imports.apify import ApifyGoogleMapsAdapter
from backend.app.imports.apify_amazon import (
    AUTOMATION_LAB_ENDPOINT,
    AUTOMATION_LAB_TIMEOUT,
    ApifyAmazonReviewsAdapter,
)
from backend.app.imports.contracts import ReviewImportError
from backend.app.imports.normalizer import normalize_provider_result


FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    """Return a configured status and JSON payload without HTTP."""

    def __init__(self, status_code=200, payload=None, json_error=None):
        """Remember the fake response values."""

        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self):
        """Return JSON or raise the configured decoding failure."""

        if self._json_error is not None:
            raise self._json_error
        return self._payload


class FakeSession:
    """Record one provider request and return a configured response."""

    def __init__(self, response):
        """Remember the response or transport exception."""

        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        """Record an unexpected provider GET."""

        self.calls.append(("get", url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def post(self, url, **kwargs):
        """Record an Apify POST."""

        self.calls.append(("post", url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def load_fixture(name):
    """Load one checked-in sanitized provider response."""

    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ImportAdapterTests(unittest.TestCase):
    """Verify exact provider calls, decoding, and safe failures."""

    def test_automation_lab_uses_exact_unfiltered_request_for_each_allowed_limit(self):
        """Send one ASIN with the exact approved natural-sample input."""

        for limit in (10, 20, 50, 100):
            with self.subTest(limit=limit):
                session = FakeSession(
                    FakeResponse(
                        payload=load_fixture(
                            "apify_automation_lab_amazon_reviews.json"
                        )
                    )
                )
                with patch.dict(
                    os.environ,
                    {"APIFY_API_TOKEN": "  test-apify-token  "},
                    clear=False,
                ):
                    result = ApifyAmazonReviewsAdapter(session=session).fetch(
                        "https://www.amazon.com/dp/B0GR6F79MT"
                        "?ref=share&social_share=example&th=1",
                        limit,
                    )

                self.assertEqual(len(session.calls), 1)
                method, url, kwargs = session.calls[0]
                self.assertEqual((method, url), ("post", AUTOMATION_LAB_ENDPOINT))
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-apify-token")
                self.assertNotIn("token=", url)
                self.assertEqual(kwargs["timeout"], AUTOMATION_LAB_TIMEOUT)
                self.assertEqual(
                    kwargs["json"],
                    {
                        "asins": ["B0GR6F79MT"],
                        "marketplace": "US",
                        "maxReviewsPerProduct": limit,
                        "sort": "helpful",
                    },
                )
                self.assertEqual(result.title, "Amazon product B0GR6F79MT")
                self.assertEqual(result.source_key, "B0GR6F79MT")
                self.assertEqual(
                    [review.rating for review in result.reviews],
                    [5, 3, 1],
                )
                self.assertEqual(
                    [review.title for review in result.reviews],
                    [
                        "Most useful positive review",
                        "Useful but mixed",
                        "Important reliability concern",
                    ],
                )
                normalized = normalize_provider_result(result, limit)
                self.assertEqual(len(normalized.reviews), 3)
                self.assertEqual([review.rating for review in normalized.reviews], [5, 3, 1])
                self.assertEqual(
                    [(review.text, review.date) for review in normalized.reviews],
                    [
                        (
                            "Most useful positive review — The laptop is fast, quiet, and lasts through a full workday.",
                            "2026-07-20",
                        ),
                        (
                            "Useful but mixed — Performance is steady, although the port selection is only adequate.",
                            "2026-07-18",
                        ),
                        (
                            "Important reliability concern — The display began flickering after several days of ordinary use.",
                            "2026-07-16",
                        ),
                    ],
                )
                for marker in (
                    "discard-reviewer-marker",
                    "discard-profile",
                    "discard-review-id",
                    "discard-review-url",
                    "discard-neutral-reviewer",
                    "discard-negative-reviewer",
                ):
                    self.assertNotIn(marker, repr(result))
                    self.assertNotIn(marker, repr(normalized))

    def test_automation_lab_valid_empty_result_returns_no_candidates(self):
        """Let the import service own the safe no-review failure mapping."""

        session = FakeSession(FakeResponse(payload=[]))
        with patch.dict(os.environ, {"APIFY_API_TOKEN": "test-token"}, clear=False):
            result = ApifyAmazonReviewsAdapter(session=session).fetch(
                "https://www.amazon.com/dp/B000000000", 10
            )

        self.assertEqual(result.source_key, "B000000000")
        self.assertEqual(result.reviews, ())

    def test_apify_uses_one_private_bearer_request_and_disables_personal_data(self):
        """Use bearer auth and explicitly disable Actor personal data."""

        session = FakeSession(FakeResponse(payload=load_fixture("apify_google_maps_reviews.json")))
        source_url = "https://www.google.com/maps/place/Test+Cafe"
        with patch.dict(os.environ, {"APIFY_API_TOKEN": "  test-apify-token  "}, clear=False):
            result = ApifyGoogleMapsAdapter(session=session).fetch(source_url, 10)

        self.assertEqual(len(session.calls), 1)
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "post")
        self.assertEqual(
            url,
            "https://api.apify.com/v2/acts/compass~google-maps-reviews-scraper/run-sync-get-dataset-items",
        )
        self.assertNotIn("token=", url)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-apify-token")
        self.assertEqual(kwargs["timeout"], (5, 60))
        self.assertEqual(
            kwargs["json"],
            {
                "startUrls": [{"url": source_url}],
                "maxReviews": 10,
                "reviewsSort": "mostRelevant",
                "reviewsOrigin": "google",
                "personalData": False,
                "language": "en",
            },
        )
        self.assertTrue(
            {
                "filterByStars",
                "starRatings",
                "filterByRating",
                "minimumRating",
            }.isdisjoint(kwargs["json"])
        )
        self.assertEqual(
            [review.rating for review in result.reviews],
            [5, 3, 1],
        )
        self.assertEqual(result.title, "Test Cafe")
        self.assertEqual(result.source_key, "ChIJFixturePlace")
        normalized = normalize_provider_result(result, 10)
        self.assertEqual(len(normalized.reviews), 3)
        self.assertEqual([review.rating for review in normalized.reviews], [5, 3, 1])
        self.assertEqual(
            [(review.text, review.date) for review in normalized.reviews],
            [
                ("Friendly staff and excellent coffee during a busy morning.", "2026-07-20"),
                ("The visit was acceptable, but service speed varied considerably.", "2026-07-18"),
                ("The order was incorrect and the issue was not resolved.", "2026-07-16"),
            ],
        )
        for marker in ("discard-reviewer-marker", "discard-owner-marker", "discard-image"):
            self.assertNotIn(marker, repr(result))
            self.assertNotIn(marker, repr(normalized))

    def test_missing_credentials_stop_before_http(self):
        """Require only the selected backend credential before network work."""

        for adapter, variable in (
            (
                ApifyAmazonReviewsAdapter(session=FakeSession(FakeResponse())),
                "APIFY_API_TOKEN",
            ),
            (ApifyGoogleMapsAdapter(session=FakeSession(FakeResponse())), "APIFY_API_TOKEN"),
        ):
            with self.subTest(variable=variable), patch.dict(os.environ, {variable: "  "}, clear=False):
                with self.assertRaises(ReviewImportError) as raised:
                    adapter.fetch("https://example.test/source", 10)
                self.assertEqual(raised.exception.code, "missing_provider_key")
                self.assertEqual(adapter.session.calls, [])

    def test_automation_lab_rejects_invalid_amazon_source_before_http(self):
        """Keep direct adapter use from sending a malformed Actor input."""

        session = FakeSession(FakeResponse(payload=[]))
        with patch.dict(os.environ, {"APIFY_API_TOKEN": "test-token"}, clear=False):
            with self.assertRaises(ReviewImportError) as raised:
                ApifyAmazonReviewsAdapter(session=session).fetch(
                    "https://www.amazon.com/s?k=kettle", 10
                )

        self.assertEqual(raised.exception.code, "invalid_import_url")
        self.assertEqual(session.calls, [])

    def test_automation_lab_statuses_transport_and_schema_failures_are_safely_mapped(self):
        """Reduce Automation Lab failures to application-owned codes."""

        cases = (
            (FakeResponse(400, []), "provider_request_rejected"),
            (FakeResponse(401, []), "provider_auth_failed"),
            (FakeResponse(402, []), "provider_quota_exhausted"),
            (FakeResponse(404, []), "provider_request_rejected"),
            (FakeResponse(409, []), "provider_request_rejected"),
            (FakeResponse(422, []), "provider_request_rejected"),
            (FakeResponse(429, []), "provider_unavailable"),
            (FakeResponse(503, []), "provider_unavailable"),
            (requests.Timeout("secret timeout"), "import_timeout"),
            (requests.ConnectionError("secret socket"), "provider_unavailable"),
            (
                FakeResponse(
                    200,
                    json_error=requests.exceptions.JSONDecodeError(
                        "secret malformed JSON",
                        "secret provider body",
                        0,
                    ),
                ),
                "provider_response_invalid",
            ),
            (FakeResponse(200, {}), "provider_response_invalid"),
            (FakeResponse(200, [1]), "provider_response_invalid"),
        )
        for response, expected in cases:
            with self.subTest(expected=expected):
                session = FakeSession(response)
                adapter = ApifyAmazonReviewsAdapter(session=session)
                with patch.dict(os.environ, {"APIFY_API_TOKEN": "secret-token"}, clear=False):
                    with (
                        self.assertLogs(
                            "backend.app.imports.apify_amazon", level=logging.WARNING
                        ) as captured,
                        self.assertRaises(ReviewImportError) as raised,
                    ):
                        adapter.fetch("https://www.amazon.com/dp/B000000000", 10)
                self.assertEqual(raised.exception.code, expected)
                self.assertNotIn("secret", str(raised.exception))
                self.assertIn(expected, "\n".join(captured.output))

    def test_automation_lab_logs_safe_failure_category_without_provider_details(self):
        """Log actionable status and code without response bodies or credentials."""

        session = FakeSession(FakeResponse(401, {"error": "secret provider body"}))
        adapter = ApifyAmazonReviewsAdapter(session=session)
        with (
            patch.dict(os.environ, {"APIFY_API_TOKEN": "secret-token"}, clear=False),
            self.assertLogs(
                "backend.app.imports.apify_amazon", level=logging.WARNING
            ) as captured,
            self.assertRaises(ReviewImportError) as raised,
        ):
            adapter.fetch("https://www.amazon.com/dp/B000000000", 10)

        logged = "\n".join(captured.output)
        self.assertEqual(raised.exception.code, "provider_auth_failed")
        self.assertIn("provider_auth_failed", logged)
        self.assertIn("status=401", logged)
        self.assertNotIn("secret-token", logged)
        self.assertNotIn("secret provider body", logged)


if __name__ == "__main__":
    unittest.main()
