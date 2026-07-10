import hashlib
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from backend.app.schemas.website import (
    ExtractionCandidate,
    NormalizationResult,
    NormalizedReview,
)


_WHITESPACE = re.compile(r"\s+")


def normalize_reviews(
    candidates: list[ExtractionCandidate],
    max_reviews: int,
) -> NormalizationResult:
    if max_reviews < 1:
        raise ValueError("max_reviews must be positive")

    unique: list[NormalizedReview] = []
    seen_text: set[str] = set()
    invalid_removed = 0
    duplicates_removed = 0

    for candidate in candidates:
        text = clean_text(candidate.text)
        if not _is_valid_review_text(text):
            invalid_removed += 1
            continue

        duplicate_key = text.casefold()
        if duplicate_key in seen_text:
            duplicates_removed += 1
            continue
        seen_text.add(duplicate_key)

        rating, original_rating, rating_scale = _normalize_rating(
            candidate.rating,
            candidate.rating_scale,
        )
        publication_date = _clean_optional(candidate.publication_date)
        source_url = _clean_optional(candidate.source_url)
        unique.append(
            NormalizedReview(
                id=_stable_review_id(text, rating, publication_date, source_url),
                text=text,
                rating=rating,
                original_rating=original_rating,
                rating_scale=rating_scale,
                author=_clean_optional(candidate.author),
                publication_date=publication_date,
                source_url=source_url,
            )
        )

    valid_count = len(unique)
    analyzed = unique[:max_reviews]
    return NormalizationResult(
        reviews=analyzed,
        found_count=len(candidates),
        valid_count=valid_count,
        duplicates_removed=duplicates_removed,
        invalid_removed=invalid_removed,
        omitted_by_cap=max(0, valid_count - len(analyzed)),
    )


def clean_text(value: str) -> str:
    return _WHITESPACE.sub(" ", str(value)).strip()


def _is_valid_review_text(text: str) -> bool:
    return len(text) >= 3 and any(character.isalpha() for character in text)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = clean_text(value)
    return cleaned or None


def _normalize_rating(
    rating_value: float | str | None,
    scale_value: float | str | None,
) -> tuple[float | None, float | None, float | None]:
    if rating_value is None:
        return None, None, None
    try:
        rating = Decimal(str(rating_value))
        scale = Decimal(str(scale_value if scale_value is not None else 5))
    except (InvalidOperation, ValueError):
        return None, None, None
    if not rating.is_finite() or not scale.is_finite() or rating <= 0 or scale <= 0 or rating > scale:
        return None, None, None

    normalized = rating if scale == 5 else rating / scale * Decimal("5")
    normalized = min(Decimal("5"), max(Decimal("1"), normalized))
    normalized = normalized.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    normalized_float = float(normalized)
    if scale == 5:
        return normalized_float, None, None
    return normalized_float, float(rating), float(scale)


def _stable_review_id(
    text: str,
    rating: float | None,
    publication_date: str | None,
    source_url: str | None,
) -> str:
    material = "\x1f".join(
        [
            text.casefold(),
            "" if rating is None else f"{rating:.2f}",
            publication_date or "",
            source_url or "",
        ]
    )
    return f"review_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:16]}"
