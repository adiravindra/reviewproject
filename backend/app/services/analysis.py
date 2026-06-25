import re
import uuid
from datetime import UTC, datetime

from backend.app.schemas.reviews import ReviewAnalysisResponse
from backend.app.services.model_sentiment import analyze_sentiment_with_model
from backend.app.services.model_summarizer import summarize_with_model
from backend.app.services.processing import prepare_reviews
from backend.app.services.summarization import summarize_review


TOPIC_TERMS = {
    "pricing": {"billing", "charge", "cost", "expensive", "invoice", "payment", "price", "refund"},
    "bugs/crashes": {"bug", "buggy", "broken", "crash", "crashed", "crashes", "error", "freeze"},
    "performance": {"lag", "laggy", "load", "loading", "slow", "speed", "timeout"},
    "UI/UX": {"confusing", "design", "easy", "interface", "layout", "navigation", "screen", "ui", "ux"},
    "login/auth": {"auth", "authentication", "login", "password", "signin", "sign-in", "signup", "sign-up"},
    "support": {"agent", "help", "helpful", "response", "respond", "support", "ticket"},
    "feature request": {"add", "feature", "missing", "option", "please", "request", "wish"},
}

TOPIC_PHRASES = {
    "login/auth": {"cannot log in", "can't log in", "log in", "sign in", "sign up"},
}

HIGH_URGENCY_TERMS = {
    "broken",
    "crash",
    "crashed",
    "crashes",
    "failed",
    "failure",
    "lost",
    "payment",
    "refund",
    "urgent",
    "urgently",
}

HIGH_URGENCY_PHRASES = {"cannot log in", "can't log in", "lost data", "payment failed"}
MEDIUM_URGENCY_TERMS = {"bug", "error", "late", "slow", "stuck", "timeout"}


# Main backend function: clean text, analyze it, and return one result.
def analyze_review(text: str) -> ReviewAnalysisResponse:
    cleaned_text = prepare_reviews([text])[0]
    sentiment_result = analyze_sentiment_with_model(cleaned_text)
    urgency_score = _urgency_score(cleaned_text, sentiment_result.sentiment)
    sentiment = sentiment_result.sentiment

    if sentiment == "neutral" and urgency_score >= 0.5:
        sentiment = "negative"

    fallback_summary = summarize_review(cleaned_text)
    model_summary = summarize_with_model([cleaned_text], fallback_summary=fallback_summary)

    return ReviewAnalysisResponse(
        id=str(uuid.uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        text=cleaned_text,
        sentiment=sentiment,
        sentiment_score=sentiment_result.score,
        topics=_detect_topics(cleaned_text),
        urgency=_urgency_label(urgency_score),
        urgency_score=urgency_score,
        summary=model_summary.summary,
        summary_source=model_summary.summary_source,
        model_name=model_summary.model_name,
        fallback_reason=model_summary.fallback_reason,
        sentiment_source=sentiment_result.sentiment_source,
        sentiment_model_name=sentiment_result.model_name,
        sentiment_confidence=sentiment_result.confidence,
        sentiment_fallback_reason=sentiment_result.fallback_reason,
    )


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z-']+", text.casefold()))


def _detect_topics(text: str) -> list[str]:
    words = _tokens(text)
    normalized_text = " ".join(text.casefold().split())
    # A topic matches when the review contains one of its simple keywords.
    topics = [
        topic
        for topic, terms in TOPIC_TERMS.items()
        if words & terms or any(phrase in normalized_text for phrase in TOPIC_PHRASES.get(topic, set()))
    ]
    return topics or ["general feedback"]


def _urgency_score(text: str, sentiment: str) -> float:
    words = _tokens(text)
    normalized_text = " ".join(text.casefold().split())
    score = 0.0

    # More urgent words make the score higher.
    score += 0.25 * len(words & HIGH_URGENCY_TERMS)
    score += 0.2 * sum(1 for phrase in HIGH_URGENCY_PHRASES if phrase in normalized_text)
    score += 0.1 * len(words & MEDIUM_URGENCY_TERMS)

    if sentiment == "negative":
        score += 0.15

    return round(min(score, 1.0), 2)


def _urgency_label(score: float) -> str:
    if score >= 0.67:
        return "high"
    if score >= 0.34:
        return "medium"
    return "low"
