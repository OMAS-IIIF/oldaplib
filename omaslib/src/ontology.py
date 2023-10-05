from typing import List, Dict, Union, Set

from pystrict import strict
from rdflib import URIRef, Literal, BNode

from omaslib.src.helpers.langstring import Languages, LangString
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.model import Model
from omaslib.src.connection import Connection
from omaslib.src.helpers.context import DEFAULT_CONTEXT, Context
from omaslib.src.helpers.datatypes import QName
from omaslib.src.propertyclass import PropertyClass
from omaslib.src.propertyrestriction import PropertyRestrictions, PropertyRestrictionType


@strict
class Ontology(Model):
    _iri: str
    _prefix: str
    _resource_iris: List[QName]
    _properties: Dict[QName, PropertyClass]

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
        self._properties = {}

    def __read_shacl_standalone_properties(self) -> None:
        #
        # now let's get all "standalone" property definitions
        #
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?shape ?p ?o ?oo
        FROM {self._prefix}:shacl
        WHERE {{
            ?shape rdf:type sh:PropertyShape ;
                ?p ?o .
            OPTIONAL {{
                ?o rdf:rest*/rdf:first ?oo
            }}
            FILTER(?o != sh:PropertyShape)
        }}
        """

        # qn = QName('omas:commentShape')
        # print('==========', context.qname2iri(qn))
        # res = self._con.rdflib_query(query, {'shape': URIRef(str(context.qname2iri(qn)))})
        res = self._con.rdflib_query(query)
        properties: Dict[QName, Dict[QName, Union[int, float, str, Set[Languages], QName]]] = {}
        for r in res:
            if not isinstance(r["shape"], URIRef):
                raise OmasError(f'Expected URIRef for sh:PropertyShape, got "{r["shape"]}"')
            shape = context.iri2qname(r["shape"])
            if properties.get(shape) is None:
                properties[shape] = {}
            prop = context.iri2qname(r["p"])
            if isinstance(r["o"], URIRef):
                o = context.iri2qname(r["o"])
                properties[shape][prop] = o
            elif isinstance(r["o"], Literal):
                properties[shape][prop] = r["o"].toPython()
            elif isinstance(r["o"], BNode):
                if prop == QName('sh:languageIn'):
                    if properties[shape].get(prop) is None:
                        properties[shape][prop] = set()
                    properties[shape][prop].add(Languages(r["oo"].toPython()))

            print(f'{shape} {prop} {r["o"]} {type(r["o"])} {r["oo"]}')
        for shape_iri, propinfo in properties.items():
            p_iri = None
            p_datatype = None
            p_name = None
            p_description = None
            p_order = None
            p_to_class = None
            restrictions = PropertyRestrictions()
            for key, val in propinfo.items():
                if key == 'sh:path':
                    p_iri = val
                elif key == 'sh:datatype':
                    p_datatype = XsdDatatypes(str(val))
                elif key == 'sh:name':
                    p_name = LangString()
                    for ll in val:
                        p_name.add(ll)
                elif key == 'sh:description':
                    p_description = LangString()
                    for ll in val:
                        p_description.add(ll)
                elif key == 'sh:order':
                    p_order = val
                elif key == 'sh:class':
                    p_to_class = val
                else:
                    try:
                        restrictions[PropertyRestrictionType(key)] = val
                    except (ValueError, TypeError) as err:
                        OmasError(f'Invalid shacl definition: "{key} {val}"')
            prop = PropertyClass(con=self._con,
                                 property_class_iri=p_iri,
                                 datatype=p_datatype,
                                 to_node_iri=p_to_class,
                                 restrictions=restrictions,
                                 name=p_name,
                                 description=p_description,
                                 order=p_order)
            self._properties[shape_iri] = prop

    def __read_shacl(self) -> None:
        #
        # first we read all standalone properties that may be used
        #
        self.__read_shacl_standalone_properties()

        #
        # first we get the IRI's of all resources in the ontology
        #
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

    def read(self):
        self.__read_shacl()


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="omas")
    onto = Ontology(con, 'omas', 'http://omas.org/base#')
    onto.read()
