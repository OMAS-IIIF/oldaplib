import json
import os
from copy import deepcopy
from threading import Lock
from typing import Any

import redis

from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.helpers.singletonmeta import SingletonMeta
from oldaplib.src.iconnection import IConnection
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


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
    Singleton class for caching using a Redis database.

    This class interacts with a Redis instance to store, retrieve, and manage
    cached data. Designed to facilitate data caching using key-value pairs,
    supporting serialization and deserialization for complex objects. Provides
    methods for synchronous operations like setting, retrieving, deleting, and
    clearing cache entries.

    :ivar _r: Connection to the Redis database.
    :type _r: redis.client.Redis
    """
    def __init__(self):
        # default connection to local redis server on port 6379

        #self._r = redis.Redis(host=os.getenv("OLDAP_REDIS_HOST", 'localhost'), port=os.getenv("OLDAP_REDIS_PORT", 6379), db=0)

        redis_url = os.getenv("OLDAP_REDIS_URL", "redis://localhost:6379")
        self._r = redis.from_url(redis_url)

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
        self._r.flushdb()

    def exists(self, key: Iri | Xsd_NCName | Xsd_QName) -> bool:
        value = self._r.get(str(key))
        return value is not None
