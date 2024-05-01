from enum import unique, Enum


@unique
class PermissionSetAttr(Enum):
    PERMISSION_SET_IRI = 'omas:permissionSetIri'  # virtual property, no equivalent in RDF
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    GIVES_PERMISSION = 'omas:givesPermission'
    DEFINED_BY_PROJECT = 'omas:definedByProject'

    @property
    def toRdf(self):
        return self.value
