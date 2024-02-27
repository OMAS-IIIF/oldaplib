# Introduction ot OMASLIB

OMASLIB implements several Python Classes which can be used to build a consistent, project specific data model in RDF,
usually implemented in a triplestore. The following terms are important:

- *Project* a project is any number of RDF statements that are associated with a certain topic/organisation
  that is called *Project* within OLDAP. *Users" (see below) may be member of one or more projects.  
  For each project, all data related RDF statements are collected in a *Named Graph* in the triple store.
- *User* is person that is registered as user. It gets access by providing its credentials (currently a
  password, but this may change in the future) on login. All Users have associated permissions which
  are connected to the association with a project. These permissions called *administrative permissions*.
- *Resources* are used to store data. All Resources are subclasses of `omas:Thing` which implements some
  basic properties like creator, creation date etc. (see below).
- *PermissionSet* is an entity that connects the resources to the user. A permission set holds the
  "DataPermissions" that define the access to the resource.

Data modeling relies on the notion of *property* and *resource* following the RDF standards.

- *Resource* is the digital equivalent to a real world object or an abstract thing like an event, a location
  etc. A Resource may have *properties* that define the properties of the subject.
- *Property* is a predicate defining some data associated with the resource.

In a datamodel, resources and properties are pre-defined and form the data model or *ontology* . Datamodels
are specific to a given project. Each datamodel is stroed in 2 distinct named graphs.

OMASLIB has the following prerequisites:

## The Resource Description Frame (RDF) and OLDAP

### What is RDF? (and RDFS, and OWL ?)

RDF is a way proposed be Tim Berners Lee to digitally represent information about real world objects or concepts.
It's also called *Linked Data* because it's main purpose is to represent such objects and their connections to each
other. Some standardized extensions like *RDF Schema* (RDFS) and the *Web Ontology Language* (OWL) allow to express
*concepts* about objects such as declaring that the *concept* "car" has 4 wheels and a steering wheel, and that it has
some kind of motor and can be driven from place A to B.

