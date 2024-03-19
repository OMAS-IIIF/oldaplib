from typing import Optional

from omaslib.src.xsd.xsd_qname import Xsd_QName


class PropertyClassSingleton(type):
    """
    The idea for this class came from "https://stackoverflow.com/questions/3615565/python-get-constructor-to-return-an-existing-object-instead-of-a-new-one".
    This class is used to create a singleton of the class.
    """
    def __call__(cls, *, property_class_iri: Optional[Xsd_QName] = None, **kwargs):
        key = f'{property_class_iri}'
        if key not in cls._cache:
            self = cls.__new__(cls, property_class_iri=property_class_iri, **kwargs)
            cls.__init__(self, property_class_iri=property_class_iri, **kwargs)
            if property_class_iri is None:
                return self
            cls._cache[key] = self
            cls._refcnt[key] = 1
        else:
            cls._refcnt[key] += 1
        print("\n===========> INIT CACHE RESPONSE", property_class_iri, cls._refcnt[property_class_iri])
        return cls._cache[key]

    def __init__(cls, name, bases, attributes):
        super().__init__(name, bases, attributes)
        cls._cache = {}
        cls._refcnt = {}
