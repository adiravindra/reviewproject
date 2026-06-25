from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.reviews import (
    HistoryResponse,
    ReviewAnalysisRequest,
    ReviewAnalysisResponse,
)
from backend.app.services.analysis import analyze_review
from backend.app.services.history import get_history, save_review_analysis


router = APIRouter(tags=["reviews"])


@router.post("/analysis/single", response_model=ReviewAnalysisResponse)
def analyze_single_review(review: ReviewAnalysisRequest) -> ReviewAnalysisResponse:
    try:
        result = analyze_review(review.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    # This MVP saves every analyzed review so the History page stays simple.
    save_review_analysis(result)
    return result


@router.get("/analysis/history", response_model=HistoryResponse)
def analysis_history(limit: int = Query(default=50, ge=1, le=200)) -> HistoryResponse:
    return get_history(limit=limit)
