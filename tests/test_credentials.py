"""Test non-generative credential preflight and sanitized status mapping."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

from backend.app.analyzer import build_model
from backend.app.credentials import validate_provider_credentials
from backend.app.errors import AnalysisError


class FakeResponse:
    """Simulate provider status and potentially sensitive body content."""

    def __init__(self, status_code, *, text=""):
        """Store the response fields needed to verify body-independent mapping."""

        self.status_code = status_code
        self.text = text


class FakeSession:
    """Simulate provider HTTP transport while recording authentication policy."""

    def __init__(self, result):
        """Configure either a fake response or transport exception result."""

        self.result = result
        self.url = None
        self.headers = None
        self.timeout = None

    def get(self, url, *, headers, timeout):
        """Record preflight inputs and produce the configured transport result."""

        self.url = url
        self.headers = headers
        self.timeout = timeout
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class CredentialTests(unittest.TestCase):
    """Group provider preflight endpoint, ordering, and safety contracts."""

    def test_gemini_uses_non_generative_model_list_endpoint(self):
        """Validate Gemini via model listing with its header and short timeout."""

        session = FakeSession(FakeResponse(200))
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "google-secret"}, clear=True):
            validate_provider_credentials("google", session=session)
        self.assertEqual(
            session.url,
            "https://generativelanguage.googleapis.com/v1beta/models",
        )
        self.assertEqual(session.headers, {"x-goog-api-key": "google-secret"})
        self.assertEqual(session.timeout, (3, 5))

    def test_groq_uses_non_generative_model_list_endpoint(self):
        """Validate Groq via model listing with bearer authentication."""

        session = FakeSession(FakeResponse(200))
        with patch.dict(os.environ, {"GROQ_API_KEY": "groq-secret"}, clear=True):
            validate_provider_credentials("groq", session=session)
        self.assertEqual(session.url, "https://api.groq.com/openai/v1/models")
        self.assertEqual(session.headers, {"Authorization": "Bearer groq-secret"})

    def test_google_preflight_and_model_share_trimmed_selected_key(self):
        """Pass one normalized Google credential to preflight and construction."""

        session = FakeSession(FakeResponse(200))
        constructor_calls = []

        class FakeGoogleModel:
            """Record the explicit Google constructor credential."""

            def __init__(self, **kwargs):
                """Capture keyword arguments supplied by the model factory."""

                constructor_calls.append(kwargs)

        fake_module = SimpleNamespace(ChatGoogleGenerativeAI=FakeGoogleModel)
        with (
            patch.dict(os.environ, {"GOOGLE_API_KEY": "  google-secret  "}, clear=True),
            patch.dict(sys.modules, {"langchain_google_genai": fake_module}),
        ):
            validate_provider_credentials("google", session=session)
            build_model("google")

        self.assertEqual(session.headers, {"x-goog-api-key": "google-secret"})
        self.assertIn("google_api_key", constructor_calls[0])
        self.assertEqual(constructor_calls[0]["google_api_key"], "google-secret")

    def test_groq_preflight_and_model_share_trimmed_selected_key(self):
        """Pass one normalized Groq credential to preflight and construction."""

        session = FakeSession(FakeResponse(200))
        constructor_calls = []

        class FakeGroqModel:
            """Record the explicit Groq constructor credential."""

            def __init__(self, **kwargs):
                """Capture keyword arguments supplied by the model factory."""

                constructor_calls.append(kwargs)

        fake_module = SimpleNamespace(ChatGroq=FakeGroqModel)
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "  groq-secret  "}, clear=True),
            patch.dict(sys.modules, {"langchain_groq": fake_module}),
        ):
            validate_provider_credentials("groq", session=session)
            build_model("groq")

        self.assertEqual(session.headers, {"Authorization": "Bearer groq-secret"})
        self.assertIn("api_key", constructor_calls[0])
        self.assertEqual(constructor_calls[0]["api_key"], "groq-secret")

    def test_missing_selected_key_stops_before_http(self):
        """Stop a missing selected credential before making any HTTP request."""

        session = FakeSession(FakeResponse(200))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AnalysisError) as raised:
                validate_provider_credentials("google", session=session)
        self.assertEqual(raised.exception.code, "missing_api_key")
        self.assertIsNone(session.url)

    def test_provider_rejection_is_safe(self):
        """Map rejection statuses without exposing credentials or response bodies."""

        for status in (400, 401, 403):
            with self.subTest(status=status):
                session = FakeSession(
                    FakeResponse(status, text="raw provider secret response")
                )
                with patch.dict(os.environ, {"GROQ_API_KEY": "groq-secret"}, clear=True):
                    with self.assertRaises(AnalysisError) as raised:
                        validate_provider_credentials("groq", session=session)
                self.assertEqual(raised.exception.code, "invalid_api_key")
                self.assertNotIn("groq-secret", str(raised.exception))
                self.assertNotIn("raw provider", str(raised.exception))

    def test_temporary_or_unknown_failure_is_safe(self):
        """Map rate, server, and transport failures to sanitized unavailability."""

        cases = [
            FakeResponse(429, text="quota internals"),
            FakeResponse(500, text="provider stack"),
            requests.Timeout("timeout details"),
            requests.ConnectionError("socket details"),
            requests.RequestException("transport details"),
        ]
        for case in cases:
            with self.subTest(case=case):
                session = FakeSession(case)
                with patch.dict(os.environ, {"GROQ_API_KEY": "groq-secret"}, clear=True):
                    with self.assertRaises(AnalysisError) as raised:
                        validate_provider_credentials("groq", session=session)
                self.assertEqual(raised.exception.code, "provider_unavailable")
                message = str(raised.exception)
                self.assertNotIn("groq-secret", message)
                for detail in (
                    "quota internals",
                    "provider stack",
                    "timeout details",
                    "socket details",
                    "transport details",
                ):
                    self.assertNotIn(detail, message)


if __name__ == "__main__":
    unittest.main()
