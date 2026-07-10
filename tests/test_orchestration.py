import unittest
from datetime import datetime, timezone

from backend.app.errors import AppError
from backend.app.schemas.website import (
    NormalizationResult,
    NormalizedReview,
    WebsiteInsights,
)
from backend.app.services.analysis import CollectionAnalysisResult
from backend.app.services.scraping import ScrapeResult
from backend.app.settings import Settings
from tests.factories import complete_response


def scrape_result() -> ScrapeResult:
    reviews = [
        NormalizedReview(id="r1", text="Excellent quality and simple setup.", rating=5, author="Ada"),
        NormalizedReview(id="r2", text="Support was slow to respond.", rating=2, author="Grace"),
    ]
    return ScrapeResult(
        requested_url="https://public.example/reviews",
        canonical_url="https://public.example/product",
        entity_name="Example Product",
        entity_type="Product",
        page_title="Example Product Reviews",
        scraper_name="json_ld",
        pages_attempted=1,
        pages_succeeded=1,
        normalization=NormalizationResult(
            reviews=reviews,
            found_count=3,
            valid_count=2,
            duplicates_removed=1,
            invalid_removed=0,
            omitted_by_cap=0,
        ),
        partial_success=True,
        warnings=["Some later review pages could not be collected."],
    )


def analysis_result() -> CollectionAnalysisResult:
    return CollectionAnalysisResult(
        insights=complete_response().insights,
        sentiments={"r1": "positive", "r2": "negative"},
        batch_count=1,
        call_count=2,
    )


class SequenceClock:
    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


class OrchestrationTests(unittest.TestCase):
    def test_builds_validated_response_and_saves_once_after_completion(self) -> None:
        from backend.app.services.orchestration import AnalysisDependencies, run_website_analysis

        saved = []
        dependencies = AnalysisDependencies(
            settings=Settings(),
            scrape=lambda url, deadline: scrape_result(),
            analyze=lambda review_items: analysis_result(),
            save=saved.append,
            clock=lambda: 10.0,
            id_factory=lambda: "run_orchestrated",
            now=lambda: datetime(2026, 7, 10, 15, 30, tzinfo=timezone.utc),
        )

        result = run_website_analysis("https://public.example/reviews", dependencies)

        self.assertEqual(result.id, "run_orchestrated")
        self.assertEqual(result.collection.found, 3)
        self.assertEqual(result.collection.valid, 2)
        self.assertEqual(result.collection.analyzed, 2)
        self.assertTrue(result.collection.partial_success)
        self.assertEqual(result.metrics.average_rating, 3.5)
        self.assertEqual(result.metrics.sentiment_counts.positive, 1)
        self.assertEqual(result.metrics.sentiment_counts.negative, 1)
        self.assertEqual(result.metrics.overall_sentiment, "mixed")
        self.assertEqual(result.reviews[0].author, "Ada")
        self.assertEqual(result.analysis.completed_at, "2026-07-10T15:30:00Z")
        self.assertEqual(saved, [result])

    def test_scrape_analysis_and_timeout_failures_never_save(self) -> None:
        from backend.app.services.orchestration import AnalysisDependencies, run_website_analysis

        failures = [
            (
                lambda url, deadline: (_ for _ in ()).throw(
                    AppError("scrape_failed", "Could not collect reviews.", "scraping", 502)
                ),
                lambda review_items: analysis_result(),
                lambda: 0.0,
                "scrape_failed",
            ),
            (
                lambda url, deadline: scrape_result(),
                lambda review_items: (_ for _ in ()).throw(
                    AppError("llm_failed", "Provider failed.", "analysis", 502)
                ),
                lambda: 0.0,
                "llm_failed",
            ),
            (
                lambda url, deadline: scrape_result(),
                lambda review_items: analysis_result(),
                SequenceClock([0.0, 121.0]),
                "request_timeout",
            ),
        ]

        for scrape, analyze, clock, code in failures:
            saved = []
            dependencies = AnalysisDependencies(
                settings=Settings(),
                scrape=scrape,
                analyze=analyze,
                save=saved.append,
                clock=clock,
                id_factory=lambda: "never-saved",
                now=lambda: datetime.now(timezone.utc),
            )
            with self.subTest(code=code), self.assertRaises(AppError) as raised:
                run_website_analysis("https://public.example/reviews", dependencies)
            self.assertEqual(raised.exception.code, code)
            self.assertEqual(saved, [])

    def test_persistence_failure_is_sanitized(self) -> None:
        from backend.app.services.orchestration import AnalysisDependencies, run_website_analysis

        dependencies = AnalysisDependencies(
            settings=Settings(),
            scrape=lambda url, deadline: scrape_result(),
            analyze=lambda review_items: analysis_result(),
            save=lambda result: (_ for _ in ()).throw(RuntimeError("secret database path")),
            clock=lambda: 0.0,
            id_factory=lambda: "save-fails",
            now=lambda: datetime.now(timezone.utc),
        )

        with self.assertRaises(AppError) as raised:
            run_website_analysis("https://public.example/reviews", dependencies)

        self.assertEqual(raised.exception.stage, "persistence")
        self.assertNotIn("secret", raised.exception.message)


if __name__ == "__main__":
    unittest.main()
