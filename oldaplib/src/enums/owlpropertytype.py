from enum import unique, Enum

from oldaplib.src.helpers.serializer import serializer


@unique
@serializer
class OwlPropertyType(Enum):
    """
    Enumeration of the two types of RDF properties that OWL distinguishes
    NOTE:
    """
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'
    StatementProperty = 'rdf:Property'

    @property
    def toRdf(self):
        return self.value
