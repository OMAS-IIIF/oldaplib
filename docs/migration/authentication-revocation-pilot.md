# Authentication revocation pilot

Follow-up: [internal connection integration](revocation-connection-integration.md) now exercises the real public User call through a restricted Fuseki test connection. The report below records the earlier query-level milestone.

Date: 2026-10-27. Status: query extraction and isolated Fuseki acceptance complete;
normal `User.revoke_authentication()` still uses its existing GraphDB transaction.
No HTTP API, public function signature, caller, ontology or service configuration
has changed. No real users or Redis data were touched.

## Implemented boundary

`oldaplib/src/helpers/authentication_revocation.py` snapshots typed OLDAP inputs
as immutable serialized RDF strings. `User.revoke_authentication()` uses this
helper to prepare exactly its previous guarded update. Authorization, transaction
ownership, verification queries, exceptions, object mutation and cache invalidation
remain in the existing method. The helper performs no I/O and grants no authority.

The isolated runner uses the same helper with an internal UUID receipt. One
SPARQL DELETE/INSERT changes authVersion, contributor and modified timestamp and
inserts a receipt under the same WHERE guard. The guard checks the expected
version, modification time, user type and absence of any existing receipt for
that ID. Missing authVersion retains the existing legacy interpretation of zero.

The receipt records a SHA-256 digest of operation kind/version, prefix context,
actor, target, expected/new version and old/new timestamps, plus the result.
The digest is an identity check, not authentication or a signature. Retrying must
reuse the entire prepared command and UUID; recreating the timestamp is not an
exact retry. Receipt vocabulary/graph are explicitly experimental and private,
not an addition to the OLDAP ontology. Normal GraphDB updates include no receipt.

For this bounded experiment, use **stock Fuseki Update plus a receipt read**.
That is one mutating HTTP request and a separate observation request, not one
HTTP round trip overall. This avoids a Java extension for the pilot and does not
decide the transport for composed resource/audit/outbox operations.

## Outcomes and uncertain delivery

| Evidence | Interpretation |
| --- | --- |
| Exact digest and expected result in receipt | This command committed; result belongs to this command, even after later edits. |
| Existing receipt with different digest/result | Operation-ID collision or inconsistent receipt; do not mutate or report success. |
| Acknowledged completed update, no receipt | Its guard did not match; map to the existing conflict behavior when integrated. |
| Transport failure and no receipt | Unknown: the original request could still execute/commit. Do not claim rollback. |
| Receipt read fails | Unknown; do not publish local success. |

An exact retry after unknown delivery is safe at the database level while the
receipt exists, including concurrent identical deliveries. No automatic retry
policy or persistent client journal is implemented yet. A later independent call
to the public method is a new revocation, not implicitly a retry of an earlier call.
Never overwrite a newer cached user with the old state carried in a historical
receipt. The future adapter must invalidate/reload appropriately after reconciliation.

## Validation

Accepted run: `~/Library/Application Support/OLDAP-Jena/probes/j2-revocation-20261027-02/`.
[Machine-readable results](authentication-revocation-results.json).
The runner owns a fresh loopback Fuseki 6.2.0/TDB2 process on port 3032 and stops it
in its finally block. Java and existing RDF/transaction checks remain included.

- 40 runner checks pass, including 13 revocation checks: legacy missing version,
  metadata/result receipt, exact replay, stale version/model, independent timestamp
  conflict, changed-payload/actor ID reuse, historical replay after another commit,
  competing commands, concurrent identical retries, lost-acknowledgement simulation,
  unknown absence, and graceful restart persistence.
- 15 offline unit tests pass: four new public-method regression tests and eleven
  existing authentication tests. Cover unchanged return type, permission rejection,
  rollback on stale verification and no object/cache success before known commit.
- The receipt-free generated update matches the HEAD implementation ignoring
  whitespace for expected versions 0, 1 and 99.
- Live GraphDB tests were not run: they create/change users in the configured
  database. Unit regression tests and query equivalence cover this extraction;
  they do not establish full end-to-end GraphDB or Jena application compatibility.

Reproduce from the library checkout after installing its development environment:

```sh
.venv/bin/python -m unittest oldaplib.test.test_authentication_revocation_unit oldaplib.test.test_authentication
.venv/bin/python tools/migration/probe_jena.py \
  --fuseki-home "$HOME/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0" \
  --output "$HOME/Library/Application Support/OLDAP-Jena/probes/j2-new-run" \
  --port 3032
```

Output must not already exist. The runner now imports the installed/editable
library to exercise real query preparation; it is no longer stdlib-only.
The lost-response test deliberately discards an acknowledged response and raises
a timeout in the caller. It is not network fault injection or a crash test.
The absent-receipt check demonstrates the observable state, not a production
unknown-outcome classifier. Restart is graceful, not power-loss recovery.

## Remaining acceptance gates

1. Integrate the verified command through an internal connection boundary while
   retaining the public method and its post-commit behavior. No Jena login/ACL
   adapter exists yet, so this pilot must not be advertised as a usable backend.
2. Decide receipt access, retention, persistent retry identity and recovery journal
   interaction. Never expire/delete receipts during an unresolved retry window.
3. Revalidate authorization dependencies for administrator-driven revocation in
   the same transaction. This pilot assumes an already authorized trusted caller;
   it is not proof of RDF 1.2 administrator permission parity or concurrent grant
   revocation safety. Existing User authorization code is unchanged.
4. Keep current valid-model assumptions explicit: singular authVersion and modified
   values. Malformed multiple values need a defined rejection policy, not an
   accidental change in migration behavior.
5. Prove resource update + audit + lifecycle outbox and transaction-local callbacks
   before selecting the architecture for the remaining inventory. Do not buffer
   arbitrary interactive transactions or silently commit their parts separately.
