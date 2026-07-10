from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from backend.app.schemas.website import ExtractionCandidate
from backend.app.services.fetching import FetchedPage
from backend.app.services.url_safety import same_origin


SCHEMA_ENTITY_TYPES = {
    "Product",
    "Restaurant",
    "LocalBusiness",
    "Hotel",
    "Place",
    "LodgingBusiness",
    "Store",
    "Service",
    "Organization",
}


@dataclass
class ExtractionResult:
    scraper_name: str
    candidates: list[ExtractionCandidate] = field(default_factory=list)
    supported: bool = False
    canonical_url: str | None = None
    entity_name: str | None = None
    entity_type: str | None = None
    page_title: str | None = None
    next_url: str | None = None


class Scraper(Protocol):
    name: str

    def extract(self, page: FetchedPage) -> ExtractionResult: ...


def html_metadata(
    soup: BeautifulSoup,
    page: FetchedPage,
) -> tuple[str, str | None, str | None]:
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    canonical_url = page.final_url
    canonical = soup.find("link", rel=lambda value: _rel_contains(value, "canonical"))
    if isinstance(canonical, Tag) and canonical.get("href"):
        candidate = urljoin(page.final_url, str(canonical.get("href")))
        if same_origin(page.final_url, candidate):
            canonical_url = candidate

    next_url = None
    for link in soup.find_all("a", href=True):
        if not isinstance(link, Tag) or not _is_trustworthy_next_link(link):
            continue
        candidate = urljoin(page.final_url, str(link.get("href")))
        if same_origin(page.final_url, candidate):
            next_url = candidate
            break
    return canonical_url, title, next_url


def schema_type_names(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value]
    names: list[str] = []
    for item in values:
        if not isinstance(item, str):
            continue
        name = item.rstrip("/").rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        if name:
            names.append(name)
    return names


def _is_trustworthy_next_link(link: Tag) -> bool:
    if _rel_contains(link.get("rel"), "next"):
        return True
    parent = link.parent
    while isinstance(parent, Tag):
        class_tokens = {str(token).casefold() for token in parent.get("class", [])}
        if class_tokens & {"review-pagination", "reviews-pagination"}:
            label = link.get_text(" ", strip=True).casefold()
            return label in {"next", "next page", "more reviews"}
        parent = parent.parent
    return False


def _rel_contains(value: object, expected: str) -> bool:
    if isinstance(value, str):
        values = value.split()
    elif isinstance(value, list):
        values = value
    else:
        return False
    return expected.casefold() in {str(item).casefold() for item in values}