The smallest unit of information is a *statement* or *triple* which basically has the form
```subject - predicate - object```.
In order to uniquely identify the 3 parts,
[Uniform Resource Identifier](https://en.wikipedia.org/wiki/Uniform_Resource_Identifier) (URI) or *IRI's* (which are
URI's but allowing all international characters). The syntax of a URI/IRI is as follows:
```
scheme ":" ["//" authority] path ["?" query] ["#" fragment]
```
where

- _scheme_: denotes the scheme, e.g. `http`, `https`, `urn`, `ftp` (not used by RDF!), etc.
- _authority_: a unique name, usually in the form of a DNS name, e.g. `dhlab.unibas.ch`.
- _path_: The path can have different forms depending on the scheme:
  - _http(s)_: A typical path for a resource on the internet, e.g. `/a/b/c` or `/xxx/yyy/z/`. That is, it may
    end with a `/`-character or not (see below for further explanation when to use a trailing `/`)
  - _urn_: There is no _authority_. The path has parts separated be colons `:`.
- _query_: Usually *not used* within RDF
- _fragment_: an ID or name that consists only of characters, numbers and the `_`. It must start with a character
  or `_`. Such names are called _NCName_'s and will have there own datatype within OLDAP.

Examples:
- `https://www.example.com:123/forum/questions#top`
- `http://myproject.important.com/`
- `https://nowhere.edu`
- `http://does.not.exit.mil/secrets/`
- `urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b`

We are using the [TRIG](https://en.wikipedia.org/wiki/TriG_(syntax))-format to represent RDF triples. For more
information about this serialization format see also the
[W3C-article](https://www.w3.org/TR/2023/WD-rdf12-trig-20231104/).

The TRIG-format requires, that URI's are enclosed in `<`, `>` brackets. For a RDF statement/triple, the following rules
apply:

#### Subject

A subject als **always** represented as URI. If several statements apply to the _same_ subject, the _same_ URI must be
used. Thus, the subject-URI uniquely identifies a real world instance of an object or conecpt. The URI *may*
resolve – if entered to a webbrowser – to a web page describing the object/concept. But this resolution is absolutely
not required!

#### Predicate

The predicate describes a property of the subject. In order to use predicates in a consistent way, predicates are also
identified by URI's. The predicate must be used in a consistent manner. Usually the exatct meaning of the predicates is
defined in accompanying documents or – even - better directly within the data using RDF-Schema or OWL which define tools
for this purpose.  

It is important to note that a given predicate may expect either a _literal value_ or the _URI_ of another subject
as _object_ (see below). Thus, predicates that point to another subject describe some form a _relation_
between 2 subjects!

#### Subject

The Subject may come either as _literal value_, e.g. a number or a string, or it may be a _URI_ which identifies
another subject.

In RDF, literal values do have a _datatype_ which conforms to the datatypes defined by
[XML Schema](https://www.w3.org/TR/xmlschema-2/). The reason is that originally RDF as expressed as XML (RML/RDF).
However, XML/RDF is difficult and contra-intuitive and has been replaced by simple serialization formats such as
_turtle_ or _TRIG_ (our preferred way).

The datatype is added to the value as `^^xml-scheme-datatype`, e.g. `"This is a string"^^xsd:string` or
`"2024-02-26"^^xsd:date`. Please note that `xsd` is a _prefix_. Prefixes are discussed further below.

### Putting things together...
Now let's have an simple (oversimplyfied) example how to express information about things in RDF:

```trig
@PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> .

<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/predicates#givenName> "Lukas"^^xsd:string .
<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/predicates#familyName> "Rosenthaler"^^xsd:string .
<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/predicates#livesIn> <http://www.geonames.org/2661810/allschwil.html> .

<http://www.geonames.org/2661810/allschwil.html> <http://example.org/predicates#locName> "Allschwil"^^xsd:string .
<http://www.geonames.org/2661810/allschwil.html> <http://example.org/predicates#locKind> "Gemeinde"^^xsd:string .
```




## Named Graphs in OMASLIB
OMASLIB relies on the systematic use of **named graphs** which are used to separate the different areas and projects.

In triple stores, "named graphs" refer to a mechanism for organizing RDF (Resource Description Framework) data into
separate and distinct graph contexts. Each named graph is identified by a unique name or identifier, and it contains a
collection of RDF triples. 

Key points about named graphs:

- **Isolation:** Named graphs provide a way to isolate and partition RDF data, making it easier to manage and query
  specific subsets of data within a triple store.

- **Contextualization:** They allow for the contextualization of triples, associating them with a specific graph or
  dataset, which can be useful for representing data from different sources, versions, or sources.

- **Querying:** Named graphs enable queries that involve specific graphs or combinations of graphs, facilitating data
  retrieval and analysis within a triple store.

Named graphs play a crucial role in organizing and structuring RDF data, especially in scenarios where multiple
datasets or sources need to be represented and managed within a single triple store.

## Project Identifier

At the base of the graph structure there is the unique IRI that each project must have. The IRI must conform to
the syntax of a Namespace IRI, that is an IRI that either ends with a "#" or "/" character. In addition, a **prefix** for
this project-IRI must be defined and consistently being used. E.g. the following prefix declaration could be used:
```turtle

@prefix myproject: <http://www.myorgranisation.edu/myproject#> .
```

It is to note that the system itself uses the prefix identifier **omas** which **must not be used**!

For each project, there are 3 different graphs (assuming *projpre* as project prefix):

* `projpre:shacl`: This graph contains all the SHACl declarations
* `projpre:onto`: This graph contains all the OWL declaration
* `projpre:data`. This graphs contains the actual data

OMASLIB primarily deals with the first two, that is the SHACL and OWL declaration and allows to build and maintain a
consistent representation of a data model. Within the data model, resource class and properties which must follow
certain project-defined constraints are defined.

## Properties (predicates)

Predicates or properties can be defined in to different flavours. Usually the private properties are preferred and
standalone properties should only be used if this results in significant advantages for the data model. Each property
is defined with a set of rules, e.g. the data type, the cardinality (e.g. how many times the property may be used on
one specific resource instance). Other restrictions may be defined as a range of values, or in case of a property that
has als target another resource, the resource class must be indicated it must point to.

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

## Data Model
A data model encompasses all definitions of property and resource classes that are defined for a specific project.
A data model as well as its constituents (properties, resources) can be created, read, updated and deleted
(CRUD-Operation) using the methods of the Python classes of OMASLIB. 

# Data Modelling using OMAS
An OMAS data modell consists of a series of declarations confirming to the SHACL standard within the
`<project-prefix>:shacl` named graph and corresponding declarations in OWL in the `<project-prefix>:onto` named
graph.

## Naming conventions
In oder to create unique IRI's, OMASLIB adds the string "Shape" to the IRI's of properties and resources if used
in context of the SHACL shape definitions. OMASLIB does add this automatically and the user should not be required to
deal with the "...Shape"-IRI's directly.

**IMPORTRANT:** All methods of OMASLIB expect the IRI's to be given *without* the "Shape"-Extension!

