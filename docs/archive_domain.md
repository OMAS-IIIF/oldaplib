# Archive domain policy and private references

AS-02 supplies reusable server-side rules on top of the Shared classes. It adds no
project namespace, project media class, role enum or ontology term. Domain writes
use `resource_transaction`, including direct `ResourceInstance` callers and the
existing archive/folder move services. Resource connections are task-local.

## Server-owned project configuration

Set `OLDAP_ARCHIVE_POLICY_FILE` to a closed JSON file. The following is a template;
its example roles/classes must be replaced with existing project-owned resources:

```json
{
  "projects": {
    "example": {
      "enabled": true,
      "structureEditorRoleIris": ["https://example.org/ns/StructureEditor"],
      "archiveEditorRoleIris": ["https://example.org/ns/Editor"],
      "cataloguedMediaClassIris": ["https://example.org/ns/CataloguedMedia"],
      "preparationNotePropertyIri": "https://schema.org/comment"
    }
  }
}
```

The preparation property must use the deployment's actual schema namespace.
Configuration accepts only the shown fields, canonical absolute IRIs, unique
nonempty arrays (maximum 100), boolean flags and valid project short names. Files
are capped at 1 MB. Invalid configuration fails closed. Roles must exist and be
owned by the configured project. Catalogue classes must resolve in that project's
model, extend `shared:MediaObject` and exclude `shared:StagingMediaObject`.
The preparation property must exist in a loaded shape; it need not exist on the
archive target class. No ontology addition is needed merely to reject late notes.

Absent projects retain legacy domain behavior. Selecting a policy file enables
the writer gate for **all resource projects** in that deployment, because incoming
references can cross project graphs. Use identical policy and coordination
settings in every API and direct-library writer. Changing policy or role
provisioning requires quiescing writers; it is not an ordinary resource command.

## Capabilities and data rights

- Structure create/rename/move/level/delete and default-folder mapping require a
  configured structure role plus ordinary instance rights. Creation additionally
  needs `ADMIN_CREATE`; parent changes require UPDATE on old/new parents; mapping
  changes require UPDATE on the folder and old/new target units.
- Existing OLDAP administration overrides remain explicit. Structure roles do not
  grant data rights, media editing rights or public visibility by themselves.
- Adding catalogue media to `shared:hasMediaObject` is a separate operation:
  unit UPDATE and media VIEW suffice. Removing/replacing links still requires
  structure capability. Existing content does not require media write access
  merely to rename/move its enclosing unit.
- Catalogue metadata needs an editorial role and the normal resource permission.
  Every attached data grant above VIEW must belong to a configured editorial
  role. In particular, transfer must not preserve a contributor DELETE grant.
  Overlapping role memberships must be reviewed before activation.
- Preparation-note writes and clears are rejected after cataloguing, even for
  combined editor/structure/admin callers and when the target model lacks the
  property. The API checks this before converting the payload.

Guards recognize transitive project subclasses on generic create/update/delete/
transform and dedicated tree operations. They check fresh persisted class and
revision, cycles, archive-level individuals, same-area private placement, protected
system identities, and portable sibling-name collisions including hidden siblings.
Creating a private root requires area UPDATE. Empty deletion is non-cascading and
checks all incoming graph references plus outgoing media/private edges without
visibility filters. Default mappings pointing to an otherwise empty unit prevent
its deletion. Generic StagingArea deletion is denied; the API's atomic empty-area
operation also checks repository references and mappings.

Raw SPARQL, ontology imports and administrative role/project writes are privileged
maintenance paths, not untrusted domain APIs. They must not run concurrently with
active domain writers. Gate coordination does not replace GraphDB access control.

## Private-reference command

`ArchiveRepository(connection, project).move_reference(body, operation_id=uuid)`
accepts only media/source/target absolute IRIs and two SHA-256 folder revisions.
It requires UPDATE on both folders, VIEW on catalogue media, the same StagingArea,
and supported paths (no Trash, no target Mobile). Folder revisions include
membership and ACL state, including hidden edges, without exposing their values.
`folder_revision` is an internal primitive: authorize the folder before exposing
its digest. AS-03 supplies these revisions through the signed mixed inventory; see [private repository lifecycle](private_repository_lifecycle.md).

The command atomically updates folder-owned edges and commits an actor/project/
command-scoped receipt. It never edits the medium or its archive unit. Same-folder
moves are revision-checked no-ops; an existing target edge is retained and only the
source edge is removed. Exact retries return the committed result; a different
body with the same ID conflicts. Retries and receipt reads recheck current
visibility. Revoked access cannot be recovered through an old receipt.

Structural audits and receipts live in the backend-owned
`urn:oldap:archive-operations` graph for the project's lifetime. Their JSON literal
records include actor, time, resource identifiers and relevant before/after state;
audit records deliberately do not become incoming RDF edges that prevent future
empty deletion. Ordinary endpoints expose only the owner's authorized receipt,
not the internal audit graph. AS-04 adds reviewed structure adoption/apply receipts.
AS-03 implements automatic private-reference creation during transfer and preserved organisation read access.

See [resource transactions](resource_transactions.md) for atomic composition and
[persistent writer recovery](writer_recovery.md) for deployment requirements.
