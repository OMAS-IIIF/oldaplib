from typing import Union, Optional, List
from pystrict import strict
from rdflib import URIRef, Literal, BNode

from connection import Connection
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.helpers.datatypes import QName, Languages
from omaslib.src.helpers.context import Context, DEFAULT_CONTEXT
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass


@strict
class ResourceClass(Model):
    _shape: Union[QName, None]
    _owl_class: Union[QName, None]
    _subshape_of: Union[QName, None]
    _properties: List[PropertyClass]
    _closed: bool

    def __init__(self,
                 con: Connection,
                 shape: Optional[QName] = None,
                 owl_cass: Optional[QName] = None,
                 subshape_of: Optional[QName] = None,
                 properties: Optional[List[PropertyClass]] = None,
                 closed: Optional[bool] = None) -> None:
        super().__init__(con)
        self._shape = shape
        self._owl_class = owl_cass
        self._subshape_of = subshape_of
        self._properties = properties if properties else []
        self._closed = True if closed is None else closed

    def __str__(self):
        blank = ' '
        indent = 4
        s = f'Shape: {self._shape}\nProperties:\n'
        for p in self._properties:
            s += f'{blank:{indent}}{str(p)}\n'
        return s

    def to_sparql_insert(self, indent: int) -> str:
        blank = ' '
        sparql = f'{blank:{indent}}{self._shape} a sh:nodeShape, {self._owl_class} ;\n'
        sparql += f'{blank:{indent + 4}}sh:targetClass {self._owl_class} ; \n'
        for p in self._properties:
            sparql += f'{blank:{indent + 4}}sh:property\n'
            sparql += f'{blank:{indent + 8}}[\n'
            sparql += f'{blank:{indent + 12}}sh:path rdf:type ;\n'
            sparql += f'{blank:{indent + 8}}] ;\n'
            sparql += f'{blank:{indent + 4}}sh:property\n'

            sparql += p.to_sparql_insert(indent + 8)
        sparql += f'{blank:{indent}}sh:closed {"true" if self._closed else "false"} .\n'
        return sparql

    @classmethod
    def from_store(cls,
                   con: Connection,
                   shape: QName,
                   context_name: str = DEFAULT_CONTEXT):
        context = Context(name=con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o
        FROM {shape.prefix}:shacl
        WHERE {{
            BIND({str(shape)} AS ?shape)
            ?shape ?p ?o
            FILTER(?p != sh:property)
        }}
        """
        res = con.rdflib_query(query1)
        owl_class = None
        subshape_of = None
        target_class = None
        closed = True
        for r in res:
            p = context.iri2qname(r[0])
            if p == 'rdf:type':
                if context.iri2qname(r[1]) == f'{shape}':
                    continue
                else:
                    owl_class = context.iri2qname(r[1])
            elif p == 'rdfs:subClassOf':
                subshape_of = context.iri2qname(r[1])
            elif p == 'sh:targetClass':
                target_class = context.iri2qname(r[1])
            elif p == 'sh:closed':
                closed = closed = r[1].value
        if target_class and owl_class and target_class != owl_class:
            raise OmasError(f'Inconsistent shape "{shape}": sh:targetClass "{target_class}" != rdf:type "{owl_class}"')
        if not owl_class and target_class:
            owl_class = target_class

        query2 = context.sparql_context
        query2 += f"""
        SELECT ?prop ?p ?o ?pp ?oo
        FROM {shape.prefix}:shacl
        WHERE {{
            BIND({str(shape)} AS ?shape)
            ?shape sh:property ?prop .
            ?prop ?p ?o .
            OPTIONAL {{
                ?o rdf:rest*/rdf:first ?oo
            }}
        }}
        """
        res = con.rdflib_query(query2)
        properties = {}
        for r in res:
            if r[2] == URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
                continue
            if not isinstance(r[1], URIRef):
                raise OmasError("INCONSISTENCY!")
            p = context.iri2qname(r[1])
            if not properties.get(r[0]):
                properties[r[0]] = {}
            if isinstance(r[2], URIRef):
                properties[r[0]][p] = context.iri2qname(r[2])
            elif isinstance(r[2], Literal):
                properties[r[0]][p] = r[2].toPython()
            elif isinstance(r[2], BNode):
                pass
            else:
                properties[r[0]][p] = r[2]
            if r[1].fragment == 'languageIn':
                if not properties[r[0]].get(p):
                    properties[r[0]][p] = set()
                properties[r[0]][p].add(r[4].toPython())
        proplist: List[PropertyClass] = []
        for x, p in properties.items():
            p_iri = None
            p_datatype = None
            p_max_count = None
            p_min_count = None
            p_langs = None
            p_order = None
            p_uniquelang = None
            p_to_class = None
            required = False
            multiple = True
            for key, val in p.items():
                if key == 'sh:path':
                    p_iri = val
                elif key == 'sh:minCount':
                    p_min_count = val
                elif key == 'sh:maxCount':
                    p_max_count = val
                elif key == 'sh:datatype':
                    p_datatype = XsdDatatypes(str(val))
                elif key == 'sh:languageIn':
                    p_langs = val
                elif key == 'sh:order':
                    p_order = val
                elif key == 'sh:uniqueLang':
                    p_uniquelang = val
                elif key == 'sh:class':
                    p_to_class = val
                elif key == 'sh:order':
                    p_order = val
                else:
                    print('---ERROR---: key=', key, ' val=', val)  # TODO: Catch this error in a better way!
                if not p_min_count and not p_max_count:
                    required = False
                    multiple = True
                elif p_min_count == 1 and not p_max_count:
                    required = True
                    multiple = True
                elif not p_min_count and p_max_count == 1:
                    required = False
                    multiple = False
                elif p_min_count == 1 and p_max_count == 1:
                    required = True
                    multiple = False


            proplist.append(PropertyClass(property_iri=p_iri,
                                          datatype=p_datatype,
                                          to_node_iri=p_to_class,
                                          required=required,
                                          multiple=multiple,
                                          languages=p_langs,
                                          unique_langs=p_uniquelang))

        return cls(con=con,
                   shape=shape,
                   owl_cass=owl_class,
                   properties=proplist,
                   closed=closed)

    def create(self, indent: int = 4):
        blank = ' '

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'INSERT DATA {{\n'
        sparql += f'{blank:{indent}}GRAPH {self._shape.prefix}:shacl {{\n'
        sparql += f'{blank:{2*indent}}{self._shape} a sh:nodeShape, {self._owl_class} ;\n'
        if self._subshape_of:
            sparql += f'{blank:{3*indent}}rdfs:subClassOf {self._subshape_of} ; \n'
        sparql += f'{blank:{3*indent}}sh:targetClass {self._owl_class} ; \n'
        for p in self._properties:
            sparql += f'{blank:{3*indent}}sh:property\n'
            sparql += f'{blank:{4*indent}}[\n'
            sparql += f'{blank:{5*indent}}sh:path rdf:type ;\n'
            sparql += f'{blank:{4*indent}}] ;\n'
            sparql += f'{blank:{3*indent}}sh:property\n'
            sparql += p.to_sparql_insert(4*indent)
        sparql += f'{blank:{2*indent}}sh:closed {"true" if self._closed else "false"} .\n'
        sparql += f'{blank:{indent}}}}\n'
        sparql += f'}}\n'
        self._con.update_query(sparql)

if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    omas_project = ResourceClass.from_store(con, QName('omas:OmasProjectShape'))
    plist = [
        PropertyClass(property_iri=QName('omas:commentstr'),
                      datatype=XsdDatatypes.string,
                      languages={Languages.DE, Languages.EN},
                      unique_langs=True,
                      multiple=True,
                      required=True),
        PropertyClass(property_iri=QName('omas:creator'),
                      to_node_iri=QName('omas:User'),
                      multiple=False,
                      required=True,
                      order=2),
        PropertyClass(property_iri=QName('omas:createdAt'),
                      datatype=XsdDatatypes.dateTime,
                      multiple=False,
                      required=True,
                      order=1)
    ]
    comment_class = ResourceClass(
        con=con,
        shape=QName('omas:OmasCommentShape'),
        owl_cass=QName('omas:OmasComment'),
        properties=plist,
        closed=True
    )
    comment_class.create()
