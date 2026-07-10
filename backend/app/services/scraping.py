import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from backend.app.errors import AppError
from backend.app.schemas.website import ExtractionCandidate, NormalizationResult
from backend.app.scrapers.registry import ScraperRegistry
from backend.app.services.fetching import FetchedPage
from backend.app.services.normalization import normalize_reviews
from backend.app.services.url_safety import same_origin
from backend.app.settings import Settings


class PageFetcher(Protocol):
    def fetch(self, url: str, deadline: float | None = None) -> FetchedPage: ...


@dataclass(frozen=True)
class ScrapeResult:
    requested_url: str
    canonical_url: str
    entity_name: str | None
    entity_type: str | None
    page_title: str | None
    scraper_name: str
    pages_attempted: int
    pages_succeeded: int
    normalization: NormalizationResult
    partial_success: bool
    warnings: list[str]


def collect_reviews(
    url: str,
    *,
    fetcher: PageFetcher,
    registry: ScraperRegistry,
    settings: Settings,
    clock: Callable[[], float] = time.monotonic,
    overall_deadline: float | None = None,
) -> ScrapeResult:
    requested_url = url.strip()
    scrape_deadline = clock() + settings.scrape_deadline_seconds
    if overall_deadline is not None:
        scrape_deadline = min(scrape_deadline, overall_deadline)

    candidates: list[ExtractionCandidate] = []
    warnings: list[str] = []
    visited: set[str] = set()
    current_url: str | None = requested_url
    root_final_url: str | None = None
    canonical_url = requested_url
    entity_name: str | None = None
    entity_type: str | None = None
    page_title: str | None = None
    scraper_name: str | None = None
    pages_attempted = 0
    pages_succeeded = 0
    partial_success = False

    while current_url and pages_attempted < settings.max_pages:
        if current_url in visited:
            warnings.append("Pagination stopped because the next-page link repeated an earlier page.")
            break
        visited.add(current_url)
        pages_attempted += 1
        try:
            page = fetcher.fetch(current_url, deadline=scrape_deadline)
            extraction = registry.extract(page, preferred_name=scraper_name)
        except AppError:
            partial_success, should_continue = _partial_or_raise(
                candidates,
                settings,
                warnings,
            )
            if should_continue:
                break
            raise
        except Exception:
            partial_success, should_continue = _partial_or_raise(
                candidates,
                settings,
                warnings,
            )
            if should_continue:
                break
            raise _scraper_failure(requested_url) from None

        pages_succeeded += 1
        if root_final_url is None:
            root_final_url = page.final_url
        canonical_url = extraction.canonical_url or canonical_url
        entity_name = entity_name or extraction.entity_name
        entity_type = entity_type or extraction.entity_type
        page_title = page_title or extraction.page_title

        if not extraction.candidates:
            if pages_attempted == 1:
                raise _empty_extraction_error(extraction.supported, requested_url)
            normalized_so_far = normalize_reviews(candidates, settings.max_reviews)
            if normalized_so_far.valid_count >= settings.min_reviews:
                partial_success = True
                warnings.append("A later page did not contain supported review markup.")
                break
            raise _empty_extraction_error(extraction.supported, requested_url)

        scraper_name = scraper_name or extraction.scraper_name
        candidates.extend(extraction.candidates)
        normalized_so_far = normalize_reviews(candidates, settings.max_reviews)
        next_url = extraction.next_url

        if normalized_so_far.omitted_by_cap > 0 or (
            normalized_so_far.analyzed_count >= settings.max_reviews and next_url
        ):
            _append_once(
                warnings,
                f"Only the first {settings.max_reviews} unique reviews were analyzed.",
            )
            break
        if not next_url:
            break
        if root_final_url is None or not same_origin(root_final_url, next_url):
            warnings.append("Pagination stopped because the next-page link changed origin.")
            break
        if pages_attempted >= settings.max_pages:
            warnings.append(f"Pagination stopped at the {settings.max_pages}-page safety limit.")
            break
        current_url = next_url

    normalization = normalize_reviews(candidates, settings.max_reviews)
    if normalization.found_count == 0:
        raise _empty_extraction_error(False, requested_url)
    if normalization.valid_count < settings.min_reviews:
        raise AppError(
            code="insufficient_reviews",
            message=f"At least {settings.min_reviews} valid reviews are required for analysis.",
            stage="scraping",
            status_code=422,
            details={
                "url": requested_url,
                "found": normalization.found_count,
                "valid": normalization.valid_count,
            },
        )
    if normalization.omitted_by_cap > 0:
        _append_once(
            warnings,
            f"Only the first {settings.max_reviews} unique reviews were analyzed.",
        )
    if normalization.analyzed_count < settings.low_sample_threshold:
        warnings.append(
            f"Only {normalization.analyzed_count} reviews were available, so insights may be less reliable."
        )

    return ScrapeResult(
        requested_url=requested_url,
        canonical_url=canonical_url,
        entity_name=entity_name,
        entity_type=entity_type,
        page_title=page_title,
        scraper_name=scraper_name or "none",
        pages_attempted=pages_attempted,
        pages_succeeded=pages_succeeded,
        normalization=normalization,
        partial_success=partial_success,
        warnings=warnings,
    )


def _partial_or_raise(
    candidates: list[ExtractionCandidate],
    settings: Settings,
    warnings: list[str],
) -> tuple[bool, bool]:
    if not candidates:
        return False, False
    normalized = normalize_reviews(candidates, settings.max_reviews)
    if normalized.valid_count < settings.min_reviews:
        return False, False
    warnings.append("Some later review pages could not be collected.")
    return True, True


def _empty_extraction_error(supported: bool, url: str) -> AppError:
    if supported:
        return AppError(
            code="no_reviews_found",
            message="No review candidates were found in the supported page structure.",
            stage="scraping",
            status_code=422,
            details={"url": url},
        )
    return AppError(
        code="unsupported_source",
        message="This page does not expose a supported static review structure.",
        stage="scraping",
        status_code=422,
        details={"url": url},
    )


def _scraper_failure(url: str) -> AppError:
    return AppError(
        code="scrape_failed",
        message="The page could not be parsed safely.",
        stage="scraping",
        status_code=502,
        details={"url": url},
    )


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
