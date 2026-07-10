import os
import unittest
from unittest.mock import patch

from backend.app.errors import AppError
from backend.app.settings import Settings


class ProviderFactoryTests(unittest.TestCase):
    def test_factory_constructs_gemini_with_bounded_provider_options(self) -> None:
        from backend.app.services import providers

        settings = Settings(
            llm_provider="google",
            llm_model="gemini-2.5-flash-lite",
            provider_timeout_seconds=20,
        )
        with (
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=True),
            patch.object(providers, "ChatGoogleGenerativeAI") as constructor,
        ):
            result = providers.create_chat_model(settings)

        self.assertIs(result, constructor.return_value)
        constructor.assert_called_once_with(
            model="gemini-2.5-flash-lite",
            temperature=0,
            timeout=20,
            max_retries=0,
        )

    def test_factory_constructs_groq_without_leaking_provider_types(self) -> None:
        from backend.app.services import providers

        settings = Settings(
            llm_provider="groq",
            llm_model="llama-3.3-70b-versatile",
            provider_timeout_seconds=12,
        )
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=True),
            patch.object(providers, "ChatGroq") as constructor,
        ):
            result = providers.create_chat_model(settings)

        self.assertIs(result, constructor.return_value)
        constructor.assert_called_once_with(
            model="llama-3.3-70b-versatile",
            temperature=0,
            timeout=12,
            max_retries=0,
        )

    def test_missing_credentials_and_unknown_provider_are_safe_llm_errors(self) -> None:
        from backend.app.services.providers import create_chat_model

        with patch.dict(os.environ, {}, clear=True), self.assertRaises(AppError) as missing:
            create_chat_model(Settings(llm_provider="google"))
        self.assertEqual(missing.exception.code, "llm_failed")
        self.assertIn("GOOGLE_API_KEY", missing.exception.message)

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test"}, clear=True), self.assertRaises(AppError) as unknown:
            create_chat_model(Settings(llm_provider="unknown"))
        self.assertEqual(unknown.exception.code, "llm_failed")
        self.assertNotIn("test", unknown.exception.message)


if __name__ == "__main__":
    unittest.main()
