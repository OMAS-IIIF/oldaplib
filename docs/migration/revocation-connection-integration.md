# Revocation connection boundary

Follow-up: [atomic authorization](revocation-authorization.md) now supports project/root administrators in the experimental path. This report preserves the earlier self-only milestone and its test evidence.

Date: 2026-10-27. Internal integration and isolated public-call acceptance pass.
The normal Connection remains GraphDB. No API route, public method signature,
login configuration, real data or external consumer was changed.

## Implementation

`IConnection._persist_authentication_revocation(command, verify_legacy_write)` is
an internal, concrete method, not a new abstract requirement for downstream
connections. Its default owns the previous start/update/verify/commit/abort flow.
`User.revoke_authentication()` still authorizes, prepares values, supplies its
fixed legacy version/timestamp verifier, and changes its object/cache only after
that boundary returns successfully. The signature and typed return are unchanged.
The verifier is an implementation detail of this specific operation, not support
for arbitrary public before_commit callbacks.

`helpers/jena_authentication_revocation.py` implements the opt-in receipt path.
A `RevocationAttempt` retains the immutable command and UUID. Its `execute` sends
one update and reads the receipt; `confirmed` can subsequently observe the same
identity without writing. It validates predicate cardinality, RDF term kinds,
datatypes, digest and expected result. A partial, duplicate or mismatched receipt
cannot establish success. The experimental receipt graph must remain private and
immutable; its schema and lifecycle are not approved for deployment yet.

- Successful update plus no receipt raises existing `OldapErrorUpdateFailed`.
- Lost update acknowledgement plus exact receipt establishes success.
- Failed/uncertain delivery without a receipt, or a failed receipt read, raises
  `OldapError` with an explicit unknown-outcome message and receipt UUID.
- Conflicting/malformed receipt raises existing `OldapErrorInconsistency`.
- No implicit retries, new public exception types or new public User parameters.

The owner must retain the attempt before transmission. A retry uses its exact
command and UUID; invoking User again would create a different business operation.
Standalone recovery deliberately does not mutate an old User object or publish
stale cached state. Recovery after process loss needs durable attempt storage and
is not implemented. Exceptions alone are not a durable recovery journal.

The Jena executor currently **rejects administrator-driven revocation before I/O**.
It implements only self-revocation until grant dependencies can be checked in the
same transaction. Existing GraphDB administrator behavior remains unchanged.
A Jena owner must reject joining an interactive transaction; these standalone
commands do not implement nested transaction composition.

## Real public-call probe

`tools/migration/probe_revocation_connection.py` implements a test-only IConnection
whose only mutation is this revocation command. It uses a synthetic trusted
AuthorizationContext, owned local Fuseki callbacks and a mocked Redis cache.
Every unrelated interface method raises explicitly. It is not a login adapter
and must not be installed as an application connection.

The probe calls the real public User method, including local authorization and
post-commit object/cache logic. It verifies:

1. Success returns Xsd_nonNegativeInteger, updates metadata and invalidates cache.
2. A stale User raises the existing conflict error without local/cache changes.
3. Simulated lost acknowledgement is resolved through a matching receipt before
   the public method returns success.
4. Uncertain delivery with no receipt leaves local/cache state unchanged and
   retains the internal attempt.
5. Replaying that retained attempt twice has one database effect and does not
   silently publish success into the earlier User instance.

Accepted run: `~/Library/Application Support/OLDAP-Jena/probes/j3-connection-20261027-01/`.
[Machine-readable evidence](revocation-connection-results.json): 45 runner checks
pass, including previous transaction/RDF/revocation checks. Owned server stopped.
Lost delivery is simulated in callbacks, not with a network fault proxy; restart
is graceful. No real GraphDB or Redis tests ran.

24 offline unit tests pass, including nine receipt/failure tests, four public
legacy-path regression tests and eleven existing authentication tests:

```sh
.venv/bin/python -m unittest \
  oldaplib.test.test_jena_authentication_revocation \
  oldaplib.test.test_authentication_revocation_unit \
  oldaplib.test.test_authentication
```

The existing probe_jena.py invocation now includes the public-call checks.

## Next gates

Implement transactional administrator authorization checks and choose the durable
receipt/recovery lifecycle before activating this path. Then prove resource update
plus audit plus lifecycle outbox as one atomic operation. Login, inference,
RDF 1.2 ACL migration and a general Jena connection remain separate work.
The public interface remains the target compatibility contract for all of them.
