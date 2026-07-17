"""Call the backend with stage-appropriate timeouts and safe error decoding."""

from collections.abc import Callable
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


_UNAVAILABLE_MESSAGE = "The FastAPI backend is not reachable."
_REQUEST_FAILED_MESSAGE = "The request could not be completed."
_INVALID_RESPONSE_MESSAGE = "The backend returned an invalid response."


def _perform_request(request: Callable[[], requests.Response]) -> requests.Response:
    """Run one HTTP request and reduce transport errors to safe exceptions."""

    try:
        response = request()
    except (requests.ConnectionError, requests.Timeout):
        raise BackendUnavailable(_UNAVAILABLE_MESSAGE) from None
    except requests.RequestException:
        raise ApiClientError("analysis_failed", _REQUEST_FAILED_MESSAGE) from None

    if response.status_code >= 400:
        try:
            payload = response.json()
        except (TypeError, ValueError):
            payload = None
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("detail"), dict)
            and isinstance(payload["detail"].get("code"), str)
            and isinstance(payload["detail"].get("message"), str)
        ):
            raise ApiClientError(payload["detail"]["code"], payload["detail"]["message"])
        raise ApiClientError("analysis_failed", _REQUEST_FAILED_MESSAGE)
    return response


def _decode_success(response: requests.Response, is_valid: Callable[[Any], bool]) -> Any:
    """Decode and validate a successful response without exposing its contents."""

    try:
        payload = response.json()
    except (TypeError, ValueError):
        raise ApiClientError("analysis_failed", _INVALID_RESPONSE_MESSAGE) from None
    if not is_valid(payload):
        raise ApiClientError("analysis_failed", _INVALID_RESPONSE_MESSAGE)
    return payload


def check_health(base_url: str, *, session=requests) -> bool:
    """Probe process readiness with a short timeout and a strict response shape."""

    endpoint = f"{base_url.rstrip('/')}/health"
    try:
        response = session.get(endpoint, timeout=2)
        return response.status_code == 200 and response.json() == {"status": "ok"}
    except (requests.RequestException, TypeError, ValueError):
        return False


def request_collection(url: str, base_url: str, *, session=requests) -> dict[str, Any]:
    """Collect reviews from a URL before requesting model-backed analysis."""

    endpoint = f"{base_url.rstrip('/')}/api/collect"
    response = _perform_request(lambda: session.post(endpoint, json={"url": url}, timeout=15))
    return _decode_success(response, lambda payload: isinstance(payload, dict))


def request_demo(base_url: str, *, session=requests) -> dict[str, Any]:
    """Load the deterministic demo collection through the backend boundary."""

    endpoint = f"{base_url.rstrip('/')}/api/demo"
    response = _perform_request(lambda: session.get(endpoint, timeout=15))
    return _decode_success(response, lambda payload: isinstance(payload, dict))


def request_analysis(
    collection: dict[str, Any], base_url: str, *, session=requests
) -> dict[str, Any]:
    """Analyze an existing collection with the longer model-stage timeout."""

    endpoint = f"{base_url.rstrip('/')}/api/analyze"
    payload = {"source": collection["source"], "reviews": collection["reviews"]}
    response = _perform_request(lambda: session.post(endpoint, json=payload, timeout=45))
    return _decode_success(response, lambda decoded: isinstance(decoded, dict))


def request_history(base_url: str, *, session=requests) -> list[dict[str, Any]]:
    """Load compact history entries from the backend."""

    endpoint = f"{base_url.rstrip('/')}/api/history"
    response = _perform_request(lambda: session.get(endpoint, timeout=5))
    return _decode_success(
        response,
        lambda payload: isinstance(payload, list) and all(isinstance(entry, dict) for entry in payload),
    )


def request_history_report(
    run_id: int, base_url: str, *, session=requests
) -> dict[str, Any]:
    """Load one stored history report after validating its local identifier."""

    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise ApiClientError("history_not_found", "That history entry was not found.")
    endpoint = f"{base_url.rstrip('/')}/api/history/{run_id}"
    response = _perform_request(lambda: session.get(endpoint, timeout=5))
    return _decode_success(response, lambda payload: isinstance(payload, dict))
