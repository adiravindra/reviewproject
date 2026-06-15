import csv
import io
import uuid
from collections import Counter
from datetime import UTC, datetime

from backend.app.schemas.reviews import (
    AnalysisMetrics,
    AnalysisRunResponse,
    KeywordItem,
    ReviewResult,
)
from backend.app.services.insights import build_insights
from backend.app.services.keywords import extract_keywords, extract_themes
from backend.app.services.processing import prepare_reviews
from backend.app.services.sentiment import analyze_sentiment, sentiment_breakdown
from backend.app.services.summarization import summarize_reviews


REVIEW_COLUMN_CANDIDATES = {"review", "reviews", "text", "comment", "feedback"}


def analyze_reviews(review_texts: list[str], source: str = "manual") -> AnalysisRunResponse:
    cleaned_reviews = prepare_reviews(review_texts)
    review_results = [_analyze_review(text) for text in cleaned_reviews]
    summary = summarize_reviews(cleaned_reviews)

    return AnalysisRunResponse(
        id=str(uuid.uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        source=source.strip() or "manual",
        review_count=len(review_results),
        reviews=review_results,
        summary=summary,
        metrics=_build_metrics(cleaned_reviews, review_results),
    )


def parse_csv_reviews(contents: bytes) -> list[str]:
    decoded = contents.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    if not reader.fieldnames:
        raise ValueError("CSV upload must include a header row.")

    review_column = _find_review_column(reader.fieldnames)
    reviews = [row.get(review_column, "") for row in reader]
    return prepare_reviews(reviews)


def estimate_urgency(review_text: str, sentiment: str) -> str:
    urgent_terms = {"broken", "refund", "terrible", "worst", "urgent", "late"}
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in review_text.split()}

    if words & urgent_terms:
        return "high"
    if sentiment == "negative":
        return "medium"
    return "low"


def _analyze_review(text: str) -> ReviewResult:
    sentiment = analyze_sentiment(text)
    themes = extract_themes([text], limit=1)
    keywords = [keyword for keyword, _ in extract_keywords([text], limit=4)]

    return ReviewResult(
        text=text,
        sentiment=sentiment.sentiment,
        sentiment_score=sentiment.score,
        topic=themes[0][0] if themes else "general feedback",
        urgency=estimate_urgency(text, sentiment.sentiment),
        summary=summarize_reviews([text]),
        keywords=keywords,
    )


def _build_metrics(review_texts: list[str], review_results: list[ReviewResult]) -> AnalysisMetrics:
    insights = build_insights(review_texts)
    urgency_counts = Counter(result.urgency for result in review_results)
    topic_counts = Counter(result.topic for result in review_results)

    return AnalysisMetrics(
        review_count=len(review_results),
        overall_sentiment=str(insights["overall_sentiment"]),
        sentiment_breakdown=sentiment_breakdown(review_texts),
        urgency_breakdown={
            "low": urgency_counts.get("low", 0),
            "medium": urgency_counts.get("medium", 0),
            "high": urgency_counts.get("high", 0),
        },
        top_topics=[
            KeywordItem(keyword=topic, count=count)
            for topic, count in topic_counts.most_common(5)
        ],
        high_priority_reviews=urgency_counts.get("high", 0),
    )


def _find_review_column(fieldnames: list[str]) -> str:
    normalized = {field.casefold().strip(): field for field in fieldnames}
    for candidate in REVIEW_COLUMN_CANDIDATES:
        if candidate in normalized:
            return normalized[candidate]
    return fieldnames[0]
