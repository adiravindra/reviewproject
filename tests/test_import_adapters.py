"""Contract-test provider adapters with saved fixtures and fake HTTP only."""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from backend.app.imports.apify import ApifyGoogleMapsAdapter
from backend.app.imports.apify_amazon import (
    AXESSO_ENDPOINT,
    AXESSO_TIMEOUT,
    ApifyAmazonReviewsAdapter,
)
from backend.app.imports.contracts import ReviewImportError


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

    def test_axesso_uses_one_bounded_request_for_each_allowed_limit(self):
        """Map each shared limit to one exact Axesso Actor request."""

        for limit, max_pages in ((10, 1), (20, 2), (50, 5), (100, 10)):
            with self.subTest(limit=limit):
                session = FakeSession(
                    FakeResponse(payload=load_fixture("apify_axesso_amazon_reviews.json"))
                )
                with patch.dict(
                    os.environ, {"APIFY_API_TOKEN": "  test-apify-token  "}, clear=False
                ):
                    result = ApifyAmazonReviewsAdapter(session=session).fetch(
                        "https://www.amazon.com/dp/B000000000", limit
                    )

                self.assertEqual(len(session.calls), 1)
                method, url, kwargs = session.calls[0]
                self.assertEqual((method, url), ("post", AXESSO_ENDPOINT))
                self.assertNotIn("token=", url)
                self.assertEqual(
                    kwargs["headers"]["Authorization"], "Bearer test-apify-token"
                )
                self.assertEqual(kwargs["timeout"], AXESSO_TIMEOUT)
                self.assertEqual(
                    kwargs["json"],
                    {
                        "input": [
                            {
                                "asin": "B000000000",
                                "domainCode": "com",
                                "sortBy": "helpful",
                                "maxPages": max_pages,
                            }
                        ]
                    },
                )
                self.assertEqual(result.title, "Fixture product")
                self.assertEqual(result.source_key, "B000000000")
                self.assertEqual(len(result.reviews), 2)
                self.assertEqual(result.reviews[0].title, "Reliable every morning")
                self.assertEqual(
                    result.reviews[0].body,
                    "The controls are simple and the results are consistent.",
                )
                self.assertEqual(result.reviews[0].rating, "5.0 out of 5 stars")
                self.assertEqual(
                    result.reviews[0].date,
                    "Reviewed in the United States on July 20, 2026",
                )
                for marker in (
                    "discard-reviewer-marker",
                    "discard-profile-marker",
                    "discard-image-marker",
                    "discard-variation-marker",
                    "discard-helpful-marker",
                    "discard-unsuccessful",
                ):
                    self.assertNotIn(marker, repr(result))

    def test_axesso_valid_empty_result_returns_no_candidates(self):
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
        self.assertEqual(result.title, "Test Cafe")
        self.assertEqual(result.source_key, "ChIJFixturePlace")
        for marker in ("discard-reviewer-marker", "discard-owner-marker", "discard-image"):
            self.assertNotIn(marker, repr(result))

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

    def test_axesso_rejects_invalid_amazon_source_before_http(self):
        """Keep direct adapter use from sending a malformed Actor input."""

        session = FakeSession(FakeResponse(payload=[]))
        with patch.dict(os.environ, {"APIFY_API_TOKEN": "test-token"}, clear=False):
            with self.assertRaises(ReviewImportError) as raised:
                ApifyAmazonReviewsAdapter(session=session).fetch(
                    "https://www.amazon.com/s?k=kettle", 10
                )

        self.assertEqual(raised.exception.code, "invalid_import_url")
        self.assertEqual(session.calls, [])

    def test_axesso_statuses_transport_and_schema_failures_are_safely_mapped(self):
        """Reduce Axesso failures to application-owned codes."""

        cases = (
            (FakeResponse(401, []), "provider_auth_failed"),
            (FakeResponse(402, []), "provider_quota_exhausted"),
            (FakeResponse(429, []), "provider_unavailable"),
            (FakeResponse(503, []), "provider_unavailable"),
            (requests.Timeout("secret timeout"), "import_timeout"),
            (requests.ConnectionError("secret socket"), "provider_unavailable"),
            (FakeResponse(200, json_error=ValueError("secret body")), "provider_response_invalid"),
            (FakeResponse(200, {}), "provider_response_invalid"),
            (FakeResponse(200, [1]), "provider_response_invalid"),
        )
        for response, expected in cases:
            with self.subTest(expected=expected):
                session = FakeSession(response)
                adapter = ApifyAmazonReviewsAdapter(session=session)
                with patch.dict(os.environ, {"APIFY_API_TOKEN": "secret-token"}, clear=False):
                    with self.assertRaises(ReviewImportError) as raised:
                        adapter.fetch("https://www.amazon.com/dp/B000000000", 10)
                self.assertEqual(raised.exception.code, expected)
                self.assertNotIn("secret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
