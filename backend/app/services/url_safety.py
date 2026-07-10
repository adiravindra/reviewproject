import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import SplitResult, urlsplit

from backend.app.errors import AppError


Resolver = Callable[..., list[tuple[Any, ...]]]


@dataclass(frozen=True)
class ValidatedURL:
    url: str
    scheme: str
    hostname: str
    port: int
    addresses: tuple[str, ...]


def validate_public_url(
    value: str,
    *,
    resolver: Resolver = socket.getaddrinfo,
) -> ValidatedURL:
    url = str(value).strip()
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise _invalid_url() from None

    scheme = parsed.scheme.casefold()
    hostname = (parsed.hostname or "").casefold().rstrip(".")
    if (
        scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise _invalid_url()

    effective_port = port if port is not None else (443 if scheme == "https" else 80)
    if not 1 <= effective_port <= 65535:
        raise _invalid_url()

    literal = _literal_ip(hostname)
    if literal is not None:
        addresses = (literal,)
    else:
        try:
            answers = resolver(hostname, effective_port, type=socket.SOCK_STREAM)
        except (OSError, KeyError):
            raise AppError(
                code="scrape_failed",
                message="The website address could not be resolved.",
                stage="scraping",
                status_code=502,
                retryable=True,
                details={"url": url},
            ) from None
        addresses = tuple(dict.fromkeys(_answer_address(answer) for answer in answers))

    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise _invalid_url(url)
    return ValidatedURL(
        url=url,
        scheme=scheme,
        hostname=hostname,
        port=effective_port,
        addresses=addresses,
    )


def origin(url: str) -> tuple[str, str, int]:
    try:
        parsed: SplitResult = urlsplit(url.strip())
        scheme = parsed.scheme.casefold()
        hostname = (parsed.hostname or "").casefold().rstrip(".")
        port = parsed.port if parsed.port is not None else (443 if scheme == "https" else 80)
    except ValueError:
        raise _invalid_url() from None
    if scheme not in {"http", "https"} or not hostname:
        raise _invalid_url()
    return scheme, hostname, port


def same_origin(first: str, second: str) -> bool:
    try:
        return origin(first) == origin(second)
    except AppError:
        return False


def _answer_address(answer: tuple[Any, ...]) -> str:
    socket_address = answer[4]
    return str(socket_address[0])


def _literal_ip(hostname: str) -> str | None:
    candidate = hostname.strip("[]")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _is_public_address(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def _invalid_url(url: str | None = None) -> AppError:
    return AppError(
        code="invalid_url",
        message="Only public HTTP and HTTPS website URLs are supported.",
        stage="validation",
        status_code=422,
        details={"url": url} if url else {},
    )
