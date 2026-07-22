"""Persist short-lived normalized provider imports in isolated local SQLite."""

import hashlib
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from backend.app.imports.contracts import ReviewImportError
from backend.app.models import CollectionResult


DEFAULT_IMPORT_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "review_import_cache.db"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS review_import_cache (
    cache_key TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    provider TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    requested_limit INTEGER NOT NULL,
    ordering TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    collection_json TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class CacheIdentity:
    """Define every dimension that may change imported evidence."""

    platform: str
    provider: str
    contract_version: str
    source_key: str
    requested_limit: int
    ordering: str

    @property
    def source_hash(self) -> str:
        """Hash the provider-neutral source identity before persistence."""

        return hashlib.sha256(self.source_key.encode("utf-8")).hexdigest()

    @property
    def digest(self) -> str:
        """Hash every evidence-changing cache dimension into one key."""

        value = "\0".join(
            (
                self.platform,
                self.provider,
                self.contract_version,
                self.source_hash,
                str(self.requested_limit),
                self.ordering,
            )
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ImportCacheStore:
    """Store validated normalized collections without provider raw data."""

    def __init__(self, db_path: Path = DEFAULT_IMPORT_CACHE_PATH):
        """Remember the cache path without touching the filesystem."""

        self.db_path = Path(db_path)

    def get(self, identity: CacheIdentity, now: datetime) -> CollectionResult | None:
        """Return one live validated entry or remove expired/corrupt data."""

        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT expires_at, collection_json FROM review_import_cache WHERE cache_key = ?",
                    (identity.digest,),
                ).fetchone()
                if row is None:
                    return None
                try:
                    expires_at = datetime.fromisoformat(row[0])
                    collection = CollectionResult.model_validate_json(row[1])
                except (TypeError, ValueError, ValidationError):
                    connection.execute(
                        "DELETE FROM review_import_cache WHERE cache_key = ?", (identity.digest,)
                    )
                    return None
                if expires_at <= now:
                    connection.execute(
                        "DELETE FROM review_import_cache WHERE cache_key = ?", (identity.digest,)
                    )
                    return None
                return collection
        except ReviewImportError:
            raise
        except (OSError, sqlite3.Error, TypeError, ValueError):
            raise ReviewImportError("cache_failed") from None

    def put(
        self,
        identity: CacheIdentity,
        collection: CollectionResult,
        fetched_at: datetime,
        expires_at: datetime,
    ) -> None:
        """Atomically insert or replace one normalized cache entry."""

        try:
            payload = collection.model_dump_json()
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO review_import_cache (
                        cache_key, platform, provider, contract_version, source_hash,
                        requested_limit, ordering, fetched_at, expires_at, collection_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        fetched_at = excluded.fetched_at,
                        expires_at = excluded.expires_at,
                        collection_json = excluded.collection_json
                    """,
                    (
                        identity.digest,
                        identity.platform,
                        identity.provider,
                        identity.contract_version,
                        identity.source_hash,
                        identity.requested_limit,
                        identity.ordering,
                        fetched_at.isoformat(),
                        expires_at.isoformat(),
                        payload,
                    ),
                )
        except (OSError, sqlite3.Error, TypeError, ValueError, ValidationError):
            raise ReviewImportError("cache_failed") from None

    @contextmanager
    def _connection(self):
        """Yield one initialized transaction and always close its connection."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        try:
            with connection:
                connection.execute(_SCHEMA)
                yield connection
        finally:
            connection.close()
