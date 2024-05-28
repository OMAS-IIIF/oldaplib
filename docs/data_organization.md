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
- `projectShortName`: The *projectShortName* is a [NCName](/python_docstrings/xsd/xsd_ncname)
  that should be a somewhat meaningful shortname for the project. This shortname will be used as `prefix` for
  all project specific elements in RDF. E.g., or the SwissBritNet we could choose the projectShortName `sbn`.
- `namespaceIri`: The `namespaceIri` is a valid IRI that must end with a `#` or `/` character. It is in combination
  with the *projectShortName* used to define prefixes: `PREFIX 'projectShortName': <'namespaceIRI'>`. For our
  example let's assume a *namespaceIri* `https://swissbritnet.ch/namespace#`. THus, a prefix definition would
  look like `PREFIX sbn: <https://swissbritnet.ch/namespace#>`.
- `label`: Informative data containing the human readable name of the Project, e.g. "SwissBritNet". You can add several
  language specific labels (but only one per language)
- `comment`: Informative data containing a brief description of the project, it's purpose etc. You can add language
  specific comments (one per language)
- `projectStart`: Informative data containing the date whe the project has started/will start. The date must have the
  format `YYYY-MM-DD`. If no `projectStart^is given, the current date is picked.
- `projectEnd`: Informative data containing the date whe the project will be finished. This is an optional element
  that also has the format `YYYY-MM-DD` and indicates when the project will end. It must be after the `projectStart`date!

For each project, **4** *named graphs* will be used (where `[projectShortName]`will be replaced by the actual
projectShortName:

- `[projectShortName]:shacl`: This graph contains all the SHACL definition of the project specific data modeling
- `[projectShortName]:onto`: This graph contains the OWL ontology definition in order to allow reasoning on the
  projects data
- `[projectShortName]:lists`: This graph contains all the hierarchical lists (theasauri) associated with the given project
- `[projectShortName]:data`: This graphs contains al the projects data


### System Project

The *System Project* (IRI: `oldap:SystemProject`, projectShortName: `oldap`) is a special project that is required for
OLDAP to implement authentication, user management and access control. It contains all the necessary data models and
data for this purpose, again  in specific named graphs. It uses the following `http://oldap.org/base#` as *namespaceIri*
and `oldap` as *projectShortName*. The following named graphs are used:

- `oldap:shacl`: Contains the SHACL definition for system specific data models.
- `oldap:onto`: Contains the OWL declarations
- `oldap:admin`: Contains all data (instances of system classes) that are necessary for OLDAP to function
  properly.

***IMPORTANT***: **Data and definitions from the system project must never be changed directly in the
triple store! This could lead to a non-working system and/or massive data loss!**

## User
A *User* is an actor that has access to the OLDAP platform. It may be a *member* of one or more *projects* with some
administrative associated with this connection. In addition, a user is associated with *permission sets* which control
the access permission to the data. For a more thorough discussion of the permission control concept see the chapter
[OLDAP Permission Concept](/permission_concept)

A User is defined with the following properties:

