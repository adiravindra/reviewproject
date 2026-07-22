"""Define replaceable provider adapter contracts and safe import failures."""

from dataclasses import dataclass
from typing import Any, Protocol


class ReviewImportError(Exception):
    """Carry one application-owned import failure code without raw details."""

    def __init__(self, code: str, public_message: str = "Review import failed."):
        """Store only an allowlisted code and safe public message."""

        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


def classify_provider_status(status_code: int) -> None:
    """Map common provider HTTP statuses to application-owned failures."""

    if status_code in {200, 201}:
        return
    if status_code in {401, 403}:
        raise ReviewImportError("provider_auth_failed")
    if status_code == 402:
        raise ReviewImportError("provider_quota_exhausted")
    if status_code == 429:
        raise ReviewImportError("provider_unavailable")
    if status_code in {408, 504}:
        raise ReviewImportError("import_timeout")
    if status_code >= 500:
        raise ReviewImportError("provider_unavailable")
    raise ReviewImportError("import_failed")


@dataclass(frozen=True)
class ProviderReviewCandidate:
    """Hold only fields needed to build normalized review evidence."""

    title: Any
    body: Any
    rating: Any
    date: Any


@dataclass(frozen=True)
class ProviderImportResult:
    """Represent provider output without exposing a vendor response shape."""

    title: str
    source_url: str
    source_key: str | None
    reviews: tuple[ProviderReviewCandidate, ...]


class ReviewProviderAdapter(Protocol):
    """Specify the narrow interface replaceable provider adapters implement."""

    provider_key: str
    provider_label: str
    platform: str
    allowed_limits: tuple[int, ...]

    def fetch(self, source_url: str, limit: int) -> ProviderImportResult:
        """Fetch one bounded set of candidate reviews."""


@dataclass(frozen=True)
class NormalizedProviderResult:
    """Pair normalized evidence with safe source metadata."""

    title: str
    source_url: str
    source_key: str | None
    reviews: tuple
