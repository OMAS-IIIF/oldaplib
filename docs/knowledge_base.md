# Knowledge Foundation for OMASLIB

OLDAP implements several Python Classes which can be used to build a consistent, project specific data model in RDF,
usually implemented in a triplestore. The following terms are important:

- ***Project***: A project is defined as a collection of RDF statements that are associated with a certain topic/organisation
  that is called *Project* within OLDAP. *Users* (see below) may be member of one or more projects.  
  For each project, all data related RDF statements are collected in a *Named Graph* in the triple store.
- ***User***: A user is a person who is registered with the system as a user. They gain access by providing their credentials
  (currently a password, though this may change in the future) upon login. Each user is granted specific permissions based on 
  their association with a project. These permissions, known as *administrative permissions*, define what actions a user is 
  authorized to perform within the system.
- ***Resources*** are used to store data. All Resources are subclasses of `omas:Thing` which implements some
  basic properties like creator, creation date etc. (see below).
- ***PermissionSet*** is an entity that connects the resources to the user. A permission set holds the
  "DataPermissions" that define the access to the resource.

Data modeling relies on the notion of *property* and *resource* following the RDF standards.

- ***Resource*** is the digital equivalent to a real world object or an abstract thing like an event, a location
  etc. A Resource may have *properties* that define the properties of the subject.
- ***Property*** is a predicate defining some data associated with the resource.

In a datamodel, resources and properties are pre-defined and form the data model or *ontology*. Datamodels
are specific to a given project. Each datamodel is stroed in 2 distinct named graphs.

OMASLIB has the following prerequisites:

## The Resource Description Frame (RDF) and OLDAP

### What is RDF? (and RDFS, and OWL)

RDF was proposed by Tim Berners Lee and is a way to digitally represent information about real world objects or concepts.
It's also called *Linked Data* because it's main purpose is to represent such objects and their connections to each
other. Some standardized extensions like *RDF Schema* (RDFS) and the *Web Ontology Language* (OWL) allow to express
*concepts* about objects such as declaring that the *concept* "car" has 4 wheels, a steering wheel, that it has
some kind of motor and that it can be driven from place A to B.

The smallest unit of information is a *statement* or *triple* which basically has the form

```text
subject - predicate - object .
```

