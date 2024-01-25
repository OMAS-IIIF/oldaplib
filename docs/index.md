# OMASLIB

OMASLIB is a library of Python classes that allows to create data models for RDF based linked data systems.
It uses RDF, RDFS, OWL and SHACL to define consistent data models for projects that are are to be based on RDF.
A short introduction of the base technology is given below.

## Linked Data

Linked Data is a way to store data in the form of a graph-based paradigm. The
[World Wide Web Consortium](https://www.w3.org) (W3C) defined the
[Resource Description Framework](https://www.w3.org/RDF/) (RDF) as a way to express graph based data. Specialized
databases (_triplestores_) are used to store the data and the query language
[SPARQL](https://en.wikipedia.org/wiki/SPARQL) is being used to query such data.

### Introduction to RDF (Resource Description Framework)

RDF, which stands for **Resource Description Framework**, is a fundamental technology for representing and linking data
on the World Wide Web. It provides a structured way to describe resources and their relationships, making it a powerful
tool for data integration, knowledge representation, and semantic web applications.

#### Key Concepts

- **Resources**: In RDF, everything is a resource, including web pages, books, people, and more.
  Each resource is uniquely identified by a Internationalized Resource Identifier (IRI). Resources may act
  as _subject_ or _object_ (see below).

- **Predicates**: In RDF, predicates are used to describe properties of resources, such as the title of a book.
  Predicates are also identified by Internationalized Resource Identifiers (IRI's). Predicates are often also called
  *properties*, a term we will use interchangeably with *predicate* within this documentation.

- **Triples**: RDF data is organized into triples, consisting of subject-predicate-object statements. These triples
  express relationships between resources, where the subject must be resource. The object may be a resource or a
  literal. The predicate defines the relationship between a resource and an object. Often the noun _property_
  is used instead of predicate. 

- **Graph Structure**: RDF data forms a graph structure, with resources as nodes and relationships as edges.
  This graph-based model enables flexible and distributed data representation. That is, predicates that connect two
  nodes form the edges of the graph, wheras the nodes are formed by the resources.

There are several serialization formats for RDF-based data, e.g. XML, turtle, trig. With the OMASLIB documentation, we
will use the _trig_ format. This format allows to define prefixes to build IRI's in a systematic way. A base IRI is
defined which is extended for the different uses. E.g. lets look at the statment that the name of a resource is
Barak Obama. Written out fully, the statement would look like:
```turtle
<http://test.org/project1#obama> <http://test.org/project1#hasName> "Barak Obama" .
```
In order to simplify, we can define a prefix `http://test.org/project1#User` and use a short notation:
```turtle
@prefix test: <http://test.org/project1#> .

test:obama test:hasName "Barak Obama" .
```

For more information about RDF, see tutorials etc. on the net, e.g. the
[official primer](https://www.w3.org/TR/rdf-primer/) pf the W3C.

## Data modelling
RDF allows to "say anything about anything" – thus imposes no limits. However, often stricter rules are needed to
create a meaningfull structure for the data. This process – called _data modelling_ is essential for avoidinfg chaos
within the data. RDF offers two complementary ways for data modelling, which both are expressed as RDF statments:

### OWL – Web Ontology Language
OWL allows on one hand to defines classes of resources and predicates. For Example the statement
```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix test: <https://test4.example.com/> .

test:Person a owl:Class .
```
declares that `test:Person` is a class of Resources. This allows later to "say"
```turtle
@prefix test: <https://test4.example.com/> .
@prefix test: <https://test4.example.com/> .

test:cbrown a test:Person .
```
With this declaration it is known (e.g. for the triplestore) that `test:cbrown` is a `test:Person`. It is also
possible to declare some characteristics for predicates:
```turtle
@prefix test: <https://test4.example.com/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix test: <https://test4.example.com/> .

test:hasName a owl:DatatypeProperty .
test:hasName rdfs:range xsd:string .
```
These to statements define that `test:hasName` is a predicate that points to a literal value which has the
datatype xsd:string.

OWL allows to define many different characteristics for both resources and predicates. A comprehensive set of OWL 
definitions, e.g. for s specific topic or project, is called an _ontology_. However, it is to be noted that OWL
definitions are not **restrictions** to the data but are used for deducing non-explicit information. Some
triplestores are able to use predicate-logic, usually known as **reasoning** to deduce information about resources
and properties. This is a very powerfull but dangerous tool which basically allows to define *semantics* within a
datamodel.


### SHACL – Shape Constraint Language
Since OWL does not impose restriction to the data entered into a triple store, the Shape Constraint Language was
explicitely designed to enforce that the data follows given rules.

SHACL, or Shapes Constraint Language, is a W3C standard designed for validating and describing the structural
constraints and shapes of RDF (Resource Description Framework) data. Its primary purpose is to ensure that RDF data
adheres to specific data models, schemas, or shapes, providing benefits such as consistency, quality control, and
interoperability in linked data applications.

#### Key Purposes

1. **Data Validation:** SHACL enables the definition of rules and conditions that RDF data must satisfy,
encompassing aspects like data types, cardinality, and value ranges. This ensures that data conforms to the desired
structure and integrity.

2. **Interoperability:** SHACL promotes interoperability by allowing data consumers to understand and expect specific
   shapes or structures within RDF data. This ensures that different data sources can be integrated and processed
   consistently, facilitating the exchange of linked data on the web.

3. **Data Quality Assurance:** SHACL supports data quality assurance efforts by specifying rules and constraints that
   automatically identify and rectify data quality issues. This includes identifying missing data, incorrect data types,
   or inconsistent data patterns.

4. **Schema Evolution:** SHACL is valuable for managing schema evolution in RDF data models. It permits developers to
   adapt and evolve data constraints while maintaining compatibility with older data versions.

5. **Semantic Web and Knowledge Graphs:** In semantic web and knowledge graph applications, SHACL is instrumental in
   defining the shape of data models. This makes it easier to represent complex relationships and ensures that data
   conforms to these representations.

Overall, SHACL serves as a versatile tool for defining and enforcing constraints on RDF data, enhancing data quality,
consistency, and utility, especially in applications relying on linked data and semantic web technologies.

