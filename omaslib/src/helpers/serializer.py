from base64 import b85encode, b85decode
from enum import Enum
from typing import Dict, Any, Self
from datetime import datetime
from uuid import UUID
import json


class _Serializer:
    """
    This class is responsible for serializing and deserializing custom objects and classes to and from json. The whole
    class is used, to serialize a complex custom objects and rebuild it after it got transmitted.
    It works as follows:
    - The class itself has to be instanciated (thus i have the magic function __call__ which makes the instance callable)
    - During the instantiation, the dict-key to enter the name of the class into the dictionary is defined and stored.
        In addition, the dict which will store the class names as key and the class constructors as value, is initialized.
    - Serializer demands, that each custom class that is to be serialized has a _as_dict methode, that transforms the
        object in a dict.
    - The serializer will be instantiated exactly once (designed as singleton -> see __new__ function).
        The resulting instance should then be used as decorator for the classes that should be serialized.
    - The methode encoder_default is passed to the json.dumps methode as the named parameter "default". If specified,
        default should be a function that gets called for objects that can’t otherwise be serialized. It should return a
        JSON encodable version of the object or raise a TypeError. If not specified, TypeError is raised. In this case
        it calls the _as_dict methode and adds the classname to the dict. Thus the class name is encoded into the json.
    - The decoder_hook methode is called by json.decode and is called each time json.decode encounters a dict. If the dict
        contains the class name, it will call the constructor of the class and returns the data as instance of that class.
    - This idea is from the following stack overflow entry:
    https://stackoverflow.com/questions/51975664/serialize-and-deserialize-objects-from-user-defined-classes

    - Additions done by me:
      - serialization/deserialization of `datetime`- and `UUID` objects added
    """
    _instance: Self | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(_Serializer, cls).__new__(cls)
            # Initialisierung der Instanz kann hier erfolgen
        return cls._instance

    def __init__(self, classname_key='__class__'):
        self._key = classname_key
        self._classes = {}  # to keep a reference to the classes used

    def __call__(self, class_):  # decorate a class
        self._classes[class_.__name__] = class_
        return class_

    def decoder_hook(self, d: Dict[Any, Any]) -> Dict[Any, Any] | datetime | UUID | bytes:
        classname = d.pop(self._key, None)
        if classname:
            if classname == 'datetime':
                return datetime.fromisoformat(d['__value__'])
            if classname == 'UUID':
                return UUID(d['__value__'])
            if classname == 'bytes':
                return b85decode(d['__value__'].encode(encoding='UTF-8'))
            if type(self._classes[classname]) == type(Enum):
                return self._classes[classname](d['__value__'])
            else:
                return self._classes[classname](**d)
        return d

    def encoder_default(self, obj):
        if isinstance(obj, datetime):
            return {self._key: 'datetime', '__value__': str(obj)}
        if isinstance(obj, UUID):
            return {self._key: 'UUID', '__value__': str(obj)}
        if isinstance(obj, Enum):
            return {self._key: obj.__class__.__name__, '__value__': obj.value}
        if isinstance(obj, bytes):
            #  NOTE: if bytes are real bytes (image, sound,...) encoding as UTF-8 will not work...
            #  Therefore I use b85-encoding
            return {self._key: 'bytes', '__value__': b85encode(obj).decode(encoding='UTF-8')}
        d = obj._as_dict()
        d[self._key] = type(obj).__name__
        return d


serializer = _Serializer()
