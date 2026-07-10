import json
import unittest
from pathlib import Path

from backend.app.services.fetching import FetchedPage


FIXTURES = Path(__file__).parent / "fixtures"


def fixture_page(name: str, url: str = "https://public.example/reviews") -> FetchedPage:
    return FetchedPage(
        requested_url=url,
        final_url=url,
        html=(FIXTURES / name).read_text(encoding="utf-8"),
        status_code=200,
        content_type="text/html; charset=utf-8",
    )


class JsonLdScraperTests(unittest.TestCase):
    def test_extracts_direct_review_lists_with_metadata(self) -> None:
        from backend.app.scrapers.jsonld import JsonLdScraper

        result = JsonLdScraper().extract(
            fixture_page("jsonld_direct.html", "https://public.example/grinder")
        )

        self.assertEqual([item.text for item in result.candidates], ["Excellent grinder.", "Hard to clean."])
        self.assertEqual(result.entity_name, "Burr Grinder")
        self.assertEqual(result.entity_type, "Product")
        self.assertEqual(result.candidates[0].author, "Ada")
        self.assertEqual(result.candidates[0].source_url, "https://public.example/grinder#review-1")
        self.assertEqual(result.next_url, "https://public.example/grinder?page=2")
        self.assertEqual(result.canonical_url, "https://public.example/grinder")

    def test_extracts_nested_graph_entity_and_non_five_star_scale(self) -> None:
        from backend.app.scrapers.jsonld import JsonLdScraper

        result = JsonLdScraper().extract(fixture_page("jsonld_nested.html"))

        self.assertEqual(result.entity_name, "Harbor Hotel")
        self.assertEqual(result.entity_type, "Hotel")
        self.assertEqual(result.candidates[0].rating, "8")
        self.assertEqual(result.candidates[0].rating_scale, "10")
        self.assertEqual(result.candidates[0].publication_date, "2026-05-12")

    def test_ignores_malformed_jsonld_without_treating_prose_as_reviews(self) -> None:
        from backend.app.scrapers.jsonld import JsonLdScraper

        html = '<html><head><script type="application/ld+json">{bad json</script></head><body><p>Great.</p></body></html>'
        result = JsonLdScraper().extract(
            FetchedPage("https://public.example", "https://public.example", html, 200, "text/html")
        )

        self.assertEqual(result.candidates, [])
        self.assertFalse(result.supported)


class StaticHtmlScraperTests(unittest.TestCase):
    def test_extracts_only_semantic_review_cards(self) -> None:
        from backend.app.scrapers.static_html import StaticHtmlScraper

        result = StaticHtmlScraper().extract(
            fixture_page("static_cards_page_1.html", "https://public.example/kettle/reviews")
        )

        self.assertEqual(len(result.candidates), 3)
        self.assertEqual(result.candidates[0].text, "Boils quickly and packs well.")
        self.assertEqual(result.candidates[0].rating, "5")
        self.assertEqual(result.candidates[0].author, "Alex")
        self.assertEqual(result.entity_name, "Trail Kettle")
        self.assertEqual(result.entity_type, "Product")
        self.assertEqual(result.next_url, "https://public.example/kettle/reviews?page=2")

        unsupported = StaticHtmlScraper().extract(fixture_page("unsupported.html"))
        self.assertEqual(unsupported.candidates, [])
        self.assertFalse(unsupported.supported)


class ScraperRegistryTests(unittest.TestCase):
    def test_registry_prefers_jsonld_over_static_cards(self) -> None:
        from backend.app.scrapers.registry import default_registry

        jsonld = json.dumps(
            {"@type": "Product", "name": "Preferred", "review": {"@type": "Review", "reviewBody": "JSON review"}}
        )
        html = f'''<html><head><script type="application/ld+json">{jsonld}</script></head>
        <body><article class="review-card"><p class="review-body">HTML review</p></article></body></html>'''
        page = FetchedPage("https://public.example", "https://public.example", html, 200, "text/html")

        result = default_registry().extract(page)

        self.assertEqual(result.scraper_name, "json_ld")
        self.assertEqual([item.text for item in result.candidates], ["JSON review"])

    def test_registry_returns_explicit_unsupported_result(self) -> None:
        from backend.app.scrapers.registry import default_registry

        result = default_registry().extract(fixture_page("unsupported.html"))

        self.assertEqual(result.scraper_name, "none")
        self.assertFalse(result.supported)
        self.assertEqual(result.candidates, [])


if __name__ == "__main__":
    unittest.main()
