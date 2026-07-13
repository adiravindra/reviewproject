import unittest
from unittest.mock import Mock

from backend.app.errors import AnalysisError
from backend.app.models import AgentInsights, CollectionResult, Review, ReviewSentiment, SourceInfo
from backend.app.service import calculate_metrics, run_analysis


def sample_reviews():
    return [
        Review(id="r1", text="Clear sound and comfortable fit.", rating=5, date="2026-06-01"),
        Review(id="r2", text="Battery is adequate for a normal day.", rating=3),
        Review(id="r3", text="Microphone quality needs meaningful improvement."),
    ]


def sample_sentiments():
    return [
        ReviewSentiment(review_id="r1", sentiment="positive"),
        ReviewSentiment(review_id="r2", sentiment="positive"),
        ReviewSentiment(review_id="r3", sentiment="negative"),
    ]


def sample_collection():
    return CollectionResult(
        source=SourceInfo(
            url="https://example.com/product",
            title="Everyday Headphones",
            extractor="json_ld",
        ),
        reviews=sample_reviews(),
    )


def sample_insights():
    return AgentInsights(
        summary="Sound and comfort are the clearest positives, while microphone quality needs work.",
        overall_sentiment="positive",
        themes=[
            {
                "name": "Daily performance",
                "description": "Customers focus on sound, comfort, battery, and microphone quality.",
                "mentions": 3,
            }
        ],
        strengths=["Clear sound", "Comfortable fit"],
        weaknesses=["Microphone quality"],
        actions=["Improve microphone noise handling"],
        review_sentiments=sample_sentiments(),
    )


class ServiceTests(unittest.TestCase):
    def test_metrics_are_derived_from_reviews_and_sentiments(self):
        metrics = calculate_metrics(sample_reviews(), sample_sentiments())
        self.assertEqual(metrics.review_count, 3)
        self.assertEqual(metrics.rated_count, 2)
        self.assertEqual(metrics.average_rating, 4.0)
        self.assertEqual(metrics.positive_percentage, 66.7)
        self.assertEqual(metrics.sentiment_counts, {"positive": 2, "neutral": 0, "negative": 1})
        self.assertEqual(metrics.rating_distribution, {"1": 0, "2": 0, "3": 1, "4": 0, "5": 1})

    def test_metrics_allow_reviews_without_ratings(self):
        reviews = [
            Review(id="r1", text="A sufficiently detailed unrated review."),
            Review(id="r2", text="Another sufficiently detailed unrated review."),
        ]
        sentiments = [
            ReviewSentiment(review_id="r1", sentiment="neutral"),
            ReviewSentiment(review_id="r2", sentiment="negative"),
        ]
        metrics = calculate_metrics(reviews, sentiments)
        self.assertIsNone(metrics.average_rating)
        self.assertEqual(metrics.rated_count, 0)
        self.assertEqual(metrics.positive_percentage, 0.0)
        self.assertEqual(metrics.rating_distribution, {str(star): 0 for star in range(1, 6)})

    def test_pipeline_calls_each_stage_once_and_returns_contract(self):
        events = []
        credential_validator = Mock(
            side_effect=lambda provider: events.append(("validate", provider))
        )
        collector = Mock(
            side_effect=lambda url: (
                events.append(("collect", url)),
                sample_collection(),
            )[1]
        )
        analyzer = Mock(
            side_effect=lambda reviews, provider: (
                events.append(("analyze", provider)),
                sample_insights(),
            )[1]
        )
        result = run_analysis(
            "https://example.com/product",
            "google",
            credential_validator=credential_validator,
            collector=collector,
            analyzer=analyzer,
        )
        credential_validator.assert_called_once_with("google")
        collector.assert_called_once_with("https://example.com/product")
        analyzer.assert_called_once_with(sample_collection().reviews, "google")
        self.assertEqual(
            events,
            [
                ("validate", "google"),
                ("collect", "https://example.com/product"),
                ("analyze", "google"),
            ],
        )
        self.assertEqual(result.source.title, "Everyday Headphones")
        self.assertEqual(result.metrics.review_count, 3)
        self.assertEqual(result.reviews, sample_collection().reviews)

    def test_credentials_are_validated_before_collection(self):
        events = []

        def validate(provider):
            events.append(("validate", provider))
            raise AnalysisError("invalid_api_key", "The selected credential is invalid.")

        collector = Mock(side_effect=lambda url: events.append(("collect", url)))
        analyzer = Mock()
        with self.assertRaises(AnalysisError):
            run_analysis(
                "https://example.com/product",
                "google",
                credential_validator=validate,
                collector=collector,
                analyzer=analyzer,
            )
        self.assertEqual(events, [("validate", "google")])
        collector.assert_not_called()
        analyzer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
