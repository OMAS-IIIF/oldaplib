from enum import unique, Enum

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


@unique
class OldapListNodeAttr(AttributeClass):
    """
    This enum class represents the fields used in the project model
    """
    # order: (QName, mandatory, immutable, datatype)
    OLDAPLISTNODE_ID = ('oldap:oldapListNodeId', True, True, Xsd_NCName)  # virtual property, represents the RDF subject
    PREF_LABEL = ('skos:prefLabel', False, False, LangString)
    DEFINITION = ('skos:definition', False, False, LangString)
