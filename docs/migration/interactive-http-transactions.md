# Interactive Python transactions over HTTP

Follow-up: the experimental receipt graph is now hidden/protected by the shared
application dataset view; see [protected transaction metadata](protected-transaction-metadata.md).
The limitations below describe this earlier milestone unless superseded there.

## Outcome

The existing Python transaction owner, structural audit, mobile callback and
outbox worker run unchanged over an experimental HTTP connection to Jena 6.2.0.
The implementation lives only in migration tools. Normal Connection and API
routes remain GraphDB-based, with no public signature changes.

This extends [the private-pipe proof](existing-python-callbacks.md). A new
connection-factory argument in that test harness runs the same 11 checks with
either transport; it does not duplicate the application callbacks.

## Transaction ownership

`tools/migration/JenaHttpSessionProbe.java` runs an owned, ephemeral loopback HTTP
server and TDB2 dataset. It is not a deployed Fuseki extension. The protocol is
intentionally small: POST `/BEGIN|UPDATE|QUERY|COMMIT|ABORT|STATUS|READ/<uuid>`.

One dedicated Java thread begins, reads/writes, commits and aborts each write
transaction. HTTP handlers submit work to it, so requests can arrive on different
threads without violating TDB2 ownership. Independent READ/STATUS requests use
committed read transactions. Only one write session is admitted; a competing
BEGIN receives 409 instead of waiting while holding a second session.

Two random process-local bearer credentials represent synthetic actors. The
session is bound to its actor; another actor cannot query, commit or abort it.
Credentials are passed through the child environment, not saved in results.
This tests identity binding, not real OLDAP authentication or RDF authorization.

The owner applies an absolute session deadline before each operation, and a
scheduled task aborts idle expired sessions on that same owner thread. Activity
does not extend the deadline. There are four HTTP handlers, a queue of 16 pending
requests, a 256 KiB request-body limit and a budget of 256 distinct session IDs
per server process. Overload handling is experimental, not a service guarantee.

## Lost commit replies

COMMIT writes a receipt in `urn:probe:http-commits` in the **same TDB2 transaction**
as application changes. Its subject is the session UUID and its value identifies
the synthetic owner. There is no second database or post-commit receipt write.

`tools/migration/probe_http_sessions.py` allocates the UUID before BEGIN and retains
it after failure. If a commit response is lost, it queries STATUS:

- A committed receipt for this actor confirms success without repeating writes.
- Missing receipt means **unknown**, including when the transaction is still
  pending. It does not authorize retrying the callback or treating it as aborted.
- Failed reconciliation propagates an OldapError with the transaction ID.

Two test-only fault injections close the HTTP exchange either before executing
COMMIT or immediately after it. The former reports uncertainty without replay;
the latter recovers success from the receipt. No update/query is automatically
retried. The production error contract for unresolved outcomes remains to be
settled before this adapter can replace a real Connection.

## Validation

Accepted run: `~/Library/Application Support/OLDAP-Jena/probes/j8-http-20261028-03`.
See `interactive-http-transactions-results.json` for 17 transport checks and
`interactive-http-callbacks-results.json` for the 11 existing callback checks.

The checks cover transaction-local reads, independent-reader isolation, actor
binding, writer contention, missing receipts, lost commit replies, identifier
reuse, actual SPARQL-error rollback and idle expiry. A SIGKILL after commit
preserves data and receipt on restart; a SIGKILL before commit leaves neither
pending application data nor a fabricated abort result. These are process-crash
tests, not power-loss or disk-failure guarantees.

The original pipe harness also passes all 11 checks after adding the factory.
Its last check closes the parent-control pipe and restarts the process. In the
HTTP variant this tests owned-server shutdown cleanup; abandoned HTTP clients
are tested separately by the deadline checks, without stopping the server.
The main capability/HTTP runner is unchanged and was not rerun for this step.

From the migration library checkout:

```sh
../oldap-api/.venv/bin/python tools/migration/probe_http_sessions.py \
  --jar '/Users/rosenth/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar' \
  --output '/absolute/path/to/a/new-output-directory'
```

Use the sibling API environment with its editable migration-library dependency.
The output must be new. All servers/datasets belong to the probe; no GraphDB,
Redis or production API service is used.

## Gates before production integration

This is a trusted-client feasibility experiment. Raw SPARQL can read or modify
all graphs, including the experimental receipt graph; the bearer check is not a
security boundary against malicious queries. Protect receipt storage and enforce
real OLDAP authentication/authorization before exposing any endpoint. The raw
READ endpoint likewise has no per-resource ACL filtering.

Further concrete requirements:

- Choose the maintained server packaging (e.g. a Fuseki extension) and integrate
  the actual OLDAP identity/context and CRUD/model path.
- Add query/update execution limits. The deadline aborts idle sessions and rejects
  late commits; it cannot preempt an already running long query or update.
- Persist operation identity and client recovery state across client restarts.
  Committed IDs cannot be reused after server restart, but uncommitted used-ID
  tombstones are currently memory-only. Callers always generate fresh UUIDs;
  this is not a durable idempotency/recovery service for arbitrary sessions.
- Define receipt lifecycle, protected status access, bounded operational load,
  TLS and lost-commit cache reconciliation. Do not assume the revocation-specific
  journal can be reused unchanged for interactive resource transactions.
- Verify full resource CRUD, policy guards and Redis coordination. The callback
  harness still uses synthetic model/resource/identity fixtures and disables the
  archive coordination gate; actual audit and mobile functions are imported.

The architectural result is positive: Python business logic need not be moved
into Java or compiled into large SPARQL statements. The extra transport code
belongs at the connection boundary and must remain separate from that logic.
