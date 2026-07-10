import re

from bs4 import BeautifulSoup, Tag

from backend.app.schemas.website import ExtractionCandidate
from backend.app.scrapers.base import (
    SCHEMA_ENTITY_TYPES,
    ExtractionResult,
    html_metadata,
    schema_type_names,
)
from backend.app.services.fetching import FetchedPage


_REVIEW_CLASSES = {
    "review",
    "review-card",
    "review-item",
    "customer-review",
    "product-review",
    "user-review",
}
_BODY_SELECTORS = (
    "[itemprop='reviewBody']",
    "[data-testid='review-body']",
    ".review-body",
    ".review-text",
    ".review-content",
)
_NUMBER = re.compile(r"(?<!\d)([0-5](?:\.\d+)?)")
_OUT_OF = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(?:out of|/)\s*([0-9]+(?:\.[0-9]+)?)", re.I)


class StaticHtmlScraper:
    name = "static_html"

    def extract(self, page: FetchedPage) -> ExtractionResult:
        soup = BeautifulSoup(page.html, "html.parser")
        canonical_url, page_title, next_url = html_metadata(soup, page)
        all_containers = [tag for tag in soup.find_all(_is_review_container) if isinstance(tag, Tag)]
        containers = [
            tag
            for tag in all_containers
            if not any(parent in all_containers for parent in tag.parents if isinstance(parent, Tag))
        ]
        candidates: list[ExtractionCandidate] = []
        for container in containers:
            body = _first(container, _BODY_SELECTORS)
            if body is None:
                continue
            text = body.get_text(" ", strip=True)
            if not text:
                continue
            rating, rating_scale = _rating(container)
            author_tag = _first(
                container,
                ("[itemprop='author']", "[data-testid='review-author']", ".review-author"),
            )
            date_tag = _first(container, ("[itemprop='datePublished']", "time"))
            publication_date = None
            if date_tag is not None:
                publication_date = str(date_tag.get("datetime") or date_tag.get("content") or date_tag.get_text(" ", strip=True))
            candidates.append(
                ExtractionCandidate(
                    text=text,
                    rating=rating,
                    rating_scale=rating_scale,
                    author=author_tag.get_text(" ", strip=True) if author_tag else None,
                    publication_date=publication_date,
                    source_url=page.final_url,
                )
            )

        entity_name, entity_type = _entity_metadata(soup)
        return ExtractionResult(
            scraper_name=self.name,
            candidates=candidates,
            supported=bool(all_containers),
            canonical_url=canonical_url,
            entity_name=entity_name,
            entity_type=entity_type,
            page_title=page_title,
            next_url=next_url,
        )


def _is_review_container(tag: Tag) -> bool:
    if not isinstance(tag, Tag):
        return False
    itemprop = {token.casefold() for token in str(tag.get("itemprop", "")).split()}
    if "review" in itemprop:
        return True
    if "Review" in schema_type_names(tag.get("itemtype")):
        return True
    test_id = str(tag.get("data-testid", "")).casefold()
    if test_id in _REVIEW_CLASSES:
        return True
    classes = {str(token).casefold() for token in tag.get("class", [])}
    return bool(classes & _REVIEW_CLASSES)


def _first(container: Tag, selectors: tuple[str, ...]) -> Tag | None:
    for selector in selectors:
        match = container.select_one(selector)
        if isinstance(match, Tag):
            return match
    return None


def _rating(container: Tag) -> tuple[str | None, str | None]:
    element = _first(
        container,
        ("[itemprop='ratingValue']", "[data-rating]", ".review-rating", ".rating"),
    )
    if element is None:
        return None, None
    explicit = element.get("content") or element.get("data-rating")
    text = element.get_text(" ", strip=True)
    match = _OUT_OF.search(text)
    if match:
        return match.group(1), match.group(2)
    if explicit is not None:
        return str(explicit), "5"
    number = _NUMBER.search(text)
    return (number.group(1), "5") if number else (None, None)


def _entity_metadata(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    for tag in soup.find_all(attrs={"itemtype": True}):
        if not isinstance(tag, Tag):
            continue
        entity_type = next(
            (name for name in schema_type_names(tag.get("itemtype")) if name in SCHEMA_ENTITY_TYPES),
            None,
        )
        if not entity_type:
            continue
        name_tag = tag.select_one("[itemprop='name']")
        if not isinstance(name_tag, Tag):
            name_tag = tag.find("h1")
        name = name_tag.get_text(" ", strip=True) if isinstance(name_tag, Tag) else None
        return name or None, entity_type
    return None, None
