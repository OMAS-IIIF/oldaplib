from enum import unique, Enum

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


@unique
class PermissionSetAttr(AttributeClass):
    # order: (QName, mandatory, immutable, datatype)
    PERMISSION_SET_ID = ('virtual:permissionSetId', True, True, Xsd_NCName)  # virtual property, no equivalent in RDF
    DEFINED_BY_PROJECT = ('oldap:definedByProject', True, True, IriOrNCName)
    GIVES_PERMISSION = ('oldap:givesPermission', True, False, DataPermission)
    LABEL = ('rdfs:label', False, False, LangString)
    COMMENT = ('rdfs:comment', False, False, LangString)
