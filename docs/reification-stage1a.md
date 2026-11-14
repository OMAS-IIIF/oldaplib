# Reification model contract and capability evidence

Stage 1A completed on 2026-11-13. This contract guides stage 1B; it does not claim that model CRUD or instance annotations are implemented. The [working plan](reification-properties-plan.md) tracks the remaining stages.

## Validation decision

OLDAP remains responsible for validation. The owner explicitly confirmed that this is intentional; replacing it requires a demonstrable benefit and a separate architecture decision. The external validator checks below are capability observations, not a proposal to change the validation engine.

Reification requires one additional traversal: for each asserted property value, find its reifiers, enforce required presence, and validate each reifier's field set using OLDAP's existing datatype and property constraints. Multiple applicable shapes are conjunctive. Refactor the relevant existing validation functions into a shared, narrowly scoped implementation when stage 3 needs them; do not create a dummy ResourceInstance with Thing metadata to validate an annotation.

## Verified capabilities

The repeatable [probe](../tools/reification/probe_capabilities.py) uses the pinned Fuseki 6.2.0 jar, current project-transfer source, synthetic data, and a new TDB2 directory. The [machine-readable report](reification-stage1a-results.json) includes fixture/source hashes. Eight native checks, five Python assertions, and four existing OLDAP validation checks pass.

| Capability | Observed result | Implementation consequence |
| --- | --- | --- |
| RDF 1.2 annotation syntax | Two stable reifiers of the same assertion parse correctly | No alternate storage encoding needed |
| TDB2 persistence | Reifiers and triple terms survive close/reopen | Native RDF 1.2 storage is suitable |
| Native project transfer | Ontology, shape, and data graphs round-trip isomorphically | Existing transfer implementation can carry this fixture |
| Different uses of isAt | Travel has annotation constraints; Building does not | Property-use context is part of model identity |
| SPARQL flat bindings | All three reifiers and typed dateTime values decode through QueryProcessor | Select reifier, base value, and fields explicitly |
| SPARQL triple binding | Jena emits type `triple`; QueryProcessor currently omits that binding | Do not use SELECT of whole triple terms in the new reader |
| Native Jena SHACL | Accepts missing reifiers and a missing required annotation field under the draft links | It cannot enforce the new rules automatically |
| pySHACL 0.31.0 | Accepts missing reifiers on an ordinary-RDF projection | It cannot replace the required traversal |
| Explicit targetNode | Both validators detect the missing field when targeting the reifier directly | Existing ordinary property constraints remain usable |
| Existing OLDAP checks | One date accepted; empty/two-value sets and invalid date rejected | Reuse current cardinality and datatype logic |

The OLDAP checks call the existing cardinality method and datatype constructor in an isolated scope. They are not end-to-end instance validation. The transfer check invokes current JenaProjectTransfer directly; it does not exercise HTTP authentication, a deployed service, or Python/YAML export paths. No live dataset or Redis instance was accessed. The tests establish the implementation path, not stage-3 acceptance.

The fixture deliberately omits OLDAP project registration/audit/Thing metadata. It is a capability fixture, not yet an importable OLDAP application ontology.

## Model identity and ownership

Use a small `ReifierShape` model class with `shape_iri`, audit metadata, and a collection of `PropertyClass` field definitions. Give DataModel an explicit `reifier_shapes` collection and `get_reifier_shapes()` accessor. Register it in the existing JSON serializer. Do not create an OWL business class or force inheritance from Thing.

The persistent identity of a property use is `(shapes graph IRI, owner shape IRI, predicate IRI)`. A standalone property definition remains identified separately. Keep independent PropertyClass instances for separate uses; never mutate a shared standalone object to attach class-local annotation rules.

ResourceClass currently assigns `inResourceClass` on its contained properties. PropertyClass read/create/update cache paths use the predicate IRI, while Redis keys are plain string representations. This cannot distinguish two uses of isAt. Stage 1B must prevent scoped properties from entering the standalone predicate cache. Cache them through their owning model/resource snapshot; a standalone PropertyClass.read must not return a class-local use. No new general cache-key registry is needed.

