import re
from collections.abc import Iterable


# Keep the review text readable, but remove messy spacing.
def clean_review_text(text: str) -> str:
    """Normalize spacing without changing the customer's wording."""
    return re.sub(r"\s+", " ", text).strip()


def prepare_reviews(review_texts: Iterable[str]) -> list[str]:
    cleaned_reviews: list[str] = []
    seen: set[str] = set()

    # This still accepts a list, even though the MVP sends one review.
    for raw_text in review_texts:
        cleaned_text = clean_review_text(raw_text)
        if not cleaned_text:
            continue

        dedupe_key = cleaned_text.casefold()
        if dedupe_key in seen:
            continue

        cleaned_reviews.append(cleaned_text)
        seen.add(dedupe_key)

    if not cleaned_reviews:
        raise ValueError("At least one non-empty review is required.")

    return cleaned_reviews
