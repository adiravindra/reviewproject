import os
from dataclasses import dataclass
from pathlib import Path


HARD_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
HARD_MAX_PAGES = 3
HARD_SCRAPE_DEADLINE_SECONDS = 25.0
HARD_MAX_REVIEWS = 60
HARD_LLM_BATCH_SIZE = 15
HARD_MAX_BATCH_CALLS = 4
HARD_MAX_SYNTHESIS_CALLS = 1
HARD_MAX_LLM_CALLS = 5
HARD_PROVIDER_TIMEOUT_SECONDS = 20.0
HARD_OVERALL_DEADLINE_SECONDS = 120.0
HARD_MAX_REDIRECTS = 5


@dataclass(frozen=True)
class Settings:
    max_response_bytes: int = HARD_MAX_RESPONSE_BYTES
    max_pages: int = HARD_MAX_PAGES
    scrape_deadline_seconds: float = HARD_SCRAPE_DEADLINE_SECONDS
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 10.0
    max_redirects: int = HARD_MAX_REDIRECTS
    max_reviews: int = HARD_MAX_REVIEWS
    llm_batch_size: int = HARD_LLM_BATCH_SIZE
    max_batch_calls: int = HARD_MAX_BATCH_CALLS
    max_synthesis_calls: int = HARD_MAX_SYNTHESIS_CALLS
    max_llm_calls: int = HARD_MAX_LLM_CALLS
    provider_timeout_seconds: float = HARD_PROVIDER_TIMEOUT_SECONDS
    overall_deadline_seconds: float = HARD_OVERALL_DEADLINE_SECONDS
    min_reviews: int = 2
    low_sample_threshold: int = 5
    llm_provider: str = "google"
    llm_model: str = "gemini-2.5-flash-lite"
    db_path: Path = Path("data/reviewinsight.db")
    user_agent: str = "ReviewInsight/1.0 (static public review analysis)"

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("REVIEWINSIGHT_LLM_PROVIDER", "google").strip().casefold() or "google"
        default_model = (
            "llama-3.3-70b-versatile"
            if provider == "groq"
            else "gemini-2.5-flash-lite"
        )
        return cls(
            max_response_bytes=_bounded_int(
                "REVIEWINSIGHT_MAX_RESPONSE_BYTES",
                HARD_MAX_RESPONSE_BYTES,
                HARD_MAX_RESPONSE_BYTES,
            ),
            max_pages=_bounded_int("REVIEWINSIGHT_MAX_PAGES", HARD_MAX_PAGES, HARD_MAX_PAGES),
            scrape_deadline_seconds=_bounded_float(
                "REVIEWINSIGHT_SCRAPE_DEADLINE_SECONDS",
                HARD_SCRAPE_DEADLINE_SECONDS,
                HARD_SCRAPE_DEADLINE_SECONDS,
            ),
            connect_timeout_seconds=_bounded_float(
                "REVIEWINSIGHT_CONNECT_TIMEOUT_SECONDS", 5.0, 10.0
            ),
            read_timeout_seconds=_bounded_float(
                "REVIEWINSIGHT_READ_TIMEOUT_SECONDS", 10.0, 20.0
            ),
            max_redirects=_bounded_int(
                "REVIEWINSIGHT_MAX_REDIRECTS", HARD_MAX_REDIRECTS, HARD_MAX_REDIRECTS
            ),
            max_reviews=_bounded_int(
                "REVIEWINSIGHT_MAX_REVIEWS", HARD_MAX_REVIEWS, HARD_MAX_REVIEWS
            ),
            llm_batch_size=_bounded_int(
                "REVIEWINSIGHT_LLM_BATCH_SIZE", HARD_LLM_BATCH_SIZE, HARD_LLM_BATCH_SIZE
            ),
            max_batch_calls=_bounded_int(
                "REVIEWINSIGHT_MAX_BATCH_CALLS", HARD_MAX_BATCH_CALLS, HARD_MAX_BATCH_CALLS
            ),
            max_synthesis_calls=_bounded_int(
                "REVIEWINSIGHT_MAX_SYNTHESIS_CALLS",
                HARD_MAX_SYNTHESIS_CALLS,
                HARD_MAX_SYNTHESIS_CALLS,
            ),
            max_llm_calls=_bounded_int(
                "REVIEWINSIGHT_MAX_LLM_CALLS", HARD_MAX_LLM_CALLS, HARD_MAX_LLM_CALLS
            ),
            provider_timeout_seconds=_bounded_float(
                "REVIEWINSIGHT_PROVIDER_TIMEOUT_SECONDS",
                HARD_PROVIDER_TIMEOUT_SECONDS,
                HARD_PROVIDER_TIMEOUT_SECONDS,
            ),
            overall_deadline_seconds=_bounded_float(
                "REVIEWINSIGHT_OVERALL_DEADLINE_SECONDS",
                HARD_OVERALL_DEADLINE_SECONDS,
                HARD_OVERALL_DEADLINE_SECONDS,
            ),
            min_reviews=_bounded_floor_int("REVIEWINSIGHT_MIN_REVIEWS", 2, HARD_MAX_REVIEWS),
            low_sample_threshold=_bounded_floor_int(
                "REVIEWINSIGHT_LOW_SAMPLE_THRESHOLD", 5, HARD_MAX_REVIEWS
            ),
            llm_provider=provider,
            llm_model=os.getenv("REVIEWINSIGHT_LLM_MODEL", default_model).strip() or default_model,
            db_path=Path(os.getenv("REVIEWINSIGHT_DB_PATH", "data/reviewinsight.db")),
            user_agent=os.getenv(
                "REVIEWINSIGHT_USER_AGENT",
                "ReviewInsight/1.0 (static public review analysis)",
            ).strip()
            or "ReviewInsight/1.0 (static public review analysis)",
        )


def _bounded_int(name: str, default: int, ceiling: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(value, ceiling) if value > 0 else default


def _bounded_float(name: str, default: float, ceiling: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(value, ceiling) if value > 0 else default


def _bounded_floor_int(name: str, default: int, ceiling: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(default, min(value, ceiling)) if value > 0 else default
