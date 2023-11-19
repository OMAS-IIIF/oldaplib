from enum import unique, Enum


@unique
class ResourceClassAttribute(Enum):
    SUBCLASS_OF = 'rdfs:subClassOf'
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    CLOSED = 'sh:closed'
