"""Retrieve a small Google Maps review set through one public Apify Actor."""

import os
from typing import Any

import requests

from backend.app.imports.contracts import (
    ProviderImportResult,
    ProviderReviewCandidate,
    ReviewImportError,
    classify_provider_status,
)


APIFY_ACTOR_ID = "compass~google-maps-reviews-scraper"
APIFY_ENDPOINT = (
    f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/run-sync-get-dataset-items"
)
APIFY_TIMEOUT = (5, 60)


class ApifyGoogleMapsAdapter:
    """Implement Google Maps imports with personal-data collection disabled."""

    provider_key = "apify_google_maps"
    provider_label = "Apify"
    platform = "google_maps"
    allowed_limits = (5, 10, 20)

    def __init__(self, *, session=requests):
        """Accept an injectable HTTP boundary for fixture-only tests."""

        self.session = session

    def fetch(self, source_url: str, limit: int) -> ProviderImportResult:
        """Run the approved Actor once and decode its dataset items."""

        token = os.getenv("APIFY_API_TOKEN", "").strip()
        if not token:
            raise ReviewImportError("missing_provider_key")
        try:
            response = self.session.post(
                APIFY_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "startUrls": [{"url": source_url}],
                    "maxReviews": limit,
                    "reviewsSort": "mostRelevant",
                    "reviewsOrigin": "google",
                    "personalData": False,
                    "language": "en",
                },
                timeout=APIFY_TIMEOUT,
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
        title = str(first.get("title") or "").strip() or "Google Maps place reviews"
        source_key = str(first.get("placeId") or "").strip() or None
        reviews = tuple(
            ProviderReviewCandidate(
                title=None,
                body=item.get("text"),
                rating=item.get("stars"),
                date=item.get("publishedAtDate"),
            )
            for item in items
        )
        return ProviderImportResult(title, source_url, source_key, reviews)


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    """Validate the synchronous Apify dataset-items response."""

    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ReviewImportError("provider_response_invalid")
    return payload
