# Introduction ot OMASLIB

OMASLIB implements several Python Classes which can be used to build a consistent, project specific data model in RDF,
usually implemented in a triplestore. OMASLIB has the following prerequisites:

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

