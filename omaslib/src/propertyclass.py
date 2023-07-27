from typing import Union, Set, Optional

from pystrict import strict

from omaslib.src.helpers.datatypes import QName, AnyIRI, Languages
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator


@strict
class PropertyClass:
    _property_class_iri: Union[QName, None]
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
        self._property_class_iri = property_iri
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
        if self._to_node_iri:
            propstr += f' Datatype: => {self._to_node_iri});'
        else:
            propstr += f' Datatype: {self._datatype.value};'
        propstr += f' Required: {required} Multiple: {multiple};'
        if self._languages:
            propstr += ' Languages: { '
        for lang in self._languages:
            propstr += str(lang.value) + ' '
        if self._languages:
            propstr += '};'
        if self._order:
            propstr += f' Order: {self._order}'
        return propstr

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
