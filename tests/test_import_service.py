"""Verify import orchestration, caching, provenance, and call boundaries."""

import unittest
from datetime import datetime, timezone

from backend.app.imports.contracts import (
    IMPORT_LIMITS,
    ProviderImportResult,
    ProviderReviewCandidate,
    ReviewImportError,
)
from backend.app.imports.service import ReviewImportService
from backend.app.models import ImportRequest


NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


class FakeAdapter:
    """Return configured provider-neutral candidates and record calls."""

    provider_key = "fake_amazon"
    provider_label = "Fixture Provider"
    platform = "amazon"
    allowed_limits = IMPORT_LIMITS

    def __init__(self, result=None, error=None):
        """Configure one normal result or safe adapter failure."""

        self.result = result or ProviderImportResult(
            title="Fixture product",
            source_url="https://www.amazon.com/dp/B000000000",
            source_key="B000000000",
            reviews=(
                ProviderReviewCandidate("Great", "This works very well every day.", 5, "2026-07-20"),
                ProviderReviewCandidate(None, "Useful product with clear controls.", 4, "2026-07-19"),
            ),
        )
        self.error = error
        self.calls = []

    def fetch(self, source_url, limit):
        """Record and answer one fake provider fetch."""

        self.calls.append((source_url, limit))
        if self.error:
            raise self.error
        return self.result


class FakeCache:
    """Hold one cache value in memory while recording operations."""

    def __init__(self):
        """Initialize empty fake cache state."""

        self.value = None
        self.get_calls = []
        self.put_calls = []

    def get(self, identity, now):
        """Return the current fake cache value."""

        self.get_calls.append((identity, now))
        return self.value

    def put(self, identity, value, fetched_at, expires_at):
        """Record and store one fake cache value."""

        self.put_calls.append((identity, value, fetched_at, expires_at))
        self.value = value


def request(refresh=False, limit=20):
    """Build one approved Amazon import request."""

    return ImportRequest(
        platform="amazon",
        url="https://www.amazon.com/dp/B000000000",
        limit=limit,
        refresh=refresh,
    )


class ImportServiceTests(unittest.TestCase):
    """Cover cache and provider orchestration without external work."""

    def setUp(self):
        """Compose the service with fake adapter, cache, and clock."""

        self.adapter = FakeAdapter()
        self.cache = FakeCache()
        self.service = ReviewImportService(
            {"amazon": self.adapter}, self.cache, clock=lambda: NOW
        )

    def test_options_come_from_registry_without_provider_internals(self):
        """Expose label and limits without touching the provider."""

        options = self.service.options()
        self.assertEqual(
            options.model_dump(),
            {
                "platforms": [
                    {
                        "key": "amazon",
                        "label": "Amazon product",
                        "limits": [10, 20, 50, 100],
                    }
                ]
            },
        )
        self.assertEqual(self.adapter.calls, [])

    def test_miss_fetches_once_normalizes_and_saves_provenance(self):
        """Fetch once on a miss and return complete source provenance."""

        result = self.service.import_reviews(request())

        self.assertEqual(self.adapter.calls, [("https://www.amazon.com/dp/B000000000", 20)])
        self.assertEqual(len(self.cache.put_calls), 1)
        self.assertEqual(result.source.provider, "Fixture Provider")
        self.assertEqual(result.source.platform, "amazon")
        self.assertEqual(result.source.requested_count, 20)
        self.assertEqual(result.source.retrieved_count, 2)
        self.assertEqual(result.source.cache_status, "miss")
        self.assertEqual(result.source.retrieved_at, NOW)

    def test_live_hit_skips_provider_and_refresh_replaces_once(self):
        """Avoid provider work on hits and fetch once on explicit refresh."""

        cached = self.service.import_reviews(request())
        self.adapter.calls.clear()
        hit = self.service.import_reviews(request())

        self.assertEqual(self.adapter.calls, [])
        self.assertEqual(hit.source.cache_status, "hit")
        self.assertEqual(hit.source.retrieved_at, cached.source.retrieved_at)

        refreshed = self.service.import_reviews(request(refresh=True))
        self.assertEqual(len(self.adapter.calls), 1)
        self.assertEqual(refreshed.source.cache_status, "refresh")

    def test_failed_refresh_does_not_replace_cached_value(self):
        """Preserve the last good cache entry when refresh fails."""

        cached = self.service.import_reviews(request())
        self.adapter.error = ReviewImportError("provider_unavailable")

        with self.assertRaises(ReviewImportError):
            self.service.import_reviews(request(refresh=True))

        self.assertEqual(self.cache.value, cached)
        self.assertEqual(len(self.cache.put_calls), 1)

    def test_invalid_limit_and_too_few_reviews_fail_safely(self):
        """Reject unsupported limits and insufficient written evidence."""

        for limit in (5, 25):
            with self.subTest(limit=limit):
                with self.assertRaises(ReviewImportError) as raised:
                    self.service.import_reviews(request(limit=limit))
                self.assertEqual(raised.exception.code, "unsupported_import_limit")
        self.assertEqual(self.adapter.calls, [])
        self.assertEqual(self.cache.get_calls, [])

        self.adapter.result = ProviderImportResult(
            "Fixture", "https://www.amazon.com/dp/B000000000", "B000000000",
            (ProviderReviewCandidate(None, "Only one useful written review.", 5, None),),
        )
        with self.assertRaises(ReviewImportError) as raised:
            self.service.import_reviews(request())
        self.assertEqual(raised.exception.code, "no_reviews")
        self.assertEqual(self.cache.put_calls, [])


if __name__ == "__main__":
    unittest.main()
