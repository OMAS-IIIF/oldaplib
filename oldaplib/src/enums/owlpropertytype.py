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
    # _owl_transitive: bool  # :ancestorOf rdf:type owl:TransitiveProperty .
    # _owl_symmetric: bool  # :marriedTo rdf:type owl:SymmetricProperty .
    # _owl_reflexive: bool  # :equalTo rdf:type owl:ReflexiveProperty .
    # _owl_irreflexive: bool  # :parentOf rdf:type owl:IrreflexiveProperty .
    # _owl_functional: bool  # :hasBirthDate rdf:type owl:FunctionalProperty .
    # _owl_inverseFunctional: bool  # :hasSocialSecurityNumber rdf:type owl:InverseFunctionalProperty .
    # _owl_inverseOf: Xsd_QName  # :hasParent owl:inverseOf :hasChild .
    # _owl_equivalent: Xsd_QName  # :hasSpouse owl:equivalentProperty :marriedTo .

    @property
    def toRdf(self):
        return self.value
