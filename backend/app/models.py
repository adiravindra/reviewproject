"""Define Pydantic contracts shared by the HTTP and agent boundaries.

These schemas keep collection, deterministic metrics, structured AI output, and
FastAPI serialization on one validated representation instead of allowing each
stage to invent its own dictionary shape.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


# Literal aliases deliberately constrain sentiment vocabulary at both runtime
# validation and static-analysis boundaries.
Sentiment = Literal["positive", "neutral", "negative"]
ThemeSentiment = Literal["positive", "neutral", "negative", "mixed"]
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
    extractor: Literal["json_ld", "html_cards", "provider_api", "demo"]
    is_demo: bool
    platform: Literal["generic", "amazon", "google_maps", "demo"] = "generic"
    provider: str | None = None
    requested_count: int | None = Field(default=None, ge=1, le=100)
    retrieved_count: int | None = Field(default=None, ge=0, le=100)
    retrieved_at: datetime | None = None
    cache_status: Literal["not_applicable", "miss", "hit", "refresh"] = "not_applicable"

    @model_validator(mode="after")
    def validate_demo_provenance(self):
        """Keep URL-less sources and their demo label internally consistent."""

        if self.url is None and self.extractor != "demo":
            raise ValueError("Only demo sources may omit a URL.")
        if self.is_demo != (self.extractor == "demo"):
            raise ValueError("Demo sources must use the demo extractor and label.")
        if self.is_demo and self.platform == "generic":
            self.platform = "demo"
        if self.extractor == "provider_api":
            if self.platform not in {"amazon", "google_maps"} or not self.provider:
                raise ValueError("Provider sources require platform and provider provenance.")
        elif any(
            value is not None
            for value in (
                self.provider,
                self.requested_count,
                self.retrieved_count,
                self.retrieved_at,
            )
        ) or self.cache_status != "not_applicable":
            raise ValueError("Only provider sources may use import provenance.")
        return self


class CollectionResult(BaseModel):
    """Bundle normalized reviews with provenance from the collection stage."""

    source: SourceInfo
    reviews: list[Review]

    @model_validator(mode="after")
    def validate_retrieved_count(self):
        """Keep provider provenance aligned with the normalized evidence."""

        if (
            self.source.retrieved_count is not None
            and self.source.retrieved_count != len(self.reviews)
        ):
            raise ValueError("Retrieved count must match normalized reviews.")
        return self


class CollectionRequest(BaseModel):
    """Validate the one URL accepted by the static collection boundary."""

    model_config = ConfigDict(extra="forbid")

    url: HttpUrl


class ImportRequest(BaseModel):
    """Validate one explicit provider-backed import request."""

    model_config = ConfigDict(extra="forbid")

    platform: Literal["amazon", "google_maps"]
    url: HttpUrl
    limit: int = Field(ge=1, le=100)
    refresh: bool = False


class ImportPlatformOption(BaseModel):
    """Describe one registered source and its deliberately small limits."""

    model_config = ConfigDict(extra="forbid")

    key: Literal["amazon", "google_maps"]
    label: str
    limits: list[int] = Field(min_length=1)


class ImportOptions(BaseModel):
    """Return platform choices without provider credentials or internals."""

    model_config = ConfigDict(extra="forbid")

    platforms: list[ImportPlatformOption]


class AnalysisRequest(BaseModel):
    """Validate previously collected evidence submitted to Groq analysis."""

    model_config = ConfigDict(extra="forbid")

    source: SourceInfo
    reviews: list[Review] = Field(min_length=2, max_length=40)

    @model_validator(mode="after")
    def validate_provider_subset_provenance(self):
        """Keep a bounded analysis subset consistent with its imported source."""

        if self.source.extractor == "provider_api":
            requested = self.source.requested_count
            retrieved = self.source.retrieved_count
            if (
                requested is None
                or retrieved is None
                or len(self.reviews) > retrieved
                or retrieved > requested
            ):
                raise ValueError(
                    "Provider analysis provenance must contain consistent import counts."
                )
        return self


class ReviewSentiment(BaseModel):
    """Associate exactly one constrained sentiment with a submitted review ID."""

    review_id: str
    sentiment: Sentiment


class Theme(BaseModel):
    """Describe a bounded recurring theme and its evidence-based mention count."""

    name: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=240)
    mentions: int = Field(ge=1)
    sentiment: ThemeSentiment


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
    platform: str | None = None
    provider: str | None = None


class PublicError(BaseModel):
    """Define the small safe error vocabulary that may cross the API boundary."""

    code: Literal[
        "invalid_url",
        "collection_failed",
        "no_reviews",
        "malformed_json_ld",
        "site_blocked",
        "collection_timeout",
        "missing_api_key",
        "invalid_api_key",
        "groq_unavailable",
        "analysis_failed",
        "model_output_invalid",
        "history_failed",
        "history_not_found",
        "invalid_import_url",
        "unsupported_import_platform",
        "unsupported_import_limit",
        "missing_provider_key",
        "provider_auth_failed",
        "provider_quota_exhausted",
        "provider_request_rejected",
        "provider_response_invalid",
        "import_failed",
        "provider_unavailable",
        "import_timeout",
        "cache_failed",
    ]
    message: str
