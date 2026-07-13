"""Validate provider credentials without generating AI output."""

import os
from dataclasses import dataclass

import requests

from backend.app.errors import AnalysisError
from backend.app.models import Provider

# Credential checks should fail quickly before collection or paid model work;
# the tuple bounds connection setup separately from response waiting.
VALIDATION_TIMEOUT = (3, 5)


@dataclass(frozen=True)
class CredentialConfig:
    """Describe one provider's secret location and authentication request."""

    display_name: str
    environment_variable: str
    endpoint: str
    header_name: str
    header_prefix: str = ""


# Provider-specific constants centralize secret names and non-generative model
# listing endpoints so preflight cannot accidentally prompt either provider.
PROVIDER_CREDENTIALS = {
    "google": CredentialConfig(
        "Gemini",
        "GOOGLE_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/models",
        "x-goog-api-key",
    ),
    "groq": CredentialConfig(
        "Groq",
        "GROQ_API_KEY",
        "https://api.groq.com/openai/v1/models",
        "Authorization",
        "Bearer ",
    ),
}


def validate_provider_credentials(provider: Provider, *, session=requests) -> None:
    """Require the selected key and map non-generative preflight status safely."""
    config = PROVIDER_CREDENTIALS[provider]
    api_key = os.getenv(config.environment_variable, "").strip()
    if not api_key:
        raise AnalysisError(
            "missing_api_key",
            f"Set {config.environment_variable} before using {config.display_name}.",
        )

    try:
        response = session.get(
            config.endpoint,
            headers={config.header_name: f"{config.header_prefix}{api_key}"},
            timeout=VALIDATION_TIMEOUT,
        )
    except requests.RequestException:
        raise AnalysisError(
            "provider_unavailable",
            f"{config.display_name} credentials could not be validated. Analysis did not start; try again when the provider is reachable.",
        ) from None

    # Only status codes influence the result. Provider response bodies are not
    # inspected or used in decisions because they may contain unstable or
    # sensitive diagnostics.
    if response.status_code in {400, 401, 403}:
        raise AnalysisError(
            "invalid_api_key",
            f"{config.display_name} rejected the configured credential. Check the key and its permissions.",
        )
    if response.status_code < 200 or response.status_code >= 300:
        raise AnalysisError(
            "provider_unavailable",
            f"{config.display_name} credentials could not be validated. Analysis did not start; try again when the provider is reachable.",
        )
