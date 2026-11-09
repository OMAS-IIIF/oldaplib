# Hierarchical list filters on Jena

## Real read path

The owned Fuseki model probe now exercises actual `OldapList.read`, hierarchy
reconstruction in `get_nodes_from_list`, `OldapListNode.read` and
`ResourceInstance.search(hlfilter=...)`. These list readers already use explicit
project list graphs and need no RDF 1.2 syntax changes. Redis cache I/O alone is
replaced by misses/no-op writes; list/node readers are not mocked.

The fixture contains two lists with overlapping nested-set indices, a tree with
root, parent, two leaves and a sibling branch, and resources with single/multiple
assignments. Additional resources have denied, below-threshold or orphan grants,
and one has its assignment only in another project's graph. Fixtures are inserted
with private SPARQL; this does not validate public list mutation methods.

## Boolean correction in the Jena path

An initial real-Fuseki run passed loading and simple subtree checks but failed an
OR over two different properties. Mandatory property joins required both sides
to exist before the OR was evaluated. Reusing a property variable also forces
AND conditions to use the same assigned node, rather than allowing different
assigned nodes to satisfy different conditions.

The opt-in Jena branch now expresses each condition as a correlated `EXISTS`:

1. Does this resource have an assigned node through this property in project data?
2. Does that node belong to the selected list in the project's list graph?
3. Are its left/right indices inside the selected node's inclusive bounds?

Each condition has its own variables. The existing LogicOp tokens combine these
independent booleans, including parentheses. This preserves OR when a second
property is absent and allows AND across multiple assignments of one property.
EXISTS does not multiply result rows. Root-resource permission filtering remains
the shared RDF 1.2 search access check; list metadata has no new resource ACL.

The correction is deliberately limited to the Jena branch. The legacy GraphDB
list query remains unchanged and should receive a separate regression review
before any equivalent correction there. Public signatures and return types,
HListNodeRef and legacy HListNode input forms remain unchanged. No API, harvester
or tools signature adaptation is needed.

## Validation

86 integration checks pass: the previous 69 and 17 new list checks. New coverage:
real hierarchy and node bounds; inclusive parent/descendant and exact leaf
membership; root matching; list-only search; overlapping-index list isolation;
legacy references; OR with absent properties; AND with different assigned nodes;
OR across lists; parentheses; combination with ordinary filters; distinct paged
results and unpaged count; missing list/node errors; and current-role removal.
Exact expected result sets also exclude denied, restricted, orphan and
other-project assignments. Every matches check compares both results and count.

The first pre-fix run failed the OR assertion, demonstrating that the new fixture
exercises the corrected behavior. The accepted run is
`~/Library/Application Support/OLDAP-Jena/probes/j12-hlists-20261028-03`.
See `jena-hierarchical-list-filters-results.json` for all checks. Run
`tools/migration/probe_model_reads.py` with the existing jar and a fresh output
folder to reproduce; it invokes `probe_hlist_checks.py` after structured search.
All servers/datasets are private and closed on completion; no shared GraphDB or
Redis service is used.

60 offline tests + 7 subtests also pass. The 12 earlier GraphDB search-query
comparisons plus list-filter result/count comparisons match HEAD modulo
whitespace. The refreshed RDF* inventory includes the shifted source locations.

## Limits and next steps

This proves valid, stable nested-set list reads and filtering. It does not prove
list creation/move/delete, index maintenance, malformed-index handling, concurrent
list edits across metadata/data reads, or Redis cache invalidation. No global
reasoner, list ACL or public backend switch was introduced. Full-text, remaining
media/read/write paths and broader inference remain migration gates. No commit,
push or deployment was performed.
