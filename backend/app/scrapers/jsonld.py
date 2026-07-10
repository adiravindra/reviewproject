import json
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from backend.app.schemas.website import ExtractionCandidate
from backend.app.scrapers.base import (
    SCHEMA_ENTITY_TYPES,
    ExtractionResult,
    html_metadata,
    schema_type_names,
)
from backend.app.services.fetching import FetchedPage


class JsonLdScraper:
    name = "json_ld"

    def extract(self, page: FetchedPage) -> ExtractionResult:
        soup = BeautifulSoup(page.html, "html.parser")
        canonical_url, page_title, next_url = html_metadata(soup, page)
        documents: list[Any] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text()
            if not raw.strip():
                continue
            try:
                documents.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                continue

        nodes = [node for document in documents for node in _walk(document)]
        entity = next((_entity_node(node) for node in nodes if _entity_node(node)), None)
        review_nodes = [node for node in nodes if "Review" in schema_type_names(node.get("@type"))]
        candidates = [candidate for node in review_nodes if (candidate := _review_candidate(node, page.final_url))]
        supported = bool(review_nodes or entity is not None)
        entity_name = _string_value(entity.get("name")) if entity else None
        entity_types = schema_type_names(entity.get("@type")) if entity else []
        entity_type = next((name for name in entity_types if name in SCHEMA_ENTITY_TYPES), None)
        return ExtractionResult(
            scraper_name=self.name,
            candidates=candidates,
            supported=supported,
            canonical_url=canonical_url,
            entity_name=entity_name,
            entity_type=entity_type,
            page_title=page_title,
            next_url=next_url,
        )


def _walk(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _entity_node(node: dict[str, Any]) -> dict[str, Any] | None:
    types = schema_type_names(node.get("@type"))
    if any(name in SCHEMA_ENTITY_TYPES for name in types) and (
        "review" in node or "reviews" in node
    ):
        return node
    return None


def _review_candidate(node: dict[str, Any], page_url: str) -> ExtractionCandidate | None:
    text = _string_value(node.get("reviewBody") or node.get("reviewText"))
    if not text:
        return None
    rating = node.get("reviewRating") or node.get("rating")
    if isinstance(rating, dict):
        rating_value = rating.get("ratingValue")
        rating_scale = rating.get("bestRating")
    else:
        rating_value = node.get("ratingValue")
        rating_scale = node.get("bestRating")
    author = node.get("author")
    if isinstance(author, dict):
        author_value = _string_value(author.get("name"))
    else:
        author_value = _string_value(author)
    source = _string_value(node.get("url"))
    return ExtractionCandidate(
        text=text,
        rating=rating_value,
        rating_scale=rating_scale,
        author=author_value,
        publication_date=_string_value(node.get("datePublished")),
        source_url=urljoin(page_url, source) if source else page_url,
    )


def _string_value(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None
