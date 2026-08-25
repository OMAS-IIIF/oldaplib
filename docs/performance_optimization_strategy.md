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
   type assertions through a structured factory result.
3. **Search summaries and batching.** Provide a backend contract that returns
   the card metadata required by clients without one resource request per hit.
4. **Application request reuse.** Deduplicate concurrent SALSAH requests and
   cache stable project-model information with explicit lifetime rules.
5. **Write/import validation.** Reuse compiled XML Schema validators and
   benchmark bulk ingest independently from interactive reads.

The steps are deliberately ordered by shared benefit: `oldaplib` first,
`oldap-api` second, and application-specific SALSAH optimizations last.
