from enum import Enum
from functools import partial, partialmethod
from pprint import pprint
from typing import Union, List, Dict
from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, SKOS, DCTERMS
from pyshacl import validate



def search(search_term: str, data: str) -> int:
    index = -1
    for i in range(0, len(data) - len(search_term)):
        for j in range(0, len(search_term)):
            if search_term[j] == data[i + j]:
                if index == -1:
                    index = i
            else:
                index = -1
                break
        if index != -1:
            return index
    return index

if __name__ == '__main__':
    i = search("gaga", "this is gaga, or not")
    print("====>", i)
    j = search("gugus", "this is gaga, or not")
    print("====>", j)
