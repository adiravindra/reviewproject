import re
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests

from backend.app.errors import AppError
from backend.app.services.url_safety import Resolver, validate_public_url
from backend.app.settings import Settings


_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_BLOCKED_STATUSES = {401, 403, 407, 429}
_CHALLENGE_MARKERS = (
    "cf-chl-",
    "captcha",
    "verify you are human",
    "attention required",
    "access denied",
    "checking your browser",
)
_CHARSET = re.compile(r"charset=([^;\s]+)", re.IGNORECASE)


@dataclass(frozen=True)
class FetchedPage:
    requested_url: str
    final_url: str
    html: str
    status_code: int
    content_type: str


class StaticHttpFetcher:
    def __init__(
        self,
        settings: Settings,
        *,
        session: Any | None = None,
        resolver: Resolver = socket.getaddrinfo,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.resolver = resolver
        self.clock = clock

    def fetch(self, url: str, deadline: float | None = None) -> FetchedPage:
        requested_url = url.strip()
        deadline = deadline or (self.clock() + self.settings.scrape_deadline_seconds)
        current_url = validate_public_url(requested_url, resolver=self.resolver).url
        redirects_followed = 0

        while True:
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise _scrape_error(
                    "The website took too long to respond.",
                    requested_url,
                    retryable=True,
                )
            try:
                response = self.session.get(
                    current_url,
                    headers={
                        "User-Agent": self.settings.user_agent,
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    timeout=(
                        max(0.001, min(self.settings.connect_timeout_seconds, remaining)),
                        max(0.001, min(self.settings.read_timeout_seconds, remaining)),
                    ),
                    allow_redirects=False,
                    stream=True,
                )
            except requests.RequestException:
                raise _scrape_error(
                    "The website could not be reached.",
                    requested_url,
                    retryable=True,
                ) from None

            try:
                status_code = int(response.status_code)
                if status_code in _REDIRECT_STATUSES:
                    location = _header(response.headers, "location")
                    if not location:
                        raise _scrape_error("The website returned an invalid redirect.", requested_url)
                    if redirects_followed >= self.settings.max_redirects:
                        raise _scrape_error("The website redirected too many times.", requested_url)
                    target = urljoin(current_url, location)
                    current_url = validate_public_url(target, resolver=self.resolver).url
                    redirects_followed += 1
                    continue

                if status_code in _BLOCKED_STATUSES:
                    raise _blocked_error(requested_url)
                if status_code >= 500:
                    raise _scrape_error(
                        "The website returned a server error.",
                        requested_url,
                        retryable=True,
                    )
                if status_code < 200 or status_code >= 300:
                    raise _scrape_error("The website returned an unsupported response.", requested_url)

                content_type = _header(response.headers, "content-type") or ""
                media_type = content_type.split(";", 1)[0].strip().casefold()
                if media_type not in {"text/html", "application/xhtml+xml"}:
                    raise _scrape_error("The URL did not return a static HTML page.", requested_url)
                content_length = _header(response.headers, "content-length")
                if content_length:
                    try:
                        if int(content_length) > self.settings.max_response_bytes:
                            raise _scrape_error("The website response was too large.", requested_url)
                    except ValueError:
                        raise _scrape_error("The website returned invalid response metadata.", requested_url) from None

                body = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    body.extend(chunk)
                    if len(body) > self.settings.max_response_bytes:
                        raise _scrape_error("The website response was too large.", requested_url)
                    if self.clock() >= deadline:
                        raise _scrape_error(
                            "The website took too long to respond.",
                            requested_url,
                            retryable=True,
                        )

                encoding = _response_encoding(content_type, getattr(response, "encoding", None))
                html = bytes(body).decode(encoding, errors="replace")
                if any(marker in html.casefold() for marker in _CHALLENGE_MARKERS):
                    raise _blocked_error(requested_url)
                return FetchedPage(
                    requested_url=requested_url,
                    final_url=current_url,
                    html=html,
                    status_code=status_code,
                    content_type=content_type,
                )
            finally:
                response.close()


def _header(headers: Any, name: str) -> str | None:
    for key, value in headers.items():
        if str(key).casefold() == name.casefold():
            return str(value)
    return None


def _response_encoding(content_type: str, response_encoding: str | None) -> str:
    match = _CHARSET.search(content_type)
    if match:
        return match.group(1).strip("\"'")
    return response_encoding or "utf-8"


def _blocked_error(url: str) -> AppError:
    return AppError(
        code="blocked_source",
        message="The website blocked automated access.",
        stage="scraping",
        status_code=403,
        details={"url": url},
    )


def _scrape_error(message: str, url: str, *, retryable: bool = False) -> AppError:
    return AppError(
        code="scrape_failed",
        message=message,
        stage="scraping",
        status_code=502,
        retryable=retryable,
        details={"url": url},
    )
