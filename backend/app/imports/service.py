"""Orchestrate one explicit cached provider-backed review import."""

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone

from backend.app.import_cache import CacheIdentity, ImportCacheStore
from backend.app.imports.contracts import ReviewImportError, ReviewProviderAdapter
from backend.app.imports.normalizer import normalize_provider_result
from backend.app.imports.policies import validate_import_source
from backend.app.models import (
    CollectionResult,
    ImportOptions,
    ImportPlatformOption,
    ImportRequest,
    SourceInfo,
)

CACHE_CONTRACT_VERSION = "1"
CACHE_TTL = timedelta(days=30)
IMPORT_ORDERING = "most_relevant"
_PLATFORM_LABELS = {
    "amazon": "Amazon product",
    "google_maps": "Google Maps place",
}


class ReviewImportService:
    """Keep providers, caching, and normalization outside analysis/history."""

    def __init__(
        self,
        registry: Mapping[str, ReviewProviderAdapter],
        cache: ImportCacheStore,
        *,
        clock: Callable[[], datetime] | None = None,
    ):
        """Compose registry, cache, and clock dependencies."""

        self.registry = dict(registry)
        self.cache = cache
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def options(self) -> ImportOptions:
        """Expose registered platform labels and small allowed limits."""

        platforms = []
        for platform in ("amazon", "google_maps"):
            adapter = self.registry.get(platform)
            if adapter is not None:
                platforms.append(
                    ImportPlatformOption(
                        key=platform,
                        label=_PLATFORM_LABELS[platform],
                        limits=list(adapter.allowed_limits),
                    )
                )
        return ImportOptions(platforms=platforms)

    def import_reviews(self, request: ImportRequest) -> CollectionResult:
        """Return cached evidence or perform exactly one explicit import."""

        adapter = self.registry.get(request.platform)
        if adapter is None:
            raise ReviewImportError("unsupported_import_platform")
        if request.limit not in adapter.allowed_limits:
            raise ReviewImportError("unsupported_import_limit")
        source = validate_import_source(request.platform, str(request.url))
        identity = CacheIdentity(
            request.platform,
            adapter.provider_key,
            CACHE_CONTRACT_VERSION,
            source.source_key,
            request.limit,
            IMPORT_ORDERING,
        )
        now = self.clock()
        if not request.refresh:
            cached = self.cache.get(identity, now)
            if cached is not None:
                return cached.model_copy(
                    update={
                        "source": cached.source.model_copy(update={"cache_status": "hit"})
                    }
                )

        provider_result = adapter.fetch(source.original_url, request.limit)
        normalized = normalize_provider_result(provider_result, request.limit)
        if len(normalized.reviews) < 2:
            raise ReviewImportError("no_reviews")
        status = "refresh" if request.refresh else "miss"
        collection = CollectionResult(
            source=SourceInfo(
                url=source.original_url,
                title=normalized.title,
                extractor="provider_api",
                is_demo=False,
                platform=request.platform,
                provider=adapter.provider_label,
                requested_count=request.limit,
                retrieved_count=len(normalized.reviews),
                retrieved_at=now,
                cache_status=status,
            ),
            reviews=list(normalized.reviews),
        )
        self.cache.put(identity, collection, now, now + CACHE_TTL)
        return collection
