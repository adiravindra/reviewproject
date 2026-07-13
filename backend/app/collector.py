"""Collect public reviews through an SSRF-resistant, size-bounded pipeline.

Every initial URL and redirect target is resolved and revalidated as public.
The collector prefers explicit JSON-LD review data, falls back only to known
review-card structures, then normalizes and deduplicates the bounded result.
"""

import ipaddress
import json
import re
import socket
from collections.abc import Callable, Iterable
from typing import Any, TypeAlias
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from backend.app.models import CollectionResult, Review, SourceInfo


Resolver: TypeAlias = Callable[..., list[tuple[Any, ...]]]

# A small manual-hop budget accommodates normal canonical redirects while
# bounding repeated DNS validation and network work on attacker-controlled URLs.
MAX_REDIRECTS = 3
# One MiB leaves room for static review markup but caps bandwidth and memory
# before the parser ever receives an untrusted response body.
MAX_RESPONSE_BYTES = 1024 * 1024
COLLECTION_MESSAGE = "The page could not be read. Try another public review page."
# An explicit product-scoped identity avoids impersonating a browser and gives
# public-site operators useful context for this narrowly scoped static fetcher.
USER_AGENT = "ReviewInsight/1.0 (+static public review analysis)"


class CollectionError(Exception):
    """Carry a stable collection code and message safe for public responses."""

    def __init__(self, code: str, public_message: str):
        """Store only the error information intentionally exposed by the API."""

        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


