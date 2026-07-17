"""Define Pydantic contracts shared by the HTTP and agent boundaries.

These schemas keep collection, deterministic metrics, structured AI output, and
FastAPI serialization on one validated representation instead of allowing each
stage to invent its own dictionary shape.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


# Literal aliases deliberately constrain sentiment vocabulary at both runtime
# validation and static-analysis boundaries.
Sentiment = Literal["positive", "neutral", "negative"]
OverallSentiment = Literal["positive", "neutral", "negative", "mixed"]


class Review(BaseModel):
    """Represent one normalized public review and its optional metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(min_length=1, max_length=5000)
    rating: int | None = Field(default=None, ge=1, le=5)
    date: str | None = None


class SourceInfo(BaseModel):
    """Identify the fetched page and the conservative extractor that succeeded."""

    model_config = ConfigDict(extra="forbid")

    url: HttpUrl | None
    title: str
    extractor: Literal["json_ld", "html_cards", "demo"]
    is_demo: bool

    @model_validator(mode="after")
    def validate_demo_provenance(self):
        """Keep URL-less sources and their demo label internally consistent."""

        if self.url is None and self.extractor != "demo":
            raise ValueError("Only demo sources may omit a URL.")
        if self.is_demo != (self.extractor == "demo"):
            raise ValueError("Demo sources must use the demo extractor and label.")
        return self


class CollectionResult(BaseModel):
    """Bundle normalized reviews with provenance from the collection stage."""

    source: SourceInfo
    reviews: list[Review]


class CollectionRequest(BaseModel):
    """Validate the one URL accepted by the static collection boundary."""

    model_config = ConfigDict(extra="forbid")

    url: HttpUrl


class AnalysisRequest(BaseModel):
    """Validate previously collected evidence submitted to Groq analysis."""

    model_config = ConfigDict(extra="forbid")

    source: SourceInfo
    reviews: list[Review] = Field(min_length=2, max_length=40)

    def to_collection(self) -> CollectionResult:
        """Reconstitute the validated collection consumed by the analysis stage."""

        return CollectionResult(source=self.source, reviews=self.reviews)


class ReviewSentiment(BaseModel):
    """Associate exactly one constrained sentiment with a submitted review ID."""

    review_id: str
    sentiment: Sentiment


class Theme(BaseModel):
    """Describe a bounded recurring theme and its evidence-based mention count."""

    name: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=240)
    mentions: int = Field(ge=1)
    sentiment: Sentiment


class AgentInsights(BaseModel):
    """Constrain the complete structured response produced by the single agent."""

    summary: str = Field(min_length=1, max_length=1200)
    overall_sentiment: OverallSentiment
    themes: list[Theme] = Field(min_length=1, max_length=6)
    strengths: list[str] = Field(max_length=5)
    weaknesses: list[str] = Field(max_length=5)
    actions: list[str] = Field(max_length=5)
    review_sentiments: list[ReviewSentiment]


class Metrics(BaseModel):
    """Expose deterministic rating and sentiment aggregates for the dashboard."""

    review_count: int
    rated_count: int
    average_rating: float | None
    positive_percentage: float
    sentiment_counts: dict[Sentiment, int]
    rating_distribution: dict[str, int]


class AnalysisResponse(BaseModel):
    """Define the successful end-to-end HTTP response contract."""

    source: SourceInfo
    metrics: Metrics
    insights: AgentInsights
    reviews: list[Review]
    history_id: int | None = None


class HistoryItem(BaseModel):
    """Represent the safe summary fields displayed in local run history."""

    id: int
    created_at: str
    source_title: str
    source_url: str | None
    extractor: str
    is_demo: bool
    review_count: int
    overall_sentiment: OverallSentiment


class PublicError(BaseModel):
    """Define the small safe error vocabulary that may cross the API boundary."""

    code: Literal[
        "invalid_url",
        "collection_failed",
        "no_reviews",
        "missing_api_key",
        "invalid_api_key",
        "provider_unavailable",
        "analysis_failed",
    ]
    message: str
