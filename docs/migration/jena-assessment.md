# GraphDB to Jena/Fuseki migration assessment

Assessment date: 2026-10-27. Source baseline: oldaplib 0.7.29
(`9f7610d`), oldap-api 0.2.37 (`9d58a12`), both on `migration/jena`.
Status: source inspection and primary-source research, not a running Fuseki
compatibility certification. No live GraphDB data was read or modified.

## Scope and findings

The target is Jena/Fuseki with TDB2 and RDF/SPARQL 1.2. Keeping existing
application behaviour, permissions and atomic operations takes priority over
merely accepting queries. Four areas require migration work: transactions,
RDF-star annotations, inference and full-text search.

**User clarification:** SHACL is used as documentation of the data model and to
read that model, not as a runtime SHACL validation service. Preserve shape graphs,
model loading and model editing. Do not introduce a SHACL engine as part of this
migration. Python value/cardinality/domain checks remain application behaviour.
The existing pySHACL ontology test does not imply runtime validation.

| Area | Evidence in OLDAP | Migration consequence |
| --- | --- | --- |
| Transactions | Connection exposes begin/query/update/commit/abort over RDF4J HTTP transaction URLs | Standard Fuseki HTTP calls are not a drop-in replacement |
| RDF-star | Permission annotations in library and API SPARQL plus bootstrap data | Explicit reifier model, coordinated query/data migration and permission regression tests |
| Inference | Repository templates select owl-max / owl-max-optimized; model reads distinguish asserted and inferred types | Define required entailments and graph visibility before selecting a Jena reasoner |
| Full text | GraphDB project connectors, named fields, property chains, entity scores | Translate supported search semantics and replace connector management |
| SHACL model description | DataModel.read and ConstructProcessor.query_shacl read project shape graphs | Preserve metadata round trips; no new validation endpoint |

## 1. Transactions: first feasibility gate

`oldaplib/src/connection.py:587` begins a server transaction and keeps the returned
URL. Queries and updates use it until commit/abort. `resource_transaction.py`
composes resource changes and transaction-local reads; imports/publication/mobile
operations append receipts and outbox records atomically. The transaction is
therefore an interactive read/check/write/read sequence, not just a list of writes.
`mutation_gate.py` and writer recovery also track its lifecycle and uncertain ends.

Jena documents serializable TDB2 transactions with one writer and concurrent
readers [1]. These are storage guarantees. Its remote connection documentation
states that SPARQL has no remote transaction protocol and discusses atomicity per
remote operation [2]. The public multi-request Fuseki proposal [3] is additional
evidence that we must not assume a stock begin/query/commit HTTP session exists.
Confirm the exact selected release in the feasibility test.

Two sound designs need comparison:

1. **One server-side command transaction.** A small Fuseki/Java extension executes
   a complete operation inside one TDB2 transaction. This avoids keeping database
   transactions open across network round trips. Conditional updates can cover
   simple cases, but existing Python decisions and callbacks cannot just be
   concatenated into a batch. Determine how much domain logic would move or need
   a declarative operation contract before choosing this design.
2. **A genuine multi-request transaction extension.** Keep Python composition and
   expose begin/query/update/commit/abort on the same Jena transaction. This requires
   bounded ownership/lifetime, authentication, thread affinity, timeout/abort,
   cancellation, restart handling and reconciliation. Holding the only writer
   across HTTP round trips is a performance and availability cost. It is real
   maintained infrastructure, not a thin URL adapter.

Recommendation: prove the smallest representative interactive transaction first,
then record an architecture decision comparing these designs. Do not build a
session framework before that decision. Client-side locks, Redis gates and buffering
updates alone do not supply rollback or transaction-local reads. Do not remove the
existing writer gate merely because TDB2 has stronger isolation: all writer paths
and recovery responsibilities must be accounted for first.

Acceptance: read own uncommitted changes; independent reader sees no partial
changes; multi-resource abort removes receipts/outbox too; concurrent conflicting
claims preserve invariants; disconnect/timeout does not leak an open writer; lost
commit response is reconciled without duplicate application; process death/restart
has a defined outcome. Exercise existing resource hooks as well as direct
Connection users and the API import/export/mobile repositories.

## 2. RDF-star to RDF 1.2: permissions and identity

A lexical inventory of Python production directories found 50 lines containing
`<<` in 7 library files and 19 lines in 4 API files. Counts include comments and
examples and are not counts of independently executable queries.

Library hotspots: `user.py`, `userdataclass.py`, `objectfactory.py`,
`archive_adoption.py`, `archive_inventory.py`, `archive_publication.py`,
`archive_repository.py`. API hotspots: `staging_area.py`,
`mobile_media/repository.py`, `imports/authorization.py`, `imports/repository.py`.
Also migrate `admin.trig`, `admin-testing.trig`, test fixtures, permission docs,
and annotations in exported/live data. The chronology document contains an
RDF-star example; `xsd/dating.py` itself uses ordinary resource triples.

