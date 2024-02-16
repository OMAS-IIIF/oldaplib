from enum import Enum
from functools import partial, partialmethod
from pprint import pprint
from typing import Union, List, Dict
from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, SKOS, DCTERMS
from pyshacl import validate


class Field(Enum):
    AN_INT = 'an_int'
    A_FLOAT = 'a_float'
    A_STR = 'a_str'

class Gaga:
    __fields: Dict[Field, int | float |str]

    def __init__(self,
                 an_int: int,
                 a_float: float,
                 a_str: str):
        self.__fields = {}
        self.__fields[Field.AN_INT] = an_int
        self.__fields[Field.A_FLOAT] = a_float
        self.__fields[Field.A_STR] = a_str

        for field in Field:
            setattr(Gaga, field.value, property(
                partial(Gaga.__get_value, field=field),
                partial(Gaga.__set_value, field=field),
                partial(Gaga.__del_value, field=field)))



    def __get_value(self, field: Field) -> int | float | str:
        return self.__fields[field]

    def __set_value(self, value: int | float | str, field: Field):
        self.__fields[field] = value

    def __del_value(self, field: Field):
        del gaga.__fields[field]


if __name__ == '__main__':
    gaga = Gaga(an_int=42, a_float=3.141592653589793, a_str='Hello World!?')
    gugus = Gaga(an_int=4711, a_float=2.7142857142857143, a_str='Hello Kitty')
    print(gaga.an_int)
    print(gaga.a_str)
    print(gugus.a_float)
    gaga.a_float = 12.12
    print(gaga.a_float)