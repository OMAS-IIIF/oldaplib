# Data Organization, Data Modeling and Access Control

Linked Data aims to transform the Web from a medium for connecting documents to a universal platform for
interlinking structured data. By promoting principles of data connectivity, semantic interoperability,
and open standards, it seeks to make data more accessible and reusable across diverse domains.
Tim Berners-Lee envisioned Linked Data as a step towards realizing the Semantic Web, a web of data that
enables machines to understand and respond to complex human requests based on their semantics.
This vision encompasses a more intelligent and efficient Web, where data from any source can be linked
and used in ways we are only beginning to imagine, fostering innovation, knowledge sharing, and
collaboration on a global scale.

In order to implement his vision of the Semantic Web, Tim Berners-Lee invented the
[Resource Description Framework](https://en.wikipedia.org/wiki/Resource_Description_Framework)
(RDF) as a technology represent and connect semantic information. Thus, RDF allows does not enforce
rules about data structuring and strict data modeling. The
[Web Ontology Language](https://en.wikipedia.org/wiki/Web_Ontology_Language) (OWL) is not designed
to *build* and *enforce* data models. It is rather a tool to declare semantic relationships and allow
the inference of non-explicit information. Using OWL, a triple store is able to extract information that
is only *implicitly* given, using a process called *reasoning*.

The lack of data modeling in the sense to *enforce* rules that the data must follow led to the development
of the [Shape Constraint Language](https://en.wikipedia.org/wiki/SHACL) that allows to create data models
and validate data against it.

RDF and triple stores, as being designed for **open access**, do provide only very little or no access control.
However, a platform like OLDAP must implement user authorization and access control.

Thus, OLDAP uses SHACL in two ways: On one hand, it implements certain subject and property classes that are
used to implement user authentication, authorization and access control. On the other hand, it allows projects
to define there proper data domain specific models and enforce the conformance of the data to these models.
The following chapters will explain how OLDAP organizes its data and how authentication and access control
are implemented. For this purpose, OLDAP uses [SHACL](https://en.wikipedia.org/wiki/SHACL) and
[Named Graphs](https://en.wikipedia.org/wiki/Named_graph). In addition OLDAP integrates
[OWL](https://en.wikipedia.org/wiki/Web_Ontology_Language) to allow the use of reasoning if desired.

The following entities are important to understand:

## Project

In OLDAP, a *Project* acts as an umbrella term encompassing all activities, data, tools, and collaborations
geared towards addressing a specific research question posed by a group of researchers or an individual scholar.
It serves as a centralized digital space that integrates and organizes every aspect of the research process,
from inception through data collection and analysis, to the dissemination of findings. This approach ensures
that all related data and resources are interconnected and accessible within the OLDAP platform, streamlining
the research workflow and fostering a collaborative and efficient research ecosystem.

In order to organize that data of a project without interfering with data from other projects, each project
uses distinct named graphs. In order to do so, for each project, the following parameters have to be defined:

- `projectIri`: The *projectIri* uniquely identifies the project. The IRI **must** be unique. It may be the
  URL of the landing page of the project's website or anything else unique in the form of an IRI. For
  example the SwissBritNet might use `https://swissbritnet.ch/`. OLDAP may assign automatically a UUID-based
  URN as projectIri.  
  **NOTE**: *The projectIri is immutable and may not be changed after creation. There choose it carefully!*
- `projectShortName`: The *projectShortName* is a [NCName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.NCName)
  that should be a somewhat meaningful shortname for the project. This shortname will be used as `prefix` for
  all project specific elements in RDF. For the SwissBritNet we could choose the projectShortName `sbn`.
- `namespaceIri`: The `namespaceIri` is a valid IRI that ends with a `#` or `/` character. It is in combination
  with the *projectShortName* used to define prefixes: `PREFIX 'projectShortName': <'namespaceIRI'>`. For our
  example let's assume a *namespaceIri* `https://swissbritnet.ch/namespace#`. THus, a prefix definition would
  look like `PREFIX sbn: <https://swissbritnet.ch/namespace#>`.
- `label`: Informative data containing the human readable name of the Project, e.g. "SwissBritNet"
- `comment`: Informative data containing a brief description of the project, it's purpose etc.
- `projectStart`: Informative data containing the date whe the project has started/will start.
- `projectEnd`: Informative data containing the date whe the project will be finished.

For each project, **3** *named graphs* will be used:

- `projectShortName:shacl`: This graph contains all the SHACL definition of the project specific data modeling
- `projectShortName:onto`: This graph contains the OWL ontology definition in order to allow reasoning on the
  projects data
- `projectShortName:data`: This graphs contains al the projects data

## System Project

The *System Project* is a special project that is required for OLDAP to implement authentication,
user management and access control. It contains all the necessary data models and data for this purpose, again
in specific named graphs. It uses the following `http://omas.org/base#` as *namespaceIri* and `omas` as
*projectShortName*. The following named graphs are used:

- `omas:shacl`: Contains the SHACL definition for system specific data models.
- `omas:onto`: Contains the OWL declarations
- `omas:admin`: Contains all data (instances of system classes) that are necessary for OLDAP to function
  properly.

***IMPORTANT***: **Data and definitions from the system project must never be changed directly in the
triple store! This could lead to a non-working system and/or massive data loss!**

## User
A *User* is an actor that has access to the OLDAP platform. 

**more to come here**

# Data Modeling

## Properties (predicates)

NOTE: ZUERST VIELLEICHT: WAS IST EINE PROPERTY? ODER STEHT DAS SCHON OBEN? WENN JA -> REFERENZ DADRAUF? ODER: WISO KOMMT HIER GENAU PROPERTIES?
PROPERTIES ARE IMPORTENT BECAUSE OF ...

Predicates or properties can be defined NOTE: BE DISTINGUISHED? in to different flavours. Usually the private properties are preferred and
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

NOTE: TEXT IST SEHR GUT ABER NOCH EIN BISSCHEN UNSTRUKTURIERT. MIR FEHLT NOCH ETWAS DER ROTE FADEN... GRAD AM SCHLUSS
HAT MAN ETWAS DAS GEFÜHL ES IST EINFACH EIN NAMENSAPPENDIX... ZUSÄTZLICH WÄRE EIN SCHLUSSKALITEL/SCHLUSSWORT SICHER NOCH GUT
 -- EVENTUELL KANN MAN DA NOCH WEITERE REFERENZEN AUFFÜHREN ODER NOCHMALS DIE WICHTIGSTEN REFERENZEN ZUSAMMENFASSEN.

