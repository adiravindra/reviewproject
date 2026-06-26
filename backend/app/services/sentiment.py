from dataclasses import dataclass


POSITIVE_WORDS = {
    "amazing",
    "easy",
    "excellent",
    "fast",
    "good",
    "great",
    "helpful",
    "love",
    "perfect",
    "quality",
    "recommend",
}

NEGATIVE_WORDS = {
    "bad",
    "broken",
    "confusing",
    "delayed",
    "difficult",
    "hate",
    "late",
    "not",
    "poor",
    "problem",
    "refund",
    "slow",
    "terrible",
    "unfortunately",
    "waste",
    "worth",
    "worst",
}


SENTIMENT_EVIDENCE_LIMIT = 3


# A tiny sentiment result object keeps the return value easy to read.
@dataclass(frozen=True)
class SentimentResult:
    text: str
    sentiment: str
    score: int


def analyze_sentiment(text: str) -> SentimentResult:
    # Count simple positive and negative words.
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in text.split()}
    score = len(words & POSITIVE_WORDS) - len(words & NEGATIVE_WORDS)

    if score > 0:
        sentiment = "positive"
    elif score < 0:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return SentimentResult(text=text, sentiment=sentiment, score=score)


def explain_sentiment(text: str, sentiment: str, score: int, confidence: float | None = None) -> str:
    """Create a short human-readable reason for the sentiment classification."""
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in text.split()}
    positive_hits = sorted(words & POSITIVE_WORDS)
    negative_hits = sorted(words & NEGATIVE_WORDS)
    confidence_text = _confidence_text(confidence)

    if sentiment == "positive":
        evidence = _evidence_phrase(positive_hits, "positive wording", "positive words")
        return f"This review was classified as positive{confidence_text} because it includes {evidence}."
    if sentiment == "negative":
        evidence = _evidence_phrase(negative_hits, "negative wording or unresolved problems", "negative terms")
        return f"This review was classified as negative{confidence_text} because it includes {evidence}."

    if positive_hits and negative_hits:
        return (
            f"This review was classified as neutral{confidence_text} because it contains both positive and negative signals, "
            "so the overall tone is mixed."
        )
    return (
        f"This review was classified as neutral{confidence_text} because it does not contain enough clearly positive "
        "or negative language to move the result in either direction."
    )


def sentiment_breakdown(review_texts: list[str]) -> dict[str, int]:
    breakdown = {"positive": 0, "neutral": 0, "negative": 0}

    for text in review_texts:
        result = analyze_sentiment(text)
        breakdown[result.sentiment] += 1

    return breakdown


def overall_sentiment(review_texts: list[str]) -> str:
    breakdown = sentiment_breakdown(review_texts)
    positive_count = breakdown["positive"]
    negative_count = breakdown["negative"]

    if positive_count and negative_count:
        return "mixed"
    if positive_count > negative_count:
        return "positive"
    if negative_count > positive_count:
        return "negative"
    return "neutral"


def _confidence_text(confidence: float | None) -> str:
    if confidence is None:
        return ""
    return f" with {confidence:.0%} model confidence"


def _evidence_phrase(matches: list[str], fallback: str, label: str) -> str:
    if not matches:
        return fallback
    examples = ", ".join(matches[:SENTIMENT_EVIDENCE_LIMIT])
    return f"{label} such as {examples}"
