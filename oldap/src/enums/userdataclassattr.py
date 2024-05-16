from enum import unique, Enum


@unique
class UserAttr(Enum):
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
    USER_IRI = 'oldap:userIri'
    USER_ID = 'oldap:userId'
    FAMILY_NAME = 'foaf:familyName'
    GIVEN_NAME = 'foaf:givenName'
    CREDENTIALS = 'oldap:credentials'
    ACTIVE = 'oldap:isActive'
    IN_PROJECT = 'oldap:inProject'
    HAS_PERMISSIONS = 'oldap:hasPermissions'

    @property
    def toRdf(self) -> str:
        return self.value
