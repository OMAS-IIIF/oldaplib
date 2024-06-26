# Data Modeling

OLDAP is based on [Semantic Web](https://en.wikipedia.org/wiki/Semantic_Web)-technologies as described in the
[Introduction](/#introduction).

## Namespaces and Prefixes

In the Resource Description Framework(RDF), everything that is not a literal is denoted by a unique URN (**U**niform
**R**esource **N**ame). However, since writing/reading long URI's is combersume, the notion of `perfixes` and
`namespaces` have been introduced. A `namespace` is a URN that ends with a `#`- or `/ `-character. In these cases, a
[NCName](https://www.w3.org/TR/xmlschema-2/#NCName) can be _appended_ to such a URN. A NCName represents an
non-colonized name, which is simply a name that does not contain colons. An NCName  value must start with either a
letter or underscore ( `_` ) and may contain only letters, digits, underscores ( `_` ), hyphens ( `-` ), and periods ( `. `).

A `prefix` is a shortname (which must also follow the NCName rules) that stands for a namespace. If the prefix is
known to the system, a URN built using a namespace can be abbreviated with `prefx:name`. As an example we
define the namespae that should be used for the resources and predicates in a given project as follows (trig-format):

```trig
@PREFIX mypro: <http://myuniiversity.edu/mydep/myinst/myproi#> .
```
Then I can use `mypro:Painting` instead of `<http://myuniiversity.edu/mydep/myinst/myproi#Painting>`. Please note
that for SPARQL queries, the prefix should be included like follows:
```sparql
PREFIX mypro: <http://myuniiversity.edu/mydep/myinst/myproi#Painting>
```
There is no `@` before the PREFIX keyword and no `.` at the end.

## Properties (predicates)

Predicates or properties come in two different flavours: _Standalone_ properties and _private_ properties.
_Standalone_-properties are defined outside of any resource and therefore can be reused for different resource classes.
_Private_-properties are defined withing the context of a resource and can be used only for the specific resource.
Usually the private properties are preferred and
standalone properties should only be used if this results in significant advantages for the data model. The
reasons are as follows:

Each property is usually defined with a set of rules, e.g. the data type, the cardinality (e.g. how many times the
property may be used on one specific resource instance). These rules are usually bound to a given resource.
Other restrictions may be defined as a range of values, or in case of a property that
has als target another resource, the resource class must be indicated it must point to. Using _private_-properties offers
more options for such rules that can be used for the so-called _reasoning_ within the RDF database (which implements
predicate logic to make implicit information explicit)

### Private Properties
A private property is used (and defined) only in the context of a given resource class. For example, the properties
`myproj:firstName` and `myproj:lastName`, will and should be used only within the context of a resource class
`myproj:Person`. Since these properties are bound to a certain resource class, we can add additional information, e.g.
the order in which the properties should be displayed in an application. In addition, the property can be used for
reasoning. The statement ```myproj:xy myproj:firstName "Charlie Brown"```, implies to the reasoner that *myproj:xy"
is a *myproj:Person*. However, relying on such implicit information ca be challenging and difficult and should be
avoided if possible.

### Standalone Properties
Standalone properties are defined without an explicit relation to a specific resource class and therefor can be
reused in different resource classes. Let's assume a property `myproj:comment` is a standalone property. It could be
used to add a comment to different resource classes.

## Resource Classes
Resource classes represent classes of "real world" things (which may be abstract things such as en "event"). A
Resource Class has a unique IRI and a set of rules that define which properties an instance must or may have.

In other words, a resource class represents a real world _concept_ with all it properties. Thus we may define
a resource class `mypro:Person` with the following properties:

- `oldap:superclass` as `foaf:Person`. This identifies this class as a subclass of the _friend of a friend_-Person
- `foaf:givenName` as _xsd:string_, with a minimal cardinality of 1 (must be defined at least once)
- `foaf:familyName` as _xsd:string_, with a cardinality of exactly 1 (must be defined exactly once)
- `birthdate` as _xsd:date_, with a cardinality of exactly 1 (must be defined exactly once)
- `deathdate` as _xsd:date_, with a maximal cardinality 1 (may be defined only once)

Furthermore, we could define a _concept_ `mypro:Composer` which is a _subclass_ of `mypro:Person`. This means
that the _Composer_ inherits all properties of the _Person_ (it **is** also a _Person_), but has some other properties.
Thus we define `mypro:Composer`as follows:

- `oldap:superclass` as `oldap:Person`
- `mypro:composed` as _link_ to a `mypro:work` with a undefined cardinality (may occur never or multiple times)

Using this kind of definition/declaration, we are able to build a complex project specific _data model_ that may
be connected to standard ontologies such as `foaf`. Using OLDAP to create the data model, automatically there
will be both OWL and SHACL declarations created, which can be user for reasoning when querying the triple store or
for the validation of data based on SHACL.

## Data Model
A data model encompasses all definitions of property and resource classes that are defined for a specific project.
A data model as well as its constituents (properties, resources) can be created, read, updated and deleted
(CRUD-Operation) using the methods of the Python classes of oldaplib. 

# Data Modelling using OLDAP
An OMAS data modell consists of a series of declarations confirming to the SHACL standard within the
`<project-prefix>:shacl` named graph and corresponding declarations in OWL in the `<project-prefix>:onto` named
graph.

## Naming conventions
In oder to create unique IRI's, oldaplib adds the string "Shape" to the IRI's of properties and resources if used
in context of the SHACL shape definitions. oldaplib does add this automatically and the user should not be required to
deal with the "...Shape"-IRI's directly.

**IMPORTRANT:** All methods of oldaplib expect the IRI's to be given *without* the "Shape"-Extension!

NOTE: TEXT IST SEHR GUT ABER NOCH EIN BISSCHEN UNSTRUKTURIERT. MIR FEHLT NOCH ETWAS DER ROTE FADEN... GRAD AM SCHLUSS
HAT MAN ETWAS DAS GEFÜHL ES IST EINFACH EIN NAMENSAPPENDIX... ZUSÄTZLICH WÄRE EIN SCHLUSSKALITEL/SCHLUSSWORT SICHER NOCH GUT
 -- EVENTUELL KANN MAN DA NOCH WEITERE REFERENZEN AUFFÜHREN ODER NOCHMALS DIE WICHTIGSTEN REFERENZEN ZUSAMMENFASSEN.

