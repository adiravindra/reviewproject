import time
import unittest

import requests

from backend.app.errors import AppError
from backend.app.settings import Settings
from tests.fakes import FakeResponse, FakeSession, resolver_for


class StaticHttpFetcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = resolver_for(
            {
                "public.example": "93.184.216.34",
                "cdn.example": "1.1.1.1",
            }
        )

    def test_streams_bounded_html_with_explicit_request_options(self) -> None:
        from backend.app.services.fetching import StaticHttpFetcher

        response = FakeResponse(chunks=[b"<html>", b"reviews</html>"])
        session = FakeSession([response])
        fetcher = StaticHttpFetcher(Settings(max_response_bytes=100), session=session, resolver=self.resolver)

        page = fetcher.fetch("https://public.example/reviews", deadline=time.monotonic() + 5)

        self.assertEqual(page.html, "<html>reviews</html>")
        self.assertEqual(page.final_url, "https://public.example/reviews")
        self.assertTrue(response.closed)
        _, options = session.calls[0]
        self.assertFalse(options["allow_redirects"])
        self.assertTrue(options["stream"])
        self.assertIn("User-Agent", options["headers"])
        self.assertIsInstance(options["timeout"], tuple)

    def test_redirect_target_is_revalidated_before_following(self) -> None:
        from backend.app.services.fetching import StaticHttpFetcher

        session = FakeSession(
            [
                FakeResponse(302, headers={"Location": "http://127.0.0.1/admin"}),
                FakeResponse(),
            ]
        )
        fetcher = StaticHttpFetcher(Settings(), session=session, resolver=self.resolver)

        with self.assertRaises(AppError) as raised:
            fetcher.fetch("https://public.example/reviews")

        self.assertEqual(raised.exception.code, "invalid_url")
        self.assertEqual(len(session.calls), 1)

    def test_follows_bounded_public_redirects(self) -> None:
        from backend.app.services.fetching import StaticHttpFetcher

        session = FakeSession(
            [
                FakeResponse(301, headers={"Location": "https://cdn.example/reviews"}),
                FakeResponse(body=b"<html>ok</html>"),
            ]
        )
        page = StaticHttpFetcher(Settings(), session=session, resolver=self.resolver).fetch(
            "https://public.example/reviews"
        )

        self.assertEqual(page.final_url, "https://cdn.example/reviews")
        self.assertEqual(len(session.calls), 2)

    def test_rejects_oversized_non_html_blocked_and_challenge_responses(self) -> None:
        from backend.app.services.fetching import StaticHttpFetcher

        cases = [
            (FakeResponse(chunks=[b"12345", b"67890"]), Settings(max_response_bytes=8), "scrape_failed"),
            (FakeResponse(headers={"Content-Type": "application/pdf"}), Settings(), "scrape_failed"),
            (FakeResponse(403), Settings(), "blocked_source"),
            (FakeResponse(body=b"<html>Verify you are human CAPTCHA</html>"), Settings(), "blocked_source"),
        ]
        for response, settings, code in cases:
            with self.subTest(code=code), self.assertRaises(AppError) as raised:
                StaticHttpFetcher(settings, session=FakeSession([response]), resolver=self.resolver).fetch(
                    "https://public.example/reviews"
                )
            self.assertEqual(raised.exception.code, code)

    def test_connection_errors_are_sanitized(self) -> None:
        from backend.app.services.fetching import StaticHttpFetcher

        fetcher = StaticHttpFetcher(
            Settings(),
            session=FakeSession([requests.ConnectionError("secret network detail")]),
            resolver=self.resolver,
        )
        with self.assertRaises(AppError) as raised:
            fetcher.fetch("https://public.example/reviews")

        self.assertEqual(raised.exception.code, "scrape_failed")
        self.assertTrue(raised.exception.retryable)
        self.assertNotIn("secret", raised.exception.message)


if __name__ == "__main__":
    unittest.main()
