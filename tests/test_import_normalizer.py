"""Verify provider-neutral review normalization and privacy boundaries."""

import unittest

from backend.app.imports.contracts import ProviderImportResult, ProviderReviewCandidate
from backend.app.imports.normalizer import normalize_provider_result


class ImportNormalizerTests(unittest.TestCase):
    """Cover provider-neutral evidence filtering and normalization."""

    def test_normalizes_filters_deduplicates_then_limits(self):
        """Filter unusable entries before deduplication and limiting."""

        result = ProviderImportResult(
            title="  Test   place  ",
            source_url="https://example.test/place",
            source_key="place-1",
            reviews=(
                ProviderReviewCandidate(
                    title="Excellent visit",
                    body="  Friendly   team and excellent coffee. ",
                    rating=5,
                    date="2026-07-20T12:30:00Z",
                ),
                ProviderReviewCandidate(
                    title="Excellent visit",
                    body="Friendly team and excellent coffee.",
                    rating="5.0",
                    date="not-a-date",
                ),
                ProviderReviewCandidate(title=None, body="Too short", rating=1, date=None),
                ProviderReviewCandidate(
                    title="Useful",
                    body="The seating area was clean and comfortable.",
                    rating="4",
                    date="Reviewed in the United States on January 23, 2018",
                ),
                ProviderReviewCandidate(title=None, body=None, rating=3, date=None),
            ),
        )

        normalized = normalize_provider_result(result, limit=2)

        self.assertEqual(normalized.title, "Test place")
        self.assertEqual([review.id for review in normalized.reviews], ["r1", "r2"])
        self.assertEqual(
            normalized.reviews[0].text,
            "Excellent visit — Friendly team and excellent coffee.",
        )
        self.assertEqual(normalized.reviews[0].rating, 5)
        self.assertEqual(normalized.reviews[0].date, "2026-07-20")
        self.assertEqual(normalized.reviews[1].rating, 4)
        self.assertEqual(normalized.reviews[1].date, "2018-01-23")

    def test_rejects_ambiguous_ratings_and_caps_text(self):
        """Keep ambiguous ratings absent and enforce the evidence text cap."""

        long_text = "A" * 6000
        result = ProviderImportResult(
            title="Product",
            source_url="https://example.test/product",
            source_key=None,
            reviews=(
                ProviderReviewCandidate(None, long_text, "4.5", None),
                ProviderReviewCandidate(None, "This review has a valid integer rating.", True, None),
            ),
        )

        normalized = normalize_provider_result(result, limit=10)

        self.assertEqual(len(normalized.reviews[0].text), 5000)
        self.assertIsNone(normalized.reviews[0].rating)
        self.assertIsNone(normalized.reviews[1].rating)

    def test_accepts_only_axesso_integer_star_rating_text(self):
        """Parse Axesso whole-star text without rounding or digit extraction."""

        result = ProviderImportResult(
            title="Product",
            source_url="https://www.amazon.com/dp/B000000000",
            source_key="B000000000",
            reviews=(
                ProviderReviewCandidate(
                    None,
                    "This review has an exact whole-star Axesso rating.",
                    "5.0 out of 5 stars",
                    None,
                ),
                ProviderReviewCandidate(
                    None,
                    "This review has a fractional Axesso rating.",
                    "4.5 out of 5 stars",
                    None,
                ),
                ProviderReviewCandidate(
                    None,
                    "This review embeds a rating in unrelated text.",
                    "Rating is 5.0 out of 5 stars",
                    None,
                ),
            ),
        )

        normalized = normalize_provider_result(result, limit=10)

        self.assertEqual(normalized.reviews[0].rating, 5)
        self.assertIsNone(normalized.reviews[1].rating)
        self.assertIsNone(normalized.reviews[2].rating)


if __name__ == "__main__":
    unittest.main()
