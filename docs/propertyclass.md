# PropertyClass

Properties represent and important part of data modelling based on RDF: In triple of the form
```
object – predicate – subject
```
the _property_ represents the _predicate_. As such, the term _property_ is a sysnonym for _predicate_. However,
programmers tend to use the term _property_ instead of _predicate_. Programmers also use the term _resource_ for
the object, since it usually represents a digital _resource_ such as the digital representation (e.g. its metadata)
of a person, a book, or the URL of a digital facsimile, image, video etc.

In data modelling, a property is more than just a semantic definition: a property carries a lot of information about
the _subject_. Most of the information contains restrictions that the value of the property must fulfil. These
restrictions can (and are) validated in OLDAP when instance data is entered or changed. In general, these restrictions
encompass

- if the associated subject must be a _literal_ value
  - the data type of the literal
  - minimal, maximal limits
  - etc.
- or if the associated subject must be another object (resource)
  - What type of resource is allowed?

Restriction are passed to the constructor using the restrictionname. They can be accessed and modified as
"normal" Python-attributes of the PropertyClass instance!

If a _property_is used within the data modeling of a specific _resource_, a _property_ may carry more
information, such as

- the cardinality that is allowed/required
- the order in which the properties should be presented in a GUI
- etc.

The Python classes "PropertyClass" and "HasPropertyData" are used to represent RDF properties. It is important to note
that OLDAP distinguished between to use classes of properties:

- _standalone properties_: These are properties that are defined on their own without a direct connection/dependence
  on a resource. These property-definition may be __re-used__ for different resource classes.
- _associated properties_: These properties are defined within the context of a resource and can be only used within
  this specific resource.

Reusing properties for different resources looks like a good idea but should be applied carefully: The property
definition carries the _semantic meaning_. Therefore, when reusing properties, the semantic meaning _must_ be excately
the same in all cases!

## Instantiation
A `PropertyClass` can be instantiated using the `ProprtyClass(..)`-constructor or the `read()` class method. The first method using
the  constructor is only used when a *new* property should be created. In all other cases, the read class method is used
to create the form the data stored in the triple store. Reading combines the information from the
`<project-prefix>:shacl` and `<project-prefix>:onto`graphs.

### Constructor
The following examples create a _minimal_ `PropertyClass` instance with no restrictions using the constructor method.
The first example creates a `owl:DatatypeProperty` which points to a _literal value_.

```python
p1 = PropertyClass(con=self._connection,
                   project=self._project,
                   property_class_iri='test:testWrite3',
                   datatype=XsdDatatypes.string)
```

The second example create a `owl:ObjectProperty` which points to another resource class.

```python
p1 = PropertyClass(con=self._connection,
                   project=self._project,
                   property_class_iri='test:testWrite3',
                   toClass='test:MyResClass')
```

_**NOTE**: It is important to note that
the instantiation of a `PropertyClass` does **not** create the property in the triple store! This has to be done
explicitely using the `create()` method_.

## Property restrictions

### toClass (Iri)

This restriction is mandatory for properties that connect to another resource. Only instances of the given ResourceClass
(or subclasses thereof) are allowed!  

Example:
```python
p1 = PropertyClass(con=self._connection,
                   project=self._project,
                   property_class_iri='test:testWrite3',
                   toClass='test:MyResClass')
```
This example restricts the value range of this property to instances of MyResClass.

### datatype (XsdDatatypes)

This restriction is mandatory for properties that are used for literal values. It defines the datatype that the literal
value must have. OLDAP allows most Xsd datatypes.  

Example:
```python
p1 = PropertyClass(con=self._connection,
                   project=self._project,
                   property_class_iri='test:testWrite3',
                   datatype=XsdDatatypes.string)
```
This property requires Xsd_string data.

The Constructor is defined a follows:
```python
    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str | None = None,  # DO NOT USE
                 created: Xsd_dateTime | datetime | str | None = None,  # Do NOT USE
                 contributor: Iri | None = None,  # DO NOT USE
                 modified: Xsd_dateTime | datetime | str | None = None,  # DO NOT USE
                 project: Project | Iri | Xsd_NCName | str,
                 property_class_iri: Iri | str | None = None,
                 notifier: Callable[[PropClassAttr], None] | None = None,  # DO NOT USE
                 notify_data: PropClassAttr | None = None,  # DO NOT USE
                 **kwargs):
    pass
```

_kwargs_ can be additional attributes/restriction to the property
has the following parameter which must be _passed by name_:

- _con_:  
  This parameters requires a valid instance of a subclass of IConnection that is connected to a triple store.
- _property_class_iri_:  
  This is an Iri (fully qualified or as QName) with the IRI that will identify this property
