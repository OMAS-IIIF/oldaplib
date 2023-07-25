import json
from pystrict import strict
from typing import List, Set, Dict, Tuple, Optional, Any, Union
from urllib.parse import quote_plus
from datetime import date

from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdValidator, XsdDatatypes
from connection import Connection, SparqlResultFormat
from model import Model
from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef, Literal



@strict
class Project(Model):
    _projectId: str
    _projectName: str
    _projectDescription: Union[str, None]
    _projectStart: date
    _projectEnd: Union[date, None]

    def __init__(self,
                 con: Connection,
                 id: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 start: Optional[date] = None,
                 end: Optional[date] = None):
        super().__init__(con)

        query1 = """
        PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX sh:   <http://www.w3.org/ns/shacl#>
        PREFIX omas: <http://omas.org/base#>
        PREFIX data: <http://omas.org/data#>
        CONSTRUCT {
	        ?shape sh:property ?po .
	        ?po ?p ?o .
        }
        FROM omas:shacl
        WHERE {
		    BIND(omas:OmasProjectShape AS ?shape)
		    ?shape sh:property ?po .
		    ?po ?p ?o .
        }
        """
        """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX xml: <http://www.w3.org/XML/1998/namespace#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX omas: <http://omas.org/base#>
SELECT ?shape ?prop ?p ?o
FROM omas:shacl
WHERE {
    BIND(omas:OmasProjectShape AS ?shape)
    ?shape sh:property ?po .
    ?po ?p ?o .
}
"""
        query = """
                PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX sh:   <http://www.w3.org/ns/shacl#>
                PREFIX omas: <http://omas.org/base#>
                PREFIX data: <http://omas.org/data#>
                SELECT ?shape ?prop ?p ?o
                FROM omas:shacl
                WHERE {
        		    BIND(omas:OmasProjectShape AS ?shape)
        		    ?shape sh:property ?prop .
        		    ?prop ?p ?o .
                }
                """
        gaga = "prefix omas: <http://omas.org/base#> CONSTRUCT { ?s ?p ?o } FROM omas:shacl WHERE { ?s ?p ?o }"
        res = self._con.query(query)

        for r in res:
            if isinstance(r[0], URIRef):
                print(r[0].fragment)


if __name__ == "__main__":
    con = Connection('http://localhost:7200', 'omas')
    project = Project(con)
