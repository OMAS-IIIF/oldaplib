# Structured search on Jena

Follow-up: [hierarchical list filters](jena-hierarchical-list-filters.md) now have real list/node acceptance coverage.
The results below describe the earlier structured-search milestone.

## Scope and design

The real `ResourceInstance.search` now has an opt-in RDF 1.2 path. Its public
signature and result/count shapes are unchanged. Normal connections retain
GraphDB; only the migration test connection sets the internal
`_resource_search_rdf12` capability. This does not activate a production backend.
Harvester, tools and API callers require no signature changes.

Two local helpers make the differences visible without duplicating the search
algorithm: `data_pattern` scopes property matches to the project data graph;
`class_pattern` matches an asserted class followed by `rdfs:subClassOf*` in the
merged project/shared/system ontology graphs. Root and linked-resource permission
patterns require asserted role links plus matching RDF 1.2 reifiers. Current role
membership and numeric permission values still come from the admin graph.

Projection, boolean expressions, count aggregation and pagination retain the
existing structure. The page selects distinct resources before expanding their
properties; Jena also explicitly orders the outer rows, because ordering only a
subquery does not guarantee final row order. Counts ignore page size and offset.
Search retains its role-based policy without a creator exception.

## Important semantics

- Missing optional values cannot satisfy comparisons. AND/OR and NOT_EXISTS
  remain explicit in the query.
- In the Jena path, linked NOT_EXISTS additionally requires a bound target.
  An absent or denied link must not behave like a readable target whose property
  is absent. This is a deliberate correctness guard; the legacy GraphDB query
  was not changed. Linked permissions remain opt-in via the existing
  `checkLinkedPermissions` argument: false still permits filtering on a linked
  target without checking that target's grants, as before.
- Superclass filtering follows paths across selected schema graphs. Returned
  `resclass` comes from asserted project data. This is limited subclass support,
  not full owl-max entailment or a guarantee for multiply asserted classes.
- GraphDB connector full-text filters raise a clear OldapErrorValue in the Jena
  prototype before a query is issued. Full-text is not silently treated as an
  empty result. The separate `search_fulltext` method is still unmigrated.

## Evidence

`probe_model_reads.py` invokes `probe_search_checks.py` against its private
Fuseki/TDB2 dataset after the model/single/batch checks. All 69 checks pass:
35 earlier checks plus 34 search checks. This includes direct text and
numeric operators, AND/OR, property absence, superclass paths across project and
shared ontologies, root/linked access checks, current-role removal, cross-project
isolation, projection, duplicate grants, multiple values, default/sorted pages,
count parity, Dating overlap and Dating ordering with absent values last.

The probe uses actual library model/search/result processing. Only Redis cache
I/O is replaced. All servers and data belong to the probe; it closes the owned
processes and never queries shared GraphDB/Redis. Accepted output:
`~/Library/Application Support/OLDAP-Jena/probes/j12-search-20261028-02`.
See `jena-structured-search-results.json`; total read requests: 370.

60 existing offline tests and 7 subtests pass. Twelve generated GraphDB queries
were compared with HEAD and match modulo whitespace: result/count variants for
class-only, property projection/sorting, OR/absence, linked permissions/classes,
Dating filters/sorting and connector full-text. Public search signature unchanged.

Reproduce using the model probe command in `jena-model-resource-reads.md`, choosing
a fresh output directory. The helper module is exercised through that runner.

## Remaining work

Hierarchical-list filter acceptance is documented in the linked follow-up, including
a Jena-specific correction to boolean combinations. Language-tagged boolean
combinations, all Dating operators/linked Dating and multiply asserted class
selection are not comprehensively covered here. No claim of universal search
or GraphDB inference parity is made.

Full-text, media-specific lookups, broader OWL behavior and remaining RDF* write
paths remain pending. Production backend wiring, query limits, performance and
cache/recovery consistency are separate gates. No commit, push or deployment.
