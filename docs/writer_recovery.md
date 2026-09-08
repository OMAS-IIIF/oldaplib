# Persistent writer ownership and controlled recovery

The accepted AS-02 operational rule is **no automatic lock expiry**. A crashed or
uncertain writer may block subsequent writes until an operator recovers it.
Availability is deliberately secondary to preventing an old GraphDB transaction
from being overtaken by another archive mutation.

## Deployment requirements

- Every API/direct library writer uses the same `OLDAP_ARCHIVE_POLICY_FILE` and
  dedicated `OLDAP_STAGING_LOCK_REDIS_URL`. Default gate URL is
  `redis://localhost:6379/1`; `OLDAP_REDIS_URL` is a separate cache database.
- Redis must support `WAITAOF` (7.2+), use `appendonly yes`, `appendfsync always`,
  `maxmemory-policy noeviction`, and be the designated primary. The implementation
  validates these settings and requires an acknowledged local AOF fsync.
- The gate store is durable operational state, not a disposable cache. Preserve its
  AOF volume, restrict destructive Redis administration, and monitor disk errors.
  No automatic failover, restoring an older snapshot, FLUSHALL, or deleting its
  volume while workers can resume is supported. A standalone dedicated instance
  is recommended; library cache initialization/clear rejects the same server/db.
- Stop old lease-based workers before activation: the shared key remains
  `oldap-api:staging:mutation`, but mixed protocol versions are unsupported.
- Existing local Redis settings were not changed by AS-02. Deployment and
  production acceptance remain separate AS-08/AS-09 steps.

Acquisition waits at most 30 seconds, then fails with coordination unavailable.
Ownership has no TTL. Nested operations join the same owner. The record contains
its token, host, PID, start time, known GraphDB transaction URLs and uncertainty.
Normal confirmed completion releases it; open transactions, ambiguous commits and
failed rollback retain it. A process crash even before transaction registration
also leaves the original durable ownership record in place.

## Operator recovery procedure

1. Pause new writers and inspect `inspect_gate(client)` from
   `oldaplib.src.mutation_gate`. Preserve the record and logs for reconciliation.
2. Identify the recorded host/process and **terminate or quarantine it so that it
   cannot resume**. PID reuse, temporarily paused containers and lost network
   access are not proof of termination. Account for all workers on that host.
3. Confirm every recorded GraphDB transaction has ended; abort an open transaction
   through the database's administrative facilities where appropriate. Also
   investigate requests that may have started before a URL could be recorded.
   A missing transaction/HTTP 404 does not say whether it committed.
4. Reconcile operation receipts and actual database state. Never blindly repeat
   an uncertain generic mutation. A committed idempotent command is resolved using
   its original caller, operation ID and request body after service restoration.
5. Call `recover_gate` with the inspected `expected_token`, explicit
   `writer_terminated=True`, `outcomes_reconciled=True`, and a
   `confirm_transaction_ended(url)` callback backed by the completed investigation.
   It verifies unchanged ownership and every transaction before durable release.
6. Resume writers and verify the intended result using ordinary authorized reads.

These are operator primitives, not public recovery endpoints. Never implement the
confirmation callback as an unconditional success in production. If worker
termination, transaction outcome, or store durability cannot be established,
leave ownership in place and resolve the uncertainty first.

## Evidence and limits

The isolated Redis test kills a writer, kills/restarts Redis, verifies retained
ownership, rejects a successor, and then exercises controlled recovery. Additional
tests cover no expiry, nested ownership, unclosed transactions, ambiguous outcomes,
old-token rejection and cache clearing. Separate GraphDB tests show competing
direct-library reference moves serialize and exact retries return one result.

These checks validate the supported local configuration. They do not establish
safety for storage loss, unsupported Redis failover or uncoordinated privileged
SPARQL writers. Production storage/process recovery must be rehearsed before
activation.
