# Reification properties implementation plan

Status: stages 1A, 1B, 2, 3 and 4 accepted locally; publication/deployment separate. Updated: 2026-11-14.

OLDAP will support project-defined annotations of property assertions using named SHACL reifier shapes. Delivery follows four stages: model management, ontology YAML, instance lifecycle, and instance search. Each stage has a separate acceptance gate. This file is the working checklist and the source of truth for scope, decisions, and remaining work.

The owner accepted the overall direction. The [stage 1A contract and evidence](reification-stage1a.md) freezes model identity, public model fields, validation ownership, discovery, and compatibility rules for stage 1B. Instance and search payloads remain for their respective stages.

## Branch and delivery strategy

- Planning branch: `codex/reification-properties`, created locally in oldaplib from `main` at `717feec`.
- Keep this plan and the library implementation together. Create corresponding branches in oldap-api and oldap-tools when their implementation starts, after inspecting their current instructions and worktrees. All three repositories now use the corresponding local branch; no commits or publication were performed during stages 1–3.
- Use reviewable commits for stages 1A, 1B, 2, 3, and 4. Record accepted commit IDs and checks in the delivery record below. Prefer incremental integration once each gate passes over an indefinitely diverging branch.
- Update each affected repository's `CODEX_LOG.md` after relevant changes and `codex.md` when architecture or public workflows change. Keep detailed progress here instead of duplicating this entire plan across repositories.
- Publication and deployment are separate from implementation. Model-management support can be delivered before instance support only with the explicit write barrier described below.

## Standards baseline and OLDAP profile

