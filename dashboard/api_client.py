from typing import Any

import requests


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"


class ApiClientError(Exception):
    pass


# Send one review to the backend.
def analyze_review(
    review_text: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    cleaned_text = review_text.strip()
    if not cleaned_text:
        raise ApiClientError("Paste one review before analyzing.")

    response = requests.post(
        _api_url(api_base_url, "/analysis/single"),
        json={"text": cleaned_text},
        timeout=30,
    )
    return _parse_response(response)


def fetch_history(
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    # Load saved reviews for the History page.
    try:
        response = requests.get(_api_url(api_base_url, "/analysis/history"), timeout=10)
    except Exception as exc:
        raise ApiClientError("Could not load analysis history from the backend.") from exc

    return _parse_response(response)


def _api_url(api_base_url: str, path: str) -> str:
    return f"{api_base_url.rstrip('/')}/{path.lstrip('/')}"


def _parse_response(response: Any) -> dict[str, Any]:
    # Turn backend or connection problems into simple Streamlit errors.
    try:
        response.raise_for_status()
    except Exception as exc:
        raise ApiClientError("The backend could not complete the request.") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise ApiClientError("The backend returned an invalid response.") from exc
