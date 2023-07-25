from typing import Any, Union, Optional, Dict
from pystrict import strict
from rdflib import Graph, ConjunctiveGraph, URIRef, Literal, BNode
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore

from connection import Connection
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator
from omaslib.src.helpers.datatypes import QName, Context
from omaslib.src.model import Model


@strict
class hasProperty(Model):
    _property_iri: Union[str, None]
    _mandatory: Union[bool, None]
    _multiple: Union[bool, None]
    _datatype: Union[XsdDatatypes, None]

    def __init__(self,
                 con: Connection,
                 property_iri: Optional[str] = None,
                 datatype: Optional[XsdDatatypes] = None,
                 mandatory: Optional[bool] = None,
                 multiple: Optional[bool] = None):
        super().__init__(con)
        if not isinstance(con, Connection):
            raise OmasError('"con"-parameter must be an instance of Connection')
        if not XsdValidator.validate(XsdDatatypes.QName, property_iri):
            raise OmasError("Invalid format of property IRI")
        self._property_iri = property_iri
        self._datatype = datatype
        self._mandatory = mandatory
        self._multiple = multiple

    @property
    def property_iri(self) -> str:
        return self._property_iri

    @property_iri.setter
    def property_iri(self, value: str) -> None:
        raise OmasError("Property IRI can not be changed!")

    @property
    def mandatory(self):
        return self._mandatory

    @mandatory.setter
    def mandatory(self, value: bool):
        self._mandatory = value

    @property
    def multiple(self):
        return self._multiple

    @multiple.setter
    def multiple(self, value: bool):
        self._multiple = value

@strict
class DataModel(Model):
    _context: Context
    _shape: Union[QName, None]

    def __init__(self,
                 con: Connection,
                 context: Context,
                 shape: Optional[QName] = None) -> None:
        super().__init__(con)
        self._context = context
        self._shape = shape

    @classmethod
    def from_store(cls,
                   con: Connection,
                   context: Context,
                   shape: QName):
        query = context.sparql_context
        query += f"""
        SELECT ?prop ?p ?o ?pp ?oo
        FROM {shape.prefix}:shacl
        WHERE {{
            BIND({shape} AS ?shape)
            ?shape sh:property ?prop .
            ?prop ?p ?o .
            OPTIONAL {{
                ?o rdf:rest*/rdf:first ?oo
            }}
        }}
        """
        res = con.rdflib_query(query)
        properties = {}
        for r in res:
            if not properties.get(r[0]):
                properties[r[0]] = {}
            if isinstance(r[2], URIRef):
                properties[r[0]][r[1].fragment] = r[2].fragment
            elif isinstance(r[2], Literal):
                properties[r[0]][r[1].fragment] = r[2].toPython()
            elif isinstance(r[2], BNode):
                pass
            else:
                properties[r[0]][r[1].fragment] = r[2]
            if r[1].fragment == 'languageIn':
                if not properties[r[0]].get(r[1].fragment):
                    properties[r[0]][r[1].fragment] = []
                properties[r[0]][r[1].fragment].append(r[4].toPython())
        for x, p in properties.items():
            print(p)

        return cls(con, context, shape)

if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    context = Context()
    DataModel.from_store(con, context, QName('omas:OmasProjectShape'))