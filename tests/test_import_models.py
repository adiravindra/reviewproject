"""Validate additive public contracts for provider-backed imports."""

import unittest

from pydantic import ValidationError

from backend.app.models import (
    CollectionResult,
    ImportOptions,
    ImportPlatformOption,
    ImportRequest,
    Review,
    SourceInfo,
)


class ImportModelTests(unittest.TestCase):
    """Cover additive import contracts and compatibility defaults."""

    def test_old_source_payload_keeps_backward_compatible_defaults(self):
        """Keep old generic sources valid without synthetic import metadata."""

        source = SourceInfo(
            url="https://example.test/product",
            title="Existing source",
            extractor="json_ld",
            is_demo=False,
        )

        self.assertEqual(source.platform, "generic")
        self.assertIsNone(source.provider)
        self.assertIsNone(source.requested_count)
        self.assertIsNone(source.retrieved_count)
        self.assertIsNone(source.retrieved_at)
        self.assertEqual(source.cache_status, "not_applicable")

    def test_provider_collection_requires_actual_count_to_match_reviews(self):
        """Reject provider provenance that disagrees with normalized evidence."""

        source = SourceInfo(
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
        )
        collection = CollectionResult(
            source=source,
            reviews=[
                Review(id="r1", text="This is the first useful review."),
                Review(id="r2", text="This is the second useful review."),
            ],
        )

        self.assertEqual(collection.source.retrieved_count, 2)
        with self.assertRaises(ValidationError):
            CollectionResult(source=source.model_copy(update={"retrieved_count": 1}), reviews=collection.reviews)

    def test_import_request_and_options_are_strict(self):
        """Forbid undeclared request fields and expose small platform choices."""

        request = ImportRequest(
            platform="google_maps",
            url="https://www.google.com/maps/place/Test",
            limit=10,
        )
        options = ImportOptions(
            platforms=[
                ImportPlatformOption(
                    key="google_maps",
                    label="Google Maps place",
                    limits=[5, 10, 20],
                )
            ]
        )

        self.assertFalse(request.refresh)
        self.assertEqual(options.platforms[0].limits, [5, 10, 20])
        with self.assertRaises(ValidationError):
            ImportRequest(
                platform="amazon",
                url="https://www.amazon.com/dp/B000000000",
                limit=5,
                secret="not-allowed",
            )


if __name__ == "__main__":
    unittest.main()
