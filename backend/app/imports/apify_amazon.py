"""Retrieve bounded Amazon review sets through Axesso's public Apify Actor."""

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
                            "sortBy": "helpful",
                            "maxPages": max_pages,
                        }
                    ]
                },
                timeout=AXESSO_TIMEOUT,
            )
            classify_provider_status(response.status_code)
            items = _extract_items(response.json())
        except ReviewImportError:
            raise
        except requests.Timeout:
            raise ReviewImportError("import_timeout") from None
        except requests.RequestException:
            raise ReviewImportError("provider_unavailable") from None
        except (TypeError, ValueError, KeyError):
            raise ReviewImportError("provider_response_invalid") from None

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
