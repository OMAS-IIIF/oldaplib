import doctest
from enum import unique, Enum

from oldaplib.src.helpers.serializer import serializer


@unique
@serializer
class OwlPropertyType(Enum):
    """
    Enumeration of the two types of RDF properties that OWL distinguishes
    NOTE:
    """
    OwlAnnotationPropert = 'owl:AnnotationProperty'  # used to declare annotation with node further semantic meaning
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'
    TransitiveProperty = 'owl:TransitiveProperty'  # Safe inference ✅ no warning
    SymmetricProperty = 'owl:SymmetricProperty'  # Safe inference ✅ no warning
    ReflexiveProperty = 'owl:ReflexiveProperty'  # Complex inference ⚠ warning
    IrreflexiveProperty = 'owl:IrreflexiveProperty'  # Complex inference ⚠ warning
    FunctionalProperty = 'owl:FunctionalProperty'  # Identity-changing 🔥strong warning or even disabled by default
    InverseFunctionalProperty = 'owl:InverseFunctionalProperty'  # Identity-changing 🔥strong warning or even disabled by default

    @property
    def toRdf(self):
        return self.value

if '__main__' == __name__:
    gaga = OwlPropertyType.IrreflexiveProperty
    print(gaga.value)