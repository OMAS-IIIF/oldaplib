from enum import unique, Enum
from typing import Self

from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.numeric import Numeric
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_string import Xsd_string


@unique
class PropClassAttr(AttributeClass):
    """
    Enumeration of all the attributes of a property. Please note that the `Oldap:restriction` attribute
    itself is a complex onbject defining restrictions to the property.
    The following attributes are defined:

    - `PropertyClassAttribute.SUBPROPERTY_OF`: The given property is a specialization of the property given here
    - `PropertyClassAttribute.PROPERTY_OF`: The given property is either a `owl:ObjectProperty` or
      a `owl:DataProperty`. These are important to create a correct OWL ontology. `owl:ObjectProperty`'s
      point to a resource, while `owl:DataProperty`'s point to literal value.
    - `PropertyClassAttribute.TO_NODE_IRI`: The given property points the a resource of the given class.
    - `PropertyClassAttribute.DATATYPE`: Th egiven property must be of the given data type (as defined by
      the XML datatypes. See [XsdDatatypes](xsd_datatypes).
    - `PropertyClassAttribute.RESTRICTION`: Restrictions the property and its values must follow
    - `PropertyClassAttribute.NAME`: Name of the property. The literal is a string that may have attached
      a language id.
    - `PropertyClassAttribute.DESCRIPTION`: Description of the property. The literal is a string that may
      have attached a language id.
    """
    # order: (QName, mandatory, immutable, datatype)
    SUBPROPERTY_OF = ('rdfs:subPropertyOf', False, False, Iri)
    TYPE = ('rdf:type', False, False, OwlPropertyType)
    CLASS = ('sh:class', False, False, Iri)
    DATATYPE = ('sh:datatype', False, False, XsdDatatypes)
    NAME = ('sh:name', False, False, LangString)
    DESCRIPTION = ('sh:description', False, False, LangString)
    LANGUAGE_IN = ('sh:languageIn', False, False, LanguageIn)
    UNIQUE_LANG = ('sh:uniqueLang', False, False, Xsd_boolean)
    IN = ('sh:in', False, False, XsdSet)
    MIN_LENGTH = ('sh:minLength', False, False, Xsd_integer)
    MAX_LENGTH = ('sh:maxLength', False, False, Xsd_integer)
    PATTERN = ('sh:pattern', False, False, Xsd_string)
    MIN_EXCLUSIVE = ('sh:minExclusive', False, False, Numeric)
    MIN_INCLUSIVE = ('sh:minInclusive', False, False, Numeric)
    MAX_EXCLUSIVE = ('sh:maxExclusive', False, False, Numeric)
    MAX_INCLUSIVE = ('sh:maxInclusive', False, False, Numeric)
    LESS_THAN = ('sh:lessThan', False, False, Iri)
    LESS_THAN_OR_EQUALS = ('sh:lessThanOrEquals', False, False, Iri)


    @classmethod
    def from_name(cls, name: str) -> Self:
        if name == 'inSet':
            name = 'in'
        if name == 'toClass':
            name = 'class'
        for member in cls:
            if member._name == name:
                return member
        raise ValueError(f"No member with name {name} found")

    @property
    def toRdf(self) -> str:
        if self.value == 'sh:inSet':
            return 'sh:in'
        elif self.value == 'sh:toClass':
            return 'sh:class'
        else:
            return self.value.toRdf

