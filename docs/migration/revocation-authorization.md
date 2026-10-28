# Atomic authorization for Jena authentication revocation

Follow-up: [durable recovery](revocation-durable-recovery.md) now reconstructs prepared commands after writer/Redis process crashes. This report retains the earlier authorization milestone.

Date: 2026-10-27. Status: isolated acceptance passed; not activated in the API.
Public User/API signatures and the receipt-free GraphDB update are unchanged.
This extends the earlier restricted self-revocation connection milestone.

## Decision inside the mutation

The receipt-mode SPARQL update evaluates the same administration rule as
`User.check_for_permissions`, using the current `oldap:admin` graph:

- The actor may revoke its own authentication without an administration grant.
- An actor with an asserted SystemProject membership and an RDF 1.2 reifier
  carrying ADMIN_OLDAP may manage any target, including one without projects.
- Otherwise the target must have at least one project, and the actor must have
  an asserted membership plus ADMIN_USERS annotation for **every current target
  project**. A missing grant, orphan reifier or grant in another graph cannot
  authorize the write.

The entire decision, user mutation and receipt insertion occur in one SPARQL
Update request/TDB2 transaction. No permission read is performed before the write
by this executor. User's existing local authorization check still runs; its
cached authorization data cannot bypass the authoritative database check.

The actor identity remains supplied by the trusted authenticated connection.
This is not a login implementation, a public SPARQL endpoint or a signature
scheme. It uses the RDF 1.2 explicit-reifier representation; it does not convert
legacy RDF-star data automatically. Actor activity/token policy is not extended
here beyond the existing caller authentication contract.

## Distinguishing denial from conflict

When the expected user version and timestamp match, the update records exactly
one outcome with the command digest:

| Outcome | User effects | Receipt fields | Python result |
| --- | --- | --- | --- |
| committed | Increment version; replace contributor and modified | digest, status, version | Success |
| denied | None | digest, status; no result version | OldapErrorNoPermission |

Conditional unbound template variables omit all user writes on denial. Tests
check that exactly one version, timestamp and contributor remain, not merely
that an old value is still present alongside an unintended new value.

The expected user revision guard remains outside the permission branch. If it
fails, no new receipt is written and an acknowledged no-op remains an
OldapErrorUpdateFailed conflict. If both revision and permission have changed,
this revision conflict takes precedence at the database boundary. A permission
failure already caught by the existing local check still fails before I/O.

The reader strictly validates the full outcome record before returning success
or raising permission denial. A denied receipt with a claimed result version is
invalid. A lost acknowledgement can be reconciled to either success or denial;
an absent receipt after uncertain delivery still means unknown.

An exact retry preserves the original decision. A denied command does not become
successful after rights are granted, and a committed command remains committed
after later rights removal. A new deliberate operation needs a new identity.
Denial writes only an internal receipt, never user metadata or Redis state.

The command digest domain is now `oldap-authentication-revocation-v2` and receipt
status is mandatory. Previous experimental receipts are deliberately incompatible
and fail closed; all acceptance runs use fresh datasets. No production receipt
migration is required because this path has never been deployed.

## Evidence

Accepted run: `~/Library/Application Support/OLDAP-Jena/probes/j4-authorization-20261027-03/`.
[Results and source hashes](revocation-authorization-results.json).

- 63 owned Fuseki runner checks pass (18 added authorization checks, including
  six concurrent removal/revocation runs within one check).
- 26 offline tests pass for receipt handling, legacy public behavior and existing
  token functionality.
- The real public User method is exercised for project administrator success,
  root success with a projectless target, and stale cached permission denial.
  Redis is mocked and its invalidation count verified.
- Tests cover missing/partial grants, wrong graph, missing base membership,
  target project additions after preparation, removed grants, denied replay
  after restoration and committed replay after removal.
- Concurrent ordering may allow the revocation before removal or deny it after
  removal. Both are valid serial orders; tests require outcome/state consistency,
  not that both orders are observed in every run.
- Receipt-free GraphDB query generation still matches HEAD ignoring whitespace
  for expected versions 0, 1 and 99. Live GraphDB data was not touched.

The initial run stopped at a test fixture assigning to frozen AuthorizationContext;
constructing its replacement fixed the harness. The final run additionally checks
exact cardinality of user metadata. The owned Fuseki process was stopped.

Reproduce with the existing `probe_jena.py` command in the earlier pilot report.
Run offline checks with:

```sh
.venv/bin/python -m unittest \
  oldaplib.test.test_jena_authentication_revocation \
  oldaplib.test.test_authentication_revocation_unit \
  oldaplib.test.test_authentication
```

## Remaining gates

Receipt retention/access and durable recovery across process restart remain open.
The restricted test connection retains attempts only in memory and trusts a
synthetic identity; it is not a general Jena login/connection. Valid singular user
version/timestamp metadata remains an assumption. No network/crash fault injector
or real Redis was used. Next, persist recovery identity before transmission and
reconcile it safely after restart, then prove composed resource/audit/outbox work.
