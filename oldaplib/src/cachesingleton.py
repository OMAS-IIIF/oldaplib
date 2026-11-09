import json
import os
from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from typing import Any

import redis

from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.helpers.singletonmeta import SingletonMeta
from oldaplib.src.iconnection import IConnection
from oldaplib.src.mutation_gate import require_separate_cache
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


_redis_clients: OrderedDict[str, redis.Redis] = OrderedDict()
_redis_clients_lock = Lock()


def _reset_redis_clients_after_fork() -> None:
    """Discard inherited clients and locks before the child serves requests."""
    global _redis_clients, _redis_clients_lock
    _redis_clients = OrderedDict()
    _redis_clients_lock = Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_redis_clients_after_fork)


def _shared_redis_client(url: str) -> redis.Redis:
    """Reuse a thread-safe pool per exact cache URL in this process.

    Retain at most eight configurations; each pool permits 32 connections.
    Evicted clients are not closed while wrappers may still be using them.
    Redis owns pool cleanup when the last reference disappears. Neither data
    objects nor authorization contexts are retained in this process cache.
    """
    with _redis_clients_lock:
        client = _redis_clients.get(url)
        if client is None:
            client = redis.from_url(url, max_connections=32)
            _redis_clients[url] = client
            if len(_redis_clients) > 8:
                _redis_clients.popitem(last=False)
        _redis_clients.move_to_end(url)
        return client


class CacheSingleton(metaclass=SingletonMeta):
    """
    Singleton class for thread-safe caching.

    This class provides a mechanism for thread-safe access and modification
    of a cache. It ensures single-instance usage via the SingletonMeta
    metaclass. The cache allows storing, retrieving, deleting, and clearing
    key-value pairs in a thread-safe manner.

    :ivar _lock: Lock object ensuring thread-safe access to the cache.
    :type _lock: Lock
    :ivar _cache: Internal dictionary used for storing the cache data.
    :type _cache: dict[Iri | Xsd_NCName, Any]
    """
    _lock: Lock
    _cache: dict[Iri | Xsd_NCName, Any]

    def __init__(self):
        self._lock = Lock()
        self._cache = {}

    def __str__(self) -> str:
        with self._lock:
            return str(self._cache)

    def get(self, key: Iri | Xsd_NCName) -> Any:
        with self._lock:
            return deepcopy(self._cache.get(key))

    def set(self, key: Iri | Xsd_NCName, value: Any, key2: Iri | Xsd_NCName | None = None) -> None:
        with self._lock:
            self._cache[key] = deepcopy(value)
            if key2 is not None:
                self._cache[key2] = self._cache[key]

    def delete(self, key: Iri | Xsd_NCName):
        with self._lock:
            if key in self._cache:
                self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()


class CacheSingletonRedis:
    """
    JSON cache wrapper using a process-local, thread-safe Redis connection pool.

    This class interacts with a Redis instance to store, retrieve, and manage
    cached data. Designed to facilitate data caching using key-value pairs,
    supporting serialization and deserialization for complex objects. Provides
    methods for synchronous operations like setting, retrieving, deleting, and
    clearing cache entries.

    :ivar _r: Connection to the Redis database.
    :type _r: redis.client.Redis
    """
    def __init__(self):
        redis_url = os.getenv("OLDAP_REDIS_URL", "redis://localhost:6379")
        self._r = _shared_redis_client(redis_url)
        require_separate_cache(self._r)

    def get(self, key: Iri | Xsd_NCName | Xsd_QName, connection: IConnection | None = None) -> Any:
        value = self._r.get(str(key))
        if connection:
            return json.loads(value, object_hook=serializer.make_decoder_hook(connection=connection)) if value else None
        else:
            return json.loads(value, object_hook=serializer.decoder_hook) if value else None

    def set(self, key: Iri | Xsd_NCName | Xsd_QName, value: Any, key2: Iri | Xsd_NCName | None = None) -> None:
        self._r.set(str(key), json.dumps(value, default=serializer.encoder_default))
        if key2 is not None:
            self._r.set(str(key2), json.dumps(value, default=serializer.encoder_default))

    def delete(self, key: Iri | Xsd_NCName | Xsd_QName):
        self._r.delete(str(key))

    def clear(self):
        require_separate_cache(self._r)
        self._r.flushdb()

    def exists(self, key: Iri | Xsd_NCName | Xsd_QName) -> bool:
        value = self._r.get(str(key))
        return value is not None
