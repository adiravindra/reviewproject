import os
import unittest
from unittest.mock import patch

import requests

from backend.app.credentials import validate_provider_credentials
from backend.app.errors import AnalysisError


class FakeResponse:
    def __init__(self, status_code, *, text=""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, result):
        self.result = result
        self.url = None
        self.headers = None
        self.timeout = None

    def get(self, url, *, headers, timeout):
        self.url = url
        self.headers = headers
        self.timeout = timeout
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class CredentialTests(unittest.TestCase):
    def test_gemini_uses_non_generative_model_list_endpoint(self):
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
        session = FakeSession(FakeResponse(200))
        with patch.dict(os.environ, {"GROQ_API_KEY": "groq-secret"}, clear=True):
            validate_provider_credentials("groq", session=session)
        self.assertEqual(session.url, "https://api.groq.com/openai/v1/models")
        self.assertEqual(session.headers, {"Authorization": "Bearer groq-secret"})

    def test_missing_selected_key_stops_before_http(self):
        session = FakeSession(FakeResponse(200))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AnalysisError) as raised:
                validate_provider_credentials("google", session=session)
        self.assertEqual(raised.exception.code, "missing_api_key")
        self.assertIsNone(session.url)

    def test_provider_rejection_is_safe(self):
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
