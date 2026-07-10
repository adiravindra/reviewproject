from collections.abc import Iterable
from typing import Any


def resolver_for(mapping: dict[str, str | list[str]]):
    def resolve(host: str, port: int, *args: Any, **kwargs: Any) -> list[tuple[Any, ...]]:
        value = mapping[host]
        addresses = value if isinstance(value, list) else [value]
        return [(2, 1, 6, "", (address, port)) for address in addresses]

    return resolve


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        *,
        body: bytes = b"<html><title>Reviews</title></html>",
        headers: dict[str, str] | None = None,
        url: str = "https://public.example/reviews",
        chunks: Iterable[bytes] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}
        self.url = url
        self.encoding = "utf-8"
        self._body = body
        self._chunks = list(chunks) if chunks is not None else [body]
        self.closed = False

    def iter_content(self, chunk_size: int = 65536) -> Iterable[bytes]:
        del chunk_size
        return iter(self._chunks)

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        response.url = url
        return response