In order to uniquely identify the 3 parts,
[Uniform Resource Identifier](https://en.wikipedia.org/wiki/Uniform_Resource_Identifier) (URI) or *IRI's* (which are
URI's but allowing international characters) are used. The syntax of a URI/IRI is as follows:
```text
scheme ":" ["//" authority] path ["?" query] ["#" fragment]
```
where

- _scheme_: denotes the scheme, e.g. `http`, `https`, `urn`, `ftp` (ftp not used by RDF!), etc.
- _authority_: a unique name, usually in the form of a DNS name, e.g. `dhlab.unibas.ch`.
- _path_: The path can have different forms depending on the scheme:
    - _http(s)_: A typical path for a resource on the internet, e.g. `/a/b/c` or `/xxx/yyy/z/`. That is, it may
    end with a `/`-character or not (see below for further explanation when to use a trailing `/`)
      - _urn_: There is no _authority_. The path has parts separated be colons `:`.
- _query_: Usually *not used* within RDF
- _fragment_: an ID or name that consists only of characters, digits and the `_`, `-`. `.`-characters.
  It must start with a character or `_`. Such names are called
  [NCName](https://docs.oracle.com/cd/E19509-01/820-6712/ghqhl/index.html)'s and will have there own Python datatype
  within OLDAP ([NCName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.NCName)).

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

A subject is **always** represented as URI. If several statements apply to the _same_ subject, the _same_ URI must be
used. Thus, the subject-URI uniquely identifies a real world instance of an object or concept. The URI *may*
resolve – if entered to a webbrowser – to a web page describing the object/concept. But this resolution is absolutely
not required!

#### Predicate

The predicate describes a property of the subject. In order to use predicates in a consistent way, predicates are also
identified by URI's. The predicate must be used in a consistent manner. Usually the exact meaning of the predicates is
defined in accompanying documents or – even – better directly within the data using RDF-Schema. RDF-Schema has two
predefined properties, `rdfs:label` and `rdfs:comment` for documentation purposes.

- `rdfs:label`: The human understandable *name* given to something (a subject, property etc.). RDF language tags may
  be used to indicate the name in different languages
- `rdfs:comment`: A comment or description of the meaning of the subject, predicate etc. Here also, language tags
  may be used.

Example:

```trig
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

mydata:Person a owl:class ;
    rdfs:label "Person"@en, "Person"@de, "Personne"@fr, "Persona"@it ;
    rdfs:comment "A Human being that can be identified uniquely, e.g. by a VIAF id or other norm data"@en,
        "Ein Mensch, der eindeutig identifizierbar ist, z.B. durch eine VIAF Id oder andere Normdaten"@de :
    ...
```

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
Now let's have a simple (oversimplyfied) example how to express information about things in RDF:

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
The `;` indicates that the next statement is for the same subject, the `,` indicates, that the next object is attached to
the same subject-predicate combination. Still, this notation is not easy to read/write for humans.

Fortunately, the
TRIG format has some tools to simplify these statements drastically and make them easy to read/write:

#### Prefixes, Namespaces and QNames

<a name="namespace"></a>
Usually, URI's are named in a systematic way. Related "things" may share a commen "base"-URI. In our example above
we find that most predicates start with `http://example.org/predicates#` (*Note the `#` at the end!*). These common
parts may be defined as ***prefix***, a kind of shortcuts. The prefix must be a XML
[NCName](https://docs.oracle.com/cd/E19509-01/820-6712/ghqhl/index.html), that is
again a string that contains only letters, digits, the `_`, `-`, `.` signs and start with a letter or "_". (See
[NCName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.NCName) for Python class). Such a *prefix* defines a `namespace`. Often related
definitions of subjects and predicates share a common prefix. They are said to be in the same **Namespace**. With this
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

- Above notation with *QName*'s can be used for subjects, predicates and objects.
- For the URN-based URI's, there is no QName equivalent, since the URN-path is built using the `:` character.

Both the *prefix* and the *fragment* are *NCName*. Also,  _QName_ has a Python representation
[QName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.QName). As we understand now, the `xsd:string` to indicate the datatype is
also a *QName* –– therefore we need to use the prefix definition `@PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> .`

#### Ontologies and Namespaces

An RDF ontology is a formal description of a given knowledge domain, using RDF. It defines the meaning and the
relations (**semantics**) of and between objects. In order to do so, specific subjects and predicates have been defined which baer a
pre-defined meaning. Most ontologies rely on RDF-Schema and (partially) OWL. The prefixes/namespaces used by RDF-Schema and OWL are:

```trig
@PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@PREFIX owl: <http://www.w3.org/2002/07/owl#> .
```

It is beyond the scope of this introduction to completeley descibe RDF-based ontologies, but let's have a brief look on
how an ontology is created in RDF/RDFS/OWL.

Let's assume – as in the example above – that we want to define an Ontology about persons where we would like to
know the names, where he/she lives and works. The Namespace we choose is `http://my.org/ontology#` (we are free to use
an arbitrary IRI as namespace – however it should be unique and must end with `#` or `/`).  We decide here,
to use the fragment indicator as separator (we could instead choose to use `/` which is basically equivalent). Thus,
we use the prefix `@PREFIX mo: <http://my.org/ontology#> .`
First we define a new *class* of subjects, called *Person*:

`mo:Person rdf:type owl:Class .`

This allows us to express with `ex:DDuck rdf:type mo:Person .` that the subject `ex:DDuck` represents a person. Now
let's define a few predicates for Person – or in other words a minimal ontology:

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

- `rdfs:label`: The human readable "name" of the given element. It should be displayed instead of the URI if the data
  is intended for human reading.
- `rdfs:comment`: A description/comment string that describes the purpose/semantics of the given element for humans.
- `rdfs:domain`: The rdfs:domain of a property specifies the class of the subject in a triple that uses the property.
  In simpler terms, it tells you what type of thing (or "entity") can possess or be described by the property in
  question. If a property is stated to have a certain rdfs:domain, then any resource that has that property is
  automatically assumed to be a member of the specified class.  
  Example: If we have a property `:hasOwner`, and we declare that its rdfs:domain is `:Vehicle`, this means that anything
  that "has an owner" is considered to be a Vehicle. So, if we know that `:Car123 :hasOwner "John"`, we can infer that `:Car123`
  is a Vehicle.
- `rdfs:range`: The *range* denotes the "right side" of a predicate, that is the type of the *object*. For literal values,
  the *range* denotes usually the data type, e.g. `ex:my_predicate rdfs:range xsd:int` defines that *ex:my_predicate*
  points to a literal which is an integer number. For predicates that point to another subject, *rdfs:range*
  indicates the subject class it should point to, e.g. the statement `ex:hasPainted rdfs:range ex:Painting`. This would
  indicate that *ex:hasPainted* points to a subject of the class *ex:Painting*. Thus, the query engine
  will infer from the statement `ex:davinci ex:hasPainted ex:MonaLisa` that `ex:MonaLisa` is a painting.

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

The query engine knows that the subject of `wrong:comment` is a book. Therefore, it realises that `ex:titlepage` is
also a `wrong:Book`. A query for all books will erroneously return also `wrong:titlepage`!

### Named Graphs in OMASLIB
RDF allows to group statements into named entities called *named graphs*. Thus, using named graphs, a triple becomes in
fact a quadruple, since, in addition to the subject, predicate and object, it's associated with a graph name as well.
The graph name can be used in queries. Usually there is
a *default* named graph for all triples that is not assigned explicitely to a named graph. Some triple store such as Ontotext's
GraphDB assigns all triples to the default graph if no graph name is given at creation indicated. For more information about
named graphs see:

- [Named Graphs - Wikipedia](https://en.wikipedia.org/wiki/Named_graph)
- [levelUp](https://levelup.gitconnected.com/working-with-rdf-database-named-graphs-a5ddab447e91) (specific for GraphDB and Stardog triple stores)

For example, the following triples will be in the default graph, since no specific graph name is given:
```trig
@PREFIX ex: <http://example.org/ex#> .
ex:davinci a ex:Painter ;
           ex:hasPainted ex:MonaLisa, ex:LastSupper .
```
The equivalent SPARQL insert statement would look as follows:
```sparql
PREFIX ex: <http://example.org/ex#>
INSERT DATA {
    ex:davinci a ex:Painter ;
             ex:hasPainted ex:MonaLisa, ex:LastSupper . 
}
```
However, if we want to put these triples into a graph names `<http://example.org/ex#data>` (or using a
prefix for a "short" graph name `ex:data`), the statements will be:
```trig
@PREFIX ex: <http://example.org/ex#> .
ex:data {
    ex:davinci a ex:Painter ;
               ex:hasPainted ex:MonaLisa, ex:LastSupper .

}
```
The equivalent SPARQL insert statement would look as follows:
```sparql
PREFIX ex: <http://example.org/ex#>
INSERT DATA {
    GRAPH ex:data {
        ex:davinci a ex:Painter ;
            ex:hasPainted ex:MonaLisa, ex:LastSupper .
    }
}
```

`OMASLIB relies on the systematic use of **named graphs** which are used to separate the different areas and projects.`

In triple stores, "named graphs" refer to a mechanism for organizing RDF (Resource Description Framework) data into
separate and distinct graph contexts. Each named graph is identified by a unique name or identifier, and it contains a
collection of RDF triples. 

Key points about named graphs are:

- **Isolation:** Named graphs provide a way to isolate and partition RDF data, making it easier to manage and query
  specific subsets of data within a triple store.

- **Contextualization:** They allow for the contextualization of triples, associating them with a specific graph or
  dataset, which can be useful for representing data from different sources, versions, or sources.

- **Querying:** Named graphs enable queries that involve specific graphs or combinations of graphs, facilitating data
  retrieval and analysis within a triple store.

Named graphs play a crucial role in organizing and structuring RDF data, especially in scenarios where multiple
datasets or sources need to be represented and managed within a single triple store.

## OLDAP Python classes to work with RDF

### Context

The Python class ***Context*** manages the prefixes that are used in TRIG/SPARQL statements. It also contains methods
to convert *AnyIRI*'s to *QNames* and vice versa. A Context simulates a [*Dict*](https://www.w3schools.com/python/python_dictionaries.asp) where the *prefixes* are the *keys* and
the full *NamespaceIRI*'s are the *values*. Context are iterable. The keys must be *NCName*s and the values of the dict
must be *NamespaceIRI*s.

Context are created with a freely selectable name. **A Context with a given name is a persistent [singleton](https://en.wikipedia.org/wiki/Singleton_pattern)!**
It implements the following methods (a complete documentation from the python doc strings can found at
[Context](/python_docstrings/context)):

- `Context(name: str)`: Constructs (or returns) a Context singleton with the given name.
- ` ns = context[NCName("prefix")]`: Returns the associated *NamespaceIRI*. Throws an `OmasError` if the key does not exist.
- `context[NCName("prefix")] = ns`: Adds (or replaces) the prefix/namespace pair to the "Dict".
- `del context[NCName("prefix")]`: Deletes the given prefix/namespace pair. Throws an `OmasError` if the Key does not exist.
- `context.items()`: Used for iteration. Returns iterator, e.g. `for prefix, nsiri in context.items()`.
- `iri2qname(iri: str | NamespaceIRI) -> QName`: Converts a Namespace IRI into a QName.
- `qname2iri(qname: QName | str) -> NamespaceIRI`: Converts a qname into a full NamespaceIRI.
- `sparql_context() -> str`: Returns a multiline string with all the prefixes defines as it is used for SPARQL queries.
- `turtle_context(self) -> str`: Returns a multiline string with all the prefixes defines as it is used for TRUTLE/TRIG statements.
- `in_use(name: str) -> bool`: A classmethod to check if there is already a Context with the given name.

The Context class implements automatically the following prefixes:

- `rdf`: http://www.w3.org/1999/02/22-rdf-syntax-ns#
- `rdfs`: http://www.w3.org/2000/01/rdf-schema#
- `owl`: http://www.w3.org/2002/07/owl#
- `xsd`: http://www.w3.org/2001/XMLSchema#
- `xml`: http://www.w3.org/XML/1998/namespace#
- `sh`: http://www.w3.org/ns/shacl#
- `skos`: http://www.w3.org/2004/02/skos/core#
- `dc`: http://purl.org/dc/elements/1.1/
- `dcterms`: http://purl.org/dc/terms/
- `foaf`: http://xmlns.com/foaf/0.1/
- `omas`: http://omas.org/base#

#### Example

```python
context = Context("MyOwnContext")
# Add my new namespace
context[NCName("my_ns")] = NamespaceIRI("http://my.own.project.org/my_ns/")
...
sparql = context.sparql_context
sparql += "SELECT ?s WHERE { ?s rdf:type my_ns:Catalogue }"
jsonres = connection.query(sparql)
...

# below will return the same context. "my_ns" is already defined for context2!
context2 = Context("MyOwnContext")
```
In above example, the sparql string that is being sent to the query will be as follows:
```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX xml: <http://www.w3.org/XML/1998/namespace#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX omas: <http://omas.org/base#>
PREFIX my_ns: <http://my.own.project.org/my_ns/>
SELECT ?s WHERE { ?s rdf:type my_ns:Catalogue }
```

### NCName

As we learned, a *NCName* is a string that contains only letters, digits, the `_`, `-`, `.` symbols and starts with a
letter. In order to enforce and validate such strings, the *NCName* class is used. It throws an `OmasErrorValue` if the
string does not conform to the XML schema for QName. It has the following methods
(not complete - full documentation from docstrings [NCName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.NCName)):

- `NCName(value: Self | str)`: The Constructor takes a NCName or a str as parameter. It validates the string to
  conform to the syntax of NCName's as defined by the XML Datatype schema.
- `str(a_ncname)`: Returns the string representation of the NCName as str.
-  `repr(a_ncname)`: Returns the RDF representation including datatype as string that can directly inserted into a
  TRIG file or SPARQL query. Example:  
  `x = NCName("a_ncname42"); rdf = repr(x)  # -> "a_ncname"^^xsd:NCName`
- Supports comparison operations `==`, `!=` and the `hash()`. Thus, a NCName may be used as key in a Dict.
- It implements the serializer-protocol for conversion to/from JSON (*Note*: If a Dict uses NCName, the resulting
  Dict cannot be serialized. The JSON methods require the key to be a real str!).

#### Example

```python
id = NCName("coyote")
...
sparql = f"INSERT DATA {{ my_ns:Hero my_ns:hasId {repr(id)} . }}"
# --> INSERT DATA { my_ns:Hero my_ns:hasId "coyote"^^xsd:NCName . }
```
### QName

A QName has the form `ncname_a:ncname_b` where the *ncname_a* is the *prefix* and the *ncname_b* is the fragment. The
class QName has the following methods (full documentation from docstrings: [QName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.QName)).
It throws an `OmasErrorValue` if the string does not conform to the XML scxhema for QName. The following usages are possible:

- `QName(value: Self | str | NCName, fragment: Optional[str | NCName] = None)`: Creates an instance of QName. 
   An instance can be constructed in
   two ways:
  - `QName("prefix:fragment")`: A string containing prefix and fragment separated by a color.
  - `QName("prefix", "fragment")` or `QName(NCName("prefix"), NCName("fragment"))`: To strings or NCNames for prefix
    and fragment
- `str(qname)`: returns the string "prefix:fragment"
- `repr(qname)`: returns the string "prefix:fragment"
- QName supports the comparison operations `==`, `!=` and the `hash()`. Thus, a QName may be used as key in a Dict.
- It implements the serializer-protocol for conversion to/from JSON (***Note***: If a Dict uses NCName, the resulting
  Dict cannot be serialized. The JSON methods requiure the key to be a real str!).
- `prefix`: The property *prefix* returns the prefix as string (not NCName!): `p = qname.prefix  # --> "prefix"`
- `fragment`: The property *fragment* returns the fragment as string (not NCName!): `f = qname.fragment  # --> "fragment"

#### Example

```python
qn1 = QName("my_ns:hasName")

ns = NCName("my_ns")
fr = NCName("TragicHeroy")
qn2 = QName(ns, fr)

sparql = f'INSERT DATA {{ {qn2} {qn1} "Wiley E. Coyote" . }}'
# Using the f-string, we don't need to use *str()* or *repr()* for QNames!
```

### AnyIRI

This python class represents a XML Schema AnyURI IRI (Note -- not to be confused: Python: Any**I**RI, XML: Any**U**RI !). The constructor
validates the string to comform the XML AnyURI scheme. Methods (not complete - full documentation from
docstrings [AnyIRI](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.AnyIRI)):

- `AnyIRI(value: Self | str)`: Takes an AnyIRI or a string and checks for conformance. Throws an `OmasErrorValue` if
  the string does not conform.
- `str(anyiri)`: returns the IRI as string
- `repr(anyiri)`: returns the IRI string as used in TRIG/SPARQL, that is with enclosing `<`, `>`. E.g.
  `x = AnyIRI("http://example.org/gaga/test/aua"); rdfstr = repr(x)  # --> <http://example.org/gaga/test/aua>`
- `len(anyiri)`: returns the length of iri string
- AnyIri supports the comparison operations `==`, `!=` and the `hash()`. Thus, a AnyIri may be used as key in a Dict.
- It implements the serializer-protocol for conversion to/from JSON (***Note***: If a Dict uses NCName, the resulting
  Dict cannot be serialized. The JSON methods requiure the key to be a real str!).

#### Example

```python
elephant_iri = AnyIRI("http://example.org/gaga/Elephant")

sparql = f'INSERT DATA {{ my_ns:Animal my_ns:isA {repr(elephantIri)} .}}'
# --> INSERT DATA { my_ns:Animal my_ns:isA <http://example.org/gaga/Elephant> .}

# Will throw an OmasErrorValue:
my_iri = AnyIRI("my.dns.com/gaga/test.html")
```

### NamespaceIRI

This python class, which is a subclass of *AnyIRI* represents an IRI that stands for a [namespace](namespace). That is, the iri
string must have a `#` or `/` as last character. The constructor validates the string to a NamespaceIRI. The methods
are (not complete - full documentation from docstrings [NamespaceIRI](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.NamespaceIRI)):

- `NamespaceIRI(value: Self | str)`: Constructor. Throws an `OmasErrorValue` if the string does not conform.
- Other methods see *AnyIRI* above.

#### Example

```python
my_ns = NamespaceIri("http://my.example.com/examples#")
context["my_ns"] = ns

# Will throw an OmasErrorValue:
my_ns = Namespace("http://this.does.not.work.ch/no_no")
```

### StringLiteral

The *StringLiteral* class is a subclass of the Python standard class *str*. It implements only one special method (not
complete - full documentation from docstrings [StringLiteral](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.StringLiteral)):

- `StringLiteral(value: str)`: Constructur. Just calls the str constructor
- `repr(strlit)`. Returns the string with encllosed `"` in order to be directly included into  TRIG/SPARQL statemenmts.
  `sl = StringLiteral("gaga"); rdfstr = repr(sl) # --> "gaga"`.

#### Example

```python

s = StringLiterall("EMD SD45")

sparql = f'INSERT DATA {{ my_ns:Engine my_ns:isType {repr(s)} }}'
# --> INSERT DATA { my_ns:Engine my_ns:isType "EMD SD45" }

```

### LangString: language dependent strings

In RDF, strings may have a language tag applied to indicate in which language it is written. Many predicates that point to
a string value thus are inherent multi-lingual. An example using *rdfs:label*:

```trig
ns:Engine rdf:type owl:Class ;
          rdfs:label "Engine"@en, "Lokomotive"@de, "Locomotive"@fr, "Locomotiva"@it .
```
The Python class *LangString* is used to work with these multi-lingual strings. LangString supports all [ISO languages](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes) 
that are described in the Enum class [Language](/python_docstrings/language). A LangString instance
acts like a *Dict* and allows the language specific string to be accessed using the `[key]` syntax where the key
is either a 2-letter ISO short for the language or – preferred – an element of the Language enum, e.g. `Language.DE`.
LangString has the following methods (not complete - full documentation from
docstrings [StringLiteral](/python_docstrings/langstring)):

- `LangString(langstring: Optional[str | List[str] | Dict[str, str] | Dict[Language, str]])`: Constructor
  - `LangString("Engine@en")`: This variant takes a string that ends with `@` and a 2-letter ISO short for the language
  - `LangString(["Engine@en", "Lokomotive@de"])`: This variant takes a list strings as parameter
  - `LangString({"en": "engine, "de": "Lokomotive})`: This variants takes a Dict with 2-letter ISO shorts as key
  - `LangString({Language.EN: "engine", Language.DE: "Lokomotive"})`: This variant takes the Language enum values as keys.
    *This is the preferred way to construct a Language instance!*
- `len(langstring)`: Returns the number of language dependent strings defined in the instance
- `s = langstring[Language.DE]`: Returns the string for the given language. The key may also be given as 2-letter ISO shortname.
- `s = langstring.get(Language.DE)`: Returns the string for the given language or `None`, if it does not exist.
  Raises an `OmasError` if specified language string for the specified language does not exist.
- `langstring[Language.FR] = "électrique"`: Assigns the given string to the specified language
- `del langstring[Language.DE]`: Deletes the string for the given language
- `str(langstring)`: Returns the string as it would be used in a SPARQL or TRIG statment.
- `repr(langstring)`: Returns the string as it would be used in a SPARQL or TRIG statment.

#### Example

```python
label = LangString({Language.DE: "Vorname", Language.FR: "Prénom", Language.EN: "First name"})

sparql = f'INSERT DATA {{ my_ns:Boss rdfs:label {label} . }}'
# --> INSERT DATA { my_ns:Boss rdfs:label "Vorname"@de, "Prénom"@fr, "First name"@en . }
```
