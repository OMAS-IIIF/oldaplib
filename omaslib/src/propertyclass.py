from typing import Union, Set, Optional, Any

from pystrict import strict

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, AnyIRI, Languages
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator
from omaslib.src.model import Model


@strict
class PropertyClass(Model):
    _property_class_iri: Union[QName, None]
    _subproperty_of: Union[QName, None]
    _exclusive_for_class: Union[QName, None]
    _required: Union[bool, None]
    _multiple: Union[bool, None]
    _to_node_iri: Union[AnyIRI, None]
    _datatype: Union[XsdDatatypes, None]
    _languages: Set[Languages]  # an empty set if no languages are defined or do not make sense!
    _unique_langs: bool
    _order: int

    def __init__(self,
                 con: Connection,
                 property_class_iri: Optional[QName] = None,
                 subproperty_of: Optional[QName] = None,
                 exclusive_for_class: Optional[QName] = None,
                 datatype: Optional[XsdDatatypes] = None,
                 to_node_iri: Optional[AnyIRI] = None,
                 required: Optional[bool] = None,
                 multiple: Optional[bool] = None,
                 languages: Optional[Set[Languages]] = None,
                 unique_langs: Optional[bool] = None,
                 order: Optional[int] = None):
        super().__init__(con)
        if not XsdValidator.validate(XsdDatatypes.QName, property_class_iri):
            raise OmasError("Invalid format of property IRI")
        self._property_class_iri = property_class_iri
        self._subproperty_of = subproperty_of
        self._exclusive_for_class = exclusive_for_class
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
        propstr = f'Property: {str(self._property_class_iri)};'
        if self._subproperty_of:
            propstr += f' Subproperty of {self._subproperty_of};'
        if self._exclusive_for_class:
            propstr += f' Exclusive for {self._exclusive_for_class};'
        if self._to_node_iri:
            propstr += f' Datatype: => {self._to_node_iri});'
        else:
            propstr += f' Datatype: {self._datatype.value};'
        propstr += f' Required: {required} Multiple: {multiple};'
        if self._languages:
            propstr += ' Languages: { '
        for lang in self._languages:
            propstr += f'"{lang.value}" '
        if self._languages:
            propstr += '};'
        if self._order:
            propstr += f' Order: {self._order}'

        return propstr

    @property
    def property_class_iri(self) -> QName:
        return self._property_class_iri

    @property_class_iri.setter
    def property_class_iri(self, value: Any):
        OmasError(f'property_iri_class cannot be set!')

    def read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o
        FROM {self._property_class_iri.prefix}:onto
        WHERE {{
            {self._property_class_iri} ?p ?o
        }}
        """
        res = self._con.rdflib_query(query1)
        print(self._property_class_iri)
        datatype = None
        to_node_iri = None
        data_prop = False
        obj_prop = False
        for r in res:
            pstr = str(context.iri2qname(r[0]))
            if pstr == 'owl:DatatypeProperty':
                data_prop = True
            elif pstr == 'owl:ObjectProperty':
                obj_prop = True
            elif pstr == 'owl:subPropertyOf':
                self._subproperty_of = r[1]
            elif pstr == 'rdfs:range':
                o = context.iri2qname(r[1])
                if o.prefix == 'xsd':
                    datatype = o
                else:
                    to_node_iri = o
            elif pstr == 'rdfs:domain':
                o = context.iri2qname(r[1])
                self._exclusive_for_class = o
        # Consistency checks
        if data_prop and obj_prop:
            OmasError("Property may not be data- and object-property at the same time")
        if data_prop:
            if datatype != self._datatype:
                OmasError(f'Property has inconstent data type definition: OWL: {datatype} vs SHACL: {self._datatype}.')
        if obj_prop:
            if to_node_iri != self._to_node_iri:
                OmasError(f'Property has inconstent object type definition: OWL: {to_node_iri} vs SHACL: {self._to_node_iri}.')

    def to_sparql_insert(self, indent: int = 0) -> str:
        blank = ' '
        sparql = f'{blank:{indent}}[\n';
        sparql += f'{blank:{indent + 4}}sh:path {str(self._property_class_iri)} ;\n'
        if self._datatype:
            sparql += f'{blank:{indent + 4}}sh:datatype {self._datatype.value} ;\n'
        if self._required:
            sparql += f'{blank:{indent + 4}}sh:minCount 1 ;\n'
        if not self._multiple:
            sparql += f'{blank:{indent + 4}}sh:maxCount 1 ;\n'
        if self._languages:
            sparql += f'{blank:{indent + 4}}sh:languageIn ( '
            for lang in self._languages:
                sparql += f'"{lang.value}" '
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
        return self._property_class_iri

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
