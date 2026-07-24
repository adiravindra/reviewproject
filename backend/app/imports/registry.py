"""Compose the replaceable platform-to-provider adapter registry."""

from backend.app.imports.apify import ApifyGoogleMapsAdapter
from backend.app.imports.apify_amazon import ApifyAmazonReviewsAdapter


def build_default_registry() -> dict[str, object]:
    """Return one backend adapter for each supported first-milestone platform."""

    adapters = (ApifyAmazonReviewsAdapter(), ApifyGoogleMapsAdapter())
    return {adapter.platform: adapter for adapter in adapters}
