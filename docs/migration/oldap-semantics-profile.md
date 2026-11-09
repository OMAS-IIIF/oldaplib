# OLDAP semantics profile: behavioral acceptance specification

**Historical specification:** the status paragraph below records steps 1–2, not
the current release state. Single-predicate SHACL inverse fields have since been
implemented (`oldap:field` plus `sh:inversePath`). Legacy OWL inverse fallback
still exists for compatibility; this document does not claim it was removed.
See [the current cutover record](graphdb-to-jena-cutover.md) for later migrations
and deployment evidence. Compound SHACL paths remain unsupported.

Historical status: step 1 specification agreed on 2026-10-29; step 2 hierarchy implementation
completed on 2026-10-30. Class equivalence is no longer evaluated; forward
subproperties are supported in filters and explicitly modeled hydrated fields.
Legacy OWL inverse behavior remains until step 3. Target inverse-path metadata,
composition and own-model rejection rules below are not yet implemented. No
ontology or stored data was migrated by step 2. Previous 120 matching Chama
comparisons are historical compatibility evidence, not full acceptance of the
new profile. See [implementation and validation](jena-bounded-entailment.md).

## Scope and principles

- Evaluate explicit `rdfs:subClassOf` and `rdfs:subPropertyOf` hierarchies,
  including multiple levels. Match the requested term itself even without a
  schema declaration. Do not infer a subclass from an asserted superclass.
- Do not evaluate `owl:equivalentClass` or `owl:equivalentProperty`, whether
  declared locally or in a registered external vocabulary. Explicitly asserted
  types and values using these vocabulary names remain ordinary usable data.
- Define reverse read fields through SHACL `sh:inversePath`. Preserve their
  existing public property names through an explicit model mapping. The mapping
  syntax is a step 3 design task; `sh:name` is a label, not a field identifier.
- Do not enable general OWL reasoning, domain/range typing, sameAs expansion,
  property chains, SHACL validation or automatic inverse writes.
- Use the same supported semantics for project, shared/base and explicitly
  registered external schema graphs. Do not load remote ontologies on reads or
  include unrelated projects' schema/data. Retain external axioms as data;
  retaining them does not promise their evaluation.
- Keep one query-building policy; do not select special fast paths depending on
  whether a model happens to contain hierarchy declarations.
- Authorization, RDF 1.2 grants, asserted types and provenance remain explicit.
  Model rules must never manufacture permissions or change write authorization.

## Operation contract

| Operation | Intended behavior |
| --- | --- |
| Class search / class check | Exact asserted type or a type connected upwards by `rdfs:subClassOf`; no equivalence expansion. |
| Resource `rdf:type` | Preserve asserted types; never replace them with ancestors. |
| `virtual:inferredTypes` | Return additional superclass types, deduplicated and excluding already asserted types; no equivalence-only types. |
| Structured property filter | A query for P also matches asserted predicates below P through `rdfs:subPropertyOf`; a modeled inverse field follows its declared reverse path. |
| Absence / sorting | Use the same effective field values as the corresponding filter, preserving existing multi-value sorting rules. |
| Single-resource and summary reads | Keep asserted fields under their original keys. Resolve explicitly modeled derived fields under their stable API keys. Do not emit every external superproperty as an additional JSON key. |
| Requested modeled superproperty | When resolved as a modeled field in a single/summary read, include its subproperty values. An unknown property is not made a model field merely by requesting it. |
| Search `includeProperties` | Preserve the existing asserted-only projection for this migration. A matching derived-value filter does not imply that its value appears in this projection. |
| Counts / paging | Count distinct authorized root resources; multiple hierarchy paths or matching values must not duplicate roots. |
| Writes | Write only canonical asserted fields; inverse read fields are read-only. Rejection must be explicit, never silently drop or reverse an incoming write. Exact error contract remains step 3 work. |
| Fulltext | Keep configured asserted predicate paths. No implicit superproperty, equivalence or inverse text-index expansion. |
| Raw RDF export | Preserve asserted data and schema; do not materialize read results into exports. |

An inverse path to P should use the same subproperty semantics as a forward
field P. This is limited to one reversed predicate plus its subproperty hierarchy;
it is not a general SHACL path-expression engine. Compound paths are out of scope.

## Representative acceptance cases

The names below are synthetic fixture identifiers, not claims about existing
production resources. Use real model terms, but create isolated fixture data.
Expected values describe relevant response fragments, not complete API payloads.

### C1: Fasnacht and Chama persons — ancestry without equivalence

Schema: `fasnacht:Person rdfs:subClassOf schema:Person`,
`schema:Person rdfs:subClassOf schema:Thing`, and the external axiom
`schema:Person owl:equivalentClass foaf:Person`.
Data: `fasnacht:TestPerson a fasnacht:Person`.

