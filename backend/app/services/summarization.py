def summarize_review(text: str, max_length: int = 180) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) > max_length:
        cleaned = f"{cleaned[: max_length - 3].rstrip()}..."
    return f"This review says: {cleaned}"
