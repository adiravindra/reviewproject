"""Normalize provider candidates into the existing review evidence contract."""

import re
from datetime import datetime
from typing import Any

from backend.app.imports.contracts import NormalizedProviderResult, ProviderImportResult
from backend.app.models import Review


_SPACE = re.compile(r"\s+")
_AMAZON_DATE = re.compile(
    r"\bon\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b",
    re.IGNORECASE,
)
_AXESSO_RATING = re.compile(r"([1-5])\.0 out of 5 stars", re.IGNORECASE)


def _clean(value: Any) -> str:
    """Collapse arbitrary provider text into a bounded plain string."""

    return _SPACE.sub(" ", str(value or "")).strip()


def _rating(value: Any) -> int | None:
    """Accept only an unambiguous one-through-five integer."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    if isinstance(value, float) and value.is_integer() and 1 <= value <= 5:
        return int(value)
    text = _clean(value)
    if len(text) == 1 and text in "12345":
        return int(text)
    match = _AXESSO_RATING.fullmatch(text)
    if match is not None:
        return int(match.group(1))
    return None


def _date(value: Any) -> str | None:
    """Convert supported provider date forms to ISO without guessing."""

    text = _clean(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        match = _AMAZON_DATE.search(text)
        if match is None:
            return None
        try:
            return datetime.strptime(" ".join(match.groups()), "%B %d %Y").date().isoformat()
        except ValueError:
            return None


def normalize_provider_result(result: ProviderImportResult, limit: int) -> NormalizedProviderResult:
    """Filter and normalize candidates before applying the requested limit."""

    reviews: list[Review] = []
    seen: set[str] = set()
    for candidate in result.reviews:
        title = _clean(candidate.title)
        body = _clean(candidate.body)
        if len(body) < 10:
            continue
        text = body if not title or title.casefold() == body.casefold() else f"{title} — {body}"
        text = text[:5000]
        identity = text.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        reviews.append(
            Review(
                id=f"r{len(reviews) + 1}",
                text=text,
                rating=_rating(candidate.rating),
                date=_date(candidate.date),
            )
        )
        if len(reviews) == limit:
            break
    return NormalizedProviderResult(
        title=_clean(result.title) or "Imported reviews",
        source_url=result.source_url,
        source_key=result.source_key,
        reviews=tuple(reviews),
    )
