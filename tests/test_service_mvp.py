"""Test deterministic metrics and staged collection-analysis orchestration."""

import os
import unittest
from unittest.mock import Mock, patch

from backend.app.errors import AnalysisError
from backend.app.models import (
    AgentInsights,
    AnalysisRequest,
    CollectionResult,
    Review,
    ReviewSentiment,
    SourceInfo,
)
from backend.app.service import calculate_metrics, run_analysis


def sample_reviews():
    """Build representative rated and unrated normalized reviews."""

    return [
        Review(id="r1", text="Clear sound and comfortable fit.", rating=5, date="2026-06-01"),
        Review(id="r2", text="Battery is adequate for a normal day.", rating=3),
        Review(id="r3", text="Microphone quality needs meaningful improvement."),
    ]


def sample_sentiments():
    """Build exact sentiment assignments for the sample review IDs."""

    return [
        ReviewSentiment(review_id="r1", sentiment="positive"),
        ReviewSentiment(review_id="r2", sentiment="positive"),
        ReviewSentiment(review_id="r3", sentiment="negative"),
    ]


def sample_collection():
    """Build a validated collector result for orchestration tests."""

    return CollectionResult(
        source=SourceInfo(
            url="https://example.com/product",
            title="Everyday Headphones",
            extractor="json_ld",
            is_demo=False,
        ),
        reviews=sample_reviews(),
    )


def sample_analysis_request():
    """Build the validated request consumed by the analysis service."""

    collection = sample_collection()
    return AnalysisRequest(source=collection.source, reviews=collection.reviews)


def sample_insights():
    """Build validated structured agent insights for service tests."""

    return AgentInsights(
        summary="Sound and comfort are the clearest positives, while microphone quality needs work.",
        overall_sentiment="positive",
        themes=[
            {
                "name": "Daily performance",
                "description": "Customers focus on sound, comfort, battery, and microphone quality.",
                "mentions": 3,
                "sentiment": "positive",
            }
        ],
        strengths=["Clear sound", "Comfortable fit"],
        weaknesses=["Microphone quality"],
        actions=["Improve microphone noise handling"],
        review_sentiments=sample_sentiments(),
    )


