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
(CRUD-Operation) using the methods of the Python classes of oldaplib. 

# Data Modelling using OMAS
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

