# OLDAP Permission Concept

There are two kinds of permissions that have to be defined to OLDAP users:

## Administrative permissions

- `ADMIN_OLDAP`: Quasi "root"-permissions, system administration
- `ADMIN_RESOURCES`: _Override_ resource permissions to manipulate
  any resources within the given project (All CRUD-operations)
- `ADMIN_USERS`: add/modify/delete users.
- `ADMIN_MODEL`: User has permission to modify the data model.
- `ADMIN_CREATE`: The user is allowed to _add_ new resources.

Administrative resources are attached to the RDF-triple that defines the
membership of a user to a project using the RDF*star syntax:

```rdf
ex:NikolaiTesla a :User .
ex:Electrify a :project .

ex:NikolaTesla :inProject ex:Electrify .
<<ex:NikolaTesla :inProject ex:Electrify>> :hasPermission :ADMIN_MODEL
<<ex:NikolaTesla :inProject ex:Electrify>> :hasPermission :ADMIN_USER
<<ex:NikolaTesla :inProject ex:Electrify>> :hasPermission :ADMIN_CREATE
```

Above example would the user ex:NikolaTesla would have the permission to modify
the data model of ex:Electrify, to add/modify/delete users and to create new
resources. 

## Data Permissions

Data permissions are used to define the access rights to the actual resources
representing the data. The data permission concept is based on the `:PermissionSet` which
are granted the access permissions. Each resource grants the access permissions based on
the connection to one or many permission sets using the `:grantsPermissions`-property. A
given user is member of one or many groups based on the `:hasPermissions`-property.
The permission set itself uses `:gives` to list the permissions in the given set.  
**NOTE**: A permission set should give all the required permission! The `EXTEND` permission
does *not* automatically also give the `VIEW`-permission! The reason are performance
issues. However, a GUI should automatcally include `VIEW` and `EXTEND`, if a permission
set is given the `UPDATE`-permission!

The following data permissions are available:

- `VIEW`: Readonly access to a resource
- `EXTEND`: Allows to extend the data (e.g. adding a comment or annotation or
  adding data to a filed that has a cardinality greater one).
- `UPDATE`: Allows to modify or update an existing resource
- `DELETE`: Allows to completely remove a resource
- `PERMISSIONS`: Allows the user to change the assignments of groups
  and the ownership of a given resource.


### Special Groups:

Special permission sets are assigned automatically to a given user according to
its login status. The following special groups are defined for
each project:

- `UNKNOWN_USER`:  
  An anonymous that is user not known. The user `anonymous` is automatically
  attached to this group. The IRI is `[admin_namespace]/psets/anonymous`.
- `KNOWN_USER`:  
  A user with a login, but not specially attached to
  a given resource (e.g. through a group assignment or project membership). A user is automatically
  assigned to this group if she/sh is authorized. The IRI `[admin_namespace]/psets/known` is
  used for this group.
- `PROJECT_MEMBER`:  
  A user is member of the project the resource is
  attached to, but is not assigned to any other group related to the
  resource. For each project, there is a project-specific group `PROJECT_MEMBER`.
  The IRI of the group is built as `[admin_namespace]/psets/project/[fragment(project_iri)]`.
- `OWNER`:  
  For each user, a user-spcific group `OWNER` is created where the user is
  automatically a member of. The IRI of the user-specific group is built as
  `[admin_namespace]/psets/user/[user_id]`.

The permission sets `UNKNOWN_USER` and `KNOWN_USER` are defined system-wide, the permission set `PROJECT_MEMBER` is
being created for each project at the moment the project is created. The permission set `OWNER` is being created
when a user is being added.


The concept looks as follows: ![PermissionConcept](assets/PermissionConcept.gif)

### Example

The following SPARQL query retrieves all resources that have the property `ex:hasName`
with a value "Gaga" and the user the `VIEW`-right.

```sparql
PREFIX ex: <http://example.org/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX : <http://oldap.org/datamodel/>

SELECT ?label
FROM ex:data
WHERE
{
    ?resource ex:hasName "Gaga" .
    ?resource rdfs:Label ?label .
    ?resource :grantsPermissions ?pset .
    <thisuser> :hasPermissions ?pset .
    ?pset :givesPermission :VIEW .
}
```

To get all the permissions of a given resource and user, the following SPARQL statement can be used:

```sparql
PREFIX ex: <http://example.org/>
PREFIX : <http://oldap.org/datamodel/>

SELECT ?permission
FROM ex:data
WHERE
{
    <res_iri> :grantsPermissions ?pset .
    <thisuser> :hasPermissions ?pset .
    ?pset :givesPermission ?permission
}
```
