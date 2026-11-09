# Persistent private repository lifecycle (AS-03)

AS-03 extends the opt-in [archive policy](archive_domain.md) without another
ontology change. It uses the two optional folder properties introduced in Shared
0.7.0 and does not require project-specific media classes in backend code.

## Atomic catalogue transfer

The existing `ResourceInstance.transform_class()` signature and HTTP transform
body/response remain unchanged. For a policy-enabled transition from a transitive
`shared:StagingMediaObject` class to a configured catalogue class, the owned
transaction also:

1. Reads the current source folder/area and checks visibility, consistent placement,
   the protected path, and the medium's existing transformation permission.
2. Requires `preserve_class="shared:MediaObject"`, retaining media IRI and binary
   facts. A catalogue target must not retain staging placement properties.
3. Validates caller-supplied target grants. If omitted, derives grants from current
   source rights, capping non-editorial writes at VIEW. Existing readers retain
   their previous access up to VIEW, including RESTRICTED rather than newly public
   VIEW. The area's authoritative, project-owned default role retains at least
   VIEW. Explicit grants cannot remove that organisation's read access or restore
   contributor write permission.
4. Transforms the medium and applies any existing authorized archive attachment.
5. Appends the folder-owned `shared:referencedMediaObject` edge, updates the folder
   modification stamp, and writes structural/transfer audit records.

Every part commits or rolls back together. No binaries are copied, no duplicate
media resources are created, and publication is not used as the lifecycle boundary.
Mappings/default archive units remain suggestions: this step never silently picks
an archive unit or turns a generic catalogue project into a Fasnacht workflow.

Automatic retention is **not relocation**. It preserves the medium's already
established placement and requires source folder/area VIEW plus the existing
medium transformation permission (DATA_DELETE, or the existing administration
exception). This narrow internal append also works in the VIEW-only Mobile inbox;
it does not weaken its ACL or authorize generic folder edits. Retaining from Trash
is rejected: restore the medium before cataloguing. Subsequent reference movement
still requires UPDATE on both folders through `ArchiveRepository.move_reference`.

The `ArchiveTransfer` hook is internal to the resource transaction decorator.
Never call its prepare/finish methods as standalone writes. Discard mutable source
objects after a failed transaction. A stale source or legacy expected-source-class
retry conflicts rather than re-transforming or recreating a reference. Existing
mobile commit receipts remain untouched and replay their original result even
after the reference has moved; they are separate from catalogue transfer audits.

## Mixed direct folder inventory

```python
from oldaplib.src.archive_inventory import ArchiveInventory

inventory = ArchiveInventory(connection, project, cursor_secret=server_owned_key)
page = inventory.page(folder_iri, limit=50)
```

The result follows the frozen v1 `InventoryResponse`: folder IRI, revision,
entries, next cursor and warnings. Entries are either `stagingMedia` or
`archiveReference`, ordered by `(kind, mediaIri)`; they do not masquerade as staging
resources. This endpoint lists direct **media** children, not descendant folders.
Existing folder-tree and generic search contracts remain unchanged.

- Limits are 1..100, default 50. The database filters visible identities and pages
  them before any per-medium metadata read. Hidden identifiers and hidden counts
  are never returned; the current implementation emits an empty warnings array.
- The complete folder revision includes membership and folder ACL state, including
  hidden edges. A revision change invalidates continuation with STALE_FOLDER.
- HMAC-protected cursors bind the caller, project, folder, revision and last sort
  position. Context and last IRI are hashed so maximum-length Unicode IRIs still
  fit the 4096-character wire limit. The last identity is resolved inside the same
  revision-bound folder; current permissions are checked again on every page.
- Signing keys must be server-owned, stable across readers and at least 32 bytes.
  The API derives a purpose-specific key from its access-token secret. Direct
  library services inject their own shared key. Rotation invalidates old cursors;
  clients restart at page one. No cursor is a media authorization capability.
- Reference entries always set `canEditMetadata=false` and `canDeleteMedia=false`.
  Folder relocation requires folder UPDATE and supported paths. A local original
  requires visible media and local binary facts; actual delivery reauthorizes
  through existing media endpoints. External links are not advertised as local
  original downloads. Capability flags are hints, never a permission grant.

Inventory uses the existing coordinated transaction boundary to obtain consistent
revision, membership and metadata reads. As with writes, an unavailable or retained
writer gate fails closed. All domain writers must participate in the same gate.

## Read-path correction required by transfer

GraphDB's evaluation of an uncorrelated `BNODE()` in the resource CONSTRUCT could
merge different roles and permissions into one binding, making the materialized
ACL map empty. The read and summary queries now bind blank-node identity to the
role/permission pair. This retains complete associations without another database
round trip and fixes the pre-existing `test_change_permissions_A` regression.
Actual multi-role transfer/re-read and the complete 61-test ObjectFactory suite
verify the correction.

## Scope and deployment

Source implementation and isolated backend checks are complete. Policy activation
still requires the reviewed ACL migration and durable gate deployment. There is no
migration, live ontology load, media-server change, CaptureApp edit or deployment
in AS-03. AS-04 provides reviewed adoption; mixed ZIP export and desktop UI/SALSAH
integration remain AS-05/AS-06/AS-07. Native Capture acceptance remains AS-08.
