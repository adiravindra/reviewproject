import unittest

from backend.app.schemas.website import ExtractionCandidate


class NormalizationTests(unittest.TestCase):
    def test_cleans_deduplicates_scales_ratings_and_caps_after_filtering(self) -> None:
        from backend.app.services.normalization import normalize_reviews

        result = normalize_reviews(
            [
                ExtractionCandidate(
                    text="  Great   stay. \n",
                    rating=8,
                    rating_scale=10,
                    author=" Ada ",
                    publication_date=" 2026-07-01 ",
                    source_url=" https://public.example/reviews#one ",
                ),
                ExtractionCandidate(text="great stay.", rating=4, rating_scale=5),
                ExtractionCandidate(text=" "),
                ExtractionCandidate(text="Quiet room", rating=3, rating_scale=5),
            ],
            max_reviews=1,
        )

        self.assertEqual(result.found_count, 4)
        self.assertEqual(result.valid_count, 2)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(result.invalid_removed, 1)
        self.assertEqual(result.omitted_by_cap, 1)
        self.assertEqual(result.analyzed_count, 1)
        self.assertEqual(result.reviews[0].text, "Great stay.")
        self.assertEqual(result.reviews[0].rating, 4.0)
        self.assertEqual(result.reviews[0].original_rating, 8.0)
        self.assertEqual(result.reviews[0].rating_scale, 10.0)
        self.assertEqual(result.reviews[0].author, "Ada")

    def test_stable_ids_do_not_depend_on_author_and_invalid_ratings_are_omitted(self) -> None:
        from backend.app.services.normalization import normalize_reviews

        first = normalize_reviews(
            [ExtractionCandidate(text="Original wording", rating=7, rating_scale=5, author="One")],
            max_reviews=60,
        ).reviews[0]
        second = normalize_reviews(
            [ExtractionCandidate(text="Original wording", rating=7, rating_scale=5, author="Two")],
            max_reviews=60,
        ).reviews[0]

        self.assertEqual(first.id, second.id)
        self.assertIsNone(first.rating)
        self.assertIsNone(first.original_rating)
        self.assertIsNone(first.rating_scale)
        self.assertEqual(first.text, "Original wording")

    def test_case_insensitive_exact_duplicates_do_not_remove_distinct_wording(self) -> None:
        from backend.app.services.normalization import normalize_reviews

        result = normalize_reviews(
            [
                ExtractionCandidate(text="Service was quick."),
                ExtractionCandidate(text="service was quick."),
                ExtractionCandidate(text="Service was very quick."),
            ],
            max_reviews=60,
        )

        self.assertEqual(result.valid_count, 2)
        self.assertEqual([review.text for review in result.reviews], ["Service was quick.", "Service was very quick."])


if __name__ == "__main__":
    unittest.main()
