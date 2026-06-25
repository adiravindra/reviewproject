# Simple fallback summary used when the model is not available.
def summarize_review(text: str, max_length: int = 180) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) > max_length:
        cleaned = f"{cleaned[: max_length - 3].rstrip()}..."
    return (
        f"The review states that {cleaned[:1].casefold()}{cleaned[1:]}. "
        "This is because the customer mentions specific details from the review."
    )
