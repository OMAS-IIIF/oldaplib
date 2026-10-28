# Model and single-resource reads on Jena

Follow-up: batch summaries are now covered in [Batch resource summaries](jena-batch-resource-reads.md).
The results below describe the original single-read milestone.

## Completed read path

The real Project, DataModel, ResourceClass/PropertyClass and ResourceInstanceFactory
now complete a representative model/resource read against the owned Fuseki
transport. The probe loads the repository's `oldap.trig`, `shared.trig` and
`objectfactory_test.trig` without rewriting those model files. SHACL remains model
metadata; no server-side SHACL validation was introduced.

`tools/migration/probe_model_reads.py` exercises factory construction, inherited
properties, `factory.read`, class-level `read` and generic `factory.read_data`.
Only Redis cache I/O is replaced with misses/no-op writes; the model classes,
query processing, domain hydration and permission decisions execute normally.
The accepted run made 301 reads without cache reuse; it is not a latency benchmark.

## Changes and compatibility

- The shared experimental Java engine now serializes CONSTRUCT results as JSON-LD.
  The test connection returns an RDFLib Graph, matching ConstructProcessor's
  existing input. SELECT/ASK responses remain SPARQL JSON.
- `IConnection._resource_read_query` is a concrete internal extension point, not
  a new abstract requirement. Existing connections inherit the GraphDB query.
- `_build_resource_read_query` shares the CONSTRUCT shape and permission logic.
  Its opt-in RDF 1.2 variant matches explicit reifiers and scopes data to the
  resource's project graph. No generic SPARQL string rewriting is used.
- The internal `creator_or_max_perm_block` gains an optional `rdf12=False` flag.
  Existing calls retain their defaults. Factory read/public method signatures
  remain unchanged; harvester/tool callers need no change for this step.

The GraphDB query was compared with HEAD for both creator policies and matches
modulo whitespace. A mock-based existing test was adjusted to invoke the real
new default hook instead of returning an unconfigured Mock as a query string.
The general production Connection remains GraphDB; the Jena dialect is selected
only by the explicit migration test connection.

## Permissions and graph boundaries

The same threshold and role membership rules remain visible in the query:

1. Current user role membership and numeric permission values come from admin.
2. The resource's role membership must be asserted in the project data graph.
3. Its RDF 1.2 reifier provides the matching data permission.
4. The existing caller decides whether creator access is permitted.

The tests check multi-role association, denied/missing resources, orphan reifiers,
below-threshold permission and live role removal. Factory.read continues to omit
the creator exception; class read and generic read_data retain their existing
creator exception. A resource IRI also present in another project's graph does
not bring that project's property values into this read.

## Explicit, limited inference

For this Jena single-resource read, the default query dataset merges only
project/shared/system ontology graphs. The application's data and admin remain
explicit named graphs. An optional `rdfs:subClassOf+` path adds visible ancestor
types while `_assertedType` is populated solely from the project data graph.
The existing factory can therefore select the concrete class and preserve
asserted/inferred type provenance without a global reasoner.

The probe verifies that a cat asserted only as `test:Cat` is read with an inferred
`test:Mammal` type, remains concretely a Cat, and inherits the Mammal's properties.
The stored data is unchanged: a plain Jena ASK for an asserted Mammal remains
false. This is a scoped entailment rule, **not** parity with GraphDB owl-max.

The checked-in API config specifies owl-max; the earlier assessment also records
owl-max-optimized in setup configuration. The running GraphDB ruleset has not
been inspected. Subproperty/equivalentProperty, equivalentClass, domain/range,
sameAs, inverse/transitive relations and external ontology closure are not
implemented by this narrow path. Their required behavior needs an explicit
entailment corpus and comparison before backend activation.

## Remaining RDF* inventory

`tools/migration/inventory_rdfstar.py` emits
`rdfstar-read-inventory.json`: 49 lexical legacy-string sites in 26 scopes across
seven library source files. It includes retained GraphDB branches and some text
fragments, so these are review candidates, not 49 independently unmigrated APIs.
It excludes RDF 1.2 triple terms and does not prove runtime query coverage.

Still requiring migration/verification include:

- Search/filter/count helpers and media lookups in objectfactory (batch summaries now have a separate proof).
- Additional user read/write and membership annotation operations.
- Archive repository/inventory/publication/adoption operations.
- Resource writes and exports, including stable reifier identity and cleanup.

This milestone does not claim all resource reads or all RDF* producers are done.
The next step after the batch follow-up is search read parity using explicit boundaries,
followed by the broader entailment corpus. Full-text behavior remains separate.

## Validation and reproduction

Accepted model run:
`~/Library/Application Support/OLDAP-Jena/probes/j12-model-reads-20261028-05`.
See `jena-model-resource-reads-results.json` for all 19 checks.

60 offline resource/model-filtering, search-query, type/IRI, transaction and cache
checks plus 7 subtests pass. The native Fuseki identity/session/callback suites
also pass again (20 + 20 + 11 checks) after adding CONSTRUCT and fixture loading.
No shared Redis/GraphDB service is used; the fixture seed option accepts only a
new owned dataset. Initial test fixture dateTime values were corrected to the
model's dateTimeStamp type, and collection-valued fields are checked as sets.

From the migration library checkout:

```sh
../oldap-api/.venv/bin/python tools/migration/probe_model_reads.py \
  --jar '/Users/rosenth/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar' \
  --output '/absolute/path/to/new/output'

../oldap-api/.venv/bin/python tools/migration/inventory_rdfstar.py \
  > docs/migration/rdfstar-read-inventory.json

../oldap-api/.venv/bin/python -m pytest --noconftest \
  oldaplib/test/test_objectfactory.py::TestResourceConstructModelFiltering \
  oldaplib/test/test_objectfactory.py::TestSearchQueryGeneration \
  oldaplib/test/test_resource_iri_aliases.py oldaplib/test/test_resource_default_roles.py \
  oldaplib/test/test_resource_transaction.py oldaplib/test/test_read_cache_optimization.py -q
```

Deployment, general backend selection, query limits, durable client recovery and
cache consistency remain open. No production switch, commit or push was performed.
