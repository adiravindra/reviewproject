"""Retrieve a small Amazon review set through Outscraper's backend API."""

import os
from typing import Any

import requests

from backend.app.imports.contracts import (
    ProviderImportResult,
    ProviderReviewCandidate,
    ReviewImportError,
    classify_provider_status,
)


OUTSCRAPER_ENDPOINT = "https://api.outscraper.com/amazon-reviews"
OUTSCRAPER_TIMEOUT = (5, 30)
_FIELDS = "product_asin,title,body,rating,date"


class OutscraperAmazonAdapter:
    """Implement the Amazon adapter without source-site user credentials."""

    provider_key = "outscraper_amazon"
    provider_label = "Outscraper"
    platform = "amazon"
    allowed_limits = (5, 10, 12)

    def __init__(self, *, session=requests):
        """Accept an injectable HTTP boundary for fixture-only tests."""

        self.session = session

    def fetch(self, source_url: str, limit: int) -> ProviderImportResult:
        """Fetch one bounded Amazon product review response."""

        key = os.getenv("OUTSCRAPER_API_KEY", "").strip()
        if not key:
            raise ReviewImportError("missing_provider_key")
        try:
            response = self.session.get(
                OUTSCRAPER_ENDPOINT,
                headers={"X-API-KEY": key},
                params={
                    "query": source_url,
                    "limit": limit,
                    "async": "false",
                    "fields": _FIELDS,
                },
                timeout=OUTSCRAPER_TIMEOUT,
            )
            classify_provider_status(response.status_code)
            payload = response.json()
            items = _extract_items(payload)
        except ReviewImportError:
            raise
        except requests.Timeout:
            raise ReviewImportError("import_timeout") from None
        except requests.RequestException:
            raise ReviewImportError("provider_unavailable") from None
        except (TypeError, ValueError, KeyError):
            raise ReviewImportError("provider_response_invalid") from None

        first = items[0] if items else {}
        asin = str(first.get("product_asin") or "").strip().upper() or None
        title = f"Amazon product {asin}" if asin else "Amazon product reviews"
        reviews = tuple(
            ProviderReviewCandidate(
                title=item.get("title"),
                body=item.get("body"),
                rating=item.get("rating"),
                date=item.get("date"),
            )
            for item in items
        )
        return ProviderImportResult(title, source_url, asin, reviews)


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    """Validate Outscraper's one-query synchronous response envelope."""

    if not isinstance(payload, dict) or str(payload.get("status", "")).lower() != "success":
        raise ReviewImportError("provider_response_invalid")
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], list):
        raise ReviewImportError("provider_response_invalid")
    if not all(isinstance(item, dict) for item in data[0]):
        raise ReviewImportError("provider_response_invalid")
    return data[0]