def collect_reviews(
    url: str,
    *,
    session: requests.Session | None = None,
    resolver: Resolver = socket.getaddrinfo,
) -> CollectionResult:
    """Fetch, extract, normalize, and validate reviews from one public page."""

    client = session or requests.Session()
    current_url = url
    try:
        # Redirects are handled manually so every hop is re-resolved before any
        # request, preventing a public URL from redirecting into a private host.
        for _ in range(MAX_REDIRECTS + 1):
            _validate_public_url(current_url, resolver)
            response = _fetch_once(client, current_url)
            if response.is_redirect or response.is_permanent_redirect:
                target = response.headers.get("Location")
                response.close()
                if not target:
                    raise CollectionError("collection_failed", COLLECTION_MESSAGE)
                current_url = urljoin(current_url, target)
                continue
            html = _read_html(response)
            break
        else:
            raise CollectionError("collection_failed", COLLECTION_MESSAGE)

        # Structured review semantics are stronger evidence than CSS naming, so
        # HTML cards are used only when JSON-LD yields no review candidates.
        title, candidates = _extract_json_ld(html)
        extractor = "json_ld"
        if not candidates:
            title, candidates = _extract_html_cards(html)
            extractor = "html_cards"
        reviews = _normalize(candidates, limit=40)
        if len(reviews) < 2:
            raise CollectionError("no_reviews", "At least two public reviews are required.")
        return CollectionResult(
            source=SourceInfo(
                url=current_url,
                title=title or urlparse(current_url).hostname or "Review page",
                extractor=extractor,
            ),
            reviews=reviews,
        )
    except CollectionError:
        raise
    except (requests.RequestException, ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise CollectionError("collection_failed", COLLECTION_MESSAGE) from None
    except Exception:
        raise CollectionError("collection_failed", COLLECTION_MESSAGE) from None


def _validate_public_url(url: str, resolver: Resolver) -> None:
    """Reject malformed, credential-bearing, or non-global destinations."""

    try:
        parsed = urlparse(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("unsupported URL")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = resolver(parsed.hostname, port, type=socket.SOCK_STREAM)
        if not addresses:
            raise ValueError("hostname did not resolve")
        for address in addresses:
            value = address[4][0]
            if ipaddress.ip_address(value).is_global is not True:
                raise ValueError("destination is not public")
    except (OSError, TypeError, ValueError):
        raise CollectionError("invalid_url", "Use a public http or https review-page URL.") from None


def _fetch_once(client: requests.Session, url: str):
    """Issue one streamed request without following redirects automatically."""

    try:
        response = client.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            timeout=(4, 10),
            allow_redirects=False,
            stream=True,
        )
    except requests.RequestException:
        raise CollectionError("collection_failed", COLLECTION_MESSAGE) from None
    if not isinstance(getattr(response, "status_code", None), int) or response.status_code >= 400:
        response.close()
        raise CollectionError("collection_failed", COLLECTION_MESSAGE)
    return response


def _read_html(response) -> str:
    """Read only HTML while enforcing the byte limit during streaming."""

    try:
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise CollectionError("collection_failed", COLLECTION_MESSAGE)
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise CollectionError("collection_failed", COLLECTION_MESSAGE)
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")
    except CollectionError:
        raise
    except Exception:
        raise CollectionError("collection_failed", COLLECTION_MESSAGE) from None
    finally:
        response.close()


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    """Yield every mapping nested in a JSON-compatible value."""

    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _extract_json_ld(html: str) -> tuple[str | None, list[dict[str, Any]]]:
    """Extract review bodies and product title from valid JSON-LD objects."""

    soup = BeautifulSoup(html, "html.parser")
    title = None
    candidates: list[dict[str, Any]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue
        try:
            document = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        objects = list(_walk_json(document))
        if title is None:
            for item in objects:
                item_type = item.get("@type")
                types = item_type if isinstance(item_type, list) else [item_type]
                if "Product" in types and _clean_text(item.get("name")):
                    title = _clean_text(item.get("name"))
                    break
        for item in objects:
            body = _clean_text(item.get("reviewBody"))
            if not body:
                continue
            rating = item.get("reviewRating")
            if isinstance(rating, dict):
                rating = rating.get("ratingValue")
            candidates.append(
                {"text": body, "rating": rating, "date": _clean_text(item.get("datePublished"))}
            )
    return title, candidates


def _extract_html_cards(html: str) -> tuple[str | None, list[dict[str, Any]]]:
    """Extract only recognized review containers as a conservative fallback."""

    soup = BeautifulSoup(html, "html.parser")
    page_title = _clean_text(soup.title.get_text()) if soup.title else None
    # Arbitrary paragraphs are intentionally excluded: ordinary page copy is
    # not reliable evidence that an author intended the text as a review.
    containers = soup.select('[itemprop="review"], .review, .review-card, [data-review-id]')
    candidates: list[dict[str, Any]] = []
    for container in containers:
        body = container.select_one(
            '[itemprop="reviewBody"], .review-body, .review-text, .review-content, [data-review-body]'
        )
        if body is None:
            continue
        rating_node = container.select_one('[itemprop="ratingValue"], .rating, [data-rating]')
        date_node = container.select_one('[itemprop="datePublished"], time, .review-date')
        rating = None
        if rating_node is not None:
            rating = (
                rating_node.get("content")
                or rating_node.get("data-rating")
                or rating_node.get("title")
                or rating_node.get_text(" ", strip=True)
            )
        date = None
        if date_node is not None:
            date = date_node.get("datetime") or date_node.get("content") or date_node.get_text(" ", strip=True)
        candidates.append({"text": body.get_text(" ", strip=True), "rating": rating, "date": date})
    return page_title, candidates


def _clean_text(value: Any) -> str | None:
    """Collapse whitespace and represent empty candidate text as absent."""

    if value is None:
        return None
    cleaned = " ".join(str(value).split())
    return cleaned or None


def _parse_rating(value: Any) -> int | None:
    """Accept only unambiguous integral ratings in the supported one-to-five range."""

    if value is None or isinstance(value, bool):
        return None
    match = re.search(r"(?<!\d)([1-5](?:\.0)?)(?!\d)", str(value))
    if not match:
        return None
    rating = float(match.group(1))
    return int(rating) if rating.is_integer() and 1 <= rating <= 5 else None


def _normalize(candidates: Iterable[dict[str, Any]], *, limit: int) -> list[Review]:
    """Clean, deduplicate, identify, and cap extracted review candidates."""

    reviews: list[Review] = []
    seen: set[str] = set()
    for candidate in candidates:
        text = _clean_text(candidate.get("text"))
        if text is None or len(text) < 10:
            continue
        # Case-insensitive exact text is stable enough for deterministic
        # deduplication without conflating merely similar customer experiences.
        fingerprint = text.casefold()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        reviews.append(
            Review(
                id=f"r{len(reviews) + 1}",
                text=text,
                rating=_parse_rating(candidate.get("rating")),
                date=_clean_text(candidate.get("date")),
            )
        )
        if len(reviews) == limit:
            break
    return reviews