- Searches for `fasnacht:Person`, `schema:Person` and `schema:Thing` find the person.
- A search for `foaf:Person` does not find it solely through equivalence.
- `rdf:type` remains `fasnacht:Person`; inferred types include `schema:Person`
  and `schema:Thing`, but not equivalence-only `foaf:Person`. Other explicitly
  declared superclass branches, such as `fasnacht:Agent`, still apply.
- A resource asserted only as `schema:Person` does not match `fasnacht:Person`.
- Repeat with the Chama person model and its complete registered hierarchy.
- Negative control: an explicitly asserted `foaf:Person` still matches that type.

### P1: Organization description — generic search, stable response keys

Schema: `fasnacht:organisationDescription rdfs:subPropertyOf schema:description`.
Data: `fasnacht:TestOrganisation fasnacht:organisationDescription "Test text"@en`.

- Both specific and generic property filters match the organization.
- A resource with only `schema:description` does not match the specific property.
- Ordinary hydration retains `fasnacht:organisationDescription`. It does not
  automatically add `schema:description` merely because the external term exists.
- In a fixture that explicitly models a `schema:description` read field, resolving
  that field returns the text too, including its language tag.
- Search projection of `schema:description` remains absent if not asserted;
  projection of the specific property returns the asserted value.
- Repeated paths/values yield one semantic RDF value, not duplicates.

Repeat property hierarchy coverage with the existing mappings
`fasnacht:memberOfOrganisation -> schema:memberOf` and
`fasnacht:contributingAgent -> schema:provider`. This tests technical handling;
it does not settle whether those mappings should remain in the domain model.
A user account's membership is not necessarily a person's membership, and a
file contributor is not necessarily a provider in the external vocabulary's sense.

### I1 and I2: Places and carnival things — canonical isPartOf only

Decision revised on 2026-10-30: use `dcterms:isPartOf` exclusively for Fasnacht
Places and CarnivalThings. Reverse stored `Parent hasPart Child` statements into
`Child isPartOf Parent`. Do not introduce a modeled inverse hasPart field.

The public “Enthält Teile” view searches children by `isPartOf = Parent`, using
ordinary permission-filtered API search. Parent display and admin writes use
isPartOf as before. Place cardinality remains at most one parent. Consumers of
the old hasPart response field need migration even though API signatures stay
unchanged. See [implementation, preflight and target sequence](fasnacht-parts.md).

### I3: Archive assignment — an asserted relation, not an inverse field

Domain decision (2026-10-30): `fasnacht:archiveUnit` means archival assignment,
whereas `schema:about` means subject matter. Store `O fasnacht:archiveUnit U`
directly, with optional maximum count 1 and target `shared:ArchiveUnit`.
Remove the former `owl:inverseOf schema:about` axiom; do not replace it with
`sh:inversePath schema:about`. A future unit-to-objects read field may use
`sh:inversePath fasnacht:archiveUnit` if a concrete UI/model need arises.

- An asserted assignment is returned under the unchanged `fasnacht:archiveUnit` key.
- `Unit schema:about Object` alone must not imply an assignment.
- A story's subject reference must not imply an assignment either.
- Keep existing subject links and the generic archive importer's `about` input.
- Do not manufacture assignments by reversing subject links during conversion.

The local Fasnacht export dated 2026-10-10 contains `fasnacht:bmg schema:about
fasnacht:BMG`: the BMG archive concerns the organisation, not an archival object
assigned to the archive. Chama exports also use subject links in stories and
sections. These are export observations, not a current live-data inventory.

The migration YAML sets `inverse_of: null` explicitly: omission preserves the
previous value during incremental API model imports. Apply this model update to
the target before read acceptance; raw project transfer only appends triples and
will not remove an old axiom already present. Inspect both orientations of the
legacy inverse axiom in the target project ontology. Existing live systems have
not been updated. Keep this model correction separate from instance conversion;
previously inferred placements require explicit domain review before asserting
anything. Public field names and function signatures remain unchanged.

#### I3 native acceptance (2026-10-30)

`tools/migration/probe_archive_assignment_checks.py` runs within the owned
model-read probe. It checks the real migration YAML declaration and applies
its direct-path shape to synthetic test resources with the actual
`fasnacht:archiveUnit` predicate. Both orientations of the legacy axiom are
seeded, the old false assignment is reproduced, and explicit target SPARQL
cleanup removes both orientations. The test verifies single-read and summary
CONSTRUCT results, public library search/count behavior, subject preservation,
assignment removal and abort restoration. All extra triples are transaction-local.