The three central annotation relations are:

- user inProject project → hasAdminPermission;
- user hasRole role → hasDefaultDataPermission;
- resource attachedToRole role → hasDataPermission.

RDF 1.2 triple terms occur as objects; `rdf:reifies` connects an annotation subject
(the reifier) to the triple term [4]. Turtle's old-looking `<< s p o >>` syntax
now denotes reification shorthand, with different identity implications [5,6].
An unchanged parse is not proof that old data/query semantics were preserved.

Illustrative explicit target form (prefixes omitted):

```turtle
ex:item oldap:attachedToRole ex:readerRole .
ex:grant123 rdf:reifies <<( ex:item oldap:attachedToRole ex:readerRole )>> ;
    oldap:hasDataPermission oldap:DATA_VIEW .
```

For this OLDAP grant, preserve the asserted base relation. A reifying triple by
itself does not assert its embedded triple. Do not invent base assertions for
unasserted quotations elsewhere in imported data.

Proposed OLDAP invariant: one annotation container per graph and annotated base
triple for the current permission model, with all its permission values preserved.
This is an application rule, not an RDF requirement. Prefer stable identifiers
for mutable permission annotations; finalize their allocation and collision rules
before implementation. Never assume blank-node labels survive requests or exports.
Queries can bind a reifier through `rdf:reifies` without returning a triple term.
Deletion must remove grants/reifiers consistently; updates must not create duplicate
containers. Revoking a role must not leave effective permissions behind.

General conversion needs parsed RDF terms and graph context, not regex replacement:
repeated annotations, nested terms, blank nodes and quoted-only statements require
explicit handling. Unknown patterns should produce a migration report, not silent
rewrites. Separate immutable source export from converted target and validate
permissions by user/role/project/resource, not only by triple counts. Preserve
lexical datatypes/languages and graph names; test re-import idempotence.

Transport boundary: `enums/sparql_result_format.py` prefers GraphDB's SPARQL-star
JSON MIME type; `helpers/query_processor.py` handles URI, blank node and literal
bindings but has no triple-term branch. Review HTTP negotiation, result parsing,
CONSTRUCT and JSON-LD/export paths. A local smoke probe with installed RDFLib 7.6.0
and its default Turtle parser rejected both legacy RDF-star and explicit RDF 1.2
triple terms with BadSyntax. This is a concrete parser limitation, not a claim
about all RDFLib plugins or versions. Prefer Jena parsing/serialization for the
conversion unless a tested Python parser is deliberately selected. Keep ordinary
application SELECT results scalar where possible; never silently drop new term types.

## 3. Inference: define the required behaviour

The API's `oldap-config.ttl:21` specifies `owl-max`; the sibling setup repository's
`files/oldap-config.ttl:21` specifies `owl-max-optimized`. These are configuration
files, not verification of the currently running GraphDB ruleset. That difference
must be resolved before taking a behavioural baseline.

Jena supplies configurable RDFS, OWL-family and generic rule reasoners [7]; their
names do not establish equivalence to GraphDB's rules. Select rules using a small
entailment corpus derived from OLDAP, rather than accepting either reduced RDFS
behaviour or unbounded additional inferences by default.

