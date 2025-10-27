"""Permission cache powered by Upstash Redis with in-memory fallback."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict, Optional, Protocol, Sequence, Set, Tuple, cast

import httpx

from app.core.config import get_settings

PermissionCacheKey = Tuple[str, str, str, str]


class PermissionCache(Protocol):
    """Contract for caching authorization decisions."""

    def get(self, key: PermissionCacheKey) -> Optional[bool]:
        ...

    def set(self, key: PermissionCacheKey, value: bool, *, principal_id: str) -> None:
        ...

    def invalidate(self) -> None:
        ...

    def invalidate_for_principal(self, principal_id: str) -> None:
        ...


@dataclass
class InMemoryPermissionCache(PermissionCache):
    """Thread-safe in-memory cache with principal-level invalidation."""

    def __post_init__(self) -> None:
        self._store: Dict[PermissionCacheKey, bool] = {}
        self._principal_index: Dict[str, Set[PermissionCacheKey]] = {}
        self._lock = RLock()

    def get(self, key: PermissionCacheKey) -> Optional[bool]:
        with self._lock:
            return self._store.get(key)

    def set(self, key: PermissionCacheKey, value: bool, *, principal_id: str) -> None:
        with self._lock:
            self._store[key] = value
            if principal_id not in self._principal_index:
                self._principal_index[principal_id] = set()
            self._principal_index[principal_id].add(key)

    def invalidate(self) -> None:
        with self._lock:
            self._store.clear()
            self._principal_index.clear()

    def invalidate_for_principal(self, principal_id: str) -> None:
        with self._lock:
            keys = self._principal_index.pop(principal_id, set())
            for key in keys:
                self._store.pop(key, None)


class RedisPermissionCache(PermissionCache):
    """Redis-backed cache using Upstash REST API."""

    def __init__(self, *, url: str, token: str, prefix: str, ttl_seconds: int) -> None:
        self._client = httpx.Client(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        self._ttl_ms = max(ttl_seconds, 1) * 1000
        self._prefix = prefix
        self._registry_key = f"{self._prefix}:principals"

    def get(self, key: PermissionCacheKey) -> Optional[bool]:
        result = self._execute("GET", self._perm_key(key))
        if result is None:
            return None
        return str(result) == "1"

    def set(self, key: PermissionCacheKey, value: bool, *, principal_id: str) -> None:
        cache_key = self._perm_key(key)
        value_str = "1" if value else "0"
        self._execute("SET", cache_key, value_str, "PX", str(self._ttl_ms))

        index_key = self._principal_index_key(principal_id)
        ttl_seconds = str(max(self._ttl_ms // 1000, 1))
        self._execute("SADD", index_key, cache_key)
        self._execute("EXPIRE", index_key, ttl_seconds)
        self._execute("SADD", self._registry_key, principal_id)
        self._execute("EXPIRE", self._registry_key, ttl_seconds)

    def invalidate(self) -> None:
        principals = cast(Sequence[str], self._execute("SMEMBERS", self._registry_key) or [])
        for principal in principals:
            self.invalidate_for_principal(principal)
        if principals:
            self._execute("DEL", self._registry_key)

    def invalidate_for_principal(self, principal_id: str) -> None:
        index_key = self._principal_index_key(principal_id)
        keys = list(cast(Sequence[str], self._execute("SMEMBERS", index_key) or []))
        if keys:
            self._execute("DEL", index_key, *keys)
        else:
            self._execute("DEL", index_key)
        self._execute("SREM", self._registry_key, principal_id)

    def _perm_key(self, key: PermissionCacheKey) -> str:
        principal_id, principal_type, resource_id, action = key
        return f"{self._prefix}:perm:{principal_id}:{principal_type}:{resource_id}:{action}"

    def _principal_index_key(self, principal_id: str) -> str:
        return f"{self._prefix}:principal:{principal_id}"

    def _execute(self, *command: str) -> Optional[object]:
        response = self._client.post("/", json=list(command))
        response.raise_for_status()
        payload = response.json()
        return payload.get("result")


_shared_cache: Optional[PermissionCache] = None


def get_permission_cache() -> PermissionCache:
    """Return the process-wide permission cache instance."""

    global _shared_cache
    if _shared_cache is not None:
        return _shared_cache

    settings = get_settings()
    redis_url = settings.redis_url
    redis_token = settings.redis_token

    if redis_url and redis_token:
        _shared_cache = RedisPermissionCache(
            url=redis_url,
            token=redis_token,
            prefix=settings.redis_cache_prefix,
            ttl_seconds=settings.redis_cache_ttl,
        )
    else:
        _shared_cache = InMemoryPermissionCache()

    return _shared_cache
