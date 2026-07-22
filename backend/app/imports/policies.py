"""Validate provider source URLs before spending quota."""

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit, urlunsplit

from backend.app.imports.contracts import ReviewImportError


_ASIN_PATH = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE)
_GOOGLE_HOSTS = {"google.com", "www.google.com", "maps.google.com"}


@dataclass(frozen=True)
class ValidatedImportSource:
    """Expose the original URL plus a non-secret stable cache identity."""

    original_url: str
    normalized_url: str
    source_key: str


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
        match = _ASIN_PATH.search(parsed.path)
        if match is None:
            raise ReviewImportError("invalid_import_url")
        return ValidatedImportSource(source_url, normalized, match.group(1).upper())

    if host == "maps.app.goo.gl":
        if parsed.path in {"", "/"}:
            raise ReviewImportError("invalid_import_url")
    elif host in _GOOGLE_HOSTS:
        path = parsed.path.rstrip("/")
        has_place_path = path.startswith("/maps/place/") or path.startswith("/maps/reviews/")
        has_cid = path == "/maps" and bool(parse_qs(parsed.query).get("cid"))
        if not (has_place_path or has_cid):
            raise ReviewImportError("invalid_import_url")
    else:
        raise ReviewImportError("invalid_import_url")
    return ValidatedImportSource(
        source_url,
        normalized,
        hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    )
