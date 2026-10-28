# Readable server command for composed resource work

Date: 2026-10-27. Status: isolated HTTP/TDB2 architectural proof, not an OLDAP
resource port or a deployable endpoint. Production Python, API routes, signatures,
GraphDB behavior and domain rules were not changed.

## Readability is an acceptance criterion

Correctness alone is insufficient. A developer should be able to locate the
transaction owner, read the operation in order, understand its preconditions,
and identify exactly what rolls back. Prefer short named steps with comments
explaining invariants over an increasingly large SPARQL expression or a generic
workflow interpreter. One HTTP request is an optimization, not an excuse to
weaken public callback semantics or duplicate the entire Python domain model.

## What the existing code actually does

The current Python owner is `oldaplib/src/resource_transaction.py`:

1. Open or join the explicitly owned transaction.
2. Apply domain guards and perform the resource method.
3. Perform retention/transfer and conditional structural audit.
4. Execute the resource's `before_commit(connection)` hook.
5. Let only the outer owner commit; any inner failure poisons the outer scope.

`archive_domain.audit_resource_operation` records changed structure only for
ArchiveUnit/StagingFolder objects. It skips unchanged structural state.
The API's `_mobile_lifecycle_hook` and
`mobile_media/lifecycle.py:append_to_active_transaction` concern mobile staging
media. The latter inserts work only when a mobile commit receipt exists.
Therefore resource+audit+outbox is not automatically one existing resource
method. A composed transaction can include a structural change and a related
media change; the test models that distinction explicitly.

## The isolated bounded command

`tools/migration/JenaCompositionProbe.java` owns a fresh TDB2 dataset and a
loopback HTTP server on an OS-assigned port. The fixed synthetic move-pair command
accepts only an operation UUID, expected revision and a test failure stage.
It accepts no raw SPARQL, arbitrary code, Python callbacks or production IRIs.
The synthetic actor, resource identities and destination are fixed by the fixture.

The essential implementation is `execute`, whose order is deliberately visible:

```text
begin write transaction
  return stored result if this exact command already committed
  check permissions and both resource revisions
  move the folder and medium
  append structural audit if the structure changed
  append lifecycle work if mobile provenance exists
  verify the resulting state
  store the operation result
  commit
on failure: abort everything
always: end transaction
```

Small helpers operate inside that one transaction and do not commit themselves.
Audit and outbox read the state just written by the resource step. The HTTP
handler returns success only after commit. A failing final assertion causes a
real rollback; it cannot silently become a successful zero-match WHERE clause.
The implementation uses Jena's RDF Model API, so this experiment adds no complex
SPARQL expression. Its Java transaction owner is commented independently from
the test/HTTP wiring.

## Evidence

Accepted run: `~/Library/Application Support/OLDAP-Jena/probes/j6-composition-20261027-03/`.
[Results and source hashes](resource-composition-results.json).

- 13 composition checks pass through real local HTTP requests: permission denial,
  stale revisions, five rollback points (after resources, audit, outbox, receipt
  and an intentionally broken postcondition), full commit, exact replay/ID reuse,
  concurrent one-winner behavior/historical result, conditional outbox, unchanged
  structural audit suppression and dataset reopen persistence.
- Rollback comparisons inspect all four graphs by RDF graph isomorphism. They
  detect stray resource, audit, outbox or receipt triples, not only an old value
  that happens to remain present.
- The full existing runner also passes: 69 top-level checks, one of which contains
  these 13 composition checks. Counts are nested, not 82 independent top-level tests.
- All 53 existing offline Python transaction-ownership and archive-domain tests
  pass. They retain coverage of outer ownership, nested failures, transactional
  reads and resource/owner callback behavior.

The first Java compile exposed that Jena Dataset is not AutoCloseable; explicit
finally-based closing corrected the probe. The final run includes the unchanged
structure rule. Both HTTP servers, the owned Redis process and datasets are
closed after the run. No existing OLDAP database or Redis service is used.

Reproduce with the existing probe_jena.py invocation; the additional Java source
runs against the same pinned Fuseki 6.2.0 jar. Run existing Python contracts with:

```sh
.venv/bin/python -m unittest \
  oldaplib.test.test_resource_transaction \
  oldaplib.test.test_archive_domain
```

## What this does not establish

This is synthetic RDF, not schema/serialization parity with actual OLDAP audit or
mobile receipt graphs. Permission is a synthetic boolean, not the full resource
ACL/domain policy. The probe's receipt binds the only business input that varies
(expected revision); it is not the general production digest/recovery protocol.
Failure injection and its unauthenticated loopback route are test facilities,
never deployment options. Reopen is graceful, not a crash test for this command.
The existing revocation Redis journal is not extended to arbitrary commands here.

Most importantly, no Python callback is serialized, replayed or executed by Java.
Existing arbitrary callbacks and transaction-local reads cannot transparently
become this one-request command. Their public semantics remain required.

## Architectural consequence and next gate

The proof supports a small, explicitly ordered server command for a **bounded,
known** operation. It does not justify moving all OLDAP business rules to Java or
building a generic plan language. Both would create avoidable maintenance costs.

Before implementation in the normal connection, select one real composed caller
and map every decision/dependency, including negative membership/reference checks,
to its transaction boundary. Keep domain preparation in Python where practical;
revalidate its dependencies atomically. Known hooks may have an internal prepared
representation without changing their public signatures.

For arbitrary Python callbacks, either retain a compatible remote interactive
transaction path or demonstrate an equally strong alternative. Such a path adds
server lifecycle/thread-ownership work, but could preserve readable existing
Python. Silently buffering its writes, moving its reads after commit or rejecting
previously supported callbacks is not acceptable. The one-request goal must yield
to correctness and public compatibility where necessary.
