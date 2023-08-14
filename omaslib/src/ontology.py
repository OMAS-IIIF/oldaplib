from typing import List

from pystrict import strict

from omaslib.src.model import Model
from omaslib.src.connection import Connection
from omaslib.src.helpers.context import DEFAULT_CONTEXT, Context
from omaslib.src.helpers.datatypes import QName


@strict
class Ontology(Model):
    _iri: str
    _prefix: str
    _resource_iris: List[QName]
    _property_iris: List[QName]

    def __init__(self,
                 con: Connection,
                 prefix: str,
                 iri: str):
        super().__init__(con)
        self._iri = iri
        self._prefix = prefix
        context = Context(name=self._con.context_name)
        context[prefix] = iri
        self._resource_iris = []

    def __read_shacl(self) -> None:
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?shape ?owl_class
        FROM {self._prefix}:shacl
        WHERE {{
            ?shape rdf:type sh:NodeShape .
            ?shape rdf:type ?owl_class .
            FILTER(?owl_class != sh:NodeShape)
        }}
        """
        res = self._con.rdflib_query(query1)
        for r in res:
            owl_class = context.iri2qname(r["owl_class"])
            shape = context.iri2qname(r["shape"])
            if f'{owl_class}Shape' == str(shape):
                self._resource_iris.append(owl_class)
        print(self._resource_iris)

        query2 = context.sparql_context
        query2 += f"""
        SELECT ?shape ?p ?o
        FROM {self._prefix}:shacl
        WHERE {{
            ?shape rdf:type sh:propertyShape ;
                ?p ?o .
            FILTER(?o != sh:propertyShape)
        }}
        """
        res = self._con.rdflib_query(query2)
        for r in res:
            print(f'{r["shape"]} {r["p"]} {r["o"]}')


    def read(self):
        self.__read_shacl()


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="omas")
    onto = Ontology(con, 'omas', 'http://omas.org/base#')
    onto.read()


