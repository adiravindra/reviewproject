from typing import Any

import requests


class BackendUnavailable(Exception):
    """The FastAPI process cannot be reached within the client boundary."""


class ApiClientError(Exception):
    """A safe, structured backend or HTTP failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def check_health(base_url: str, *, session=requests) -> bool:
    try:
        response = session.get(f"{base_url.rstrip('/')}/health", timeout=2)
        return response.status_code == 200 and response.json() == {"status": "ok"}
    except (requests.RequestException, ValueError):
        return False


def request_analysis(
    url: str,
    provider: str,
    base_url: str,
    *,
    session=requests,
) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/analyze"
    try:
        response = session.post(
            endpoint,
            json={"url": url, "provider": provider},
            timeout=45,
        )
    except (requests.ConnectionError, requests.Timeout):
        raise BackendUnavailable("The FastAPI backend is not reachable.") from None
    except requests.RequestException:
        raise ApiClientError("analysis_failed", "The request could not be completed.") from None

    if response.status_code >= 400:
        detail: dict[str, Any] = {}
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                payload = response.json()
                if isinstance(payload, dict) and isinstance(payload.get("detail"), dict):
                    detail = payload["detail"]
            except (TypeError, ValueError):
                detail = {}
        raise ApiClientError(
            str(detail.get("code", "analysis_failed")),
            str(detail.get("message", "The request could not be completed.")),
        )

    try:
        payload = response.json()
    except (TypeError, ValueError):
        raise ApiClientError("analysis_failed", "The backend returned an invalid response.") from None
    if not isinstance(payload, dict):
        raise ApiClientError("analysis_failed", "The backend returned an invalid response.")
    return payload
