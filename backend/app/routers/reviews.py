from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.reviews import (
    CleanedReview,
    InsightsResponse,
    KeywordItem,
    KeywordResponse,
    ReviewAnalysis,
    ReviewBatchInput,
    ReviewCollectionResponse,
    ReviewInput,
    SentimentResponse,
    SummaryResponse,
)
from backend.app.services.insights import build_insights
from backend.app.services.keywords import extract_keywords, extract_themes
from backend.app.services.processing import prepare_reviews
from backend.app.services.sentiment import analyze_sentiment
from backend.app.services.summarization import summarize_reviews


router = APIRouter(tags=["reviews"])


def _prepare_or_422(review_texts: list[str]) -> list[str]:
    try:
        return prepare_reviews(review_texts)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def _collection_response(review_texts: list[str]) -> ReviewCollectionResponse:
    reviews = [CleanedReview(text=text) for text in review_texts]
    return ReviewCollectionResponse(count=len(reviews), reviews=reviews)


@router.post("/reviews", response_model=ReviewCollectionResponse)
def accept_single_review(review: ReviewInput) -> ReviewCollectionResponse:
    review_texts = _prepare_or_422([review.text])
    return _collection_response(review_texts)


@router.post("/reviews/batch", response_model=ReviewCollectionResponse)
def accept_multiple_reviews(review_batch: ReviewBatchInput) -> ReviewCollectionResponse:
    review_texts = _prepare_or_422([review.text for review in review_batch.reviews])
    return _collection_response(review_texts)


@router.post("/sentiment", response_model=SentimentResponse)
def analyze_review_sentiment(review: ReviewInput) -> SentimentResponse:
    review_text = _prepare_or_422([review.text])[0]
    result = analyze_sentiment(review_text)
    return SentimentResponse(
        text=result.text,
        sentiment=result.sentiment,
        score=result.score,
    )


@router.post("/keywords", response_model=KeywordResponse)
def extract_review_keywords(review_batch: ReviewBatchInput) -> KeywordResponse:
    review_texts = _prepare_or_422([review.text for review in review_batch.reviews])
    keywords = [
        KeywordItem(keyword=keyword, count=count)
        for keyword, count in extract_keywords(review_texts)
    ]
    themes = [
        KeywordItem(keyword=theme, count=count)
        for theme, count in extract_themes(review_texts)
    ]
    return KeywordResponse(keywords=keywords, themes=themes)


@router.post("/summarize", response_model=SummaryResponse)
def summarize_review_batch(review_batch: ReviewBatchInput) -> SummaryResponse:
    review_texts = _prepare_or_422([review.text for review in review_batch.reviews])
    return SummaryResponse(
        summary=summarize_reviews(review_texts),
        review_count=len(review_texts),
    )


@router.post("/insights", response_model=InsightsResponse)
def generate_review_insights(review_batch: ReviewBatchInput) -> InsightsResponse:
    review_texts = _prepare_or_422([review.text for review in review_batch.reviews])
    return InsightsResponse(**build_insights(review_texts))


@router.post("/analyze", response_model=ReviewAnalysis)
def analyze_review(review: ReviewInput) -> ReviewAnalysis:
    review_text = _prepare_or_422([review.text])[0]
    sentiment = analyze_sentiment(review_text).sentiment
    themes = extract_themes([review_text], limit=1)

    return ReviewAnalysis(
        sentiment=sentiment,
        topic=themes[0][0] if themes else "general feedback",
        urgency=_estimate_urgency(review_text, sentiment),
        summary=summarize_reviews([review_text]),
    )


def _estimate_urgency(review_text: str, sentiment: str) -> str:
    urgent_terms = {"broken", "refund", "terrible", "worst", "urgent"}
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in review_text.split()}

    if words & urgent_terms:
        return "high"
    if sentiment == "negative":
        return "medium"
    return "low"
