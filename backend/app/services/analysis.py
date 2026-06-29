import uuid
from datetime import UTC, datetime

from backend.app.schemas.reviews import ReviewAnalysisResponse
from backend.app.services.model_sentiment import analyze_sentiment_with_model
from backend.app.services.model_summarizer import summarize_with_model
from backend.app.services.processing import prepare_reviews
from backend.app.services.sentiment import explain_sentiment
from backend.app.services.summarization import summarize_review


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
