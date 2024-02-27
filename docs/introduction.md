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

### What is RDF? (and RDFS, and OWL)

RDF is a way proposed be Tim Berners Lee to digitally represent information about real world objects or concepts.
It's also called *Linked Data* because it's main purpose is to represent such objects and their connections to each
other. Some standardized extensions like *RDF Schema* (RDFS) and the *Web Ontology Language* (OWL) allow to express
*concepts* about objects such as declaring that the *concept* "car" has 4 wheels and a steering wheel, and that it has
some kind of motor and can be driven from place A to B.

The smallest unit of information is a *statement* or *triple* which basically has the form

```
subject predicate object .
```

In order to uniquely identify the 3 parts,
[Uniform Resource Identifier](https://en.wikipedia.org/wiki/Uniform_Resource_Identifier) (URI) or *IRI's* (which are
URI's but allowing international characters). The syntax of a URI/IRI is as follows:
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
- _fragment_: an ID or name that consists only of characters, digits and the `_`, `-`. `.`-characters.
  It must start with a character or `_`. Such names are called
  [NCName](https://docs.oracle.com/cd/E19509-01/820-6712/ghqhl/index.html)'s and will have there own Python datatype
  within OLDAP ([NCName](/python_docstrings/datatypes#NCName)).

Examples:

- `https://www.example.com:123/forum/questions#top`
- `http://myproject.important.com/`
- `https://nowhere.edu`
- `http://does.not.exit.mil/secrets/`
- `urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b`

We are using the [TRIG](https://en.wikipedia.org/wiki/TriG_(syntax))-format to represent RDF triples. For more
information about this serialization format see also the
[W3C-article](https://www.w3.org/TR/2023/WD-rdf12-trig-20231104/).

The TRIG-format requires URI's to be enclosed in `<`, `>` brackets. For a RDF statement/triple, the following rules
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

<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/datamodel#givenName> "Lukas"^^xsd:string .
<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/datamodel#familyName> "Rosenthaler"^^xsd:string .
<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/datamodel#livesIn> <http://www.geonames.org/2661810/allschwil.html> .
<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/datamodel#worksIn> <http://www.geonames.org/2661604/basel.html> .
<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/datamodel#worksIn> <http://www.geonames.org/2657976/windisch.html> .

<http://example.org/datamodel#Allschwil> <http://example.org/datamodel#geonameUrl> "http://www.geonames.org/2661810/allschwil.html"^^xsd:anyURI .
<http://example.org/datamodel#Allschwil> <http://example.org/datamodel#locName> "Allschwil"^^xsd:string .
<http://example.org/datamodel#Allschwil> <http://example.org/datamodel#locKind> "Gemeinde"^^xsd:string .

<http://example.org/datamodel#Basel> <http://example.org/datamodel#geonameUrl> "http://www.geonames.org/2661604/basel.html"^^xsd:anyURI .
<http://example.org/datamodel#Basel> <http://example.org/datamodel#locName> "Basel"^^xsd:string .
<http://example.org/datamodel#Basel> <http://example.org/datamodel#locKind> "Stadt"^^xsd:string .

<http://example.org/datamodel#Windisch> <http://example.org/datamodel#geonameUrl> "http://www.geonames.org/2657976/windisch.html"^^xsd:anyURI .
<http://example.org/datamodel#Windisch> <http://example.org/datamodel#locName> "Windisch"^^xsd:string .
<http://example.org/datamodel#Windisch> <http://example.org/datamodel#locKind> "Gemeinde"^^xsd:string .
```
The above example is the (very verbose) way to express the following things:  

The subject "`<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b>`"

- is something that has a `<http://example.org/datamodel#givenName>` with a value "Lukas"
- is something that has a `<http://example.org/datamodel#familyName>` with a value "Rosenthaler"
- has a connection to `<http://example.org/datamodel#Allschwil>` named `<http://example.org/predicates#livesIn>`
- has connections to `<http://example.org/datamodel#Basel>` and `<http://example.org/datamodel#Windisch>`
  named `<http://example.org/datamodel#worksIn>`
- etc.

*It is important to note that each statement must be terminated by a `.`!*

The TRIG-Format now allows some syntactic sugar to make above statements a bit simpler:
```trig
@PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> .

<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> <http://example.org/datamodel#givenName> "Lukas"^^xsd:string ;
                                                <http://example.org/datamodel#familyName> "Rosenthaler"^^xsd:string ;
                                                <http://example.org/datamodel#livesIn> <http://example.org/datamodel#Allschwil> ;
                                                <http://example.org/datamodel#worksIn> <http://example.org/datamodel#Basel>, <http://example.org/datamodel#Windisch> .

<http://example.org/datamodel#Allschwil> <http://example.org/datamodel#geonameUrl> "http://www.geonames.org/2661810/allschwil.html"^^xsd:anyURI ;
                                         <http://example.org/datamodel#locName> "Allschwil"^^xsd:string ;
                                         <http://example.org/datamodel#locKind> "Gemeinde"^^xsd:string .

<http://example.org/datamodel#Basel> <http://example.org/datamodel#geonameUrl> "http://www.geonames.org/2661604/basel.html"^^xsd:anyURI ;
                                     <http://example.org/datamodel#locName> "Basel"^^xsd:string ;
                                     <http://example.org/datamodel#locKind> "Stadt"^^xsd:string .

<http://example.org/datamodel#Windisch> <http://example.org/datamodel#geonameUrl> "http://www.geonames.org/2657976/windisch.html"^^xsd:anyURI ;
                                        <http://example.org/datamodel#locName> "Windisch"^^xsd:string ;
                                        <http://example.org/datamodel#locKind> "Gemeinde"^^xsd:string .
```
The `;` indicates that the next statement is for the same subject, the `,` indicates, that the next object attached to
the same subject-predicate combination. Still, this notation is not easy to read/write for humans.

Fortunately, the
TRIG format has some tools to simplify these stemenents drastically and make them easy to read/write:

#### Prefixes, Namespaces and QNames

Usually, URI's are named in as systematic ways. Related "things" may share a commen "base"-URI. In our example above
we find that most predicates start with `http://example.org/predicates#` (*Note the `#` at the end!*). These common
parts may be defined as _prefix_, a kind of shortcuts. The prefix must be a XML
[NCName](https://docs.oracle.com/cd/E19509-01/820-6712/ghqhl/index.html), that is
again a string that contains only characters, digits, the `_`, `-`, `.` and start with a character or "_". (See
[NCName](/python_docstrings/datatypes#NCName) for Python class). Such a Prefix defines a `namespace`. Often related
definitions of subjects and predicates share a common preofx. They are said to be in the same Namespace. With this
knowledge, out example may further be simplified:

```trig
@PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> .
@PREFIX ex:  <http://example.org/datamodel#> .

<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> ex:givenName "Lukas"^^xsd:string ;
                                                ex:familyName "Rosenthaler"^^xsd:string ;
                                                ex:livesIn ex:Allschwil ;
                                                ex:worksIn ex:Basel, ex:Windisch .

ex:Allschwil ex:geonameURL "http://www.geonames.org/2661810/allschwil.html"^^xsd:anyURI ;
             ex:locName "Allschwil"^^xsd:string ;
             ex:locKind "Gemeinde"^^xsd:string .

ex:Basel ex:geonameURL "http://www.geonames.org/2661604/basel.html"^^xsd:anyURI ;
         ex:locName "Basel"^^xsd:string ;
         ex:locKind "Stadt"^^xsd:string .

ex:Windisch ex:geonameURL "http://www.geonames.org/2657976/windisch.html"^^xsd:anyURI ;
            ex:locName "Windisch"^^xsd:string ;
            ex:locKind "Gemeinde"^^xsd:string .
```

As you will notice in the example above, the URI's in the form `<....>` have been replaced by an expression
`prefix:fragment` without the `<`, `>` brackets, a so called *qualified name* or *QName*.

*Important notes*:

- Above notation with *QName*'s can be used for subjects, predicates and objects!.
- For the URN-based URI's, there is no QName equivalent, since the URN-path is built using the `:` character!*

Both the *prefix* and the *fragment* are *NCName*. Also,  _QName_ has a Python representation
[QName](/python_docstrings/datatypes#QName)). As we understand now, the `xsd:string` to indicate the datatype is
also a *QName* –– therefore we need to use the prefix definition `@PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> .`

#### Ontologies and Namespaces

An RDF ontology is a formal description of a given knowledge domain, using RDF. It defines the meaning and the
relations (**semantics**). In order to do so, specific subjects and predicates have been defined which baer a
pre-defined meaning. Most ontologies rely on RDF-Schema and (partially) OWL. The prefixes/namespaces used are:

```trig
@PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@PREFIX owl: <http://www.w3.org/2002/07/owl#> .
```

It beyond the scope of this introduction to completeley descibe RDF-based ontologies, but let's have a brief look on
how an ontology is created in RDF/RDFS/OWL.
Let's assume – as in the example above – that we would like to define an Ontology about persons where we would like to
know the names, where he/she lives and works. The Namespace should be `http://my.org/ontology#`. We decide here,
to use the fragment indicator a s separator (we could instead choose to use `/` which is basically equivalent). Thus,
we use the prefix `@PREFIX mo: <http://my.org/ontology#> .`
First we define a new *class* of subjects, called *Person*:

`mo:Person rdf:type owl:Class .`

This allows us to express with `ex:DDuck rdf:type mo:Person .` that the subject `ex:DDuck` represents a person. Now
let's define a few predicates for Person:

```trig
@PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@PREFIX owl: <http://www.w3.org/2002/07/owl#> .
@PREFIX mo:  <http://my.org/ontology#> .

# define subject mo:Person
mo:Person rdf:type owl:Class .

# define subject mo:Location
mo:Location rdf:type owl:Class .

# define data properties (point to literals)
mo:familyName rdf:type owl:DatatypeProperty .
mo:givenName rdf:type owl:DatatypeProperty .

mo:geonameURL rdf:type owl:DatatypeProperty .
mo:locName rdf:type owl:DatatypeProperty .
mo:locKind rdf:type owl:DatatypeProperty .

# define object properties (point to other subject)
mo:livesIn rdf:type owl:ObjectProperty .
mo:worksIn rdf:type owl:ObjectProperty .
```

With these definitions, we have a minimal characterization and we can define the data:

```trig
@PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@PREFIX owl: <http://www.w3.org/2002/07/owl#> .
@PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> .
@PREFIX mo:  <http://my.org/ontology#> .
@PREFIX ex:  <http://example.org/datamodel#> .

<urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b> rdf:type mo:Person ;
                                                mo:givenName "Lukas"^^xsd:string ;
                                                mo:familyName "Rosenthaler"^^xsd:string ;
                                                mo:livesIn mo:Allschwil ;
                                                mo:worksIn mo:Basel, mo:Windisch .

mo:Allschwil rdf:type mo:Location ;
             mo:geonameURL "http://www.geonames.org/2661810/allschwil.html"^^xsd:anyURI ;
             mo:locName "Allschwil"^^xsd:string ;
             mo:locKind "Gemeinde"^^xsd:string .

mo:Basel rdf:type mo:Location ;
         mo:geonameURL "http://www.geonames.org/2661604/basel.html"^^xsd:anyURI ;
         mo:locName "Basel"^^xsd:string ;
         mo:locKind "Stadt"^^xsd:string .

mo:Windisch rdf:type mo:Location ;
            mo:geonameURL "http://www.geonames.org/2657976/windisch.html"^^xsd:anyURI ;
            mo:locName "Windisch"^^xsd:string ;
            mo:locKind "Gemeinde"^^xsd:string .
```
Using additional RDF/RDFS/OWL properties we can even add more semantic information to the ontology:

```trig
@PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@PREFIX owl: <http://www.w3.org/2002/07/owl#> .
@PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> .
@PREFIX mo:  <http://my.org/ontology#> .

# define subject mo:Person
mo:Person rdf:type owl:Class ;
          rdfs:label "Person" ;
          rdfs:comment "A human being..." .

# define subject mo:Location
mo:Location rdf:type owl:Class ;
            rdfs:label "Location" ;
            rdfs:comment "A geographical location with a name" .

# define data properties (point to literals)
mo:familyName rdf:type owl:DatatypeProperty ;
              rdfs:label "Family name" ;
              rdfs:comment "The famile name, last name etc." ;
              rdfs:domain mo:Person ;
              rdfs:range xsd:string .

mo:givenName rdf:type owl:DatatypeProperty ;
             rdfs:labal "Given name" ;
             rdfs:comment "The given name for the person (frist name)" ;
             rdfs:domain mo:Person ;
             rdfs:range xsd:string .

mo:geonameURL rdf:type owl:DatatypeProperty ;
              rdfs:label "Geoname URL" ;
              rdfs:comment "URL for the location on http://geonames.org" ;
              rdfs:domain mo:Location ;
              rdfs:range xsd:anyIRI .
                          

mo:locName rdf:type owl:DatatypeProperty ;
           rdfs:label "Location name" ;
           rdfs:comment "Name of the location" ;
           rdfs:domain mo:Location ;
           rdfs:range xsd:string .

mo:locKind rdf:type owl:DatatypeProperty .

# define object properties (point to other subject)
mo:livesIn rdf:type owl:ObjectProperty ;
           rdfs:label "Lives in" ;
           rdfs:comment "The location the person lives in" ;
           rdfs:domain mo:Person ;
           rdfs:range mo:Location .

mo:worksIn rdf:type owl:ObjectProperty ;
           rdfs:label "Works in" ;
           rdfs:comment "The location the person works in" ;
           rdfs:domain mo:Person ;
           rdfs:range mo:Location .
```

This Ontology gives quite a lot of semantic information about the relation between `mo:person`, `mo:Location` and the
data predicates that point to literal values. We have been using additional RDFS predicates:

- `rdfs:label`: The human readable "name" this element has. Should be displayed instead of the URI if the data is
  is prepared for human reading.
- `rdfs:comment`: A description/comment string that describes the purpose/semantics of the given element for humans.
- `rdfs:domain`: The subject class a predicate is used for. E.g. `mo:worksIn rdfs:domain mo:Person` tells the query
  system of the triple store that the subject is a `mo:Person`.
- `rdfs:range`: The object of the predicate has a certain data type or points to a certain subject class.

It's important to note that `rdfs:domain` and `rdfs:range` are **not restrictions**! The just let the query engine
know if it encounters a certain predicate what's on the left and right side of it. If a predicate is beeing used
incorrectly the query engine may make wrong assumptions. Example:

```trig
...
 
wrong:Book rdf:type owl:Class .
wrong:Page rdf:type owl:Class .

wrong:inBook rdf:type owl:ObjectProperty ;
             rdfs:domain wrong:Page ;
             rdfs:range wrong:Book .

wrong:comment rdf:type owl:DatatypeProperty ;
              rdf:domain wrong:Book ;
              rdfs:range xsd:string .

#
# ...and now the BIG BIG error
#
ex:titlepage rdf:type wrong:Page ;
             wrong:comment "Title page with beautiful illustration" .
```

The query engine knows that the subject of `wrong:comment` is a book. Therefore it registers that `ex:titlepage` is
also a `wrong:Book`. A query for all books will result erroneously return also `wrong:titlepage`!

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

