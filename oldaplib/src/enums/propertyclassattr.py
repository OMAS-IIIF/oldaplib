from enum import unique, Enum
from typing import Self

from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.attributeclass import AttributeClass, Target
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.numeric import Numeric
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_qname import Xsd_QName
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
    # order: (QName, mandatory, immutable, datatype, target)
    SUBPROPERTY_OF = ('rdfs:subPropertyOf', False, False, Iri)
    TYPE = ('rdf:type', False, False, ObservableSet, Target.OWL)
    CLASS = ('sh:class', False, False, Iri, Target.SHACL)
    NODEKIND = ('sh:nodeKind', False, False, Iri, Target.SHACL)
    DATATYPE = ('sh:datatype', False, False, XsdDatatypes, Target.SHACL)
    NAME = ('sh:name', False, False, LangString, Target.SHACL)  # needs notifier
    DESCRIPTION = ('sh:description', False, False, LangString, Target.SHACL)  # needs notifier
    LANGUAGE_IN = ('sh:languageIn', False, False, LanguageIn, Target.SHACL)  # needs notifier
    UNIQUE_LANG = ('sh:uniqueLang', False, False, Xsd_boolean, Target.SHACL)
    IN = ('sh:in', False, False, XsdSet, Target.SHACL)  # needs notifier
    MIN_LENGTH = ('sh:minLength', False, False, Xsd_integer, Target.SHACL)
    MAX_LENGTH = ('sh:maxLength', False, False, Xsd_integer, Target.SHACL)
    PATTERN = ('sh:pattern', False, False, Xsd_string, Target.SHACL)
    MIN_EXCLUSIVE = ('sh:minExclusive', False, False, Numeric, Target.SHACL)
    MIN_INCLUSIVE = ('sh:minInclusive', False, False, Numeric, Target.SHACL)
    MAX_EXCLUSIVE = ('sh:maxExclusive', False, False, Numeric, Target.SHACL)
    MAX_INCLUSIVE = ('sh:maxInclusive', False, False, Numeric, Target.SHACL)
    LESS_THAN = ('sh:lessThan', False, False, Iri, Target.SHACL)
    LESS_THAN_OR_EQUALS = ('sh:lessThanOrEquals', False, False, Iri, Target.SHACL)
    INVERSE_OF = ('owl:inverseOf', False, False, Xsd_QName, Target.OWL)
    EQUIVALENT_PROPERTY = ('owl:equivalentProperty', False, False, Xsd_QName, Target.OWL)


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

