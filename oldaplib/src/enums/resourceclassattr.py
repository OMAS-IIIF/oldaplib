from enum import unique, Enum


@unique
class ResClassAttribute(Enum):
    SUBCLASS_OF = 'rdfs:subClassOf'
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    CLOSED = 'sh:closed'
