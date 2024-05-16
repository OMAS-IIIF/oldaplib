from enum import unique, Enum


@unique
class PermissionSetAttr(Enum):
    PERMISSION_SET_IRI = 'oldap:permissionSetIri'  # virtual property, no equivalent in RDF
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    GIVES_PERMISSION = 'oldap:givesPermission'
    DEFINED_BY_PROJECT = 'oldap:definedByProject'

    @property
    def toRdf(self):
        return self.value
