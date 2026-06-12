from pydantic import BaseModel, Field


class ReviewInput(BaseModel):
    text: str = Field(..., description="Raw customer review text.")


class ReviewBatchInput(BaseModel):
    reviews: list[ReviewInput] = Field(..., min_length=1)


class CleanedReview(BaseModel):
    text: str


class ReviewCollectionResponse(BaseModel):
    count: int
    reviews: list[CleanedReview]


class HealthResponse(BaseModel):
    status: str
    project: str
    version: str


class ReviewAnalysis(BaseModel):
    sentiment: str
    topic: str
    urgency: str
    summary: str


class SentimentResponse(BaseModel):
    text: str
    sentiment: str
    score: int


class KeywordItem(BaseModel):
    keyword: str
    count: int


class KeywordResponse(BaseModel):
    keywords: list[KeywordItem]
    themes: list[KeywordItem]


class SummaryResponse(BaseModel):
    summary: str
    review_count: int


class InsightsResponse(BaseModel):
    review_count: int
    overall_sentiment: str
    sentiment_breakdown: dict[str, int]
    positive_themes: list[str]
    negative_themes: list[str]
    common_complaints: list[str]
    summary: str
    suggested_action_items: list[str]
