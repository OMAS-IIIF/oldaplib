# Idle polling and growth-triggered TDB maintenance

The API now checks job eligibility with an ordinary read before starting a write
transaction. Import claims, export claims/expiry/audit purge and mobile lifecycle
claims return directly when no work is eligible. A positive hint is **never**
used as authority to write: selection runs again inside the transaction. Another
worker winning in between therefore cannot cause a stale claim or deletion.
Public routes, signatures, leases and replay protection are unchanged. The same
repository improvement applies to GraphDB and Jena.

## Service policy

`services/jena/src/JenaCompaction.java` performs native Jena TDB2 compaction in
the service JVM that owns storage. It is packaged by `services/jena/build.py`.
Supply all seven optional properties together to enable its periodic check:

```properties
compactionCheckSeconds=900
compactionMinSeconds=86400
compactionGrowthBytes=536870912
compactionGrowthRatio=2.0
compactionZone=Europe/Zurich
compactionWindowStart=01:00
compactionWindowEnd=03:00
```

These mean: check every 15 minutes; wait at least 24 hours after the last completed
compaction; require both 512 MiB additional logical TDB size and twice the previous
post-compaction size. With no previous baseline, an existing database is initially
eligible at 512 MiB. A large import is picked up by the next check; the import
request does not trigger an unconditional compaction or wait for one itself.
No keys means disabled, preserving existing deployment behavior. A partial or
invalid policy refuses startup. The example configuration and setup's candidate
template expose these controls; enable the template via
`oldap_jena_compaction_enabled=true` only with a matching service release.

The checker measures only the active `Data-NNNN` generation, not backup archives
or Lucene directories. Logical size is a conservative estimate; sparse allocation
can make it larger than physical usage. Require enough usable space for a full
second generation **and** retain the 20% filesystem reserve. Insufficient space
causes a logged skip rather than a risky operation. No blanket deletion/pruning
of older backups or unrelated generations is performed.

## Coordination and data preservation

The engine's transaction-owner thread runs maintenance. It defers if a session
is still active or a reader holds the maintenance lock. When it obtains exclusive
access, new application/console work receives a retryable 503 during compaction.
Existing transactions/readers are not interrupted. This conservative OLDAP
boundary is stricter than native TDB's possible online-reader behavior and avoids
races with managed fulltext configuration/index replacement.

The service counts all quads, fsyncs `compaction.pending`, invokes native
`DatabaseMgr.compact(storage.asDatasetGraph(), true)`, verifies the generation
switch and equal quad count, then atomically records `compaction.properties`.
Native Jena retires the replaced generation after its switch; it is not retained
as a local rollback copy. A verified external backup remains required before
activation. **Replay reservations and commit receipts are ordinary preserved RDF;
none is pruned.** Lucene indexes are unchanged because RDF content is unchanged.
The resulting file baseline and completion time survive service restarts.

Shutdown stops future checks and waits for an in-flight one before closing the
engine. There is no forced compaction timeout: storage work must finish normally.
During a long run, keep readiness false/ingress maintenance rather than restarting
the JVM to satisfy a health deadline. Existing namespace recovery returns
`backend-not-ready` while the health route returns 503.

## Failure handling and operator workflow

Look for `OLDAP compaction:` / `OLDAP compaction bytes:` in service logs and the
private dataset's `compaction.properties` (completed epoch seconds, logical bytes,
quad count). `writer-active`, `readers-active`, `insufficient-space` are deferrals;
`not-due` is intentionally quiet. Host alert delivery remains an operations gate.

A failed native operation or incomplete bookkeeping leaves `compaction.pending`
and fences further service access. Restart refuses **before opening storage**,
even if scheduling was disabled. The marker records the previous generation,
expected quad count and start time. Do not blindly remove it or roll back to an
older service that does not recognize it. Keep ingress/workers stopped and use
the coordinated namespace maintenance workflow. Retain the current directory;
verify the selected generation, RDF/receipt contents, fulltext rebuild, API/media
acceptance and backup availability on an isolated copy. Restore the matched
backup if the outcome cannot be verified. Only remove the marker after explicit
operator verification, then recover Jena, identity/API and workers in order.

A recent successfully completed compaction is compatible with the same TDB2
version; configuration rollback must remove unsupported optional properties when
selecting an older service. That is not a substitute for failure verification.

## Acceptance and rollout status

Implemented and tested locally; no home/production rollout or timer activation
has occurred yet. Build/deploy the updated API image together with the new Jena
service bundle using new immutable references; stable/latest images stay untouched.
Then measure idle receipts/growth and real job handling on home before production.

Coverage:

- Five idle paths generate no transaction; five lost-candidate race cases reselect
  safely; broader import/export/mobile suite passes (271 tests).
- `CompactionAcceptance.java` exercises actual native compaction, reader/writer
  deferral, 503 admission, receipt/domain/fulltext preservation, restart baseline
  and interruption marker handling.
- `check_administration.py --compaction` exercises the real scheduled callback in
  the packaged service, native console and API, post-compaction fulltext writes,
  restart and pending-marker startup refusal.
- The standard service acceptance covers 300 commits, actor-bound replay guards,
  expiry, graceful/hard restart and fulltext recovery.
- Native compaction of a grown disposable fixture reduces logical TDB bytes from
  361,148,408 to 201,764,856 while preserving 10,000 domain and 2,000 receipt triples.

Compile acceptance classes against the packaged JARs into a separate test folder;
put the packaged JARs first on the runtime classpath. Never run these probes on
live datasets. Initial analysis and storage evidence are in the setup repository's
`docs/tdb-growth-analysis.md`; maintenance acceptance evidence is in
`docs/jena-compaction-acceptance.json` there.

## Night-only admission

The configured local window permits starts only (default 01:00 inclusive to
03:00 exclusive, Europe/Zurich). Outside it, checks perform no maintenance.
The service rechecks the window immediately before maintenance admission.
Growth after bulk operations waits for the next eligible night. Windows spanning
midnight are supported; equal start/end is invalid. Java zone rules handle
summer/winter time; the minimum interval remains elapsed time, so a daylight
saving transition may defer a run to a later check or night.

An admitted native compaction runs to completion even after the window ends;
interrupting it is not a safe deadline mechanism. Measure duration on home and
leave enough margin before daytime traffic. Coordinate this window with the
backup schedule before rollout. The current defaults are a proposal, not an
installed timer. No home or production service was changed.
