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

### Project Identifier

At the base of the graph structure there is the unique IRI that each project must have. The IRI must conform to
the syntax of a Namespace IRI, that is an IRI that either ends with a "#" or "/" character. In addition, a prefix for
this project-IRI must be defined and consistently being used. E.g. the following prefix declaration could be used:
```turtle

@prefix myproject: <http://www.myorgranisation.edu/myproject#> .
```

It is to note that the system itself uses the prefix identifier **omas** which **must not be used**!

For each project, there are 3 different graphs (assuming *projpre* as project prefix):

* `projpre:shacl`: This graph contains all the SHACl declarations
* `projpre:onto`: This graph contains all the OWL declaration
* `projpre:data`. This graphs contains the actual data

OMASLIB primarely deals with the first two, that is the SHACL and OWL declaration and allows to build and maintain a
consistent representation of a data model. Within the data model, resource class and properties which must follow
certain project-defined constraints are defined.

### 


