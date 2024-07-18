import threading
from typing import Optional

from oldaplib.src.xsd.xsd_qname import Xsd_QName


class PropertyClassSingleton(type):
    """
    The idea for this class came from "https://stackoverflow.com/questions/3615565/python-get-constructor-to-return-an-existing-object-instead-of-a-new-one".
    This class is used to create a singleton of the class.
    """
    def __call__(cls, *, property_class_iri: Optional[Xsd_QName] = None, **kwargs):
        print(".......in __call__()")
        with cls._lock:
            key = f'{property_class_iri}'
            if key not in cls._cache:
                self = cls.__new__(cls, property_class_iri=property_class_iri, **kwargs)
                print('*************************')
                cls.__init__(self, property_class_iri=property_class_iri, **kwargs)
                print("+++++++++++++++++++++++++")
                if property_class_iri is None:
                    return self
                cls._cache[key] = self
                print("---add to cache---", property_class_iri)
            else:
                print("---return from cache---", property_class_iri)
            return cls._cache[key]

    def __init__(cls, name, bases, attributes):
        cls._lock = threading.Lock()
        print("--initialization of cache---")
        super().__init__(name, bases, attributes)
        cls._cache = {}

    def delete_from_cache(cls, *, property_class_iri: Optional[Xsd_QName] = None, **kwargs):
        with cls._lock:
            del cls._cache[property_class_iri]

    def in_cache(cls, *, property_class_iri: Optional[Xsd_QName] = None) -> bool:
        with cls._lock:
            return property_class_iri in cls._cache



class Gaga(metaclass=PropertyClassSingleton):

    def __init__(self, *,
                 property_class_iri: Optional[Xsd_QName]):
        print("--initialization of gaga---")
        self.property_class_iri = property_class_iri

    def out(self):
        print(self.property_class_iri)

    @classmethod
    def factory(cls, *, property_class_iri: Optional[Xsd_QName], recache: bool = False):
        if cls.in_cache(property_class_iri=property_class_iri):
            print("*****> in Cache")
        else:
            print("*****> NOT in Cache")
        if recache:
            cls.delete_from_cache(property_class_iri=property_class_iri)
        return cls(property_class_iri=property_class_iri)

if __name__ == '__main__':
    gaga = Gaga(property_class_iri=Xsd_QName('test:gaga'))
    gaga.out()
    gugus = Gaga(property_class_iri=Xsd_QName('test:gugus'))
    gugus.out()
    test = Gaga(property_class_iri=Xsd_QName('test:gaga'))
    test2 = Gaga.factory(property_class_iri=Xsd_QName('test:gaga'))
    test3 = Gaga.factory(property_class_iri=Xsd_QName('test:gaga'), recache=True)