Annotation-field ownership is a shape IRI, not an OWL class IRI. Keep the existing ResourceClass context for class-owned properties and add a private explicit shape-owner context where needed by annotation fields. Reuse property-node rendering, but let ReifierShape coordinate its graph mutations. Never write OWL class restrictions against a reifier shape merely to reuse ResourceClass persistence.

Property uses store shape references, not independently mutable embedded copies. Resolve referenced shapes once per model operation through the existing connection and project-access rules. Final-review update: cache complete owner DataModel snapshots, including their ReifierShape definitions, to preserve existing read latency. Explicit shape reads and write-policy validation remain fresh and transaction-local; shape writes evict their owner model before mutation and at outer transaction completion. Active-transaction model reads bypass cache lookup and publication. This supersedes the initial no-persistent-definition-cache proposal. Changes to property attachments must invalidate the owner's ResourceClass and DataModel snapshots, including cached subclasses identified through the existing SHACL inheritance links. Unknown legacy cache entries must not bypass this rule after the new reader is introduced.

## Discovery and reference rules

- Write managed definitions as `a sh:NodeShape, oldap:ReifierShape`. Add the small `oldap:ReifierShape` marker class to oldap.trig as a subclass of sh:NodeShape. The marker distinguishes even unused/empty managed definitions; it adds no validation semantics.
- Accept an unmarked named NodeShape reached through sh:reifierShape if its entire structure fits the supported profile. A managed write normalizes the marker. Never reinterpret every targetless NodeShape as a reifier definition.
- Handle multiple rdf:type values explicitly. A marked shape carrying targetClass or ordinary resource-class identity is invalid for this OLDAP profile. Anonymous reifier-shape references and arbitrary target/logic/path constructs receive explicit unsupported-model errors.
- Resolve local references in the owning project and shared references in the existing accessible shared model. Reject missing/inaccessible references. Do not copy a shared shape into a consumer project or grant its consumers write access to it.
- Load definitions before resolving links so forward references work. Reject recursive annotation links in the initial profile. Duplicate predicates inside one annotation shape are ambiguous to the existing property map and must be rejected.
- Inherited annotation constraints accumulate: take the union of referenced shapes; required presence is true if any applicable definition requires it. A child cannot weaken its parent by writing false or removing the parent's reference. Different referenced shapes constrain the same reifier together. Preserve this conjunction rather than silently choosing one superclass.
- Retain distinct inherited definitions until validation; reject structural ambiguities that the existing model cannot represent. Do not promise a general satisfiability solver for combinations of SHACL constraints.

The marker is a deliberate refinement of the initial plan: references alone cannot discover an unreferenced managed shape. This concrete distinction justifies one OLDAP class, while the actual validation links remain standard draft vocabulary.

## Public model contract for stage 1B

| Layer | Field | Meaning |
| --- | --- | --- |
| RDF | sh:reifierShape | Set of named shape references on a property use |
| RDF | sh:reificationRequired | Optional explicit boolean on that use |
| Python PropertyClass | reifierShapes | Set of shape IRIs, following existing observable-set conventions |
| Python PropertyClass | reificationRequired | Xsd_boolean or None |
| Model API | reifierShapes | Top-level array of shape definitions, with iri, properties, and existing audit fields |
| API property definition | reifierShapes | Array of referenced shape IRIs |
| API property definition | reificationRequired | Boolean when explicitly present |
| YAML | reifier_shapes / reification_required | Names established in the working plan |

Keep `annotationProperties` for legacy appliesToProperty data; do not change its payload meaning. Shape definitions reuse the existing property payload conventions, including current read/write naming differences for class constraints. Stage 1B must document exact routes in the API's existing route style when implementing them; route naming does not affect this model contract.

