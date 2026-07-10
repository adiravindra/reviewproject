from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Sentiment = Literal["positive", "neutral", "negative"]
OverallSentiment = Literal["positive", "neutral", "negative", "mixed"]


class WebsiteAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(..., min_length=1, description="Public website URL containing customer reviews.")


class ExtractionCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    rating: float | str | None = None
    rating_scale: float | str | None = None
    author: str | None = None
    publication_date: str | None = None
    source_url: str | None = None


class NormalizedReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    rating: float | None = Field(default=None, ge=1, le=5)
    original_rating: float | None = None
    rating_scale: float | None = None
    author: str | None = None
    publication_date: str | None = None
    source_url: str | None = None


class NormalizationResult(BaseModel):
    reviews: list[NormalizedReview]
    found_count: int = Field(ge=0)
    valid_count: int = Field(ge=0)
    duplicates_removed: int = Field(ge=0)
    invalid_removed: int = Field(ge=0)
    omitted_by_cap: int = Field(ge=0)

    @property
    def analyzed_count(self) -> int:
        return len(self.reviews)


class SourceMetadata(BaseModel):
    requested_url: str
    canonical_url: str
    entity_name: str | None = None
    entity_type: str | None = None
    page_title: str | None = None
    scraper_name: str
    pages_attempted: int = Field(ge=1)
    pages_succeeded: int = Field(ge=1)


class CollectionMetadata(BaseModel):
    found: int = Field(ge=0)
    valid: int = Field(ge=0)
    analyzed: int = Field(ge=0)
    duplicates_removed: int = Field(ge=0)
    invalid_removed: int = Field(ge=0)
    omitted_by_cap: int = Field(ge=0)
    partial_success: bool = False
    low_sample: bool = False
    warnings: list[str] = Field(default_factory=list)


class SentimentCounts(BaseModel):
    positive: int = Field(default=0, ge=0)
    neutral: int = Field(default=0, ge=0)
    negative: int = Field(default=0, ge=0)


class ReviewMetrics(BaseModel):
    reviews_found: int = Field(ge=0)
    reviews_valid: int = Field(ge=0)
    reviews_analyzed: int = Field(ge=0)
    reviews_skipped: int = Field(ge=0)
    rated_reviews: int = Field(ge=0)
    average_rating: float | None = Field(default=None, ge=1, le=5)
    rating_distribution: dict[str, int]
    sentiment_counts: SentimentCounts
    overall_sentiment: OverallSentiment


class EvidenceItem(BaseModel):
    label: str
    summary: str
    review_ids: list[str] = Field(default_factory=list)


class ReviewSentiment(BaseModel):
    review_id: str
    sentiment: Sentiment


class BatchAnalysisOutput(BaseModel):
    sentiments: list[ReviewSentiment]
    positive_themes: list[EvidenceItem] = Field(default_factory=list)
    complaints: list[EvidenceItem] = Field(default_factory=list)
    aspects: list[EvidenceItem] = Field(default_factory=list)
    opportunities: list[EvidenceItem] = Field(default_factory=list)


class SynthesisOutput(BaseModel):
    executive_summary: str
    strengths: list[EvidenceItem] = Field(default_factory=list)
    complaints: list[EvidenceItem] = Field(default_factory=list)
    aspects: list[EvidenceItem] = Field(default_factory=list)
    opportunities: list[EvidenceItem] = Field(default_factory=list)
    representative_review_ids: list[str] = Field(default_factory=list)


class RepresentativeReview(BaseModel):
    review_id: str
    text: str
    sentiment: Sentiment
    rating: float | None = None
    publication_date: str | None = None
    source_url: str | None = None


class WebsiteInsights(BaseModel):
    executive_summary: str
    strengths: list[EvidenceItem] = Field(default_factory=list)
    complaints: list[EvidenceItem] = Field(default_factory=list)
    aspects: list[EvidenceItem] = Field(default_factory=list)
    opportunities: list[EvidenceItem] = Field(default_factory=list)
    representative_reviews: list[RepresentativeReview] = Field(default_factory=list)


class AnalysisMetadata(BaseModel):
    provider: str
    model: str
    batch_count: int = Field(ge=1)
    llm_call_count: int = Field(ge=1)
    completed_at: str


class WebsiteAnalysisResponse(BaseModel):
    id: str
    source: SourceMetadata
    collection: CollectionMetadata
    metrics: ReviewMetrics
    insights: WebsiteInsights
    reviews: list[NormalizedReview]
    analysis: AnalysisMetadata


class WebsiteHistoryItem(BaseModel):
    id: str
    completed_at: str
    source_url: str
    entity_name: str | None = None
    review_count: int = Field(ge=0)
    average_rating: float | None = None
    overall_sentiment: OverallSentiment
    executive_summary: str
    provider: str
    model: str


class WebsiteHistoryResponse(BaseModel):
    items: list[WebsiteHistoryItem]


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
