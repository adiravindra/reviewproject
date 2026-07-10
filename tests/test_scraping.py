import unittest
from pathlib import Path
from typing import Any

from backend.app.errors import AppError
from backend.app.scrapers.registry import default_registry
from backend.app.services.fetching import FetchedPage
from backend.app.settings import Settings


FIXTURES = Path(__file__).parent / "fixtures"


def fixture_page(name: str, url: str) -> FetchedPage:
    return FetchedPage(
        requested_url=url,
        final_url=url,
        html=(FIXTURES / name).read_text(encoding="utf-8"),
        status_code=200,
        content_type="text/html; charset=utf-8",
    )


class MappingFetcher:
    def __init__(self, outcomes: dict[str, FetchedPage | AppError]) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[str, float | None]] = []

    def fetch(self, url: str, deadline: float | None = None) -> FetchedPage:
        self.calls.append((url, deadline))
        outcome = self.outcomes[url]
        if isinstance(outcome, AppError):
            raise outcome
        return outcome


def scrape_failure(url: str) -> AppError:
    return AppError(
        code="scrape_failed",
        message="The website could not be reached.",
        stage="scraping",
        status_code=502,
        retryable=True,
        details={"url": url},
    )


class ScrapingOrchestrationTests(unittest.TestCase):
    def test_follows_same_origin_pages_and_applies_cap_after_deduplication(self) -> None:
        from backend.app.services.scraping import collect_reviews

        first_url = "https://public.example/kettle/reviews"
        second_url = "https://public.example/kettle/reviews?page=2"
        fetcher = MappingFetcher(
            {
                first_url: fixture_page("static_cards_page_1.html", first_url),
                second_url: fixture_page("static_cards_page_2.html", second_url),
            }
        )

        result = collect_reviews(
            first_url,
            fetcher=fetcher,
            registry=default_registry(),
            settings=Settings(max_pages=2, max_reviews=4),
        )

        self.assertEqual([call[0] for call in fetcher.calls], [first_url, second_url])
        self.assertEqual(result.pages_attempted, 2)
        self.assertEqual(result.pages_succeeded, 2)
        self.assertEqual(result.normalization.found_count, 6)
        self.assertEqual(result.normalization.valid_count, 6)
        self.assertEqual(result.normalization.analyzed_count, 4)
        self.assertEqual(result.normalization.omitted_by_cap, 2)
        self.assertEqual(result.scraper_name, "static_html")
        self.assertEqual(result.entity_name, "Trail Kettle")
        self.assertIn("Only the first 4 unique reviews were analyzed.", result.warnings)

    def test_later_page_failure_is_partial_after_enough_valid_reviews(self) -> None:
        from backend.app.services.scraping import collect_reviews

        first_url = "https://public.example/kettle/reviews"
        second_url = "https://public.example/kettle/reviews?page=2"
        fetcher = MappingFetcher(
            {
                first_url: fixture_page("static_cards_page_1.html", first_url),
                second_url: scrape_failure(second_url),
            }
        )

        result = collect_reviews(first_url, fetcher=fetcher, registry=default_registry(), settings=Settings())

        self.assertTrue(result.partial_success)
        self.assertEqual(result.pages_attempted, 2)
        self.assertEqual(result.pages_succeeded, 1)
        self.assertIn("Some later review pages could not be collected.", result.warnings)
        self.assertIn("Only 3 reviews were available, so insights may be less reliable.", result.warnings)

    def test_later_page_failure_does_not_hide_insufficient_collection(self) -> None:
        from backend.app.services.scraping import collect_reviews

        first_url = "https://public.example/one"
        second_url = "https://public.example/two"
        one_review = FetchedPage(
            first_url,
            first_url,
            '<article class="review-card"><p class="review-body">Only one review.</p></article><a rel="next" href="/two">Next</a>',
            200,
            "text/html",
        )
        fetcher = MappingFetcher({first_url: one_review, second_url: scrape_failure(second_url)})

        with self.assertRaises(AppError) as raised:
            collect_reviews(first_url, fetcher=fetcher, registry=default_registry(), settings=Settings())

        self.assertEqual(raised.exception.code, "scrape_failed")

    def test_distinguishes_unsupported_no_reviews_and_insufficient_reviews(self) -> None:
        from backend.app.services.scraping import collect_reviews

        unsupported_url = "https://public.example/unsupported"
        empty_url = "https://public.example/empty"
        one_url = "https://public.example/one"
        pages: list[tuple[str, FetchedPage, str]] = [
            (unsupported_url, fixture_page("unsupported.html", unsupported_url), "unsupported_source"),
            (
                empty_url,
                FetchedPage(
                    empty_url,
                    empty_url,
                    '<script type="application/ld+json">{"@type":"Product","name":"Empty","review":[]}</script>',
                    200,
                    "text/html",
                ),
                "no_reviews_found",
            ),
            (
                one_url,
                FetchedPage(
                    one_url,
                    one_url,
                    '<article class="review-card"><p class="review-body">Only one valid review.</p></article>',
                    200,
                    "text/html",
                ),
                "insufficient_reviews",
            ),
        ]

        for url, page, code in pages:
            with self.subTest(code=code), self.assertRaises(AppError) as raised:
                collect_reviews(
                    url,
                    fetcher=MappingFetcher({url: page}),
                    registry=default_registry(),
                    settings=Settings(),
                )
            self.assertEqual(raised.exception.code, code)

    def test_page_limit_stops_pagination_with_explicit_warning(self) -> None:
        from backend.app.services.scraping import collect_reviews

        first_url = "https://public.example/kettle/reviews"
        second_url = "https://public.example/kettle/reviews?page=2"
        second = fixture_page("static_cards_page_2.html", second_url)
        second_with_next = FetchedPage(
            second.requested_url,
            second.final_url,
            second.html.replace("</body>", '<a rel="next" href="?page=3">Next</a></body>'),
            second.status_code,
            second.content_type,
        )
        fetcher = MappingFetcher(
            {
                first_url: fixture_page("static_cards_page_1.html", first_url),
                second_url: second_with_next,
            }
        )

        result = collect_reviews(
            first_url,
            fetcher=fetcher,
            registry=default_registry(),
            settings=Settings(max_pages=2),
        )

        self.assertEqual(len(fetcher.calls), 2)
        self.assertIn("Pagination stopped at the 2-page safety limit.", result.warnings)


if __name__ == "__main__":
    unittest.main()
