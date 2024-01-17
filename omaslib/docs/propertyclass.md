# PropertyClass

## Instantiation
A `PropertyClass` can be instantiated using the `constructor()` or using the `read()` class method. The first method using
the  constructor is only used when a *new* property should be created. In all other cases, the read class method is used
to create the form the data stored in the triple store. Reading combines the information from the
`<project-prefix>:shacl` and `<project-prefix>:onto`graphs.

### Constructor
The following example creates a `PropertyClass` instance using the constructor method.

_**NOTE**: It is important to note that
the instantiation of a `PropertyClass` does **not** create the property in the triple store! This has to be done
explicitely using the `create()` method_.


```python
props: PropertyClassAttributesContainer = {
    PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
    PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
    PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
    PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
    PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
        restrictions={PropertyRestrictionType.MAX_COUNT: 1}),
    PropertyClassAttribute.ORDER: 5,
}
p = PropertyClass(con=self._connection,
                  graph=NCName('test'),
                  property_class_iri=QName('test:testprop'),
                  attrs=props)
```

The Constructor is defined a follows:
```python
 def __init__(self, *,
               con: Connection,
               graph: NCName,
               property_class_iri: Optional[QName] = None,
               attrs: Optional[PropertyClassAttributesContainer] = None,
               notifier: Optional[Callable[[PropertyClassAttribute], None]] = None,
               notify_data: Optional[PropertyClassAttribute] = None):
    pass
```
has the following parameter which must be passed by name:

- _con_:
  This parameters requires a valid `Connection` instance that is connected to a triple store.
- _graph_:
  The graph parameters requires a `NCName` which contains the project prefix.
- _property_class_iri_:  
  This is a QName with the IRI that will identify this property
- _attrs_:
  A property may have many attributes which define the characteristics of the property. These attributes are
  passed as a `Dict` as defined by the data class 
  ```PropertyClassAttributesContainer = Dict[PropertyClassAttribute, PropTypes]```.
- _notifier_:
  An optional parameter which is used to pass a callable that is called whenever something is being changed in the
  definition of the notifier
- _notify_data_:
  An optional `PropertyClassAttribute` that will be passed to the notifier method when called.

The _notifier_ and _notifier_data_ are for internal use only and should not be used directly!

### PropertyClass Attributes

The following attributes are defined:
```python
@unique
class PropertyClassAttribute(Enum):
    SUBPROPERTY_OF = 'rdfs:subPropertyOf'
    PROPERTY_TYPE = 'rdf:type'
    TO_NODE_IRI = 'sh:class'
    DATATYPE = 'sh:datatype'
    RESTRICTIONS = 'omas:restrictions'
    NAME = 'sh:name'
    DESCRIPTION = 'sh:description'
    ORDER = 'sh:order'
```
The correspond to SHACL or OWL properties that are used to define the characteristics of a property shape.

#### NAME
This attribute defines a human readable name for the property that should be used in GUI's instead of the IRI.  
*NOTE*: The name is a `LangString`-instance in oder to give language dependent names, e.g.
```python
{
    ...
    PropertyClassAttribute.NAME: LangString(["Prénom@fr", "Vorname@de", "First name@en"]),
    ...
}
```

#### DESCRIPTION
A short description about the property. This attribute may for example be used in GUI to display a help popup when
the property is used in an input form. It also multilingual and thus must be a `LangString`.
```python
{
    ...
    PropertyClassAttribute.DESCRIPTION: LangString(["nom personnel donné à quelqu'un en plus de son nom de famille@fr", ...]),
    ...
}
```

#### ORDER
The order is hint that indicates the order in which the properties should be displayed in a GUI form. It is an
integer number. The following code would put the given property on the 3rd row in a entry form.
```python
{
    ...
    PropertyClassAttribute.ORDER: 3,
    ...
}
```

#### SUBPROPERTY_OF
In OWL allows to declare that a certain property is a sub-property of another proerty (which means that it is
more specialized). E.g. a *side-node* may be a specialized subproperty of a *comment* property. This declaration is
only defined in OWL and can be used for queries that will encompass all subproperties. E.g. the search for *comment*
will also return *side-note* properties. The Value of the *SUBPROPERTY_OF* must be a *QName* that identifies the
super-property.
```python
{
    ...
    PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
    ...
}
```
Above example defines the given property to be a sub-property of the *test:comment* property.

#### PROPERTY_TYPE
The attribute `PROPERTY_TYPE` is usually set automatically by the system. But it is possible to get its value. This
attribute sets the OWL type of the property, that is either `owl:DatatypeProperty` or `owl:ObjectProperty`.
The first indicates that the property points to a literal value, where as the latter requires the property to point
to a resource. The `PROPERTY_TYPE` can be accessed using the normal *Dict* syntax (assuming *prop* to be an instance
of PropertyClass)
```python
ptype = prop[PropertyClassAttribute.PROPERTY_TYPE]
```

