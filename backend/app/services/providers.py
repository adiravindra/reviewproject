import os
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from backend.app.errors import AppError
from backend.app.settings import Settings


def create_chat_model(settings: Settings) -> Any:
    provider = settings.llm_provider.casefold()
    options = {
        "model": settings.llm_model,
        "temperature": 0,
        "timeout": settings.provider_timeout_seconds,
        "max_retries": 0,
    }
    try:
        if provider in {"google", "gemini"}:
            if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
                raise _credential_error("GOOGLE_API_KEY")
            return ChatGoogleGenerativeAI(**options)
        if provider == "groq":
            if not os.getenv("GROQ_API_KEY"):
                raise _credential_error("GROQ_API_KEY")
            return ChatGroq(**options)
    except AppError:
        raise
    except Exception:
        raise AppError(
            code="llm_failed",
            message="The configured language-model provider could not be initialized.",
            stage="analysis",
            status_code=502,
        ) from None
    raise AppError(
        code="llm_failed",
        message="The configured language-model provider is not supported.",
        stage="analysis",
        status_code=422,
    )


def _credential_error(variable_name: str) -> AppError:
    return AppError(
        code="llm_failed",
        message=f"Set {variable_name} in the environment before running analysis.",
        stage="analysis",
        status_code=503,
    )
