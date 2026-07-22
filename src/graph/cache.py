"""Query cache layer for analyst agent data sources.

Read-through cache keyed by source + normalized expression + bounded rows.
Persisted to disk cache with optional TTL/Max-Age semantics when a result
includes ``Cache-Control`` metadata from the provider.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


def _safe_ttl_since(created_epoch: float, max_age_seconds: float | None) -> bool:
    if not max_age_seconds or max_age_seconds <= 0:
        return True
    return (time.time() - created_epoch) < max_age_seconds


def _normalize(expression: str) -> str:
    return " ".join((expression or "").split()).lower().strip()


def _now() -> float:
    return time.time()


class QueryCache:
    def __init__(self, cache_dir: str | Path | None = None, ttl_seconds: float | None = 3600) -> None:
        self.cache_dir = Path(cache_dir or Path(os.environ.get("AGENT_QUERY_CACHE_DIR", "data/query-cache")))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def _key(self, source: str, expression: str) -> str:
        payload = json.dumps({"source": source, "expression": _normalize(expression)}, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _shard_path(self, key: str) -> Path:
        return self.cache_dir / key[:2] / f"{key}.json"

    def get(self, source: str, expression: str) -> tuple[list[dict[str, object]] | None, dict[str, Any] | None]:
        path = self._shard_path(self._key(source, expression))
        if not path.exists():
            return None, None
        try:
            payload = json.loads(path.read_text("utf-8"))
            meta = payload.get("meta") or {}
            max_age = meta.get("max_age", self.ttl_seconds)
            if meta.get("created_epoch") and not _safe_ttl_since(float(meta["created_epoch"]), float(max_age)):
                return None, None
            return payload.get("rows"), meta
        except Exception:
            return None, None

    def put(
        self,
        source: str,
        expression: str,
        rows: list[dict[str, object]],
        *,
        meta: dict[str, Any] | None = None,
        max_age: float | int | None = None,
    ) -> None:
        key = self._key(source, expression)
        payload = {
            "rows": rows,
            "meta": {
                "created_epoch": _now(),
                "max_age": max_age if max_age is not None else self.ttl_seconds,
                "row_count": len(rows or []),
                "source": source,
                "expression": _normalize(expression),
                **(meta or {}),
            },
        }
        path = self._shard_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)

    def delete(self, source: str, expression: str) -> None:
        path = self._shard_path(self._key(source, expression))
        if path.exists():
            path.unlink()
