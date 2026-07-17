"""Test Groq credential preflight and sanitized status mapping."""

import os
import unittest
from unittest.mock import patch

import requests

from backend.app.credentials import (
    GROQ_API_KEY_VARIABLE,
    GROQ_MODELS_ENDPOINT,
    VALIDATION_TIMEOUT,
    get_groq_api_key,
    validate_groq_credentials,
)
from backend.app.errors import AnalysisError


class FakeResponse:
    """Simulate a Groq status and potentially sensitive response body."""

    def __init__(self, status_code, *, text=""):
        """Store response values used to verify body-independent mapping."""

        self.status_code = status_code
        self.text = text


class FakeSession:
    """Simulate HTTP transport while recording the requested preflight."""

    def __init__(self, result):
        """Configure either a fake response or transport exception result."""

        self.result = result
        self.calls = 0
        self.url = None
        self.headers = None
        self.timeout = None

    def get(self, url, *, headers, timeout):
        """Record preflight inputs and produce the configured transport result."""

        self.calls += 1
        self.url = url
        self.headers = headers
        self.timeout = timeout
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class CredentialTests(unittest.TestCase):
    """Group Groq preflight endpoint, ordering, and safety contracts."""

    def test_model_list_uses_bearer_header_timeout_and_trimmed_key(self):
        """Validate Groq through its model list using the normalized shared key."""

        session = FakeSession(FakeResponse(200))
        with patch.dict(os.environ, {GROQ_API_KEY_VARIABLE: "  groq-secret  "}, clear=True):
            validate_groq_credentials(session=session)

        self.assertEqual(session.url, GROQ_MODELS_ENDPOINT)
        self.assertEqual(session.headers, {"Authorization": "Bearer groq-secret"})
        self.assertEqual(session.timeout, VALIDATION_TIMEOUT)

    def test_missing_or_blank_key_stops_before_http(self):
        """Reject unavailable credentials before starting a network request."""

        for api_key in (None, "", "   "):
            with self.subTest(api_key=api_key):
                session = FakeSession(FakeResponse(200))
                environment = {} if api_key is None else {GROQ_API_KEY_VARIABLE: api_key}
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaises(AnalysisError) as raised:
                        validate_groq_credentials(session=session)
                self.assertEqual(raised.exception.code, "missing_api_key")
                self.assertEqual(
                    str(raised.exception), "Set GROQ_API_KEY before analyzing reviews."
                )
                self.assertEqual(session.calls, 0)

    def test_get_groq_api_key_returns_a_trimmed_value(self):
        """Normalize the one credential before any boundary uses it."""

        with patch.dict(os.environ, {GROQ_API_KEY_VARIABLE: "  groq-secret  "}, clear=True):
            self.assertEqual(get_groq_api_key(), "groq-secret")

    def test_rejection_statuses_are_sanitized(self):
        """Map rejected credentials without exposing keys or response bodies."""

        for status in (400, 401, 403):
            with self.subTest(status=status):
                session = FakeSession(FakeResponse(status, text="raw provider secret response"))
                with patch.dict(os.environ, {GROQ_API_KEY_VARIABLE: "groq-secret"}, clear=True):
                    with self.assertRaises(AnalysisError) as raised:
                        validate_groq_credentials(session=session)
                self.assertEqual(raised.exception.code, "invalid_api_key")
                self.assertNotIn("groq-secret", str(raised.exception))
                self.assertNotIn("raw provider", str(raised.exception))

    def test_unavailable_statuses_and_transport_failures_are_sanitized(self):
        """Map outages to a stable code without body, key, or transport details."""

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
                with patch.dict(os.environ, {GROQ_API_KEY_VARIABLE: "groq-secret"}, clear=True):
                    with self.assertRaises(AnalysisError) as raised:
                        validate_groq_credentials(session=session)
                self.assertEqual(raised.exception.code, "groq_unavailable")
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