#### DATATYPE
An attribute that defines the datatype of the property. This is a mandatory attributes (excpept when the `TO_NODE_IRI`)
is given. The following datatypes from the [XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/) are supported:

- XsdDatatypes.string = 'xsd:string'
- XsdDatatypes.boolean = 'xsd:boolean'
- XsdDatatypes.decimal = 'xsd:decimal'
- XsdDatatypes.float = 'xsd:float'
- XsdDatatypes.double = 'xsd:double'
- XsdDatatypes.duration = 'xsd:duration'
- XsdDatatypes.dateTime = 'xsd:dateTime'
- XsdDatatypes.dateTimeStamp = 'xsd:dateTimeStamp'
- XsdDatatypes.time = 'xsd:time'
- XsdDatatypes.date = 'xsd:date'
- XsdDatatypes.gYearMonth = 'xsd:gYearMonth'
- XsdDatatypes.gYear = 'xsd:gYear'
- XsdDatatypes.gMonthDay = 'xsd:gMonthDay'
- XsdDatatypes.gDay = 'xsd:gDay'
- XsdDatatypes.gMonth = 'xsd:gMonth'
- XsdDatatypes.hexBinary = 'xsd:hexBinary'
- XsdDatatypes.base64Binary = 'xsd:base64Binary'
- XsdDatatypes.anyURI = 'xsd:anyURI'
- XsdDatatypes.QName = 'xsd:QName'
- XsdDatatypes.normalizedString = 'xsd:normalizedString'
- XsdDatatypes.token = 'xsd:token'
- XsdDatatypes.language = 'xsd:language'
- XsdDatatypes.Name = 'xsd:name'
- XsdDatatypes.NCName = 'xsd:NCName'
- XsdDatatypes.NMTOKEN = 'xsd:NMTOKEN'
- XsdDatatypes.ID = 'xsd:ID'
- XsdDatatypes.IDREF = 'xsd:IDREF'
- XsdDatatypes.IDREFS = 'xsd: IDREFS'
- XsdDatatypes.integer = 'xsd:integer'
- XsdDatatypes.nonPositiveInteger = 'xsd:nonPositiveInteger'
- XsdDatatypes.negativeInteger = 'xsd:negativeInteger'
- XsdDatatypes.long = 'xsd:long'
- XsdDatatypes.int = 'xsd:int'
- XsdDatatypes.short = 'xsd:short'
- XsdDatatypes.byte = 'xsd:byte'
- XsdDatatypes.nonNegativeInteger = 'xsd:nonNegativeInteger'
- XsdDatatypes.unsignedLong = 'xsd:unsignedLong'
- XsdDatatypes.unsignedInt = 'xsd:unsignedInt'
- XsdDatatypes.unsignedShort = 'xsd:unsignedShort'
- XsdDatatypes.unsignedByte = 'xsd:unsignedByte'
- XsdDatatypes.positiveInteger = 'xsd:positiveInteger'

#### TO_NODE_IRI
This attribute indicates the ResourceClass the given property should point at. It automatically sets `PROPERTY_TYPE` to
`owl:ObjectProperty`.
```python
{
    ...
    PropertyClassAttribute.TO_NODE_IRI: QName('test:Person'),
    ...
}
```

#### RESTRICTIONS and PropertyRestcrion-Class
Restrictions is a compound attribute that itself of an instance of the `PropertyRestrictions` class. Property
restriction are rules that a property and it(s) value(s) must obey. The following restrictions are supported by
OMASLIB and defines as Enum `PropertyRestrictions(Enum)`:

- MIN_COUNT (sh:minCount, owl:cardinality, owl:minCardinality, owl:maxCardinality)
- MAX_COUNT = (sh:maxCount)
- LANGUAGE_IN (sh:languageIn)
- UNIQUE_LANG (sh:uniqueLang)
- IN = (sh:in)
- MIN_LENGTH (sh:minLength)
- MAX_LENGTH (sh:maxLength)
- PATTERN (sh:pattern)
- MIN_EXCLUSIVE (sh:minExclusive)
- MIN_INCLUSIVE (sh:minInclusive)
- MAX_EXCLUSIVE  (sh:maxExclusive
- MAX_INCLUSIVE (sh:maxInclusive)
- LESS_THAN  (sh:lessThan)
- LESS_THAN_OR_EQUALS (sh:lessThanOrEquals)

##### MIN_COUNT






