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

## WR-02 maintenance barrier and audited recovery

`writer_recovery.WriterRecovery` adds a persistent maintenance barrier, exact-record
SHA-256 revision binding, idempotent operation journal and atomic audited release.
`writer_recovery_operator` is the separate offline Docker/SSH controller. Its
reviewed inventory must match the digest configured in the API. It removes all old
writer containers, verifies a GraphDB process restart (including unregistered or
in-flight requests), then verifies operator-reviewed reconciliation reads before
publishing evidence. No transaction URL from a record is followed. A boolean claim
or missing transaction is never accepted as proof through this path.

New gate records include a process-instance UUID and monotonic record revision.
UUIDs/PIDs/age are diagnostic, not fencing tokens. Every writer must understand the
new barrier before activation; mixed protocol generations remain unsupported.
Freezing a live owner prevents subsequent journaling/release, but cannot stop an
already submitted database request. Only the independent runtime proof resolves
that window. A legacy owner record is refused by the new recovery service.

The original `recover_gate` remains a trusted offline legacy primitive for old
installations and cannot cross an active recovery barrier. **Do not expose it via
HTTP.** New recovery uses the journal and evidence ACLs instead. Unverifiable legacy
state requires the documented manual investigation and coordinated upgrade.

Use the separate recovery-api/operator Redis ACL identities generated by
oldap-setup. The API can read but cannot create operational evidence. A persistent
controller key serializes offline control and blocks release during any phase;
failed commands retain it because a remote command may still run. Host operators
must verify termination before compare-deleting only that controller record.

The completed operation retains actor, reason, inspected owner/revision, reviewed
runtime inventory, runtime observations, reconciliation reads/conclusions and final
actor/time. It is written before gate/barrier deletion in one Lua script. Lost
acknowledgements are resolved by the same operation ID, without replaying an archive
write. Journal keys have no TTL and share the existing writer AOF persistence and
no-rollback requirements. No ontology or media-storage change is introduced.

Detailed configuration, the two-phase CLI and explicit supported-runtime limits:
`oldap-setup/docs/writer-recovery.md`. Actual target activation and native MacBook
controller adaptation remain subject to WR-04 acceptance.

### WR-03 diagnostic projection

`WriterRecovery.readiness(record)` supplies an advisory awaiting-operator,
controller-blocked, ready or completed state for already authorized callers. It
uses the same evidence binding as finish and never interprets lock age as death.
HTTP adapters expose a closed projection, not the raw owner/evidence record.
`RecoveryOutcomeUnknown` distinguishes an unconfirmed durable acknowledgement from
a definite safety refusal; it remains a MutationGateUnavailable subtype for existing
callers. Read/retry the same operation ID. The optional `Connection.query(timeout=)`
parameter lets the API bound its fresh role query while preserving all other query
callers' existing behavior.

## WR-04 native macOS control

`writer_recovery_macos.LaunchdDomain` supports a reviewed single-host inventory of
foreground, non-daemonizing LaunchAgents. A native inventory sets
`runtime: macos-launchd-v1`, `domain`, `databaseService`, `queryEndpoint`, and
`nativeServices` entries with `label`, absolute `plist` and SHA256 of the private
plist. The same `inventory_digest()` binds this topology to the API. Legacy Docker
inventory digests remain unchanged. Native proof uses `macos-launchd-restart-v1`;
HTTP contracts, ontology and Capture payloads are unchanged.

The controller preflights all jobs, refuses a live owner outside managed writer
services or on another host, observes exact process exits with kqueue, waits for
launchd namespace removal, then starts fresh database/API processes behind the
barrier. Kernel start timestamps distinguish checkpoint process generations;
missing PID/age alone never releases a gate. Unexpected child/fork activity refuses
proof. Managed programs must not daemonize or escape supervision. The native API
entry point disables the reloader and worker forks. Reconciliation verifies the
same service generations both before and after its actual database reads.

MacBook activation and real isolated/native acceptance are recorded in
`FasnachtsPage/docs/wr-04/README.md`. Local recovery is enabled for the explicitly
selected operator rosenth. Remote/production activation remains target-specific.
The kernel exit primitive follows Apple's `kqueue(2)` documentation:
https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/kqueue.2.html
Darwin structure layout and launchd shutdown semantics were also checked against
the installed SDK `sys/proc_info.h` and local `launchd.plist(5)` manual.