class ServiceTests(unittest.TestCase):
    """Group metric determinism and pipeline-order regression contracts."""

    def test_metrics_are_derived_from_reviews_and_sentiments(self):
        """Compute all aggregate values directly from reviews and sentiments."""

        metrics = calculate_metrics(sample_reviews(), sample_sentiments())
        self.assertEqual(metrics.review_count, 3)
        self.assertEqual(metrics.rated_count, 2)
        self.assertEqual(metrics.average_rating, 4.0)
        self.assertEqual(metrics.positive_percentage, 66.7)
        self.assertEqual(
            metrics.sentiment_counts,
            {"positive": 2, "neutral": 0, "negative": 1, "mixed": 0},
        )
        self.assertEqual(metrics.rating_distribution, {"1": 0, "2": 0, "3": 1, "4": 0, "5": 1})

    def test_metrics_count_mixed_reviews_without_inflating_positive_share(self):
        """Keep legitimate mixed evidence visible while preserving the positive numerator."""

        sentiments = [
            ReviewSentiment(review_id="r1", sentiment="positive"),
            ReviewSentiment(review_id="r2", sentiment="mixed"),
            ReviewSentiment(review_id="r3", sentiment="negative"),
        ]

        metrics = calculate_metrics(sample_reviews(), sentiments)

        self.assertEqual(metrics.positive_percentage, 33.3)
        self.assertEqual(
            metrics.sentiment_counts,
            {"positive": 1, "neutral": 0, "negative": 1, "mixed": 1},
        )

    def test_metrics_allow_reviews_without_ratings(self):
        """Keep unrated review metrics defined without inventing an average."""

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

    def test_pipeline_validates_then_analyzes_exact_collection_once(self):
        """Validate Groq once before analyzing exactly the submitted evidence."""

        events = []
        request = sample_analysis_request()
        credential_validator = Mock(side_effect=lambda: events.append("validate"))
        analyzer = Mock(
            side_effect=lambda reviews: (
                events.append("analyze"),
                sample_insights(),
            )[1]
        )
        result = run_analysis(
            request,
            credential_validator=credential_validator,
            analyzer=analyzer,
        )
        credential_validator.assert_called_once_with()
        analyzer.assert_called_once_with(request.reviews)
        self.assertEqual(events, ["validate", "analyze"])
        self.assertIs(result.source, request.source)
        self.assertEqual(result.metrics.review_count, 3)
        self.assertEqual(result.reviews, request.reviews)
        self.assertIsNone(result.history_id)

    def test_analysis_subset_preserves_one_hundred_review_source_provenance(self):
        """Analyze exactly 40 reviews while retaining the actual imported count."""

        reviews = [
            Review(
                id=f"r{index + 1}",
                text=f"Imported review number {index + 1} has useful evidence.",
                rating=5,
            )
            for index in range(40)
        ]
        request = AnalysisRequest(
            source=SourceInfo(
                url="https://www.amazon.com/dp/B000000000",
                title="Fixture product",
                extractor="provider_api",
                is_demo=False,
                platform="amazon",
                provider="Apify (Axesso)",
                requested_count=100,
                retrieved_count=100,
                retrieved_at="2026-07-23T12:00:00Z",
                cache_status="miss",
            ),
            reviews=reviews,
        )
        analyzer = Mock(
            return_value=AgentInsights(
                summary="The analyzed subset is consistently positive.",
                overall_sentiment="positive",
                themes=[
                    {
                        "name": "Consistency",
                        "description": "The submitted reviews consistently describe useful evidence.",
                        "mentions": 40,
                        "sentiment": "positive",
                    }
                ],
                strengths=["Consistent results"],
                weaknesses=[],
                actions=[],
                review_sentiments=[
                    ReviewSentiment(review_id=review.id, sentiment="positive")
                    for review in reviews
                ],
            )
        )

        result = run_analysis(
            request,
            credential_validator=lambda: None,
            analyzer=analyzer,
        )

        analyzer.assert_called_once_with(reviews)
        self.assertEqual(result.source.retrieved_count, 100)
        self.assertEqual(result.metrics.review_count, 40)
        self.assertEqual(len(result.reviews), 40)

    def test_credential_failure_stops_analyzer_and_metrics(self):
        """Stop all downstream analysis work when Groq preflight rejects a key."""

        def validate():
            """Simulate a Groq credential rejection."""

            raise AnalysisError("invalid_api_key", "The selected credential is invalid.")

        analyzer = Mock()
        with self.assertRaises(AnalysisError):
            run_analysis(
                sample_analysis_request(),
                credential_validator=validate,
                analyzer=analyzer,
            )
        analyzer.assert_not_called()

    def test_blank_groq_key_stops_before_analyzer_or_http_call(self):
        """Use the real preflight to reject a blank key before analysis begins."""

        analyzer = Mock()
        with patch("backend.app.credentials.requests.get") as request_get:
            with patch.dict(
                os.environ,
                {"GROQ_API_KEY": "   "},
                clear=True,
            ):
                with self.assertRaises(AnalysisError) as raised:
                    run_analysis(
                        sample_analysis_request(),
                        analyzer=analyzer,
                    )

        self.assertEqual(raised.exception.code, "missing_api_key")
        request_get.assert_not_called()
        analyzer.assert_not_called()

    def test_demo_collection_metadata_is_preserved(self):
        """Keep URL-less demo provenance intact across the analysis boundary."""

        collection = CollectionResult(
            source=SourceInfo(
                url=None,
                title="Demo reviews",
                extractor="demo",
                is_demo=True,
            ),
            reviews=sample_reviews(),
        )
        request = AnalysisRequest(source=collection.source, reviews=collection.reviews)
        result = run_analysis(
            request,
            credential_validator=lambda: None,
            analyzer=lambda reviews: sample_insights(),
        )
        self.assertIs(result.source, request.source)
        self.assertIsNone(result.source.url)
        self.assertEqual(result.source.extractor, "demo")
        self.assertTrue(result.source.is_demo)

    def test_service_has_no_collection_or_provider_orchestration(self):
        """Keep collection and provider selection out of the staged service."""

        with open("backend/app/service.py", encoding="utf-8") as service_file:
            service_source = service_file.read()
        self.assertNotIn("Provider", service_source)
        self.assertNotIn("collect_reviews", service_source)
        self.assertNotIn("url: str", service_source)


if __name__ == "__main__":
    unittest.main()