- `userIri`: A unique IRI describing the User. It is highly recommended to use the [ORCID](https://orcid.org)-Id as
  *userIri*. If a user doesn't have an ORCID, the *userIri* can me omitted and OLDAP will assign a UUID-based URN.
- `userID`: The *userId* is a NCName that is used as shortname or nickname. It must also must be unique (which is
  enforced by OLDAP – it does not allow a user to be added with as *userId* already in use). The userId is used
  to identify the user at login etc.
- `familyName`: The family name as defined by the [FOAF](http://xmlns.com/foaf/spec/) ontology. This property is
  for descriptive use only.
- `givenName`: The given name (or "firstname") of the person, also according to the [FOAF](http://xmlns.com/foaf/spec/)
  ontology. This property is for descriptive use only.
- `credentials`: The password of the user to login. Internally the password is stored as a hash value. Thus, the plain
  text of the password is never stored within OLDAP for security reasons.
- `active`: This is a boolean value that is `True` if the user is active, `False` otherwise. This property allows
  to temporarily prevent a user accessing the OLDAP platform.
- `inProject`: This property defines the project(s) a user is member of and which permissions he has for this project.
  The following permissions are availabe:
    - `ADMIN_OLDAP`: only used for the `omas:SystemProject`. If a user is member of the *system project* and has this
    permission, he has full control of the OLDAP platform (*"super user"*).
    - `ADMIN_USERS`: The user may manage the users of the project this permission is associated with (add/modify/delete
      users and the permissions).
    - `ADMIN_PERMISSION_SETS`: Modify the permission sets for data access for this user.
    - `ADMIN_RESOURCES`: Change permissions amd ownership of data items ("*resources*).
    - `ADMIN_MODEL`: Extend or change the data model for the given project.
    - `ADMIN_CREATE`: Create now data items ("resources") in the context of the given project.
    - `ADMIN_LISTS`: Create, modify and delete lists and list nodes
- `hasPermissions`: Define the *Permission Sets* a user is associated with. For more information about the role of
  *permission sets* see the chapter [Permission Concept](/permission_concept). The *permission sets* are items defined
  in the `omas:admin` graph and can be added/modified/deleted by a user that has the `ADMIN_PERMISSION_SETS` permission
  for the given project.  

  For a detailed description of the format of this field please see the description of the [User class](/python_docstrings/user).

## Permission Set

A *permission set* is the link between the user and a data item that defines how a user is allowed to access a specific
data item. A permission set is an item that is defined withing the `oldap:admin`-graph and has the class
`oldap:PermissionSet`. User with the appropriate administrative permission may add/modify/delete permisson sets.
The permission sets are both associated with data items/resources and user (see [Permission Concept](/permission_concept))
The following permissions are defined:

- `DATA_RESTRICTED`: Allows restricted access to the data item. The meaning of "*restricted*" must be defined by the
  project context. For an image resource, it may restrict the maximal resolution or impose a watermark on the image. For
  a data only resource it may render certain fields/properties hidden.
- `DATA_VIEW`: Allow full, unrestricted view of the data item/resource. However, the item may not be changed/deleted in
  any way.
- `DATA_EXTEND`: The resource is allowed to be *extend* (adding information such as a comment or annotation etc.),
  but may not otherwise be modifed.
- `DATA_UPDATE`: The resource may be changed, but be deleted.
- `DATA_DELETE`: The resouirce may be deleted (there is still the restriction that the resource must not
  be referenced by another resource in order to be deleted).
- `DATA_PERMISSIONS`: The permissions of the data item/resource may be changed

**NOTE (A)**: *The data permissions are ordered in a hierarchy. This is `DATA_EXTEND` automatically includes `DATA_VIEW`
and `DATA_RESTRICTED` etc. Thus, `DATA_PERMISSIONS` encompasses all other permissions too.*  

**NOTE (B)**: *The owner of a data item/resource -- that is the user that created the item -- always has all permissions
even if there are no explicit permissions associated.*  

**NOTE (C)**: *A user associated with the __System project__ having there the `ADMIN_OLDAP` privilege also has full
access to all resources.*

A Permission Set is defined by the following properties:

- `permissionSetId`: An project-unique ID identifying the permission set. The ID is a [NCName](/python_docstrings/xsd/xsd_ncname)
  that must be unique within the project. It's used to identify/access/modify the Permission Set.
- `label`: Informative data containing the human readable name of the permission set. You can add several language
  specific labels (but only one per language)
- `comment`: Informative data containing a brief description of the permission set, it's purpose etc. You can add several
  language specific comments (one per language)
- `givesPermission`: The permission that this permission set grants (see above).
- `definedByproject`: The project that the permission set is defined in. This parameter can either be the
  [IRI](/python_docstrings/xsd/iri) of the project, or the `projectShortName` given as
  [NCName](/python_docstrings/xsd/xsd_ncname).