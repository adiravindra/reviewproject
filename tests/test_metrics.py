import unittest

from backend.app.schemas.website import NormalizedReview


def review(review_id: str, rating: float | None) -> NormalizedReview:
    return NormalizedReview(id=review_id, text=f"Review {review_id}", rating=rating)


class MetricTests(unittest.TestCase):
    def test_counts_ratings_and_sentiments_are_calculated_deterministically(self) -> None:
        from backend.app.services.metrics import calculate_metrics

        metrics = calculate_metrics(
            found_count=4,
            valid_count=3,
            reviews=[review("r1", 1.49), review("r2", 2.50), review("r3", None)],
            sentiments={"r1": "positive", "r2": "negative", "r3": "neutral"},
        )

        self.assertEqual(metrics.reviews_found, 4)
        self.assertEqual(metrics.reviews_valid, 3)
        self.assertEqual(metrics.reviews_analyzed, 3)
        self.assertEqual(metrics.reviews_skipped, 1)
        self.assertEqual(metrics.rated_reviews, 2)
        self.assertEqual(metrics.average_rating, 2.0)
        self.assertEqual(
            metrics.rating_distribution,
            {"1": 1, "2": 0, "3": 1, "4": 0, "5": 0},
        )
        self.assertEqual(
            metrics.sentiment_counts.model_dump(),
            {"positive": 1, "neutral": 1, "negative": 1},
        )
        self.assertEqual(metrics.overall_sentiment, "mixed")

    def test_overall_sentiment_is_the_unique_leader(self) -> None:
        from backend.app.services.metrics import calculate_metrics

        metrics = calculate_metrics(
            found_count=3,
            valid_count=3,
            reviews=[review("r1", 5), review("r2", 4), review("r3", 2)],
            sentiments={"r1": "positive", "r2": "positive", "r3": "negative"},
        )

        self.assertEqual(metrics.overall_sentiment, "positive")

    def test_missing_or_unknown_sentiments_are_rejected(self) -> None:
        from backend.app.services.metrics import calculate_metrics

        with self.assertRaises(ValueError):
            calculate_metrics(
                found_count=1,
                valid_count=1,
                reviews=[review("r1", 5)],
                sentiments={"r1": "delighted"},
            )


if __name__ == "__main__":
    unittest.main()
