from typing import Any, Union, Optional, Dict, List, Set
from pystrict import strict
from rdflib import Graph, ConjunctiveGraph, URIRef, Literal, BNode
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore

from connection import Connection
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator
from omaslib.src.helpers.datatypes import QName, Languages, AnyIRI
from omaslib.src.helpers.context import Context
from omaslib.src.model import Model


@strict
class Property:
    _property_iri: Union[QName, None]
    _required: Union[bool, None]
    _multiple: Union[bool, None]
    _to_node_iri: Union[AnyIRI, None]
    _datatype: Union[XsdDatatypes, None]
    _languages: Set[Languages]  # an empty set if no languages are defined or do not make sense!
    _unique_langs: bool
    _order: int

    def __init__(self,
                 property_iri: Optional[QName] = None,
                 datatype: Optional[XsdDatatypes] = None,
                 to_node_iri: Optional[AnyIRI] = None,
                 required: Optional[bool] = None,
                 multiple: Optional[bool] = None,
                 languages: Optional[Set[Languages]] = None,
                 unique_langs: Optional[bool] = None,
                 order: Optional[int] = None):
        if not XsdValidator.validate(XsdDatatypes.QName, property_iri):
            raise OmasError("Invalid format of property IRI")
        self._property_iri = property_iri
        self._datatype = datatype
        self._to_node_iri = to_node_iri
        self._required = required
        self._multiple = multiple
        self._languages = languages if languages else set()
        self._unique_langs = True if unique_langs else False
        self._order = order

    def __str__(self):
        required = '✅' if self._required else '❌'
        multiple = '✅' if self._multiple else '❌'
        propstr = f'Property: {str(self._property_iri)};'
        if self._to_node_iri:
            propstr += f' Datatype: => {self._to_node_iri});'
        else:
            propstr += f' Datatype: {self._datatype.value};'
        propstr += f' Required: {required} Multiple: {multiple};'
        if self._languages:
            propstr += ' Languages: { '
        for lang in self._languages:
            propstr += str(lang) + ' '
        if self._languages:
            propstr += '};'
        if self._order:
            propstr += f' Order: {self._order}'
        return propstr

    def to_sparql_insert(self, indent: int = 0) -> str:
        blank = ' '
        sparql = f'{blank:{indent}}[\n';
        sparql += f'{blank:{indent + 4}}sh:path {str(self._property_iri)} ;\n'
        if self._datatype:
            sparql += f'{blank:{indent + 4}}sh:datatype {self._datatype.value} ;\n'
        if self._required:
            sparql += f'{blank:{indent + 4}}sh:minCount 1 ;\n'
        if not self._multiple:
            sparql += f'{blank:{indent + 4}}sh:maxCount 1 ;\n'
        if self._languages:
            sparql += f'{blank:{indent + 4}}sh:languageIn ( '
            for lang in self._languages:
                sparql += str(lang) + ' '
            sparql += f') ;\n'
        if self._unique_langs:
            sparql += f'{blank:{indent + 4}}sh:uniqueLang true ;\n'
        if self._to_node_iri:
            sparql += f'{blank:{indent + 4}}sh:class {str(self._to_node_iri)} ;\n'
        if self._order:
            sparql += f'{blank:{indent + 4}}sh:order {self._order} ;\n'
        sparql += f'{blank:{indent}}] ; \n'
        return sparql

    @property
    def property_iri(self) -> QName:
        return self._property_iri

    @property_iri.setter
    def property_iri(self, value: Union[QName, str]) -> None:
        raise OmasError("Property IRI can not be changed!")

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, value: bool):
        self._required = value

    @property
    def multiple(self):
        return self._multiple

    @multiple.setter
    def multiple(self, value: bool):
        self._multiple = value

    @property
    def languages(self) -> Set[Languages]:
        return self._languages

    def add_language(self, lang: Languages) -> None:
        self._languages.add(lang)

    def remove_language(self, lang: Languages) -> None:
        self._languages.discard(lang)

    def valid_language(self, lang: Languages) -> bool:
        return lang in self._languages



@strict
class DataModel(Model):
    _context: Context
    _shape: Union[QName, None]
    _properties: List[Property]

    def __init__(self,
                 con: Connection,
                 context: Context,
                 shape: Optional[QName] = None,
                 properties: Optional[List[Property]] = None) -> None:
        super().__init__(con)
        self._context = context
        self._shape = shape
        self._properties = properties if properties else []

    def __str__(self):
        blank = ' '
        indent = 4
        s = f'Shape: {self._shape}\nProperties:\n'
        for p in self._properties:
            s += f'{blank:{indent}}{str(p)}\n'
        return s

    def to_sparql_insert(self, indent: int) -> str:
        blank = ' '
        sparql = f'{blank:{indent}}{self._shape} a sh:nodeShape, XXXX ;\n'
        sparql += f'{blank:{indent + 4}}sh:targetClass XXXXX ; \n'
        for p in self._properties:
            sparql += p.to_sparql_insert(indent + 4)
        sparql += f'{blank:{indent}}sh:closed true .\n'
        return sparql

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
        proplist: List[Property] = []
        for x, p in properties.items():
            p_iri = None
            p_datatype = None
            p_max_count = None
            p_min_count = None
            p_langs = None
            p_order = None
            p_uniquelang = None
            p_to_class = None
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
                required = False
                multiple = True
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


            proplist.append(Property(property_iri=p_iri,
                                     datatype=p_datatype,
                                     to_node_iri=p_to_class,
                                     required=required,
                                     multiple=multiple,
                                     languages=p_langs,
                                     unique_langs=p_uniquelang))

        return cls(con=con,
                   context=context,
                   shape=shape,
                   properties=proplist)

if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    context = Context()
    omas_project = DataModel.from_store(con, context, QName('omas:OmasProjectShape'))
    print(omas_project.to_sparql_insert(4))
