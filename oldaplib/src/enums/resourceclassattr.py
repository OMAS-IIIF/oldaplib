from enum import unique, Enum

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@unique
class ResClassAttribute(AttributeClass):
    # order: (QName, mandatory, immutable, datatype)
    SUPERCLASS = ('oldap:superclass', False, False, ObservableDict)  # virtual attribute, SHACL: sh:node, OWL: rdfs:subClassOf
    LABEL = ('rdfs:label', False, False, LangString)
    COMMENT = ('rdfs:comment', False, False, LangString)
    CLOSED = ('sh:closed', False, False, Xsd_boolean)

