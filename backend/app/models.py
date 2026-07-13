from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


Sentiment = Literal["positive", "neutral", "negative"]
OverallSentiment = Literal["positive", "neutral", "negative", "mixed"]
Provider = Literal["google", "groq"]


class Review(BaseModel):
    id: str
    text: str
    rating: int | None = Field(default=None, ge=1, le=5)
    date: str | None = None


class SourceInfo(BaseModel):
    url: HttpUrl
    title: str
    extractor: Literal["json_ld", "html_cards"]


class CollectionResult(BaseModel):
    source: SourceInfo
    reviews: list[Review]


class AnalysisRequest(BaseModel):
    url: HttpUrl
    provider: Provider = "google"


class ReviewSentiment(BaseModel):
    review_id: str
    sentiment: Sentiment


class Theme(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=240)
    mentions: int = Field(ge=1)


class AgentInsights(BaseModel):
    summary: str = Field(min_length=1, max_length=1200)
    overall_sentiment: OverallSentiment
    themes: list[Theme] = Field(min_length=1, max_length=6)
    strengths: list[str] = Field(max_length=5)
    weaknesses: list[str] = Field(max_length=5)
    actions: list[str] = Field(max_length=5)
    review_sentiments: list[ReviewSentiment]


class Metrics(BaseModel):
    review_count: int
    rated_count: int
    average_rating: float | None
    positive_percentage: float
    sentiment_counts: dict[Sentiment, int]
    rating_distribution: dict[str, int]


class AnalysisResponse(BaseModel):
    source: SourceInfo
    metrics: Metrics
    insights: AgentInsights
    reviews: list[Review]


class PublicError(BaseModel):
    code: Literal[
        "invalid_url",
        "collection_failed",
        "no_reviews",
        "missing_api_key",
        "analysis_failed",
    ]
    message: str
