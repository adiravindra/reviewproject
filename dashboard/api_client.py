from typing import Any

import requests


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
ANALYZE_TIMEOUT_SECONDS = 130


class ApiClientError(Exception):
    """User-facing error raised when Streamlit cannot complete an API call."""


def analyze_website(
    website_url: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    cleaned_url = website_url.strip()
    if not cleaned_url:
        raise ApiClientError("Enter a public review page URL before analyzing.")

    try:
        response = requests.post(
            _api_url(api_base_url, "/analysis/website"),
            json={"url": cleaned_url},
            timeout=ANALYZE_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise ApiClientError("The website analysis request timed out.") from exc
    except requests.RequestException as exc:
        raise ApiClientError("Could not reach the backend analysis service.") from exc
    return _parse_response(response)


def fetch_history(api_base_url: str = DEFAULT_API_BASE_URL) -> dict[str, Any]:
    try:
        response = requests.get(_api_url(api_base_url, "/analysis/history"), timeout=10)
    except requests.RequestException as exc:
        raise ApiClientError("Could not load website analysis history.") from exc
    return _parse_response(response)


def _api_url(api_base_url: str, path: str) -> str:
    return f"{api_base_url.rstrip('/')}/{path.lstrip('/')}"


def _parse_response(response: Any) -> dict[str, Any]:
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ApiClientError("The backend could not complete the request.") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiClientError("The backend returned an invalid response.") from exc
    if not isinstance(payload, dict):
        raise ApiClientError("The backend returned an invalid response.")
    return payload
