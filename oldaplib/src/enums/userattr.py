from enum import unique, Enum

from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.serializeableset import SerializeableSet
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_string import Xsd_string


@unique
class UserAttr(AttributeClass):
    """
    Enumeration that defined the data fields (properties)

    - _UserFields.USER_IRI_ (RDF: 'oldap:userIri')
    - _UserFields.USER_ID_ (RDF: 'oldap:userId')
    - _UserFields.FAMILY_NAME_ (RDF: 'foaf:familyName)
    - _UserFields.GIVEN_NAME_ (RDF: 'foaf:givenName')
    - _UserFields.CREDENTIALS_ (RDF: 'oldap:credentials')
    - _UserFields.ACTIVE_ (RDF: 'oldap:isActive')
    - _UserFields.IN_PROJECT_ (RDF: 'oldap:inProject')
    - _UserFields.HAS_PERMISSIONS_ (RDF: 'oldap:hasPermissions')
    """
    # order: (QName, mandatory, immutable, datatype)
    USER_IRI = ('oldap:userIri', False, True, Iri)
    USER_ID = ('oldap:userId', True, False, Xsd_NCName)
    FAMILY_NAME = ('schema:familyName', True, False, Xsd_string)
    GIVEN_NAME = ('schema:givenName', True, False, Xsd_string)
    CREDENTIALS = ('oldap:credentials', True, False, Xsd_string)
    ACTIVE = ('oldap:isActive', False, False, Xsd_boolean)
    IN_PROJECT = ('oldap:inProject', False, False, InProjectClass)
    HAS_PERMISSIONS = ('oldap:hasPermissions', False, False, ObservableSet)

