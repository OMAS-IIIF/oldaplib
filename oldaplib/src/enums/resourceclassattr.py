from enum import unique, Enum


@unique
class ResClassAttribute(Enum):
    SUPERCLASS = 'oldap:superclass'  # virtual attribute, SHACL: sh:node, OWL: rdfs:subClassOf
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    CLOSED = 'sh:closed'
