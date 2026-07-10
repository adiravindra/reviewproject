from typing import Any
from urllib.parse import quote

import requests


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
ANALYZE_TIMEOUT_SECONDS = 130
HISTORY_TIMEOUT_SECONDS = 10


class ApiClientError(Exception):
    """Structured, user-facing failure from the backend or HTTP boundary."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "scrape_failed",
        stage: str = "request",
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.stage = stage
        self.retryable = retryable
        self.details = details or {}


def analyze_website(
    website_url: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    cleaned_url = website_url.strip()
    if not cleaned_url:
        raise ApiClientError(
            "Enter a public review page URL before analyzing.",
            code="invalid_url",
            stage="validation",
        )
    try:
        response = requests.post(
            _api_url(api_base_url, "/analysis/website"),
            json={"url": cleaned_url},
            timeout=ANALYZE_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise ApiClientError(
            "The website analysis request exceeded the client timeout.",
            code="request_timeout",
            stage="request",
            retryable=True,
        ) from exc
    except requests.RequestException as exc:
        raise ApiClientError(
            "Could not reach the backend analysis service.",
            code="scrape_failed",
            stage="request",
            retryable=True,
        ) from exc
    return _parse_response(response)


def fetch_history(api_base_url: str = DEFAULT_API_BASE_URL) -> dict[str, Any]:
    return _get_json(_api_url(api_base_url, "/analysis/history"))


def fetch_history_item(
    run_id: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
) -> dict[str, Any]:
    encoded_id = quote(run_id, safe="")
    return _get_json(_api_url(api_base_url, f"/analysis/history/{encoded_id}"))


def _get_json(url: str) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=HISTORY_TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise ApiClientError(
            "The history request timed out.",
            code="request_timeout",
            stage="history",
            retryable=True,
        ) from exc
    except requests.RequestException as exc:
        raise ApiClientError(
            "Could not load website analysis history.",
            code="scrape_failed",
            stage="history",
            retryable=True,
        ) from exc
    return _parse_response(response)


def _api_url(api_base_url: str, path: str) -> str:
    return f"{api_base_url.rstrip('/')}/{path.lstrip('/')}"


def _parse_response(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except (TypeError, ValueError) as exc:
        raise ApiClientError(
            "The backend returned an invalid response.",
            code="scrape_failed",
            stage="request",
        ) from exc
    if not isinstance(payload, dict):
        raise ApiClientError(
            "The backend returned an invalid response.",
            code="scrape_failed",
            stage="request",
        )

    status_code = int(getattr(response, "status_code", 500))
    if status_code >= 400:
        error = payload.get("error")
        if isinstance(error, dict):
            details = error.get("details")
            raise ApiClientError(
                str(error.get("message") or "The backend could not complete the request."),
                code=str(error.get("code") or "scrape_failed"),
                stage=str(error.get("stage") or "request"),
                retryable=bool(error.get("retryable", False)),
                details=details if isinstance(details, dict) else {},
            )
        raise ApiClientError("The backend could not complete the request.")
    return payload
