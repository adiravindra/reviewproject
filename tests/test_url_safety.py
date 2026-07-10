import socket
import unittest

from backend.app.errors import AppError
from tests.fakes import resolver_for


class UrlSafetyTests(unittest.TestCase):
    def test_accepts_public_http_url_and_normalizes_origin(self) -> None:
        from backend.app.services.url_safety import origin, validate_public_url

        validated = validate_public_url(
            " HTTPS://Public.Example:443/reviews?q=1 ",
            resolver=resolver_for({"public.example": "93.184.216.34"}),
        )

        self.assertEqual(validated.hostname, "public.example")
        self.assertEqual(validated.port, 443)
        self.assertEqual(origin(validated.url), ("https", "public.example", 443))

    def test_rejects_unsupported_credentials_and_non_public_destinations(self) -> None:
        from backend.app.services.url_safety import validate_public_url

        resolver = resolver_for(
            {
                "private.example": "10.0.0.2",
                "link.example": "169.254.10.4",
                "mixed.example": ["93.184.216.34", "127.0.0.1"],
            }
        )
        urls = [
            "ftp://private.example/reviews",
            "https://user:secret@private.example/reviews",
            "http://127.0.0.1/reviews",
            "https://private.example/reviews",
            "https://link.example/reviews",
            "https://mixed.example/reviews",
        ]

        for url in urls:
            with self.subTest(url=url), self.assertRaises(AppError) as raised:
                validate_public_url(url, resolver=resolver)
            self.assertEqual(raised.exception.code, "invalid_url")

    def test_dns_failure_is_a_safe_retryable_scrape_error(self) -> None:
        from backend.app.services.url_safety import validate_public_url

        def failed_resolver(*_: object, **__: object) -> list[tuple[object, ...]]:
            raise socket.gaierror("sensitive resolver detail")

        with self.assertRaises(AppError) as raised:
            validate_public_url("https://missing.example/reviews", resolver=failed_resolver)

        self.assertEqual(raised.exception.code, "scrape_failed")
        self.assertTrue(raised.exception.retryable)
        self.assertNotIn("sensitive", raised.exception.message)

    def test_same_origin_accounts_for_default_ports(self) -> None:
        from backend.app.services.url_safety import same_origin

        self.assertTrue(same_origin("https://example.com/a", "https://example.com:443/b"))
        self.assertFalse(same_origin("https://example.com", "http://example.com"))
        self.assertFalse(same_origin("https://example.com", "https://other.example.com"))


if __name__ == "__main__":
    unittest.main()
