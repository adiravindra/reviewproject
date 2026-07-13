"""Call the backend with stage-appropriate timeouts and safe error decoding."""

from typing import Any

import requests


class BackendUnavailable(Exception):
    """The FastAPI process cannot be reached within the client boundary."""


class ApiClientError(Exception):
    """A safe, structured backend or HTTP failure."""

    def __init__(self, code: str, message: str):
        """Store only the code and message approved for dashboard rendering."""

        super().__init__(message)
        self.code = code
        self.message = message


def check_health(base_url: str, *, session=requests) -> bool:
    """Probe process readiness with a short timeout and a strict response shape."""

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
    """Request a potentially long analysis and return its decoded object response."""

    endpoint = f"{base_url.rstrip('/')}/api/analyze"
    try:
        # Analysis includes collection and one provider call, so it receives a
        # longer budget than the two-second health/readiness probe.
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
        # Error JSON is treated as untrusted: preserve only the documented nested
        # code/message fields and fall back safely for every other response shape.
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
