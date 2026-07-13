"""Test public-network validation and conservative review extraction."""

import socket
import unittest
from pathlib import Path

from backend.app.collector import CollectionError, collect_reviews


FIXTURE = Path(__file__).parent / "fixtures" / "review_page.html"


def public_resolver(host, port, *args, **kwargs):
    """Simulate DNS resolution to a globally routable address."""

    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 443))]


def private_resolver(host, port, *args, **kwargs):
    """Simulate DNS resolution to a loopback address blocked by collection."""

    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port or 80))]


class FakeResponse:
    """Simulate the streamed subset of a requests response used by collection."""

    def __init__(self, text, *, status_code=200, headers=None, url="https://example.com/reviews"):
        """Configure encoded content, status, headers, and redirect flags."""

        self._content = text.encode("utf-8")
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}
        self.url = url
        self.is_redirect = status_code in {301, 302, 303, 307, 308}
        self.is_permanent_redirect = status_code in {301, 308}
        self.closed = False

    def iter_content(self, chunk_size=65536):
        """Yield response bytes in caller-selected chunks for size enforcement."""

        for start in range(0, len(self._content), chunk_size):
            yield self._content[start : start + chunk_size]

    def close(self):
        """Record that the collector released the response resource."""

        self.closed = True


class TextSession:
    """Simulate a requests session while recording fetch policy arguments."""

    def __init__(self, text, *, responses=None):
        """Configure fallback text and any ordered explicit responses."""

        self.text = text
        self.responses = list(responses or [])
        self.calls = 0
        self.kwargs = []

    def get(self, url, **kwargs):
        """Record one request and return the next configured fake response."""

        self.calls += 1
        self.kwargs.append(kwargs)
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse(self.text, url=url)


class FixtureSession(TextSession):
    """Load an HTML fixture into the recording text-session boundary."""

    def __init__(self, path):
        """Read fixture text using the same UTF-8 assumption as the tests."""

        super().__init__(Path(path).read_text(encoding="utf-8"))


def cards(texts):
    """Build minimal recognized review-card markup for fallback tests."""

    return "<html><head><title>Customer reviews</title></head><body>" + "".join(
        f'<article class="review-card" data-review-id="{index}">'
        f'<p class="review-body">{text}</p><span itemprop="ratingValue">5</span></article>'
        for index, text in enumerate(texts, start=1)
    ) + "</body></html>"


class CollectorTests(unittest.TestCase):
    """Group collector extraction, normalization, and network-safety contracts."""

    def test_extracts_json_ld_reviews_and_source_metadata(self):
        """Prefer JSON-LD and preserve source metadata under streamed fetching."""

        session = FixtureSession(FIXTURE)
        result = collect_reviews(
            "https://example.com/product",
            session=session,
            resolver=public_resolver,
        )
        self.assertEqual(result.source.title, "Everyday Headphones")
        self.assertEqual(result.source.extractor, "json_ld")
        self.assertEqual(len(result.reviews), 5)
        self.assertEqual(result.reviews[0].id, "r1")
        self.assertEqual(result.reviews[0].rating, 5)
        self.assertEqual(session.kwargs[0]["timeout"], (4, 10))
        self.assertFalse(session.kwargs[0]["allow_redirects"])
        self.assertTrue(session.kwargs[0]["stream"])

    def test_static_cards_are_a_conservative_fallback(self):
        """Use recognized review cards only when structured data is unavailable."""

        html = cards(["Clear sound and a comfortable fit.", "Useful controls and dependable battery life."])
        result = collect_reviews(
            "https://example.com/reviews",
            session=TextSession(html),
            resolver=public_resolver,
        )
        self.assertEqual(result.source.extractor, "html_cards")
        self.assertEqual(result.source.title, "Customer reviews")
        self.assertEqual(len(result.reviews), 2)

    def test_fallback_does_not_promote_arbitrary_paragraphs(self):
        """Reject ordinary page prose as insufficient review evidence."""

        session = TextSession("<html><body><p>This is long ordinary product prose, not a review.</p></body></html>")
        with self.assertRaises(CollectionError) as raised:
            collect_reviews("https://example.com/product", session=session, resolver=public_resolver)
        self.assertEqual(raised.exception.code, "no_reviews")

    def test_rejects_private_urls_before_requesting(self):
        """Block private destinations before opening an HTTP connection."""

        session = TextSession("")
        with self.assertRaises(CollectionError) as raised:
            collect_reviews(
                "http://internal.example/reviews",
                session=session,
                resolver=private_resolver,
            )
        self.assertEqual(raised.exception.code, "invalid_url")
        self.assertEqual(session.calls, 0)

    def test_rejects_credentials_before_requesting(self):
        """Block credential-bearing URLs before opening an HTTP connection."""

        session = TextSession("")
        with self.assertRaises(CollectionError) as raised:
            collect_reviews(
                "https://user:secret@example.com/reviews",
                session=session,
                resolver=public_resolver,
            )
        self.assertEqual(raised.exception.code, "invalid_url")
        self.assertEqual(session.calls, 0)

    def test_deduplicates_caps_and_requires_two_reviews(self):
        """Require two unique reviews and cap normalized output deterministically."""

        duplicated = cards(["Same useful review", "same useful review"])
        with self.assertRaises(CollectionError) as raised:
            collect_reviews(
                "https://example.com/reviews",
                session=TextSession(duplicated),
                resolver=public_resolver,
            )
        self.assertEqual(raised.exception.code, "no_reviews")

        unique = cards([f"Useful review number {index:02d}" for index in range(45)])
        result = collect_reviews(
            "https://example.com/reviews",
            session=TextSession(unique),
            resolver=public_resolver,
        )
        self.assertEqual(len(result.reviews), 40)
        self.assertEqual(result.reviews[-1].id, "r40")

    def test_revalidates_redirect_targets(self):
        """Resolve and reject a redirect target before following it."""

        redirect = FakeResponse("", status_code=302, headers={"Location": "http://internal.example/reviews"})
        session = TextSession("", responses=[redirect])

        def resolver(host, port, *args, **kwargs):
            """Resolve the initial host publicly and redirected host privately."""

            return private_resolver(host, port, *args, **kwargs) if host == "internal.example" else public_resolver(host, port, *args, **kwargs)

        with self.assertRaises(CollectionError) as raised:
            collect_reviews("https://example.com/reviews", session=session, resolver=resolver)
        self.assertEqual(raised.exception.code, "invalid_url")
        self.assertEqual(session.calls, 1)

    def test_rejects_non_html_and_oversized_responses_safely(self):
        """Reject unsupported content and streamed bodies beyond the byte cap."""

        non_html = FakeResponse("{}", headers={"content-type": "application/json"})
        with self.assertRaises(CollectionError) as raised:
            collect_reviews(
                "https://example.com/reviews",
                session=TextSession("", responses=[non_html]),
                resolver=public_resolver,
            )
        self.assertEqual(raised.exception.code, "collection_failed")

        oversized = FakeResponse("x" * (1024 * 1024 + 1))
        with self.assertRaises(CollectionError) as raised:
            collect_reviews(
                "https://example.com/reviews",
                session=TextSession("", responses=[oversized]),
                resolver=public_resolver,
            )
        self.assertEqual(raised.exception.code, "collection_failed")


if __name__ == "__main__":
    unittest.main()
