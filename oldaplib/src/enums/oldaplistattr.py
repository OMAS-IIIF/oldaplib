from enum import unique, Enum

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


@unique
class OldapListAttr(AttributeClass):
    """
    This enum class represents the fields used in the project model
    """
    # order: (QName, mandatory, immutable, datatype)
    OLDAPLIST_ID = ('oldap:oldapListId', True, True, Xsd_NCName)  # virtual property, represents the RDF subject
    PREF_LABEL = ('skos:prefLabel', False, False, LangString)
    DEFINITION = ('skos:definition', False, False, LangString)
