# Project-owned creation grants

An archive policy can opt into `grantEditorRolesOnCreation: true`. The optional
boolean defaults to false, preserving existing source-scoped policies. It is
independent of capability checks: ordinary resource permissions still apply.

For an enabled project:

- New ArchiveUnits, including subclasses, receive at least DATA_DELETE for every
  configured structure editor role. Empty-unit deletion checks remain mandatory.
- New configured catalogue media, including subclasses and staging transfers,
  receive at least DATA_UPDATE for every configured media editor role.
- Direct creation, reviewed adoption and catalogue transfer use the same grant
  rule. Adoption includes the flag in its review digest; changing the setting
  invalidates an outstanding preflight. Adds happen inside the existing resource
  transaction and roll back together with domain writes and audit.

Grants use the existing project-owned role IRIs. No classes, ontology properties,
permission levels or client request/response fields are added. Existing projects
without the flag retain their previous behavior, including when a policy file is
selected but that project is disabled.

This is a creation rule, not permission inheritance or an administrative bypass.
It does not regrant roles during metadata updates, retrofit existing resources,
change private folders, expand public access, or alter original media identity.
Catalogue transfer continues to preserve organisation reads and private references;
late preparation notes remain forbidden, including clears and administrator writes.
An existing higher valid editorial grant is preserved.

Explicit invalid archive-media write grants still fail validation; the creation
rule does not silently sanitize caller ACLs or user-wide defaults. Direct archive
creation must already supply a valid archive ACL (or use valid user defaults).
In particular, legacy contributor/Unknown write defaults are not made valid by
this setting. Omitted transfer ACLs retain the existing contributor-to-VIEW cap.

Example project entry (role/class IRIs must exist in that project):

```json
{
  "enabled": true,
  "structureEditorRoleIris": ["https://example.org/archive/StructureEditor"],
  "archiveEditorRoleIris": ["https://example.org/archive/MediaEditor"],
  "cataloguedMediaClassIris": ["https://example.org/archive/Photograph"],
  "preparationNotePropertyIri": "https://schema.org/comment",
  "grantEditorRolesOnCreation": true
}
```

Deployment still requires the additive Shared model, reviewed existing-resource
ACLs, compatible library/API writers and the persistent gate configuration from
[writer recovery](writer_recovery.md). Old library versions reject the new field;
deploy the matching library before selecting such a file. Selecting a policy file
already activates shared coordination, even with `enabled: false`.
