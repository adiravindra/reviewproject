"""Exercise the isolated normalized review import cache with real SQLite."""

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.import_cache import CacheIdentity, ImportCacheStore
from backend.app.models import CollectionResult, Review, SourceInfo


NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)


def collection(status="miss"):
    """Build one valid normalized provider collection for cache tests."""

    return CollectionResult(
        source=SourceInfo(
            url="https://www.amazon.com/dp/B000000000",
            title="Amazon product B000000000",
            extractor="provider_api",
            is_demo=False,
            platform="amazon",
            provider="Apify (Axesso)",
            requested_count=20,
            retrieved_count=2,
            retrieved_at=NOW,
            cache_status=status,
        ),
        reviews=[
            Review(id="r1", text="First useful imported review."),
            Review(id="r2", text="Second useful imported review."),
        ],
    )


class ImportCacheTests(unittest.TestCase):
    """Verify isolated SQLite cache behavior and stored-data boundaries."""

    def setUp(self):
        """Create a fresh temporary cache database path."""

        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "nested" / "imports.db"
        self.store = ImportCacheStore(self.path)
        self.identity = CacheIdentity(
            "amazon",
            "apify_axesso_amazon",
            "1",
            "B000000000",
            20,
            "most_relevant",
        )

    def tearDown(self):
        """Remove the temporary cache database."""

        self.temp.cleanup()

    def test_put_get_and_expiry_use_lazy_isolated_schema(self):
        """Create lazily, return live data, and delete expired entries."""

        self.assertFalse(self.path.exists())
        self.store.put(self.identity, collection(), NOW, NOW + timedelta(days=30))

        self.assertEqual(self.store.get(self.identity, NOW), collection())
        self.assertIsNone(self.store.get(self.identity, NOW + timedelta(days=31)))
        with closing(sqlite3.connect(self.path)) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(review_import_cache)")}
        self.assertEqual(
            columns,
            {
                "cache_key", "platform", "provider", "contract_version", "source_hash",
                "requested_limit", "ordering", "fetched_at", "expires_at", "collection_json",
            },
        )

    def test_identity_dimensions_do_not_collide(self):
        """Keep every evidence-changing cache dimension isolated."""

        self.store.put(self.identity, collection(), NOW, NOW + timedelta(days=30))
        variants = (
            CacheIdentity("google_maps", "apify_axesso_amazon", "1", "B000000000", 20, "most_relevant"),
            CacheIdentity("amazon", "other", "1", "B000000000", 20, "most_relevant"),
            CacheIdentity("amazon", "apify_axesso_amazon", "2", "B000000000", 20, "most_relevant"),
            CacheIdentity("amazon", "apify_axesso_amazon", "1", "OTHER", 20, "most_relevant"),
            CacheIdentity("amazon", "apify_axesso_amazon", "1", "B000000000", 50, "most_relevant"),
            CacheIdentity("amazon", "apify_axesso_amazon", "1", "B000000000", 20, "newest"),
        )
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertIsNone(self.store.get(variant, NOW))

    def test_corrupt_entry_is_removed_and_cache_contains_no_identity_or_secret_marker(self):
        """Discard invalid JSON and persist only normalized collection data."""

        self.store.put(self.identity, collection(), NOW, NOW + timedelta(days=30))
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE review_import_cache SET collection_json = ? WHERE cache_key = ?",
                    ("discard-reviewer-marker secret-token", self.identity.digest),
                )
        self.assertIsNone(self.store.get(self.identity, NOW))
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM review_import_cache").fetchone()[0], 0)

        self.store.put(self.identity, collection(), NOW, NOW + timedelta(days=30))
        with closing(sqlite3.connect(self.path)) as connection:
            stored = connection.execute(
                "SELECT collection_json FROM review_import_cache WHERE cache_key = ?",
                (self.identity.digest,),
            ).fetchone()[0]
        self.assertNotIn("discard-reviewer-marker", stored)
        self.assertNotIn("secret-token", stored)


if __name__ == "__main__":
    unittest.main()
