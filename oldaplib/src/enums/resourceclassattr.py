from enum import unique, Enum


@unique
class ResClassAttribute(Enum):
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    CLOSED = 'sh:closed'
