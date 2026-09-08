# Reviewed archive adoption

`oldaplib.src.archive_adoption.ArchiveAdoption(connection, project)` implements
project-neutral proposal, preflight and atomic apply. The opt-in archive policy,
ordinary instance rights and persistent writer gate from AS-02 remain mandatory.
No new ontology term is required; folder mappings use `shared:defaultArchiveUnit`
and new nodes use the existing `shared:ArchiveUnit` and seven `shared:ArchiveLevel`
individuals. Project classes and namespaces are never hard-coded.

## Lifecycle

1. `proposal({"sourceFolderIri": iri})` reads a visible connected private subtree.
   Top is traversed without copying it; Trash/Mobile branches are excluded.
   Existing mappings are preserved and reused as suggested parents. Unreadable
   targets are null with `mappingState: unavailable`; their branches receive no
   automatic suggestion. New inner nodes default to Series, leaves to File, with
   the folder name under the library's `LangString.defaultLanguage` (normally `en`;
   an editable initial label, not language detection). Stable request-local
   keys derive from folder identities; they are not persistent resource IRIs.
2. Edit `suggestedPlan`: create grouping nodes, use existing targets, map several
   folders to one node, or explicitly clear/skip a mapping. Omitted folders stay
   unchanged. Every new node must lead to a mapped target. Duplicate keys/folder
   actions, unknown keys, cycles, out-of-scope/protected folders and unavailable
   mappings are rejected. Existing archive nodes cannot be edited through a plan.
3. `preflight({"plan": plan})` checks the actual resource model, level vocabulary,
   folder/target UPDATE rights, readable ancestors, structure capability and
   ADMIN_CREATE for new nodes. It returns counts and a `reviewDigest`, storing no
   draft. The digest binds the normalized plan, source snapshot, existing target
   and ancestor revisions, and policy. Array order and absent/null positions are
   normalized; editorial text is preserved. There is no clock expiry.
4. `apply({"plan": plan, "reviewDigest": digest, "confirm": True},
   operation_id=uuid)` repeats validation under the shared writer gate. It creates
   parents before children, sets/clears folder defaults, journals changes and
   records the result in one GraphDB transaction. Failure rolls all of it back.
   Subsequent deliveries therefore add only reviewed new nodes, preserving
   curated names, levels, parents and grants of existing archive units.

## Access defaults

New nodes inherit roles from the source folders mapped to them or their new
descendants. Shared grouping nodes combine these grants. No configured structure
role is added merely because it exists in policy: private visibility stays tied
to the reviewed source folders. Existing structure-role grants are capped at
DELETE; other roles at UPDATE; public `oldap:Unknown` at VIEW. Weaker grants remain
weaker. The ordinary resource creator semantics still apply. Structure capability
remains an additional guard and does not replace instance permissions. Readers of
one source folder may see the common new grouping node; they do not acquire read
access to unrelated children. Moving/renaming existing nodes uses ordinary guarded
archive operations, not adoption.

## Consistency, retries and limits

Source and review hashes use RFC 8785 canonical JSON and SHA-256. Source snapshots
contain visible folder facts and visible target revisions; complete opaque folder
revisions also detect membership/ACL changes. Hidden target identifiers are never
returned. Source reads are batched; preflight writes no resource/draft. Fixed vocabulary
and folder ACLs are resolved once per review, then propagated through the new-unit
tree. Apply reuses that calculation from its own fresh review; all normal guarded
CRUD and live permission checks remain active. There is no permission cache across
requests. Resource reads use an equivalent existential role threshold instead of
redundant maximum-permission aggregation; QName parsing avoids double validation
while preserving validation of supplied typed IRI objects.

The operation key is scoped to actor, project and command. Exact retries check the
committed receipt before reviewing stale input, then recheck current visibility.
Different content with the same key returns IDEMPOTENCY_CONFLICT. Later deletion
or access loss cannot resurrect a created resource or disclose its old receipt.
`ArchiveRepository.operation(uuid)` reads adoption and reference-move receipts.
If a caller deliberately reuses a UUID across both commands, the unqualified GET
returns a conflict; replay the original command to disambiguate.

Receipts and compact before/after structural audit records are literal JSON in
`urn:oldap:archive-operations`, committed alongside the writes. Each adoption audit
record carries `operationId`. They contain neither whole plans nor media metadata
and create no incoming RDF resource references that would prevent deletion.
Retain receipts for project lifetime. Deployment/recovery rules are unchanged.

Ceilings are 2,000,000 JSON bytes, 5,000 visible source folders and 500 total creates
plus set/clear actions. Both arrays are independently limited to 500 entries.
Skip actions do not consume the mutation budget. Oversized proposals/plans fail
with TOO_LARGE (HTTP 413), without automatic splitting. Choose a smaller subtree.
Permissions and revisions are checked again at apply; knowing a digest grants no
permission. Existing YAML v1 import remains create-only and unchanged.

The packaged `src/schemas/archive_structure_v1.json` is the frozen wire contract.
`jsonschema` validates closed request shapes; `rfc8785` implements canonicalization.
See the matching API guide and FasnachtsPage `docs/as-04/` for isolated integration,
concurrency, rollback and maximum-envelope verification. UI integration is AS-06;
this source implementation does not activate any project policy.
