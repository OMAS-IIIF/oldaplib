from copy import deepcopy
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
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()
