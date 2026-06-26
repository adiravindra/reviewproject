from typing import Any

from pydantic import BaseModel, Field


# These classes describe the JSON sent between Streamlit and FastAPI.
class ReviewAnalysisRequest(BaseModel):
    text: str = Field(..., description="A single customer review to analyze.")


class ReviewAnalysisResponse(BaseModel):
    id: str
    created_at: str
    text: str
    sentiment: str
    sentiment_score: int
    topics: list[str]
    urgency: str
    urgency_score: float
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


class HistoryItem(BaseModel):
    id: str
    created_at: str
    text: str
    sentiment: str
    topics: list[str]
    urgency: str
    summary: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    # Pydantic v2 uses model_dump; older versions use dict.
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
