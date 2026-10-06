"""TTL-aware JSON cache on disk.

Adapted from bist-quant (github.com/Safa675/bist-quant @ 8473426,
src/bist_quant/common/disk_cache.py, Apache-2.0), with these changes:
- JSON values only; the pandas/Parquet half is dropped until the project
  actually depends on pandas;
- reads return the value together with when it was cached, so a cached
  response is never presented as freshly retrieved;
- NaN, Infinity and values that are not plain JSON are rejected, instead of
  being written as non-standard JSON or silently turned into strings;
- category and key names are validated, so a key cannot write outside the
  cache directory;
- each entry is one file written atomically (temporary file, then rename),
  replacing the separate data and metadata files;
- TTLs come from the constructor instead of environment variables.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)

_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SUFFIX = ".json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CachedValue:
    value: Any
    cached_at: datetime
    expires_at: datetime
    source: str


class DiskCache:
    """One JSON file per entry under `cache_dir/<category>/<key>.json`."""

    def __init__(
        self,
        cache_dir: Path | str,
        *,
        default_ttl_seconds: int,
        ttl_by_category: Mapping[str, int] | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._cache_dir = Path(cache_dir)
        self._default_ttl = _checked_ttl(default_ttl_seconds)
        self._ttl_by_category = {
            _checked_name(category, "category"): _checked_ttl(ttl)
            for category, ttl in (ttl_by_category or {}).items()
        }
        self._clock = clock
        self._lock = Lock()
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get_json(self, category: str, key: str) -> CachedValue | None:
        """Return the cached value with its timestamps, or None if missing or expired."""
        path = self._path(category, key)
        if not path.is_file():
            return None
        entry = self._read(path)
        if entry is None or self._now() >= entry.expires_at:
            return None
        return entry

    def set_json(
        self,
        category: str,
        key: str,
        value: Any,
        *,
        source: str,
        ttl_seconds: int | None = None,
    ) -> CachedValue:
        """Store a JSON-serializable value. Raises ValueError/TypeError before touching disk."""
        if not isinstance(source, str) or not source:
            raise ValueError("source must be a non-empty string")
        path = self._path(category, key)
        ttl = _checked_ttl(ttl_seconds) if ttl_seconds is not None else self._ttl_for(category)
        now = self._now()
        expires_at = now + timedelta(seconds=ttl)
        payload = json.dumps(
            {
                "cached_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "ttl_seconds": ttl,
                "source": source,
                "value": value,
            },
            ensure_ascii=False,
            allow_nan=False,
        )
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(path, payload)
        # Return the value as it will read back (for example, tuples become lists).
        return CachedValue(value=json.loads(payload)["value"], cached_at=now, expires_at=expires_at, source=source)

    def is_valid(self, category: str, key: str) -> bool:
        return self.get_json(category, key) is not None

    def clear(self, category: str | None = None) -> int:
        """Remove cached entries; returns the number of files removed."""
        targets = (
            [self._cache_dir / _checked_name(category, "category")]
            if category is not None
            else [child for child in self._cache_dir.iterdir() if child.is_dir()]
        )
        removed = 0
        with self._lock:
            for target in targets:
                if target.is_dir():
                    removed += sum(1 for item in target.rglob("*") if item.is_file())
                    shutil.rmtree(target)
        return removed

    def clear_expired(self) -> int:
        """Remove expired entries; returns the number removed."""
        removed = 0
        now = self._now()
        with self._lock:
            for path in self._entry_files():
                entry = self._read(path)
                if entry is not None and now >= entry.expires_at:
                    path.unlink(missing_ok=True)
                    removed += 1
        return removed

    def inspect(self) -> dict[str, list[dict[str, Any]]]:
        """Summarize entries by category, without their values."""
        now = self._now()
        result: dict[str, list[dict[str, Any]]] = {}
        for path in self._entry_files():
            entry = self._read(path)
            if entry is None:
                continue
            result.setdefault(path.parent.name, []).append({
                "key": path.name.removesuffix(_SUFFIX),
                "cached_at": entry.cached_at.isoformat(),
                "expires_at": entry.expires_at.isoformat(),
                "source": entry.source,
                "expired": now >= entry.expires_at,
            })
        return result

    def _path(self, category: str, key: str) -> Path:
        return self._cache_dir / _checked_name(category, "category") / f"{_checked_name(key, 'key')}{_SUFFIX}"

    def _ttl_for(self, category: str) -> int:
        return self._ttl_by_category.get(category, self._default_ttl)

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return now

    def _entry_files(self) -> list[Path]:
        return sorted(
            path for path in self._cache_dir.glob(f"*/*{_SUFFIX}")
            if _NAME.fullmatch(path.parent.name) and _NAME.fullmatch(path.name.removesuffix(_SUFFIX))
        )

    def _read(self, path: Path) -> CachedValue | None:
        """Parse an entry; a corrupt entry is removed and reported as missing."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entry = CachedValue(
                value=raw["value"],
                cached_at=_aware(datetime.fromisoformat(raw["cached_at"])),
                expires_at=_aware(datetime.fromisoformat(raw["expires_at"])),
                source=str(raw["source"]),
            )
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Removing unreadable cache entry %s (%s)", path.name, type(exc).__name__)
            path.unlink(missing_ok=True)
            return None
        return entry


def _checked_name(name: str, kind: str) -> str:
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ValueError(f"invalid cache {kind} {name!r}: use letters, digits, '.', '_' or '-', "
                         "starting with a letter or digit")
    return name


def _checked_ttl(ttl: int) -> int:
    if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl <= 0:
        raise ValueError("TTL must be a positive whole number of seconds")
    return ttl


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("cache timestamp has no offset")
    return value


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