- _kwargs_:  
  A property may have many attributes which define the characteristics of the property. The following attributes
  are allowed:  
    - _subPropertyOf_: [Iri] A property can be defined as a "subclass" of another property. Thus, the property will be a
    sub-property of the property given here. Let's assume a property `test:partOf` which defines that something is a
    part of something else. The property `test:pageOf` is a special case of `test:partOf` in the sense that of course
    a page of a book is a phyiscal part of that book. Thus, search patterns based on the super-property, e.g.
    `test:partOf` will also find `test:pageOf`.
      - _toClass_: [Iri] Defines the resource class the property connects to
      - _datatype_: [XsdDatatypes] The datatype of the literal the property represents
      - _name_: [LangString] The human readable name of the property
      - _description_: [LangString] A description of the semantics of the property
      - _languageIn_: [LanguageIn] In case of an Xsd_string literal this restricts the languages allowed to those listed here.
      - _uniqueLang_: [Xsd_boolean] Indicates that each language can occure only once. _**Note**: At the moment OLDAP allows
        only one item per language for all language sensitive strings (as if _uniqueLang_ is always True). This restriction
        may be removed in a future version of OLDAP.
      - _inSet_: [XsdSet] The value must be an element of the given set of valid values.
      - _minLength_: [Xsd_integer] Minimal length of a string value (currently only for datatype Xsd_string)
      - _maxLength_: [Xsd_integer] Maximal length of a string value (currently only for datatype Xsd_string)
      - _pattern_: [Xsd_string] A regex pattern that a string value must conform to
      - _minExclusive_: [Numeric] The numeric value must be greater than the value of this attribute
      - _minInclusive_: [Numeric] The numeric value must be greater or equal than the value of this attribute
      - _maxExclusive_: [Numeric] The numeric value must be less than the value of this attribute
      - _maxInclusive_, [Numeric] The numeric value must be less or equal than the value of this attribute
      - _lessThan_: [Iri] The numeric value must be less that the value of the given property
      - _lessThanOrEquals_: [Iri] The numeric value must be less or equal that the value of the given property


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
*Datatype*: `LangString`      
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
*Datatape*: `LangString`  
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
*Datatype*: `int`  
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
*Datatype*: `QName`  
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
*Datatype*: `QName`  
The attribute `PROPERTY_TYPE` is usually set automatically by the system. But it is possible to get its value. This
attribute sets the OWL type of the property, that is either `owl:DatatypeProperty` or `owl:ObjectProperty`.
The first indicates that the property points to a literal value, where as the latter requires the property to point
to a resource. The `PROPERTY_TYPE` can be accessed using the normal *Dict* syntax (assuming *prop* to be an instance
of PropertyClass)
```python
ptype = prop[PropertyClassAttribute.PROPERTY_TYPE]
```

#### DATATYPE
*Datatype*: `XsdDatatype`  
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
*Datatype*: `QName`  
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
*Datatype*: `PropertyRestrictions`  
Restrictions is a compound attribute that itself of an instance of the `PropertyRestrictions` class. Property
restriction are rules that a property and it(s) value(s) must obey. The following restrictions are supported by
oldaplib and defines as Enum `PropertyRestrictions(Enum)`:

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
*Datatype*: `int`  
Indicates the minimal cardinality a property must have. E.g. a `MIN_COUNT 1` indicates, that at least one instance
of the property must be present. The value is an integer number. Can be combined with *MAX_COUNT*.  
**NOTE**: The restriction *MIN_COUNT* also sets `owl:minCardinalty` in the OWL ontology for this property. If
*MIN_COUNT* is equal *MAX_COUNT*, `owl:cardinality` will be set!
```python
PropertyRestrictions(restrictions={PropertyRestrictionType.MAX_COUNT: 1})
```

#### MAX_COUNT
*Datatype*: `int`  
Indicates the maximal cardinalty a property must have. E.g. a `MAX_COUNT 1` indicates, that a property must occur only
once. The value is an integer number. Can be combined with *MIN_COUNT*  
**NOTE**: The restriction *MIN_COUNT* also sets `owl:maxCardinalty` in the OWL ontology for this property. If
*MAN_COUNT* is equal *MIX_COUNT*, `owl:cardinality` will be set!
```python
PropertyRestrictions(restrictions={PropertyRestrictionType.MIN_COUNT: 1})
```
#### LANGUAGE_IN
*Datatype*: `Set[Language]`  
This restriction enforces, that the given `string` property will only accept strings with the given language tags. The
value is a set of Language enums.
```python
PropertyRestrictions(restrictions={PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE}})
```
#### UNIQUE_LANG
*Datatype*: `bool`  
If set to `True`, the given `string` property will only accept one value per language tag.
PropertyRestrictions(restrictions={PropertyRestrictionType.UNIQUE_LANG: True})

#### IN
*Datatype*: `Set[]`  
Allow only values for the properties that are in the given set.
```python
PropertyRestrictions(restrictions={
    PropertyRestrictionType.IN: {
        "http://www.test.org/comment1",
        "http://www.test.org/comment2",
        "http://www.test.org/comment3"
    }
})
```
#### MIN_LENGTH
*Datatype*: `int`  
Requires that the value of the properties hat a length >= the given value. The value is a positive integer. 
Is often used for strings.
```python
PropertyRestrictions(restrictions={PropertyRestrictionType.MIN_LENGTH: 8})
```

#### MAX_LENGTH
*Datatype*: `int`  
Requires that the value of the properties hat a length <= the given value. The value is a positive integer. 
Is often used for strings.
```python
PropertyRestrictions(restrictions={PropertyRestrictionType.MAX_LENGTH: 32})
```

#### PATTERN
*Datatype*: `str`  
This restriction defines a regex pattern that the value (string) must conform to. THe value of this restriction must be
a regex expression as string
```python
PropertyRestrictions(restrictions={PropertyRestrictionType.PATTERN: "[A..Z]*"})
```

#### MIN_EXCLUSIVE

#### MIN_INCLUSIVE

#### MAX_EXCLUSIVE

#### MAX_INCLUSIVE

#### LESS_THAN

#### LESS_THAN_OR_EQUALS







