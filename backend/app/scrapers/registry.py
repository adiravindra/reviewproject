from backend.app.scrapers.base import ExtractionResult, Scraper
from backend.app.scrapers.jsonld import JsonLdScraper
from backend.app.scrapers.static_html import StaticHtmlScraper
from backend.app.services.fetching import FetchedPage


class ScraperRegistry:
    def __init__(self, scrapers: list[Scraper]) -> None:
        self.scrapers = scrapers

    def extract(self, page: FetchedPage, preferred_name: str | None = None) -> ExtractionResult:
        ordered = self.scrapers
        if preferred_name:
            preferred = [scraper for scraper in self.scrapers if scraper.name == preferred_name]
            others = [scraper for scraper in self.scrapers if scraper.name != preferred_name]
            ordered = preferred + others

        supported_result: ExtractionResult | None = None
        for scraper in ordered:
            result = scraper.extract(page)
            if result.candidates:
                return result
            if result.supported and supported_result is None:
                supported_result = result
        if supported_result is not None:
            return supported_result
        return ExtractionResult(
            scraper_name="none",
            supported=False,
            canonical_url=page.final_url,
        )


def default_registry() -> ScraperRegistry:
    return ScraperRegistry([JsonLdScraper(), StaticHtmlScraper()])
