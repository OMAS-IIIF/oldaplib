# Batch resource summaries on Jena

Follow-up: [structured search](jena-structured-search.md) now has a separate acceptance proof.
The results below describe the original batch milestone.

## Scope and compatibility

`ResourceInstanceFactory.read_summaries(iris, include_properties=())` now has an
opt-in RDF 1.2 query path, exercised through the real factory on owned Fuseki/TDB2.
The public signature, return objects, input validation, ordering and permission
policy are unchanged. Harvester, tools and HTTP API callers need no adaptation
for this step. The normal production connection still uses GraphDB.

`IConnection._resource_summaries_query` is a concrete internal extension point,
following the single-resource read boundary. `_build_resource_summaries_query`
keeps the existing CONSTRUCT shape and provides explicit annotation/dataset
variants. The migration connection selects `rdf12=True`; other connections
inherit the GraphDB default. There is no runtime query-string rewriting.

The GraphDB queries were compared with HEAD for a single resource with no extra
properties and a mixed QName/full-IRI batch with multiple properties: identical
modulo whitespace. The existing mock query test now calls the real default hook.

## Readable permission and inference rules

The query still follows these steps:

1. Restrict resources to the requested VALUES batch.
2. Accept the creator, or require a current user role with at least DATA_VIEW.
3. Require the resource's asserted role link plus the matching RDF 1.2 permission
   reifier in the project's data graph.
4. Return selected properties, asserted types and complete role/permission pairs.
5. Add superclass types from project/shared/system ontology graphs, as in the
   previous single-resource proof; preserve the concrete/asserted type separately.

Data from another project's graph cannot enter the result. Grant pairs use the
existing blank-node binding, which distinguishes permissions even when the same
roles occur on multiple resources with different permission values. The creator
exception is intentionally retained for summaries, matching read_data/class
reads; it does not change the stricter factory.read policy.

This remains scoped subclass entailment, not GraphDB owl-max equivalence.

## Validation

The extended `tools/migration/probe_model_reads.py` passes 35 checks: the previous
19 model/single-read checks and 16 new batch checks. Only Redis cache I/O is
replaced; real model parsing, factory behavior, SPARQL execution and hydration run.
The dataset, identities and HTTP processes are private to the probe and closed
on completion. Shared GraphDB and Redis are not used.

New coverage includes:

- One HTTP READ for a mixed batch after model/list context initialization.
- Input order, duplicate collapse and full-IRI aliases.
- Missing, denied, orphan-reifier and below-threshold omission.
- An unrequested creator-owned resource cannot escape the VALUES restriction.
- Requested-property projection and project isolation.
- Concrete/asserted/inferred types and opposing multi-resource role grants.
- Creator access, type-only summaries and wholly unreadable batches.
- Empty batches and invalid scalar/resource/property limits without requests.
- The maximum 100-resource batch using one query, without phantom results.
- Current role removal, while retaining explicit creator access.

60 existing offline tests plus 7 subtests pass. See
`jena-batch-resource-reads-results.json` for the integration checks. The owned run
is `~/Library/Application Support/OLDAP-Jena/probes/j12-batch-reads-20261028-01`.
Reuse the commands in `jena-model-resource-reads.md` with a fresh output directory.
The one-query claim concerns the batch after initialization, not cold model
loading or an end-to-end HTTP API latency benchmark.

## Next step and limits

Structured search/filter/count, media lookups, full-text search and broader OWL
inference remain open. Search has additional default-graph assumptions and is
kept as a separate change so its authorization/count/pagination behavior can be
verified independently. Dating expansion is retained but is not newly exercised
by this cat-model probe. Production backend wiring and cache consistency also
remain open. No deployment, commit or push was performed.