For partial updates, omission leaves an attribute unchanged. An explicit empty reference array clears local references; null clears the local required flag; false remains an explicit false. Reject a final state with an explicit required flag but no local or inherited reifier shape. Apply all edits to a use together before validating the final state. Shape/property collections use explicit CRUD operations; omission from a model readback never means deletion. Validate duplicate/reference errors before issuing mutations.

First-version fields support existing datatype/class/node-kind constraints, cardinalities, language constraints, enumeration, patterns, lengths, and numeric bounds where already represented by PropertyClass. Reject unimplemented constraints rather than stripping them. Cross-property comparisons inside annotation shapes are deferred until scope-correct reuse is tested: validate_value currently accesses the instance's _values. The source also warrants targeted coverage of maxCount zero and lessThanOrEquals before claiming complete constraint parity. UI metadata such as name/description/order does not become a data constraint.

## Changes to existing models

The repository ontology inventory finds three appliesToProperty permission shapes and the declaration of statementShape, but no statementShape use in the scanned ontology/testdata files. This is not a claim about live deployments.

Keep appliesToProperty behavior unchanged. Reserve statementShape as legacy vocabulary; if encountered in managed model input, return an unsupported-legacy-model error with a migration explanation. Do not guess its meaning or silently discard it. Automatic alias conversion is deferred until real usage establishes equivalence.

Permit label/description/order/audit changes without data migration. Delete a reifier shape only if no supported model references it. For initial structural updates, conservatively reject changes to a shape or attachment while affected asserted data exists, unless a full conformance check proves the change safe. Shared references and inherited uses count. No automatic timestamp generation or annotation loss is acceptable when tightening/removing constraints.

## Instance write barrier before stage 3

The barrier belongs in the library's common mutation path and applies to direct users as well as the API. After effective model resolution and before mutation, detect reifier constraints on the source and destination class, including inherited uses. Reject create/update/delete/transform/restore until the complete relevant lifecycle path is supported. Return OldapErrorValue with a stable explanation; map it through the API's established client-error handling rather than introducing an unrelated exception hierarchy.

For existing resources, also check for business reifiers attached to asserted subject/property statements even if the model has lost a link. Exclude existing protected permission annotations from this business-feature check. This prevents older replacement and deletion paths from dropping externally imported annotations. Use graph-scoped scalar ASK/SELECT patterns; do not rely on cached model snapshots alone for this protection.

Audit entry points in objectfactory.create/update/delete/transform_class, resource_history.restore, batch/data import, and any direct writer bypass. Raw root project transfer is an administrative preservation path, not a claim of validated instance CRUD; keep its existing authorization and native preservation behavior. Stage 1B must test barrier coverage before exposing model writes to older instance clients. The barrier is specified here, not yet implemented.

## Reproduction

From the repository root, use a fully provisioned project environment:

```sh
python tools/reification/probe_capabilities.py \
  --java-home /path/to/jdk25 \
  --service-lib /path/to/oldap-jena-service/lib \
  --output /path/to/new-probe-directory
```

The service lib supplies the service classes and pinned Fuseki jar; the probe recompiles the current transfer source ahead of those classes. Output contains compiled probe classes, an isolated TDB2 store, raw result bindings, projections, and report.json. Keep these synthetic artifacts or remove only the probe's owned directory after inspection.

The accepted run used the sibling oldap-api virtualenv to execute this checkout's source because oldaplib's current virtualenv lacks the declared convertdate dependency. No dependency or environment was changed. Python libraries in the accepted run are RDFLib 7.6.0 and pySHACL 0.31.0. Native runtime and fixture hashes are retained in the report.

## Next implementation boundary

Proceed to stage 1B: implement ReifierShape, graph discovery, owner-scoped properties and cache handling, model CRUD, serialization and barrier tests in oldaplib; then create the corresponding oldap-api branch and expose the model contract. oldap-tools remains unchanged until stage 2. The remaining unknowns are implementation acceptance checks, not a need to replace OLDAP validation.
