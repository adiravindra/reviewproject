import uuid
from collections import Counter
from datetime import UTC, datetime
import re

from backend.app.schemas.reviews import ReviewAnalysisResponse, ReviewReportResponse, ReviewSentimentItem
from backend.app.services.model_sentiment import analyze_sentiment_with_model, analyze_sentiments_with_model
from backend.app.services.model_summarizer import summarize_with_model
from backend.app.services.processing import prepare_reviews
from backend.app.services.sentiment import NEGATIVE_WORDS, POSITIVE_WORDS, explain_sentiment, sentiment_evidence
from backend.app.services.summarization import summarize_review


REPORT_TERM_LIMIT = 8
STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "because",
    "but",
    "for",
    "from",
    "had",
    "have",
    "into",
    "its",
    "not",
    "our",
    "out",
    "that",
    "the",
    "their",
    "them",
    "then",
    "this",
    "was",
    "were",
    "with",
}
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")


# Main backend function: clean text, analyze it, and return one result.
def analyze_review(text: str) -> ReviewAnalysisResponse:
    cleaned_text = prepare_reviews([text])[0]
    sentiment_result = analyze_sentiment_with_model(cleaned_text)
    sentiment = sentiment_result.sentiment

    # Build the fallback text only as a recovery path. The model result is used
    # unless model loading, inference, or decoding fails.
    fallback_summary = summarize_review(cleaned_text)
    model_summary = summarize_with_model([cleaned_text], fallback_summary=fallback_summary)

    return ReviewAnalysisResponse(
        id=str(uuid.uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        text=cleaned_text,
        sentiment=sentiment,
        sentiment_score=sentiment_result.score,
        summary=model_summary.summary,
        summary_source=model_summary.summary_source,
        model_name=model_summary.model_name,
        fallback_reason=model_summary.fallback_reason,
        sentiment_source=sentiment_result.sentiment_source,
        sentiment_explanation=explain_sentiment(
            cleaned_text,
            sentiment,
            sentiment_result.score,
            sentiment_result.confidence,
        ),
        sentiment_model_name=sentiment_result.model_name,
        sentiment_confidence=sentiment_result.confidence,
        sentiment_fallback_reason=sentiment_result.fallback_reason,
    )


def analyze_reviews(texts: list[str]) -> ReviewReportResponse:
    cleaned_reviews = prepare_reviews(texts)
    sentiment_results = analyze_sentiments_with_model(cleaned_reviews)

    fallback_summary = summarize_review(" ".join(_representative_reviews(cleaned_reviews, sentiment_results)))
    model_summary = summarize_with_model(cleaned_reviews, fallback_summary=fallback_summary)
    sentiment_counts = _sentiment_counts(sentiment_results)

    analyzed_reviews = [
        ReviewSentimentItem(
            text=text,
            sentiment=result.sentiment,
            sentiment_score=result.score,
            sentiment_explanation=explain_sentiment(text, result.sentiment, result.score, result.confidence),
            sentiment_confidence=result.confidence,
            sentiment_source=result.sentiment_source,
        )
        for text, result in zip(cleaned_reviews, sentiment_results, strict=False)
    ]

    praised_features = _top_terms_for_sentiment(cleaned_reviews, sentiment_results, "positive")
    complaints = _top_terms_for_sentiment(cleaned_reviews, sentiment_results, "negative")

    return ReviewReportResponse(
        id=str(uuid.uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        review_count=len(cleaned_reviews),
        overall_sentiment=_overall_sentiment_from_counts(sentiment_counts),
        sentiment_counts=sentiment_counts,
        report_summary=model_summary.summary,
        summary_source=model_summary.summary_source,
        model_name=model_summary.model_name,
        fallback_reason=model_summary.fallback_reason,
        common_issues=complaints[:REPORT_TERM_LIMIT],
        frequently_praised_features=praised_features[:REPORT_TERM_LIMIT],
        recurring_complaints=complaints[:REPORT_TERM_LIMIT],
        main_reasons_liked=praised_features[:5],
        main_reasons_disliked=complaints[:5],
        analyzed_reviews=analyzed_reviews,
    )


def _sentiment_counts(sentiment_results: list) -> dict[str, int]:
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for result in sentiment_results:
        if result.sentiment in counts:
            counts[result.sentiment] += 1
    return counts


def _overall_sentiment_from_counts(counts: dict[str, int]) -> str:
    positive_count = counts.get("positive", 0)
    negative_count = counts.get("negative", 0)
    neutral_count = counts.get("neutral", 0)

    if positive_count and negative_count:
        return "mixed"
    if positive_count > max(negative_count, neutral_count):
        return "positive"
    if negative_count > max(positive_count, neutral_count):
        return "negative"
    return "neutral"


def _representative_reviews(review_texts: list[str], sentiment_results: list) -> list[str]:
    selected: list[str] = []
    for tone in ("negative", "positive", "neutral"):
        for text, result in zip(review_texts, sentiment_results, strict=False):
            if result.sentiment == tone and text not in selected:
                selected.append(text)
                break
    return selected or review_texts[:3]


def _top_terms_for_sentiment(review_texts: list[str], sentiment_results: list, sentiment: str) -> list[str]:
    counter: Counter[str] = Counter()
    for text, result in zip(review_texts, sentiment_results, strict=False):
        if result.sentiment != sentiment:
            continue
        counter.update(_sentiment_phrases(text, sentiment))
        counter.update(_keywords(text, sentiment))
    return [term for term, _ in counter.most_common(REPORT_TERM_LIMIT)]


def _sentiment_phrases(text: str, sentiment: str) -> list[str]:
    return [item.phrase for item in sentiment_evidence(text, sentiment)]


def _keywords(text: str, sentiment: str) -> list[str]:
    sentiment_words = POSITIVE_WORDS if sentiment == "positive" else NEGATIVE_WORDS
    tokens: list[str] = []
    for match in WORD_PATTERN.finditer(text):
        token = match.group(0).casefold().strip("'")
        if token in STOPWORDS:
            continue
        if sentiment == "positive" and token in POSITIVE_WORDS:
            continue
        if sentiment == "negative" and token not in sentiment_words and len(tokens) >= 3:
            continue
        tokens.append(token)
    return tokens[:6]
