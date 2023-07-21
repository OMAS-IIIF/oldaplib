from typing import Union, List
from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, SKOS, DCTERMS
from pyshacl import validate

if __name__ == '__main__':
    g = ConjunctiveGraph()
    g.parse('omaslib/ontologies/omas.ttl')
    g.parse('omaslib/ontologies/omas.shacl.trig')
    print('...DONE...')