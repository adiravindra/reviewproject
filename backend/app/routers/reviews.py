from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from backend.app.schemas.reviews import (
    AnalysisRunResponse,
    CleanedReview,
    DashboardMetricsResponse,
    HistoryResponse,
    InsightsResponse,
    KeywordItem,
    KeywordResponse,
    ReviewAnalysis,
    ReviewBatchAnalysisRequest,
    ReviewBatchInput,
    ReviewCollectionResponse,
    ReviewDetailResponse,
    ReviewInput,
    SingleReviewStructuredAnalysis,
    SentimentResponse,
    SingleReviewAnalysisRequest,
    SummaryResponse,
)
from backend.app.services.analysis import (
    analyze_reviews,
    analyze_single_review_text,
    estimate_urgency,
    parse_csv_reviews,
)
from backend.app.services.history import (
    get_analysis_run,
    get_dashboard_metrics,
    get_history,
    get_latest_analysis_run,
    get_review_detail,
    save_analysis_run,
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


@router.post("/analysis/review", response_model=AnalysisRunResponse)
def analyze_single_review(review: SingleReviewAnalysisRequest) -> AnalysisRunResponse:
    run = analyze_reviews([review.text], source=review.source)
    save_analysis_run(run)
    return run


@router.post("/analysis/reviews", response_model=AnalysisRunResponse)
def analyze_review_batch(review_batch: ReviewBatchAnalysisRequest) -> AnalysisRunResponse:
    run = analyze_reviews(
        [review.text for review in review_batch.reviews],
        source=review_batch.source,
    )
    save_analysis_run(run)
    return run


@router.post("/analysis/csv", response_model=AnalysisRunResponse)
async def analyze_review_csv(file: UploadFile = File(...)) -> AnalysisRunResponse:
    try:
        review_texts = parse_csv_reviews(await file.read())
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSV upload must be UTF-8 encoded.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    run = analyze_reviews(review_texts, source="csv")
    save_analysis_run(run)
    return run


@router.get("/history", response_model=HistoryResponse)
def analysis_history(limit: int = Query(default=25, ge=1, le=100)) -> HistoryResponse:
    return get_history(limit=limit)


@router.get("/analysis/runs/{run_id}", response_model=AnalysisRunResponse)
def analysis_run_detail(run_id: str) -> AnalysisRunResponse:
    run = get_analysis_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found.")
    return run


@router.get("/analysis/latest", response_model=AnalysisRunResponse)
def latest_analysis_run() -> AnalysisRunResponse:
    run = get_latest_analysis_run()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analysis history found.")
    return run


@router.get("/analysis/runs/{run_id}/reviews/{review_index}", response_model=ReviewDetailResponse)
def analysis_review_detail(run_id: str, review_index: int) -> ReviewDetailResponse:
    detail = get_review_detail(run_id, review_index)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review detail not found.")
    return detail


@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
def dashboard_metrics() -> DashboardMetricsResponse:
    return get_dashboard_metrics()


@router.post("/analyze", response_model=ReviewAnalysis)
def analyze_review(review: ReviewInput) -> ReviewAnalysis:
    review_text = _prepare_or_422([review.text])[0]
    sentiment = analyze_sentiment(review_text).sentiment
    themes = extract_themes([review_text], limit=1)

    return ReviewAnalysis(
        sentiment=sentiment,
        topic=themes[0][0] if themes else "general feedback",
        urgency=estimate_urgency(review_text, sentiment),
        summary=summarize_reviews([review_text]),
    )


@router.post("/api/analyze/single", response_model=SingleReviewStructuredAnalysis)
def analyze_single_review_for_frontend(review: ReviewInput) -> SingleReviewStructuredAnalysis:
    review_text = _prepare_or_422([review.text])[0]
    return analyze_single_review_text(review_text)