The [SHACL 1.2 Core Working Draft of 10 November 2026](https://www.w3.org/TR/2026/WD-shacl12-core-20261110/) defines `sh:reifierShape` and `sh:reificationRequired`. Reifier shapes constrain every reifier of each value's assertion; required reification means at least one reifier per assertion. The path must be an IRI. These are draft semantics, not a final Recommendation.

The [RDF 1.2 Turtle Working Draft of 11 November 2026](https://www.w3.org/TR/2026/WD-rdf12-turtle-20261111/) defines annotation syntax and its expansion into an asserted base triple plus a resource linked by `rdf:reifies` to a triple term. Multiple reifiers can describe the same triple. Pin these dated references and review changes before releasing the feature.

Proposed OLDAP profile:

- Use `sh:reifierShape` as the canonical model link and `sh:reificationRequired` as its optional boolean. Store shape references as a set; each referenced shape applies, rather than offering alternatives. Preserve explicit `false` through serializers and updates.
- Introduce a small `ReifierShape` domain object with a stable shape IRI, metadata, and existing property definitions. It is not a `ResourceClass`, does not require `sh:targetClass`, and does not acquire Thing audit or permission fields as instance requirements.
- Keep annotation constraints at the property-use site. Reusing a predicate must not accidentally impose the same annotations on every resource class. Resolve how this fits existing PropertyClass identity and cache behavior before coding; do not add a general property-wrapper hierarchy without a demonstrated need.
- Initially support named shapes, simple forward predicates, and annotation fields using the existing supported property constraints. Support both literal and IRI base values. Reject nested reification and unsupported shape constructs explicitly rather than losing them on save.
- Define project-local shapes in the project's shapes graph. Allow references to accessible shared shapes through existing project-resolution rules. Shared definitions remain owned by their source project; consumers cannot modify them indirectly. Defer arbitrary cross-project dependency discovery.
- For managed instance data, keep the asserted base triple and its reifiers in the same project data graph. Generate stable reifier IRIs; allow multiple independent reifiers for the same assertion. Each managed reifier belongs to one assertion. This ownership rule is an OLDAP restriction, not a general RDF restriction.
- Reifier metadata inherits the owning instance's access control. Permission reifiers remain a protected existing subsystem; generic business annotations cannot edit grants.
- Ordinary property cardinality counts base values. Annotation property cardinality counts values on each reifier. No implicit ordering or one-reifier-per-triple rule.
- Keep OLDAP's own validation as explicitly confirmed by the owner on 2026-11-13. Introduce the missing reifier traversal and reuse existing field checks. Replacing validation requires concrete benefits and a separate architecture decision.
- Mark managed definitions with oldap:ReifierShape in addition to sh:NodeShape so unused definitions are discoverable. Standard draft predicates still express all reification constraints; see the stage 1A contract for ownership and cache rules.

## Current implementation boundaries

| Area | Existing location | Consequence |
| --- | --- | --- |
| Legacy annotation model | `oldaplib/ontologies/oldap.trig`, `oldaplib/src/propertyclass.py` | `oldap:appliesToProperty` represents existing permission annotation properties. |
| Reserved model link | `oldaplib/ontologies/oldap.trig` | `oldap:statementShape` is declared; the inspected library source has no matching handler. Inventory actual usage before defining migration behavior. |
| Model reader | `oldaplib/src/datamodel.py` | Special-cases appliesToProperty; other NodeShapes are treated as resource classes requiring targetClass. |
| Property model | `oldaplib/src/enums/propertyclassattr.py`, `oldaplib/src/propertyclass.py`, `oldaplib/src/resourceclass.py` | New attributes, use-site semantics, serialization, change tracking, and cache dependencies need explicit support. |
| Model API | `../oldap-api/oldap_api/views/datamodelling_views.py` | Already exposes annotationProperties; preserve its legacy meaning and add a distinct reifier-shape contract. |
| YAML | `../oldap-tools/src/oldap_tools/ontology.py`, `ontology_api.py`, `ontology_api_dump.py`, `schemas/ontology_schema.yaml` | Both direct and API transports, including exports and update planning, need coverage. |
| Instances and search | `oldaplib/src/objectfactory.py`, `../oldap-api/oldap_api/views/instance_views.py` | Generic CRUD, response encoding, permissions, and search must handle reifier identity. |
| History | `oldaplib/src/resource_history.py` | Annotation changes must participate in history and restore. |

## Stage 1 model management in oldaplib and oldap-api

Outcome: a project ontology can define, read, modify, export, and delete annotation shapes without losing information or confusing them with resource classes.

### Stage 1A contract and capability checks

- [x] Freeze the minimal profile, model identity, use-site ownership, JSON field names, deletion rules, and supported constraints. See the stage 1A contract for scoped property ownership and cache rules.
- [x] Build an isolated Travel fixture with GeographicLocation, isAt, VisitAnnotationShape, Building with a different policy, and two visits to one location: oldaplib/testdata/reification/travel.trig.
- [x] Probe pinned Jena parser/storage/SPARQL, Python result decoding, native transfer source, external validators, and existing OLDAP cardinality/datatype checks. Evidence: reification-stage1a-results.json. HTTP transport and end-to-end lifecycle remain later acceptance work.
- [x] Inventory repository ontology/testdata legacy usage. Retain permission semantics; unsupported legacy statementShape input must not be silently rewritten. No live-model inventory claimed.
- [x] Define shared references, inherited conjunction, managed unused shapes, and unsupported-model errors in the stage 1A contract.
- [x] Define the pre-stage-3 library write barrier, inherited/source/destination model checks, and existing business-reifier detection. Implementation and coverage tests remain in 1B.

Gate 1A passed: the contract and capability evidence establish native RDF storage/transfer and an OLDAP validation extension path. Seventeen checks pass. External validators do not automatically enforce the draft links; OLDAP remains the validator. Complete lifecycle tests remain in stage 3.

### Stage 1B model implementation

- [x] Add ReifierShape, DataModel access, and property-use references with typed interfaces, structured docstrings, serialization, deepcopy, notifications, changesets, and dependency-aware cache invalidation.
- [x] Extend graph queries and writers for named shapes, including unreferenced managed definitions. Preserve shape IRIs and existing metadata conventions; distinguish these from OWL class IRIs.
- [x] Validate reference existence and graph ownership. Reject deletion of referenced shapes and unsafe tightening/removal of constraints on existing data; return actionable errors rather than silently migrating data.
- [x] Add API read/create/update/delete operations for shape definitions and attachment to properties. Keep existing annotationProperties responses compatible. Document omission, explicit removal, replacement, and error semantics in OpenAPI.
- [x] Keep oldap:statementShape as legacy vocabulary; explicitly reject its use in managed input for now rather than guessing a translation. A later migration requires confirmed stored meaning. New exports use the canonical SHACL predicates.
- [x] Implement and test the write barrier. Update model documentation and an isolated example ontology, without activating constraints in live project ontologies.

Gate 1B: library and API round trips preserve the complete model; updates invalidate cached dependent models; deletion-in-use and unsupported input fail clearly. Tests cover two class contexts sharing a predicate, shared references, multiple referenced shapes, optional/required/false states, metadata-only updates, and legacy permission model regression. Existing unannotated model API fixtures remain compatible.

Local gate 1B passed on 2026-11-14: 83 focused tests and seven isolated native Jena checks. [Implementation, API semantics and limitations](reification-stage1b.md). No release or deployment; stage 2 is next.

## Stage 2 ontology YAML in oldap-tools

Outcome: users can author, validate, import, update, and export the same model in readable YAML through both transports.

Implemented syntax follows existing snake_case keys. A single list form avoids singular/plural aliases:

```yaml
ontology:
  project:
    shortname: travel
  reifier_shapes:
    travel:VisitAnnotationShape:
      properties:
        - iri: travel:dateTime
          datatype: xsd:dateTime
          min_count: 1
          max_count: 1
  classes:
    travel:GeographicLocation: {}
    travel:Travel:
      properties:
        - iri: travel:isAt
          to_class: travel:GeographicLocation
          reifier_shapes:
            - travel:VisitAnnotationShape
          reification_required: true
```

This example assumes an existing project. A new project also needs the existing required project fields. The complete runnable fixture is `../oldap-tools/examples/ontology/travel-reification.yaml`.

- [x] Extend the YAML schema, property-key mapping, model builder, direct synchronizer, API planner, and both export paths.
- [x] Validate the entire desired model and references before writing. Create shapes before their references; remove references before eligible shape deletion. Resolve forward references without requiring YAML document ordering.
- [x] Preserve existing update-mode rules: omitted definitions are not deletions; explicit removal follows the tools' remove-unused behavior and model in-use checks. Distinguish absent, false, and clear operations.
- [x] Make plans/dry runs show shape changes and affected class/property uses. API operations remain separate transactions: report partial completion accurately, support safe retry, and do not imply whole-file atomicity.
- [x] Ensure backups and dumps contain all managed shapes and references, including shared references without copying ownership. Document the new syntax in `../oldap-tools/docs/ontology-yaml.md` with a complete runnable fixture.

Gate 2: YAML → library/API → RDF → YAML preserves model semantics for both transports. Reimport produces no changes. Invalid references and unsupported fields fail before mutations. A mid-import failure can be diagnosed and resumed without duplicate shapes. Existing Fasnacht YAML fixtures remain unchanged in meaning.

Local gate 2 passed on 2026-11-14: 199 tools tests and seven subtests, including direct/library and Flask API round trips on RDFLib and pinned native Jena/TDB2, plus 84 focused library/API regressions. Definitions omitted from YAML are retained; explicit null shape deletion requires `--remove-unused`. [Contract and acceptance](../../oldap-tools/docs/reification-stage2.md). No publication or deployment; stage 3 is next.

## Stage 3 instance lifecycle

Outcome: create, read, modify, and delete annotations on both object and literal property values through library and API, with full validation and history.

- [x] Freeze a small typed representation containing the base value, reifier IRI, and annotation property values. Multiple annotation records may share a base value. Keep existing plain property-value interfaces compatible; add explicit annotation operations instead of changing every scalar into a wrapper.
- [x] Define and document JSON encoding using existing RDF-term conventions. Allocate reifier IDs on creation; target updates/deletes by ID and verify graph, owning subject, predicate, and value. Never locate a unique annotation solely by the base triple.
- [x] Read and serialize complete annotation groups. Define a controlled import policy for blank-node reifiers and externally created/shared reifiers before accepting them as writable managed data; never silently merge or renumber identities during reads.
- [x] Create asserted base values and reifiers atomically. Apply annotation edits, instance modification timestamps, validation, and history within the existing transaction boundary and concurrency guard. Reuse supported datatype/class/cardinality checks.
- [x] Preserve the parent instance's authorization requirements for reads and writes. Check link targets using existing visibility rules; prevent generic operations on protected permission predicates/reifiers.
- [x] Implement explicit deletion semantics: removing one reifier retains the base triple and other reifiers; removing a base value removes its owned reifiers; removing an instance removes its owned annotations. Reject deletion of the last reifier when reification is required and the base assertion remains. Guard external inbound references rather than cascading across ownership boundaries.
- [x] Record annotation-only changes in history; restore assertions and annotations consistently with current model validation and existing permissions. Ensure no-op writes remain no-ops and stale writers cannot overwrite annotation changes.
- [x] Audit transformation, copying, batch operations, data YAML/import/export, and project transfer for preservation. Implement support or explicit rejection before enabling the feature on those paths. Property renames and changes of base values must not leave orphan reifiers.
- [x] Remove the stage-1 write barrier only after supported mutation paths enforce the complete profile. Update API docs and library examples together.

Gate 3: two visits to the same location survive create/read/update/delete independently. Test missing/invalid timestamps, multiple fields on one reifier, optional annotations, literal base values, unauthorized access, cross-graph IDs, transaction rollback, concurrent edits, history restore, deletion cleanup, and transfer round trips. Existing plain CRUD and permission operations retain their behavior. Use a real isolated Jena dataset for integration evidence, not mocks alone.

Local gate 3 passed on 2026-11-14: 18 native lifecycle/performance tests, 100 focused library/API tests, and 200 tools tests plus seven subtests. [Contract, limits and acceptance](reification-stage3.md); [performance receipt](reification-stage3-performance.json). Ordinary reads/searches retain identical queries and results, with no statistically resolved slowdown in the local paired benchmark. Unsupported transforms and instance-data YAML are explicitly rejected. All work remains local.

## Stage 4 instance search

Outcome: structured search can constrain an assertion and its annotations together, without changing existing instance result cardinality or permissions.

- [x] Add an explicit reifier-filter group to the existing typed filter/API contract. One group binds one base assertion and one reifier; multiple constraints within that group must match that same reifier. Separate groups can express separate visits.
- [x] First support base property/value matching, annotation comparison/ranges, and annotation existence/absence. Resolve fields through the model and use existing RDF-term escaping and datatype validation.
- [x] Compile correlated, graph-scoped EXISTS conditions, anchored to the asserted base triple. Do not match orphan annotations or combine annotation values from different reifiers accidentally.
- [x] Keep instance-level DISTINCT, count, pagination, and permission behavior. Make annotation projection an explicit option, preserving grouping and stable reifier IDs without multiplying result rows.
- [x] Define missing-value and multi-reifier semantics before adding annotation sorting. Defer sorting, aggregation, and fulltext indexing unless a concrete requirement justifies them; do not choose an arbitrary timestamp implicitly.
- [x] Document filters with examples and explain existential same-reifier behavior in the search documentation. Compare query plans and bounded timings on representative data with multiple annotations per assertion.

Gate 4: searches such as “Travel at A with a timestamp within this interval” return correct instances. Include a negative fixture where two different reifiers each satisfy only half of a filter group. Verify correct count/paging with duplicate matches, missing annotations, project isolation, linked-target visibility, and no regression of existing unannotated searches.

Local gate 4 passed on 2026-11-14: 11 search/parser/evidence tests, 18 lifecycle/performance tests and 122 focused library/API regressions plus two subtests. [Search contract and acceptance](reification-stage4.md), [ordinary-path performance](reification-stage4-performance.json) and [native query algebra/timings](reification-stage4-search.json). Ordinary queries/results remain identical; no statistically resolved slowdown against stage 3. Annotation search uses explicit AND groups, class-scoped model resolution and optional complete page projection. Sorting/fulltext/aggregation remain deferred.

## Acceptance and release sequence

| Milestone | Prerequisite | Deliverable |
| --- | --- | --- |
| M1 | Gates 1A and 1B | Library/API model CRUD, explicit capability boundary, documented model format |
| M2 | M1 and gate 2 | YAML authoring and semantic round trips through both transports |
| M3 | M2 and gate 3 | Complete instance lifecycle, validation, authorization, history, transfer |
| M4 | M3 and gate 4 | Structured annotation search with correct grouping and pagination |

For each release, pin compatible library/API/tools versions and verify installed artifacts. Do not let an older writer silently drop annotations; capability checks or a documented minimum writer version must block unsafe combinations. Enable a small test project first. Existing project ontologies and permission annotations require no automatic migration. A rollback after annotated data exists must retain the data and restrict incompatible writers; reverting binaries alone is not sufficient.

Frontend editors, a new Visit business class, arbitrary SHACL execution, recursive annotations, separate annotation ACLs, and broad permission-model migration are outside these four stages.

## Working record

Update this section after each work package. Mark tasks above complete only with a linked test result or implementation commit. Keep stable decisions in the profile and record unresolved decisions here with the stage that must settle them.

| Work package | Status | Evidence or next action |
| --- | --- | --- |
| Planning | Complete | Repository boundaries inspected; working plan and branch created |
| 1A contract and capabilities | Complete | reification-stage1a.md and reification-stage1a-results.json; 17 checks pass |
| 1B model CRUD | Complete locally | reification-stage1b.md |
| 2 YAML | Complete locally | ../oldap-tools/docs/reification-stage2.md |
| 3 instances | Complete locally | reification-stage3.md and reification-stage3-performance.json |
| 4 search | Complete locally | reification-stage4.md and both stage-4 receipts |
| Final source review | Complete locally | reification-final-check.md; two full passes and regression/package/performance checks |
| Publication and deployment | Not started | Record compatible artifact versions and rollout evidence per milestone |

Stage 3 fixes the typed JSON contract and managed-identity ownership rules; external/blank/shared reifiers remain read-only. Stage 4 now fixes the conjunctive same-reifier grammar, missing-value semantics and explicit page projection while preserving ordinary read/search query text and counts.

All four implementation stages are accepted locally. The final source review is documented in reification-final-check.md. Next is a separate coordinated release decision, installed-artifact and live acceptance; no live model, installed dependency version or deployment was changed.
