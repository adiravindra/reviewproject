"""Validate the Groq credential without generating AI output."""

import os

import requests

from backend.app.errors import AnalysisError


# Credential checks fail quickly before collection or paid model work; the
# tuple bounds connection setup separately from response waiting.
GROQ_API_KEY_VARIABLE = "GROQ_API_KEY"
GROQ_MODELS_ENDPOINT = "https://api.groq.com/openai/v1/models"
VALIDATION_TIMEOUT = (3, 5)


def get_groq_api_key() -> str:
    """Return the normalized Groq credential or raise a safe public error."""

    api_key = os.getenv(GROQ_API_KEY_VARIABLE, "").strip()
    if not api_key:
        raise AnalysisError(
            "missing_api_key", "Set GROQ_API_KEY before analyzing reviews."
        )
    return api_key


def validate_groq_credentials(*, session=requests) -> None:
    """Check Groq model access and map its status without exposing responses."""

    api_key = get_groq_api_key()
    try:
        response = session.get(
            GROQ_MODELS_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=VALIDATION_TIMEOUT,
        )
    except requests.RequestException:
        raise AnalysisError(
            "groq_unavailable",
            "Groq credentials could not be validated. Analysis did not start; try again when Groq is reachable.",
        ) from None

    # Status alone determines the safe outcome. Response bodies can contain
    # unstable or sensitive diagnostics and must never cross this boundary.
    if response.status_code in {400, 401, 403}:
        raise AnalysisError(
            "invalid_api_key",
            "Groq rejected the configured credential. Check the key and its permissions.",
        )
    if response.status_code < 200 or response.status_code >= 300:
        raise AnalysisError(
            "groq_unavailable",
            "Groq credentials could not be validated. Analysis did not start; try again when Groq is reachable.",
        )
