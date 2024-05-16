from enum import unique, Enum


@unique
class UserAttr(Enum):
    """
    Enumeration that defined the data fields (properties)

    - _UserFields.USER_IRI_ (RDF: 'omas:userIri')
    - _UserFields.USER_ID_ (RDF: 'omas:userId')
    - _UserFields.FAMILY_NAME_ (RDF: 'foaf:familyName=
    - _UserFields.GIVEN_NAME_ (RDF: 'foaf:givenName')
    - _UserFields.CREDENTIALS_ (RDF: 'omas:credentials')
    - _UserFields.ACTIVE_ (RDF: 'omas:isActive')
    - _UserFields.IN_PROJECT_ (RDF: 'omas:inProject')
    - _UserFields.HAS_PERMISSIONS_ (RDF: 'omas:hasPermissions')

    """
    USER_IRI = 'omas:userIri'
    USER_ID = 'omas:userId'
    FAMILY_NAME = 'foaf:familyName'
    GIVEN_NAME = 'foaf:givenName'
    CREDENTIALS = 'omas:credentials'
    ACTIVE = 'omas:isActive'
    IN_PROJECT = 'omas:inProject'
    HAS_PERMISSIONS = 'omas:hasPermissions'

    @property
    def toRdf(self) -> str:
        return self.value
