# Bounded Jena read entailment

**Step 2 implemented (2026-10-30):** class ancestry and subproperty reads follow
[the OLDAP semantics profile](oldap-semantics-profile.md). Class/property
equivalence is not evaluated. Legacy inverse axioms remain active until step 3
provides modeled inverse fields. No general OWL reasoner or materialization is
enabled. Public API routes and library signatures are unchanged. GraphDB retains
its existing behavior, so intentional content differences are now expected.

## Read the implementation

- `oldaplib/src/helpers/jena_entailment.py` defines the common class path, class
  selection, schema selection and inverse-value pattern. It is deliberately a
  small query helper, not a new reasoning framework.
- `JenaConnection._resource_schema_graphs()` resolves external vocabularies from
  `oldap:ExternalOntology`/`oldap:prefix` declarations in this project's, shared's
  and OLDAP's SHACL graphs. These are model metadata reads, not SHACL validation.
- `objectfactory.py` uses the helpers in single/batch reads and structured search.
  Media classification and archive class checks use the same class selection.

Only project/shared/base ontology graphs and explicitly registered vocabulary
`urn:oldap:vocab:<prefix>` graphs become the query's default schema graph. Resource
data and administration stay in separately named graphs. Vocabulary files must
already be provisioned in the target; the reader does not fetch remote ontologies.
A registration is resolved on each query build, using the caller's transaction
when active. Outside a transaction, discovery and the data query are separate
reads, not a coordinated snapshot. No new persistent cache or invalidation
mechanism is introduced.

## Classes

The class path is:

```sparql
rdfs:subClassOf+
```

It follows superclasses only, not subclass edges downwards or equivalence edges.
For example, an asserted `chama:Person` can yield `schema:Person` and
`schema:Thing`, but no longer equivalence-only `foaf:Person`. An explicitly
asserted `foaf:Person` remains queryable.
Asserted resource types remain distinct from `virtual:inferredTypes`. Cycles are
handled by SPARQL path evaluation and do not create an infinite recursion.

Class searches first collect distinct asserted types from the project data, test
that small set against the selected hierarchy, then join authorized instances.
The requested type matches by equality even without schema triples. The class
selection is placed before the instance/ACL joins so it is not reevaluated for
every result. Bound linked-resource/media/archive checks use correlated paths.
A 1,000-person rehearsal exposed the cost of repeating paths or enumerating all
unused classes of large external vocabularies.
Single/batch hydration starts its class paths at the resources' asserted types.

## Subproperties

Search filters, absence checks, linked filters and sort keys match direct values
plus narrower asserted predicates through `rdfs:subPropertyOf+`. Direct matches
remain independent of schema declarations. Property equivalence is ignored.
Multiple paths do not multiply distinct resource counts.

Single/summary hydration additionally reads project/shared/base SHACL named
graphs. Added superproperty values must have a matching `sh:property`/`sh:path`
on a shape whose `sh:targetClass` is the asserted class or a superclass. Direct
assertions retain their existing treatment. An arbitrary external superproperty
is not automatically a JSON response field. No validation engine is involved.

The hierarchy branch rejects paths through protected type/grant/permission/
provenance predicates, including endpoints. It conservatively rejects the whole
source/target pair if any route passes through such a predicate, even when a
harmless alternative route also exists. Authorization itself never uses this
value expansion. No schema-dependent fast path or new cache is introduced.

## Legacy inverse properties (replacement pending step 3)

If the selected ontology declares `chama:hasKnowledgeContribution owl:inverseOf
chama:describes`, an asserted contribution-to-photo `describes` link also produces
the photo-to-contribution backlink on read. Either direction of the inverse axiom
is accepted; the property names are read from the ontology. No Chama-specific
property or class is built into library code.

The inverse branch reads incoming triples from the same project data graph. It
joins them with inverse definitions in the selected schema graph. CONSTRUCT/SET
semantics prevent duplicated values when an asserted and inverse link coincide.
Only one declared inverse step is supported; this is not a property-chain or
`owl:equivalentProperty` reasoner.

Root and linked-resource authorization checks remain separate, asserted queries.
Neither inverse declarations nor class rules may manufacture ACL memberships,
grants, grant values, asserted types or OLDAP provenance fields. A returned
linked IRI does not authorize reading the linked object, exactly as for an
asserted link. The existing API can return links to objects not readable by the
caller; this change does not expand their payloads.

## Existing API details deliberately preserved

- Individual and summary reads return derived values and inferred type lists.
- Structured-search filters (including linked filters, absence checks and sort
  keys) can match subproperty and legacy inverse values. Class filters follow
  the selected subclass hierarchy. Counts and paging still operate on distinct roots.
- Search `includeProperties` projections retain the existing **asserted-only**
  behavior. GraphDB also omits an inverse-only projected value even if its filter
  matches that value. This was verified rather than silently changing responses.
- Fulltext token indexes continue indexing configured asserted predicate paths.
  Inverse-property text-index expansion is not added by these read rules.
- Mutation/permission helpers still use explicit triples. No inferred link or
  class is persisted as part of a migration import.

These rules do not cover OWL restrictions, domain/range typing, `owl:sameAs`,
property chains or arbitrary OWL constructs. Unsupported axioms are not evaluated
by this helper. Future compatibility work should be driven by actual source
models and behavioral comparisons, not by enabling all OWL features implicitly.

## Step 2 validation

57 offline tests, 141 native model/search checks and 154 API regressions pass.
See [retained step 2 results](jena-semantics-step2-results.json). The native
model/search runner includes transaction-scoped step 2 fixtures and rollback;
its test transport now decodes transactional JSON-LD CONSTRUCT responses as well
as SELECT/ASK. Offline checks also exercise missing schema graphs without remote
IRI dereferencing.

The final modeled inverse-field design (including inverse/subproperty
composition), own-model equivalence rejection and legacy writer/data migration
remain separate work. In particular this step does not remove `owl:inverseOf`.
The new profile's full real-project comparison and performance measurement are
still required; earlier latency numbers must not be reused as step 2 benchmarks.

## Historical rehearsal evidence (before step 2)

The Chama rehearsal uses actual source exports and both administrator/anonymous
API calls, an isolated TDB2/Jena API and real socket-only Redis. It also preserves
source namespace prefixes used in API responses: `foaf:Person` versus its full IRI
would otherwise be a serialization difference despite identical RDF meaning.
Prefixes are presentation metadata; importing them does not select their ontology
graphs for entailment. The production cutover must retain this distinction.

The enhanced runner compares the original 112 reads plus eight summary/search
requests and tests synthetic inverse directions, cycles, graph isolation,
authorization/provenance exclusion and registration removal/rollback. Details,
raw timing samples and final counts are retained with the API migration report.

The previous 120-match Chama report describes the earlier equivalence-aware
implementation. The unchanged strict GraphDB comparator and its old entailment
checks can now report expected differences; do not bypass those failures or claim
new parity. A later profile-aware rehearsal must enumerate exact changed types
and searches while preserving comparison of all other content.
