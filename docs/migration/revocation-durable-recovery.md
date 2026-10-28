# Durable revocation identity and restart recovery

Date: 2026-10-27. Internal implementation and isolated crash acceptance complete.
No API/public method signature, normal GraphDB operation, installed Redis service
or deployment configuration changed.

## Reuse of the writer store

`helpers/revocation_journal.py` uses the existing writer-store requirements from
`mutation_gate`: designated primary, appendonly=yes, appendfsync=always,
noeviction and acknowledged local WAITAOF. Canonical JSON uses the existing
`writer_recovery.encoded` helper. No SQLite/file journal, new service or second
operator recovery controller was introduced.

The journal is a separate record type for prepared commands. WriterRecovery's
maintenance barrier and process-fencing proof remain unchanged; saving/loading a
revocation never releases a writer gate. Production wiring must supply the
private writer-store client, never the resource-cache client. The isolated probe
owns a separate Redis process with no TCP port and a private Unix socket.

## Persistence before transmission

`RevocationJournal.execute` saves the immutable attempt before calling its update
transport. Each record binds schema, configured dataset-generation identity,
receipt UUID, complete serialized command, command digest and exact generated
SPARQL hash. It contains no login password or transport secret.

An atomic compare-and-set refuses a different payload under an existing UUID.
Exact repeats write the same bytes again. SET and WAITAOF use one pinned Redis
connection; the connection ID and server incarnation are checked around the
write/acknowledgement sequence. redis-py reconnects therefore cannot accidentally
confirm a different connection's write offset. Failed store validation, failed
persistence acknowledgement or reconnection prevents any database transport call.
Redis connection failures at this execution boundary map to the existing
MutationGateUnavailable/OldapError family.

Records have no TTL. The library provides no deletion/expiry API. Retention and
receipt access policies are deployment gates, not inferred from elapsed time.

## Recovery after restart

A new process can discover `retained_ids()` and `load(id)`. Discovery is a SCAN of
this dataset's namespace, not a queue or a pending-only view: completed and denied
commands remain retained and SCAN may repeat IDs. Missing or malformed records
must not be interpreted as database rollback.

Load validates schema, dataset, identity, digest and the regenerated update hash.
An incompatible software change fails closed instead of silently rewriting a
saved operation. Historical commands need an explicit compatibility/migration
path if the serializer/query generator changes.

After load, first call `attempt.confirmed(query)` without writing:

- Matching committed receipt proves the original command committed.
- Matching denied receipt raises existing OldapErrorNoPermission.
- No receipt means unresolved, not proof of rollback.
- Malformed or mismatched receipt fails closed.

An explicitly selected retry calls `journal.execute(loaded_attempt, ...)` with
exactly the same identity and snapshot. It reconfirms journal durability, then
uses the already-tested guarded/idempotent mutation. There is no automatic retry,
new public User argument or background recovery service. Calling User again is a
new operation, not recovery of the saved one.

The configured dataset identity is a trusted binding to the transport, not an
endpoint autodiscovery mechanism. Replaced/restored datasets require a new
identity and an explicit reconciliation decision. Never reuse the namespace to
send old commands into a different dataset.

## Validation

Accepted integration run:
`~/Library/Application Support/OLDAP-Jena/probes/j5-recovery-20261027-03/`.
[Results and source hashes](revocation-durable-recovery-results.json).

- 68 owned Fuseki/Redis runner checks pass, including five new recovery checks.
- 34 targeted Python tests pass: eight journal tests using an owned real AOF
  Redis, plus the previous 26 receipt/authentication/public-contract tests.
- A child Python writer terminates with os._exit after durable preparation but
  before HTTP. Redis is then SIGKILLed and restarted from AOF. The new journal
  reconstructs the command; two explicit exact retries produce one increment.
- A child terminates after Fuseki answers but before receipt observation. After
  Redis SIGKILL/restart, both committed and denied outcomes are recoverable.
- The real public User method runs through the restricted test connection with
  journaling enabled. The sender verifies the saved snapshot before HTTP; normal
  object/cache success occurs only after the receipt is confirmed. Cache is mocked.
- Tests cover no TTL, ID collisions, dataset separation, corrupt/incompatible
  records, missing fsync acknowledgement, unavailable Redis and reconnection
  between the write and durability acknowledgement.

Both owned servers are stopped and the temporary socket removed; Redis AOF and
logs remain in the run directory. No real application/cache data is accessed.
These are process-crash tests, not power-loss, storage-volume-loss or asynchronous
replica-failover guarantees. Fuseki's own persistence restart check remains part
of the runner; the new fault injection kills the writer and the journal Redis.

The first unit run used an incorrect redis-py attribute name in its assertion;
it was corrected to match the installed implementation. A later test explicitly
proved that a physical reconnection blocks transmission. Final suites pass.

Reproduce using the existing probe_jena.py command; it now additionally requires
redis-server on PATH. Run targeted tests with:

```sh
.venv/bin/python -m unittest \
  oldaplib.test.test_revocation_journal \
  oldaplib.test.test_jena_authentication_revocation \
  oldaplib.test.test_authentication_revocation_unit \
  oldaplib.test.test_authentication
```

## Remaining deployment gates and next transaction

Production recovery must authenticate operators, bind the dataset/store/transport
configuration, restrict Redis/receipt access and reconcile cache invalidation
before reporting recovery complete to an application. The journal deliberately
does not rewrite a stale Python User or publish old values into cache. Records
remain retained if cache reconciliation fails. No recovery HTTP route is added.

A general Jena login/connection and receipt/journal retention policy remain open.
The next architectural proof is resource mutation + audit + lifecycle outbox
under one atomic operation, including failures and nested transaction ownership.
The revocation journal is not a generic interactive-transaction replay engine.
