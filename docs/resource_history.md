# Property history

`ResourceInstance.update()` automatically preserves previous business-property
states in `<project>:history`. Instances of `oldap:Thing` and its subclasses are
eligible. Direct and inherited properties admitted by the resolved model qualify
regardless of namespace. System metadata, role grants, RDF types and inverse
fields do not qualify. Inverse fields are versioned at their stored counterpart.

Creation produces no entries. Existing data needs no backfill: history starts
with the next actual change. Each entry contains a UUID IRI, replacement timestamp,
actor IRI, resource IRI, property IRI and the **complete previous value set**.
An empty set means absence, allowing the first addition to be undone. There is
no global resource-version counter. Timestamp ties have deterministic UUID order,
not a causal ordering guarantee.

## Reading and restoring

```python
from oldaplib.src.resource_history import ResourceHistory

history = ResourceHistory(con, "fasnacht")
entries = history.list(resource_iri, property_iri="schema:name", limit=100, offset=0)
entry = history.get(resource_iri, entries[0].iri)
instance = history.restore(resource_iri, entry.iri)
```

Reads freshly check access through `ResourceInstanceFactory.read()`. The right
to view an instance includes its history, including older contents that may not
have been public at the time. The public entry values are typed OLDAP objects;
empty values are an empty tuple. Pages contain at most 1,000 entries, default 100.
Entries remain readable after a property is removed from the model; restoring
such an entry fails until the property is writable again.

Restore uses normal property assignment and `update()`, with current write
permissions, cardinalities, constraints, transaction guards and optional
`before_commit` hooks. It is a new change, recording the replaced current state;
existing history is immutable. Equal value sets produce no history. Dating
restoration copies content rather than overwriting arbitrary historical node
identities. Normal Dating write limitations (including multi-root replacements)
also apply to restore.

## Storage and transaction behavior

`oldap:PropertyHistory` is internal vocabulary, not a `Thing` subclass. Its
predicates are `historyResource`, `historyProperty`, `historyUser`,
`historyTimestamp`, `historyValue` and optional `historyDatingSnapshot`.
`historyValue` retains RDF literals/IRIs with their datatype and language. Dating
closures are frozen as N-Triples string literals, preventing mutable shared IRIs
from changing older records. Ordinary object links preserve only the link, not a
snapshot of the linked instance or external media bytes.

Changes read selected explicit property states before and after the normal write,
inside the same transaction. Each operation needs two additional bounded CONSTRUCT
queries and, only if values changed, one history INSERT. No complete resource
snapshots or cross-request caches are added. A fresh modification-time check
rejects stale mutable instances. Existing transaction ownership and backend
isolation/writer coordination remain authoritative; history adds no distributed
lock. The committed actor/time are those of the replacing operation.

Class transformations also record changed business properties and an optional
source link. New-instance creation and whole-instance deletion do not generate
property versions. Deletion retains existing history but makes it inaccessible
through this API, which requires a readable live instance; resource resurrection
is outside scope. History references do not prevent deletion. Raw SPARQL writers
bypassing resource operations do not automatically generate history.

Jena managed fulltext accepts explicit `...data` graphs only; `...history` cannot
be configured as a source. History never receives application title predicates.
Backups/exports intended to preserve history must include the history graph.
Deployment must install matching library/API code; no service restart, migration,
release or deployment is performed by this source change.

## Validation

84 focused tests cover stored SPARQL, value roundtrips, creation, empty/no-op
states, access checks, current cardinalities, rollback, stale writers, class
transformation, API routing and domain move dispatch. Run from the library root
with an environment containing the library/API dependencies and pytest:

```sh
PYTHONPATH="$PWD:$PWD/../oldap-api" ../oldap-api/.venv/bin/python -m pytest \
  oldaplib/test/test_resource_history.py oldaplib/test/test_resource_transaction.py \
  oldaplib/test/test_resource_iri_aliases.py oldaplib/test/test_dating_rdf_roundtrip.py \
  oldaplib/test/test_archive_tree.py oldaplib/test/test_staging_folder_tree.py \
  ../oldap-api/oldap_api/test/test_instance_history.py \
  ../oldap-api/oldap_api/test/test_dating_serialization.py \
  ../oldap-api/oldap_api/test/test_read_instance_fast_path.py -q
```

An additional isolated Jena acceptance run executed 10 resource-history scenarios
through real HTTP transactions on owned temporary TDB2 storage. Two fulltext
checks verified that replaced text is absent from live search and that a history
graph configuration is rejected. All 12 checks passed. No installed service or
dataset was modified. Legacy GraphDB-dependent API transform tests could not run
because the old localhost:7200 test backend is stopped; the Jena transformation
scenario and offline API/domain contracts passed.

## Home deployment

On 2026-11-11, the property-history candidate and additive OLDAP ontology update
were deployed to home.org. See `../oldap-setup/docs/property-history-home-20261111.md`
(relative to the repository root) for the exact image, scope and recovery paths.
Production promotion and frontend integration remain separate.

## Production deployment

Later on 2026-11-11, the exact home image and additive ontology patch were also
deployed to production. Deployment and rollback details are in
`../oldap-setup/docs/property-history-production-20261111.md` (relative to the
repository root). Frontend integration remains separate.

## Project transfer (1.1.0)

Native Jena project dumps include the project `history` graph whenever data is
selected; `--no-data` excludes both. Import preserves native RDF values and Dating
snapshots, and accepts older data-only dumps without inventing history entries.
Raw transfer remains root-only, additive, and restricted to the selected project
graphs. The existing bounded transfer size is unchanged. Deploy Jena service
1.1.0 together with tools 1.1.0 before using history-aware dumps.

Offline native regression: compile and run
`tools/migration/JenaProjectTransferHistoryProbe.java` against the service and
Fuseki jars. It checks history/data round trips, old dumps, authorization and
rejection of foreign graphs before writes.
