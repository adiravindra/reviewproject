import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError

from backend.app.errors import AppError
from backend.app.schemas.website import (
    AnalysisMetadata,
    CollectionMetadata,
    NormalizedReview,
    SourceMetadata,
    WebsiteAnalysisResponse,
)
from backend.app.scrapers.registry import default_registry
from backend.app.services.analysis import CollectionAnalysisResult, analyze_collection
from backend.app.services.fetching import StaticHttpFetcher
from backend.app.services.history import save_website_analysis
from backend.app.services.metrics import calculate_metrics
from backend.app.services.scraping import ScrapeResult, collect_reviews
from backend.app.settings import Settings


ScrapeCallable = Callable[[str, float], ScrapeResult]
AnalyzeCallable = Callable[[list[NormalizedReview]], CollectionAnalysisResult]
SaveCallable = Callable[[WebsiteAnalysisResponse], None]


@dataclass(frozen=True)
class AnalysisDependencies:
    settings: Settings
    scrape: ScrapeCallable
    analyze: AnalyzeCallable
    save: SaveCallable
    clock: Callable[[], float] = time.monotonic
    id_factory: Callable[[], str] = lambda: f"run_{uuid.uuid4().hex}"
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


def build_analysis_dependencies(settings: Settings | None = None) -> AnalysisDependencies:
    active_settings = settings or Settings.from_env()
    clock = time.monotonic
    fetcher = StaticHttpFetcher(active_settings, clock=clock)
    registry = default_registry()
    model_holder: list[object] = []

    def scrape(url: str, deadline: float) -> ScrapeResult:
        return collect_reviews(
            url,
            fetcher=fetcher,
            registry=registry,
            settings=active_settings,
            clock=clock,
            overall_deadline=deadline,
        )

    def analyze(reviews: list[NormalizedReview]) -> CollectionAnalysisResult:
        if not model_holder:
            from backend.app.services.providers import create_chat_model

            model_holder.append(create_chat_model(active_settings))
        return analyze_collection(
            reviews,
            model=model_holder[0],
            settings=active_settings,
        )

    return AnalysisDependencies(
        settings=active_settings,
        scrape=scrape,
        analyze=analyze,
        save=lambda response: save_website_analysis(response, active_settings.db_path),
        clock=clock,
    )


def run_website_analysis(
    url: str,
    dependencies: AnalysisDependencies,
) -> WebsiteAnalysisResponse:
    deadline = dependencies.clock() + dependencies.settings.overall_deadline_seconds
    scrape = dependencies.scrape(url, deadline)
    _ensure_within_deadline(dependencies.clock, deadline)

    analysis = dependencies.analyze(scrape.normalization.reviews)
    _ensure_within_deadline(dependencies.clock, deadline)

    try:
        metrics = calculate_metrics(
            found_count=scrape.normalization.found_count,
            valid_count=scrape.normalization.valid_count,
            reviews=scrape.normalization.reviews,
            sentiments=analysis.sentiments,
        )
        completed_at = _timestamp(dependencies.now())
        response = WebsiteAnalysisResponse(
            id=dependencies.id_factory(),
            source=SourceMetadata(
                requested_url=scrape.requested_url,
                canonical_url=scrape.canonical_url,
                entity_name=scrape.entity_name,
                entity_type=scrape.entity_type,
                page_title=scrape.page_title,
                scraper_name=scrape.scraper_name,
                pages_attempted=scrape.pages_attempted,
                pages_succeeded=scrape.pages_succeeded,
            ),
            collection=CollectionMetadata(
                found=scrape.normalization.found_count,
                valid=scrape.normalization.valid_count,
                analyzed=scrape.normalization.analyzed_count,
                duplicates_removed=scrape.normalization.duplicates_removed,
                invalid_removed=scrape.normalization.invalid_removed,
                omitted_by_cap=scrape.normalization.omitted_by_cap,
                partial_success=scrape.partial_success,
                low_sample=(
                    scrape.normalization.analyzed_count
                    < dependencies.settings.low_sample_threshold
                ),
                warnings=scrape.warnings,
            ),
            metrics=metrics,
            insights=analysis.insights,
            reviews=scrape.normalization.reviews,
            analysis=AnalysisMetadata(
                provider=dependencies.settings.llm_provider,
                model=dependencies.settings.llm_model,
                batch_count=analysis.batch_count,
                llm_call_count=analysis.call_count,
                completed_at=completed_at,
            ),
        )
        response = WebsiteAnalysisResponse.model_validate(response.model_dump(mode="json"))
    except (ValidationError, ValueError, TypeError):
        raise AppError(
            code="llm_failed",
            message="The completed analysis did not match the required response structure.",
            stage="analysis",
            status_code=502,
        ) from None

    _ensure_within_deadline(dependencies.clock, deadline)
    try:
        dependencies.save(response)
    except Exception:
        raise AppError(
            code="scrape_failed",
            message="The completed analysis could not be saved.",
            stage="persistence",
            status_code=500,
        ) from None
    return response


def _ensure_within_deadline(clock: Callable[[], float], deadline: float) -> None:
    if clock() > deadline:
        raise AppError(
            code="request_timeout",
            message="The website analysis exceeded the overall request deadline.",
            stage="request",
            status_code=504,
            retryable=True,
        )


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
