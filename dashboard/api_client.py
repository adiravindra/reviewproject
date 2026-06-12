from collections.abc import Callable
from typing import Any

import requests


class ApiClientError(Exception):
    """Raised when the dashboard cannot get a usable backend response."""


PostFunction = Callable[..., Any]


def fetch_review_insights(
    review_texts: list[str],
    api_base_url: str = "http://127.0.0.1:8000",
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    cleaned_reviews = [
        {"text": review_text.strip()}
        for review_text in review_texts
        if review_text.strip()
    ]

    if not cleaned_reviews:
        raise ApiClientError("Enter at least one review before analyzing.")

    insights_url = f"{api_base_url.rstrip('/')}/insights"

    try:
        response = post(
            insights_url,
            json={"reviews": cleaned_reviews},
            timeout=10,
        )
        response.raise_for_status()
    except Exception as exc:
        raise ApiClientError(
            "Could not analyze reviews. Make sure the FastAPI backend is running."
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise ApiClientError("The backend returned an invalid response.") from exc
