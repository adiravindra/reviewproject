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


class SingleReviewStructuredAnalysis(BaseModel):
    text: str
    sentiment: str
    topics: list[str]
    urgency_score: float
    urgency_label: str
    summary: str


class KeywordItem(BaseModel):
    keyword: str
    count: int


class SingleReviewAnalysisRequest(ReviewInput):
    source: str = Field("manual", description="Where this review entered ReviewInsight.")


class ReviewBatchAnalysisRequest(ReviewBatchInput):
    source: str = Field("api", description="Where this review batch entered ReviewInsight.")


class ReviewResult(BaseModel):
    text: str
    sentiment: str
    sentiment_score: int
    topic: str
    urgency: str
    summary: str
    keywords: list[str]


class AnalysisMetrics(BaseModel):
    review_count: int
    overall_sentiment: str
    sentiment_breakdown: dict[str, int]
    urgency_breakdown: dict[str, int]
    top_topics: list[KeywordItem]
    average_urgency: float
    high_priority_reviews: int


class AnalysisRunResponse(BaseModel):
    id: str
    created_at: str
    source: str
    review_count: int
    reviews: list[ReviewResult]
    summary: str
    metrics: AnalysisMetrics
    most_urgent_reviews: list[ReviewResult]


class ReviewDetailResponse(BaseModel):
    run_id: str
    review_index: int
    review: ReviewResult


class HistoryItem(BaseModel):
    id: str
    created_at: str
    source: str
    review_count: int
    overall_sentiment: str
    high_priority_reviews: int
    summary: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class DashboardMetricsResponse(BaseModel):
    total_runs: int
    total_reviews: int
    sentiment_breakdown: dict[str, int]
    urgency_breakdown: dict[str, int]
    top_topics: list[KeywordItem]
    recent_summaries: list[str]


class SentimentResponse(BaseModel):
    text: str
    sentiment: str
    score: int


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
