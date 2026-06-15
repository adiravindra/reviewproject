from collections.abc import Callable
from typing import Any

import requests


class ApiClientError(Exception):
    """Raised when the dashboard cannot get a usable backend response."""


PostFunction = Callable[..., Any]
GetFunction = Callable[..., Any]


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


def _api_url(api_base_url: str, path: str) -> str:
    return f"{api_base_url.rstrip('/')}/{path.lstrip('/')}"


def _clean_review_text(text: str) -> str:
    cleaned_text = text.strip()
    if not cleaned_text:
        raise ApiClientError("Enter at least one review before analyzing.")
    return cleaned_text


def _review_payload(review_texts: list[str]) -> dict[str, list[dict[str, str]]]:
    cleaned_reviews = [
        {"text": review_text.strip()}
        for review_text in review_texts
        if review_text.strip()
    ]

    if not cleaned_reviews:
        raise ApiClientError("Enter at least one review before analyzing.")

    return {"reviews": cleaned_reviews}


def _parse_response(response: Any) -> dict[str, Any]:
    try:
        response.raise_for_status()
    except Exception as exc:
        raise ApiClientError(
            "Could not analyze reviews. Make sure the FastAPI backend is running."
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise ApiClientError("The backend returned an invalid response.") from exc


def fetch_health(
    api_base_url: str = DEFAULT_API_BASE_URL,
    get: GetFunction = requests.get,
) -> dict[str, Any]:
    try:
        response = get(_api_url(api_base_url, "/health"), timeout=10)
    except Exception as exc:
        raise ApiClientError(
            "Could not reach the backend health endpoint. Make sure FastAPI is running."
        ) from exc

    return _parse_response(response)


def analyze_single_review(
    review_text: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    response = post(
        _api_url(api_base_url, "/analysis/review"),
        json={"text": _clean_review_text(review_text), "source": "manual"},
        timeout=10,
    )
    return _parse_response(response)


def analyze_reviews_from_api_payload(
    review_texts: list[str],
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    payload = _review_payload(review_texts)
    payload["source"] = "api"
    response = post(
        _api_url(api_base_url, "/analysis/reviews"),
        json=payload,
        timeout=10,
    )
    return _parse_response(response)


def analyze_reviews_csv(
    filename: str,
    contents: bytes,
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    if not contents:
        raise ApiClientError("Upload a CSV file before analyzing.")

    response = post(
        _api_url(api_base_url, "/analysis/csv"),
        files={"file": (filename, contents, "text/csv")},
        timeout=10,
    )
    return _parse_response(response)


def fetch_history(
    api_base_url: str = DEFAULT_API_BASE_URL,
    get: GetFunction = requests.get,
) -> dict[str, Any]:
    try:
        response = get(_api_url(api_base_url, "/history"), timeout=10)
    except Exception as exc:
        raise ApiClientError("Could not load analysis history from the backend.") from exc

    return _parse_response(response)


def fetch_dashboard_metrics(
    api_base_url: str = DEFAULT_API_BASE_URL,
    get: GetFunction = requests.get,
) -> dict[str, Any]:
    try:
        response = get(_api_url(api_base_url, "/dashboard/metrics"), timeout=10)
    except Exception as exc:
        raise ApiClientError("Could not load dashboard metrics from the backend.") from exc

    return _parse_response(response)


def submit_single_review(
    review_text: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    response = post(
        _api_url(api_base_url, "/reviews"),
        json={"text": _clean_review_text(review_text)},
        timeout=10,
    )
    return _parse_response(response)


def submit_review_batch(
    review_texts: list[str],
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    response = post(
        _api_url(api_base_url, "/reviews/batch"),
        json=_review_payload(review_texts),
        timeout=10,
    )
    return _parse_response(response)


def fetch_sentiment(
    review_text: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    response = post(
        _api_url(api_base_url, "/sentiment"),
        json={"text": _clean_review_text(review_text)},
        timeout=10,
    )
    return _parse_response(response)


def fetch_keywords(
    review_texts: list[str],
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    response = post(
        _api_url(api_base_url, "/keywords"),
        json=_review_payload(review_texts),
        timeout=10,
    )
    return _parse_response(response)


def fetch_summary(
    review_texts: list[str],
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    response = post(
        _api_url(api_base_url, "/summarize"),
        json=_review_payload(review_texts),
        timeout=10,
    )
    return _parse_response(response)


def fetch_review_insights(
    review_texts: list[str],
    api_base_url: str = DEFAULT_API_BASE_URL,
    post: PostFunction = requests.post,
) -> dict[str, Any]:
    response = post(
        _api_url(api_base_url, "/insights"),
        json=_review_payload(review_texts),
        timeout=10,
    )
    return _parse_response(response)
