# Performance optimization strategy

OLDAP performance work follows an incremental, measurement-led approach. Each
step should improve a reusable backend boundary before application-specific
work is added, preserve existing public contracts where possible, and include
focused regression coverage.

## Principles

- Measure representative operations before and after each change.
- Reduce redundant triplestore work before introducing broader caches.
- Keep caches bounded and define their freshness or invalidation semantics.
- Preserve API response formats during internal read-path improvements.
- Prefer bulk or summary contracts over client-side N+1 request patterns.
- Optimize validation separately for read and write/import workloads.

## Incremental roadmap

1. **Hierarchical-list context preparation.** Discover the special list-node
   QName prefixes at most once per connection and project. Resource reads must
   not load complete lists merely to prepare `QueryProcessor`. **Completed:**
   list discovery is connection-scoped and full-list loading was removed from
   the generic read path.
2. **Single-resource API read path.** Remove the preliminary standalone
   `rdf:type` lookup and avoid repeated parsing/model resolution while retaining
   the current API representation. **Completed:** one permission-checked
   CONSTRUCT now returns both reasoning-visible data and explicit project-graph
   type assertions through a structured factory result; the same CONSTRUCT
   also carries the complete attached-role permission map, eliminating the
   former follow-up roles query.
3. **Search summaries and batching.** Provide a backend contract that returns
   the card metadata required by clients without one resource request per hit.
   **Completed:** `ResourceInstanceFactory.read_summaries()` performs one
   permission-filtered CONSTRUCT for up to 100 known resource IRIs and a
   caller-selected property set. Missing and unreadable resources are omitted
   identically, and readable results retain request order.
4. **Application request reuse.** Deduplicate concurrent SALSAH requests and
   cache stable project-model information with explicit lifetime rules.
   **In progress:** SALSAH search cards and linked-record previews consume the
   bounded summary endpoint instead of issuing per-resource metadata and media
   requests.
5. **Write/import validation.** Reuse compiled XML Schema validators and
   benchmark bulk ingest independently from interactive reads.

The steps are deliberately ordered by shared benefit: `oldaplib` first,
`oldap-api` second, and application-specific SALSAH optimizations last.

The summary primitive removes per-resource GraphDB reads. It deliberately does
not replace complete resource reads for editing, nor does it remove initial
datamodel construction or unrelated application requests; those boundaries
remain separately measurable.


## Measured warm-read optimization (2026-09-29)

The API baseline found 563 Redis reads and 524 Project.read invocations for one
resource, although GraphDB needed only three queries. The implementation now:

- Shares a thread-safe Redis connection pool per exact URL in each process,
  retaining at most eight configurations and 32 connections per pool. Pool
  exhaustion raises the redis-py connection error; this is not a throughput
  promise. Configuration changes select a different client. Forked children
  discard inherited clients and locks. Eviction never closes a borrowed client.
- Rechecks cache/writer separation on wrapper construction and before flush.
  Distinct database numbers are recognized with redis-py's own URL parser;
  same-database configurations still require fresh server identity checks.
- Reuses Project snapshots only during synchronous DataModel.read and resource
  factory construction. Nested reads on the same connection share snapshots;
  independent operations, threads and connections do not. Every result is a
  separate deep copy retaining the caller's connection and its own notifiers
  and changeset. ignore_cache=True bypasses and refreshes any successful snapshot.

The short-lived scope is for model construction, never mutations or transaction
lifetimes. Nothing persists on a long-lived Connection. Complete mutable models,
permissions and factories are not cached globally. RDF queries and response
contracts are unchanged. The retained Redis wire format is unchanged.

For measurement methodology, exact request catalogs and before/after evidence,
see the sibling API repository's doc/performance/ directory. Local development
activation is separate from publishing a release; record its precise source
hashes because a development wheel may retain the published version number.
