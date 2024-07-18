from threading import Lock
from typing import Any

from oldaplib.src.helpers.singletonmeta import SingletonMeta
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


class CacheSingleton(metaclass=SingletonMeta):
    _lock: Lock
    _cache: dict[Iri | Xsd_NCName, Any]

    def __init__(self):
        self._lock = Lock()
        self._cache = {}

    def get(self, key: Iri | Xsd_NCName) -> Any:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: Iri | Xsd_NCName, value: Any):
        with self._lock:
            self._cache[key] = value

    def delete(self, key: Iri | Xsd_NCName):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()