Result: **152 native model/search checks (11 new) and 57 offline checks pass**.
See [retained evidence](jena-archive-assignment-results.json). This proves the
query semantics after schema cleanup, not a full Fasnacht model import through
the HTTP API or a live-data migration. General modeled inverse-field acceptance
remains separate. No application function signatures or response keys change.

The subsequent [owned HTTP acceptance](../../../oldap-api/doc/jena-archive-assignment.md)
uses the real tools CLI and normal model-update endpoint to clear the forward
axiom, retain all instance triples and verify zero-write replay. It uses a
minimal demo model, not the entire Fasnacht ontology. Reverse/external axioms
remain a separate inventory requirement.

### I4: Chama contributions — preserve existing backlinks

Data: `chama:TestContribution chama:describes chama:TestPhoto`.
Target model: photo field `chama:hasKnowledgeContribution` uses
`[ sh:inversePath chama:describes ]`.

- Photo single/summary reads retain the contribution under the existing field key.
- Filtering photos by contribution still finds the photo, with asserted-only
  search projection as before. The contribution retains its `describes` field.
- Neither reads nor export invent stored reverse triples.
- Additional rehearsal gate: preserve the existing Chama story `schema:hasPart`
  backlink through a modeled inverse of `schema:isPartOf` before removing OWL
  inverse handling. Confirm the actual shape and stored direction from export.

### E1: Ignored equivalence is observable, not silently normalized away

For named classes A/B and properties p/q linked only by OWL equivalence:
`x a A; p y` does not imply `x a B` or `x q y`. Explicitly asserted B/q data still
works. Test local and registered external declarations, in either direction.
Keep equivalent IRIs distinct. Unsupported own-model equivalence declarations
should eventually receive a clear modeling error; external files remain intact.

## Cross-cutting acceptance boundaries

- Run single, batch and filter cases with admin and ordinary authorized callers,
  and verify an unauthorized root stays unavailable with existing API behavior.
- Preserve the existing distinction between returning a linked IRI and permission
  to hydrate that linked resource. A returned IRI grants no access. Negative
  linked-resource filter tests must retain their existing authorization checks.
- Include two-level hierarchies, diamonds, cycles, exact terms absent from schema,
  and unrelated schema/data graphs. Ensure no duplicates or graph-scope expansion.
- Test inverse paths with subproperties, literal values for forward properties,
  and language/datatype preservation. An inverse field produces source resources,
  not reversed literal subjects.
- Test schema changes within transactions and rollback. Cache behavior must not
  hide changes after confirmed commit; do not introduce a new cache in step 1.
- Rights/provenance predicates remain asserted-only even if a malicious model
  declares subproperty or inverse links to/from them. Protect intermediate
  hierarchy paths too, not only the requested predicate.
- Audit legacy data for reverse-only triples, both directions, contradictory
  links and writes to future derived fields before choosing canonical migration
  transforms. Never delete these triples based on this specification alone.

## Delivery order and remaining decisions

1. This specification and source inventory (documentation only).
2. Implement property hierarchy support and remove equivalence expansion; turn
   C1/P1/E1 and relevant boundary cases into executable regression tests.
3. Specify stable field-to-path metadata in oldaplib and ontology YAML, shape
   inheritance/applicability and inverse source-class constraints; implement I1–I4.
   Audit all writers, including tools and harvesters, before rejecting old writes.
   Keep the existing inverse implementation until replacements pass acceptance.
4. Rehearse real exports and compare API outcomes and timings. Class-equivalence
   changes are explicit expected differences; no blanket removal of inferred
   fields from comparisons. Retain baseline evidence. Canonical stored direction
   and modeled-field filtering can introduce further differences requiring review.

No public function signature changes are planned. Stable signatures alone do not
prove compatibility: response content, accepted writes and field metadata also
need consumer checks. Archive assignment semantics are resolved in I3; general
inverse model syntax and its acceptance remain a separate implementation gate.

## Source inventory

- `oldaplib/src/helpers/jena_entailment.py`: subclass/subproperty and inverse read rules.
- `oldaplib/src/objectfactory.py`: hydration, summary and search query builders.
- `oldaplib/ontologies/shared.trig`: ArchiveUnit subject field.
- `oldaplib/src/archive_import.py`: asserted `schema:about` write direction.
- `../oldap-tools/fasnacht/fasnacht-onto.yaml`: three subproperties; place/thing
  inverse pairs and explicit removal of the archive-unit inverse axiom.
- `../oldap-api/tools/migration/probe_graphdb_project.py`: real Chama baseline,
  summaries, class searches and inverse filter/projection comparison.
- [Current implementation and historical evidence](jena-bounded-entailment.md).
- [Cutover knowledge index](graphdb-to-jena-cutover.md).