Include subclass/type inheritance, subproperties, external equivalent classes and
properties, domain/range, sameAs where actually used, and transitive relations
(e.g. shared ontology's beforeDating). Review ontology updates and deletions too:
derived statements must disappear when their premises are removed.

Graph scope is essential. `_read_resource_construct` and the `_assertedType`
marker in `objectfactory.py` distinguish explicit project graph types from inferred
types. Default graph, FROM, FROM NAMED, GRAPH and union semantics must be specified
independently. Do not merge inferred statements into asserted graphs or enable a
union default graph and assume equivalence. Compare concrete class selection,
properties exposed by reads, project separation and authorization. Replace the
GraphDB-only `Connection.recompute_inference` operation deliberately.

Candidate implementation choices are query-time inference or managed
materialization. Benchmark actual required rules and deletion/update costs before
choosing. Validate that inference, text indexing and transactions compose correctly.

## 4. Full text: retain behaviour, change integration

`objectfactory.py` generates `luc:query`, `luc:entities`, `luc:score` against a
project-named GraphDB connector. `lucene_connector.py` accepts GraphDB-native JSON
including field names and property chains. The API exposes that configuration via
`/admin/lucene/<project>`. This is an externally visible backend-specific contract.

Jena Text supplies Lucene integration via `text:query` and configurable entity/field
mapping [8]. Its default indexing model and query shape differ from OLDAP's current
connectors. Port direct properties first, then explicitly cover required property
chains and entity-level boolean field queries. Inventory actual connector options
before declaring any translation complete. Reject unsupported options clearly;
do not silently ignore them. Existing exports containing connector configuration
also need a versioned translation or an explicit unsupported-option report.

Test language/accent handling, phrases, wildcards, AND/OR across fields, duplicate
hits, counts, stable pagination and ranking. Compare relevant results rather than
requiring equal numerical Lucene scores. Apply permissions before final pagination
and counts: an early top-N index limit can omit accessible results. Verify index
visibility after commit, rollback, update/delete, restart and full rebuild. Do not
assume RDF and external Lucene state have identical crash behaviour without testing.

Keep search policy in OLDAP and index-specific code at a small explicit boundary.
Do not introduce a general search framework solely for this migration.

## 5. SHACL remains model metadata

`datamodel.py:366` reads shapes through `ConstructProcessor.query_shacl`;
`propertyclass.py` and `resourceclass.py` read/write shape and ontology graphs.
Preserve these paths, ordering, labels, inheritance and model export/import.
The ontology declares a custom `oldap:statementShape`; audit its descriptive meaning
for reifiers, but do not treat it as an implemented validation engine.

No Fuseki SHACL endpoint, precommit validation service or replacement validation
engine is required. Existing focused ontology tests can remain useful. Native
Python constraints must not be removed under the mistaken assumption that SHACL
currently enforces them.

## Release baseline and evidence limits

The official download page retrieved during this assessment advertises Jena/Fuseki
6.2.0 and Java 21+ [9]. The retrieved Jena changelog describes RDF 1.2 syntax and
SPARQL 1.2 features in 6.1.0 [10]. Use a pinned released artifact and record its
checksum/JVM version during installation; do not equate a feature announcement
with passing the OLDAP compatibility corpus.

The retrieved W3C Concepts document is a Candidate Recommendation Snapshot and
Turtle is a Working Draft [4,5]. Pin the tested specification/implementation
behaviour and recheck versions at installation. No Jena runtime was installed or
executed in this assessment, and no live GraphDB settings or data were queried.

## Ordered work packages and completion gates

1. **J0 — Isolated capability tests:** install pinned Jena/Fuseki + Java on a free
   local port with separate TDB2/text storage; no production credentials/data.
   Test exact RDF 1.2 syntax/results and interactive transaction feasibility.
   Deliver the transaction architecture decision before broad backend edits.
2. **J1 — Permission representation:** finalize reifier identity/lifecycle;
   convert minimal admin/project fixtures; implement annotation query/write
   primitives used by both library and API. Prove login, grants, revocation,
   membership without defaults, multiple roles, create/update/delete and replay.
3. **J2 — Connection and atomic workflows:** implement the chosen transaction
   boundary, endpoint/auth configuration and recovery semantics. Preserve
   transaction-local reads and atomic resource/receipt/outbox changes. Tests must
   explicitly refuse original GraphDB/Redis endpoints.
4. **J3 — Model and inference parity:** load shape/ontology data and compare model
   reconstruction, asserted/inferred types and required entailments, including
   removals and graph scope. No SHACL engine work.
5. **J4 — Full-text parity:** migrate query generation, project index settings and
   management API/export contract; test permissions, fields, lifecycle and rebuild.
6. **J5 — Migration rehearsal:** export a consistent asserted-data snapshot;
   inventory/convert annotations; load into an empty target; rebuild inference
   and indexes; compare permission matrices, model/data round trips and workflows.
   Benchmark representative reads/writes, document cutover and rollback. The
   original GraphDB environment remains the reference until these gates pass.

Non-goals: FastAPI rewrite, new SHACL enforcement, permanent multi-backend plugin
framework, removal of writer coordination without evidence, or live cutover now.
Use existing IConnection and domain composition as starting boundaries; introduce
only the abstractions required by the demonstrated transaction/annotation/search
contracts. The public API should remain stable except where GraphDB-specific
connector management requires an explicit compatibility decision.

## Primary sources

1. [Jena TDB transactions](https://jena.apache.org/documentation/txn/transactions_tdb.html)
2. [Jena RDFConnection, remote transactions](https://jena.apache.org/documentation/rdfconnection/)
3. [Apache Jena issue 4123: multi-request transaction proposal](https://github.com/apache/jena/issues/4123)
4. [W3C RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)
5. [W3C RDF 1.2 Turtle](https://www.w3.org/TR/rdf12-turtle/)
6. [Jena archived RDF-star CG documentation](https://jena.apache.org/documentation/archive/rdf-star-cg.html)
7. [Jena reasoners and inference](https://jena.apache.org/documentation/inference/)
8. [Jena Text](https://jena.apache.org/documentation/query/text-query.html)
9. [Jena releases](https://jena.apache.org/download/)
10. [Jena changelog](https://raw.githubusercontent.com/apache/jena/main/CHANGES.txt)
