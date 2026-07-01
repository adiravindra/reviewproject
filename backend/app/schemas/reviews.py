from typing import Any

from pydantic import BaseModel, Field


# These classes describe the JSON sent between Streamlit and FastAPI.
class ReviewAnalysisRequest(BaseModel):
    text: str = Field(..., description="A single customer review to analyze.")


class ReviewBatchAnalysisRequest(BaseModel):
    texts: list[str] = Field(..., description="Customer reviews to analyze together.")


class ReviewAnalysisResponse(BaseModel):
    id: str
    created_at: str
    text: str
    sentiment: str
    sentiment_score: int
    summary: str
    summary_source: str = "rule_based_fallback"
    model_name: str | None = None
    fallback_reason: str | None = None
    sentiment_source: str = "rule_based_fallback"
    sentiment_explanation: str | None = None
    sentiment_model_name: str | None = None
    sentiment_confidence: float | None = None
    sentiment_fallback_reason: str | None = None
    saved_to_history: bool = True


class ReviewSentimentItem(BaseModel):
    text: str
    sentiment: str
    sentiment_score: int
    sentiment_explanation: str | None = None
    sentiment_confidence: float | None = None
    sentiment_source: str = "rule_based_fallback"


class ReviewReportResponse(BaseModel):
    id: str
    created_at: str
    review_count: int
    overall_sentiment: str
    sentiment_counts: dict[str, int]
    report_summary: str
    summary_source: str = "rule_based_fallback"
    model_name: str | None = None
    fallback_reason: str | None = None
    common_issues: list[str] = Field(default_factory=list)
    frequently_praised_features: list[str] = Field(default_factory=list)
    recurring_complaints: list[str] = Field(default_factory=list)
    main_reasons_liked: list[str] = Field(default_factory=list)
    main_reasons_disliked: list[str] = Field(default_factory=list)
    analyzed_reviews: list[ReviewSentimentItem] = Field(default_factory=list)


class HistoryItem(BaseModel):
    id: str
    created_at: str
    text: str
    sentiment: str
    summary: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    # Pydantic v2 uses model_dump; older versions use dict.
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
