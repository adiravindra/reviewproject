"""Validate provider source URLs before spending quota."""

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit, urlunsplit

from backend.app.imports.contracts import ReviewImportError


_ASIN_PATH = re.compile(
    r"/(?:dp|gp/product|gp/aw/d|product-reviews)/([A-Z0-9]{10})(?:/|$)",
    re.IGNORECASE,
)
_GOOGLE_HOSTS = {"google.com", "www.google.com", "maps.google.com"}


@dataclass(frozen=True)
class ValidatedImportSource:
    """Expose the original URL plus a non-secret stable cache identity."""

    original_url: str
    normalized_url: str
    source_key: str


def extract_amazon_asin(source_url: str) -> str | None:
    """Extract an ASIN from one of the approved Amazon product path shapes."""

    try:
        path = urlsplit(source_url).path
    except (TypeError, ValueError):
        return None
    match = _ASIN_PATH.search(path)
    return match.group(1).upper() if match else None


def validate_import_source(platform: str, source_url: str) -> ValidatedImportSource:
    """Apply the selected platform's strict HTTPS URL allowlist."""

    if platform not in {"amazon", "google_maps"}:
        raise ReviewImportError("unsupported_import_platform")
    try:
        parsed = urlsplit(source_url)
        port = parsed.port
    except (TypeError, ValueError):
        raise ReviewImportError("invalid_import_url") from None
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise ReviewImportError("invalid_import_url")

    host = parsed.hostname.lower().rstrip(".")
    normalized = urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))
    if platform == "amazon":
        if host not in {"amazon.com", "www.amazon.com"}:
            raise ReviewImportError("invalid_import_url")
        asin = extract_amazon_asin(source_url)
        if asin is None:
            raise ReviewImportError("invalid_import_url")
        return ValidatedImportSource(source_url, normalized, asin)

    if host == "maps.app.goo.gl":
        if parsed.path in {"", "/"}:
            raise ReviewImportError("invalid_import_url")
    elif host in _GOOGLE_HOSTS:
        path = parsed.path.rstrip("/")
        has_place_path = path.startswith("/maps/place/") or path.startswith("/maps/reviews/")
        has_cid = (
            path in {"", "/maps"}
            and bool(parse_qs(parsed.query).get("cid"))
            and host in {"google.com", "www.google.com", "maps.google.com"}
        )
        if not (has_place_path or has_cid):
            raise ReviewImportError("invalid_import_url")
    else:
        raise ReviewImportError("invalid_import_url")
    return ValidatedImportSource(
        source_url,
        normalized,
        hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    )
