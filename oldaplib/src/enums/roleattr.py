from enum import unique, Enum

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


@unique
class RoleAttr(AttributeClass):
    # order: (QName, mandatory, immutable, datatype)
    ROLE_ID = ('virtual:roleId', True, True, Xsd_NCName)  # virtual property, no equivalent in RDF
    DEFINED_BY_PROJECT = ('oldap:definedByProject', True, True, IriOrNCName)
    LABEL = ('rdfs:label', False, False, LangString)
    COMMENT = ('rdfs:comment', False, False, LangString)
