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
    "poor",
    "problem",
    "refund",
    "slow",
    "terrible",
    "worst",
}


@dataclass(frozen=True)
class SentimentResult:
    text: str
    sentiment: str
    score: int


def analyze_sentiment(text: str) -> SentimentResult:
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in text.split()}
    score = len(words & POSITIVE_WORDS) - len(words & NEGATIVE_WORDS)

    if score > 0:
        sentiment = "positive"
    elif score < 0:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return SentimentResult(text=text, sentiment=sentiment, score=score)


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
