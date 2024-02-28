from enum import unique, Enum


@unique
class PropertyClassAttribute(Enum):
    """
    Enumeration of all the attributes of a property. Please note that the `omas:restriction` attribute
    itself is a complex onbject defining restrictions to the property.
    The following attributes are defined:

    - `PropertyClassAttribute.SUBPROPERTY_OF`: The given property is a specialization of the property given here
    - `PropertyClassAttribute.PROPERTY_OF`: The given property is either a `owl:ObjectProperty` or
      a `owl:DataProperty`. These are important to create a correct OWL ontology. `owl:ObjectProperty`'s
      point to a resource, while `owl:DataProperty`'s point to literal value.
    - `PropertyClassAttribute.TO_NODE_IRI`: The given property points the a resource of the given class.
    - `PropertyClassAttribute.DATATYPE`: Th egiven property must be of the given data type (as defined by
      the XML datatypes. See [XsdDatatypes](xsd_datatypes).
    - `PropertyClassAttribute.RESTRICTION`: Restrictions the property and its values must follow
    - `PropertyClassAttribute.NAME`: Name of the property. The literal is a string that may have attached
      a language id.
    - `PropertyClassAttribute.DESCRIPTION`: Description of the property. The literal is a string that may
      have attached a language id.
    """
    SUBPROPERTY_OF = 'rdfs:subPropertyOf'
    PROPERTY_TYPE = 'rdf:type'
    TO_NODE_IRI = 'sh:class'
    DATATYPE = 'sh:datatype'
    RESTRICTIONS = 'omas:restrictions'
    NAME = 'sh:name'
    DESCRIPTION = 'sh:description'
    ORDER = 'sh:order'
