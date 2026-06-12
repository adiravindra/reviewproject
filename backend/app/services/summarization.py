from backend.app.services.keywords import extract_keywords


def _truncate(text: str, max_length: int = 180) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def summarize_reviews(review_texts: list[str]) -> str:
    if len(review_texts) == 1:
        return f"This review says: {_truncate(review_texts[0])}"

    keywords = [keyword for keyword, _ in extract_keywords(review_texts, limit=3)]
    keyword_phrase = ", ".join(keywords) if keywords else "general customer feedback"

    return (
        f"Summary of {len(review_texts)} reviews: customers frequently mention "
        f"{keyword_phrase}. Review the detailed themes for specific follow-up."
    )
