"""Retrieve bounded Amazon review sets through Axesso's public Apify Actor."""

import logging
import math
import os
from typing import Any

import requests

from backend.app.imports.contracts import (
    IMPORT_LIMITS,
    ProviderImportResult,
    ProviderReviewCandidate,
    ReviewImportError,
    classify_provider_status,
)
from backend.app.imports.policies import extract_amazon_asin


AXESSO_ACTOR_ID = "axesso_data~amazon-reviews-scraper"
AXESSO_ENDPOINT = (
    "https://api.apify.com/v2/acts/"
    "axesso_data~amazon-reviews-scraper/run-sync-get-dataset-items"
)
AXESSO_TIMEOUT = (5, 120)
LOGGER = logging.getLogger(__name__)


class ApifyAmazonReviewsAdapter:
    """Implement Amazon imports through one replaceable Axesso Actor call."""

    provider_key = "apify_axesso_amazon"
    provider_label = "Apify (Axesso)"
    platform = "amazon"
    allowed_limits = IMPORT_LIMITS

    def __init__(self, *, session=requests):
        """Accept an injectable HTTP boundary for fixture-only tests."""

        self.session = session

    def fetch(self, source_url: str, limit: int) -> ProviderImportResult:
        """Run the approved Actor once and decode only normalized evidence fields."""

        token = os.getenv("APIFY_API_TOKEN", "").strip()
        if not token:
            raise ReviewImportError("missing_provider_key")
        asin = extract_amazon_asin(source_url)
        if asin is None:
            raise ReviewImportError("invalid_import_url")
        max_pages = min(10, max(1, math.ceil(limit / 10)))
        response_status = None
        try:
            response = self.session.post(
                AXESSO_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "input": [
                        {
                            "asin": asin,
                            "domainCode": "com",
                            "sortBy": "recent",
                            "maxPages": max_pages,
                            "filterByStar": "five_star",
                            "filterByKeyword": "good",
                            "reviewerType": "all_reviews",
                            "formatType": "current_format",
                            "mediaType": "all_contents",
                        }
                    ]
                },
                timeout=AXESSO_TIMEOUT,
            )
            response_status = response.status_code
            classify_provider_status(response.status_code)
            items = _extract_items(response.json())
        except ReviewImportError as error:
            _log_provider_failure(error.code, response_status)
            raise
        except requests.Timeout:
            _log_provider_failure("import_timeout", response_status)
            raise ReviewImportError("import_timeout") from None
        except (requests.exceptions.JSONDecodeError, TypeError, ValueError, KeyError):
            _log_provider_failure("provider_response_invalid", response_status)
            raise ReviewImportError("provider_response_invalid") from None
        except requests.RequestException:
            _log_provider_failure("provider_unavailable", response_status)
            raise ReviewImportError("provider_unavailable") from None

        successful = [
            item
            for item in items
            if item.get("statusCode") == 200
            and str(item.get("statusMessage") or "").upper() == "FOUND"
        ]
        first = successful[0] if successful else {}
        source_key = str(first.get("asin") or "").strip().upper() or asin
        title = (
            str(first.get("productTitle") or "").strip()
            or f"Amazon product {source_key}"
        )
        reviews = tuple(
            ProviderReviewCandidate(
                title=item.get("title"),
                body=item.get("text"),
                rating=item.get("rating"),
                date=item.get("date"),
            )
            for item in successful
        )
        return ProviderImportResult(title, source_url, source_key, reviews)


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    """Validate the synchronous Axesso dataset-items response."""

    if not isinstance(payload, list) or not all(
        isinstance(item, dict) for item in payload
    ):
        raise ReviewImportError("provider_response_invalid")
    return payload


def _log_provider_failure(code: str, status_code: int | None) -> None:
    """Record only safe diagnostics, never credentials or provider bodies."""

    LOGGER.warning(
        "Amazon review import failed provider=%s code=%s status=%s",
        ApifyAmazonReviewsAdapter.provider_key,
        code,
        status_code if status_code is not None else "unavailable",
    )
