import os
import unittest
from pathlib import Path
from unittest.mock import patch


class SettingsTests(unittest.TestCase):
    def test_documented_defaults_are_centralized(self) -> None:
        from backend.app.settings import Settings

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.max_response_bytes, 2 * 1024 * 1024)
        self.assertEqual(settings.max_pages, 3)
        self.assertEqual(settings.scrape_deadline_seconds, 25.0)
        self.assertEqual(settings.max_reviews, 60)
        self.assertEqual(settings.llm_batch_size, 15)
        self.assertEqual(settings.max_batch_calls, 4)
        self.assertEqual(settings.max_synthesis_calls, 1)
        self.assertEqual(settings.max_llm_calls, 5)
        self.assertEqual(settings.provider_timeout_seconds, 20.0)
        self.assertEqual(settings.overall_deadline_seconds, 120.0)
        self.assertEqual(settings.min_reviews, 2)
        self.assertEqual(settings.low_sample_threshold, 5)
        self.assertEqual(settings.llm_provider, "google")
        self.assertEqual(settings.llm_model, "gemini-2.5-flash-lite")

    def test_environment_overrides_are_clamped_to_safe_hard_ceilings(self) -> None:
        from backend.app.settings import Settings

        environment = {
            "REVIEWINSIGHT_MAX_RESPONSE_BYTES": str(9 * 1024 * 1024),
            "REVIEWINSIGHT_MAX_PAGES": "99",
            "REVIEWINSIGHT_MAX_REVIEWS": "999",
            "REVIEWINSIGHT_LLM_BATCH_SIZE": "100",
            "REVIEWINSIGHT_MAX_LLM_CALLS": "20",
            "REVIEWINSIGHT_OVERALL_DEADLINE_SECONDS": "900",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.max_response_bytes, 2 * 1024 * 1024)
        self.assertEqual(settings.max_pages, 3)
        self.assertEqual(settings.max_reviews, 60)
        self.assertEqual(settings.llm_batch_size, 15)
        self.assertEqual(settings.max_llm_calls, 5)
        self.assertEqual(settings.overall_deadline_seconds, 120.0)

    def test_provider_model_and_database_path_are_configurable(self) -> None:
        from backend.app.settings import Settings

        environment = {
            "REVIEWINSIGHT_LLM_PROVIDER": "groq",
            "REVIEWINSIGHT_LLM_MODEL": "llama-3.3-70b-versatile",
            "REVIEWINSIGHT_DB_PATH": "tmp/custom.db",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.llm_provider, "groq")
        self.assertEqual(settings.llm_model, "llama-3.3-70b-versatile")
        self.assertEqual(settings.db_path, Path("tmp/custom.db"))


if __name__ == "__main__":
    unittest.main()
