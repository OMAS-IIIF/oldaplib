# Fuseki sessions with existing OLDAP identity validation

Follow-up: [Jena credential bootstrap](jena-credential-bootstrap.md) now exercises
the real Connection password initialization with a separately protected read route.
The earlier identity/session milestone below remains its regression baseline.

## Implemented scope

The interactive transaction endpoint now runs as a servlet mounted directly on
an embedded Fuseki 6.2.0 server. The earlier HTTP server and the Fuseki servlet
share `tools/migration/JenaSessionEngine.java`; no duplicate transaction state
machine was introduced. Python business callbacks and public signatures remain
unchanged. All new wiring is still under migration tools, not production startup.

Files:

- `JenaSessionEngine.java`: dedicated owner thread, session deadline, protected
  application view, atomic receipt, status/reconciliation and cleanup.
- `FusekiSessionProbe.java`: Fuseki `/tx/*` servlet, service authentication,
  verified actor lookup, request parsing and HTTP response handling.
- `JenaHttpSessionProbe.java`: previous transport retained as a regression host
  for the shared engine, with its earlier synthetic identity mapping.
- `probe_fuseki_identity.py`: owns a private Python identity-verification peer,
  creates fixture tokens using the real TokenCodec and runs the common suites.
- `probe_http_sessions.py`: common connection/test harness; now also treats
  server-side commit failures or malformed commit confirmations as uncertain
  until a receipt proves success. It never replays the mutation.

## Identity flow

1. The internal caller supplies a dedicated service credential and an OLDAP
   access token. A user access token alone cannot call the servlet.
2. Fuseki verifies the service credential and sends the access token to a
   separately credentialed private Python introspection peer.
3. The peer calls the unchanged `TokenCodec.decode_access_token`, exactly the
   existing library's token-validation implementation. It returns only whether
   the token is valid and the verified `AuthorizationContext.userIri`.
4. Fuseki binds the session and receipt to that verified IRI. No caller-supplied
   actor header is trusted. A new valid token for the same actor can continue the
   session; another actor cannot.

Java neither receives the fixture JWT signing key nor implements JWT, password
or role validation. Access-token purpose, issuer, audience, signature, expiry and
claim structure remain checked in Python. Verification runs for each request;
there is no identity cache. Unavailable or malformed verification returns 503
before dispatch, while an invalid identity returns 401.

The peer is an experimental local host around the existing TokenCodec, **not** a
new deployed oldap-api endpoint. Its signing keys, identities and two distinct
service credentials are fresh fixtures. No real user credentials are read.
This proves bearer-identity integration; username/password login, anonymous
connections and fresh user/profile lookup from Jena are still open.

The existing access-token semantics are preserved: a token contains an
AuthorizationContext snapshot. This does not add live user/authVersion revocation
checks or implement RDF resource permissions in Java. Trusted Python callers
remain responsible for business authorization before issuing SPARQL.

## Server exposure and transaction results

Only `/tx/*` is mounted on the session server. No standard raw dataset, update,
query, Graph Store or administrative dataset endpoint is registered as an
alternative route. Non-POST servlet methods return 405. The protected dataset
view from the previous milestone still applies to application statements;
commit receipts use the private backing dataset in the same transaction.

Commit-reply fault injection is test-only: the servlet returns 503 immediately
before or after commit. A post-commit failure is resolved by STATUS; without a
receipt the outcome stays unknown. The previous transport additionally tests
actual connection closure with no response. Authentication failure during a
session does not itself commit or abort the writes: a valid actor can abort,
or the existing session deadline eventually cleans up the abandoned transaction.

## Verification

Accepted run: `~/Library/Application Support/OLDAP-Jena/probes/j10-fuseki-identity-20261028-03`.

- 20 identity/boundary checks: existing codec acceptance, service/actor separation,
  unsigned actor rejection, expired/wrong-purpose/audience/issuer/malformed/forged
  token rejection, token renewal for the same actor, verifier failure, rollback,
  unavailable raw dataset route and protected introspection access.
- 20 shared HTTP session checks run on actual Fuseki, including atomic receipt
  protection, uncertain commit, deadlines, competing actors and SIGKILL recovery.
- 11 unchanged audit/mobile callback checks run on the Fuseki servlet.
- The old HTTP transport passes the same 20 session and 11 callback checks after
  extracting the shared engine.
- 19 existing token/API authentication boundary tests plus 3 subtests pass with
  `--noconftest` in the API environment. Three existing API docstring escape
  warnings were observed; those unrelated files were not changed.

Results are in `fuseki-identity-results.json`, `fuseki-session-results.json` and
`fuseki-callback-results.json`. The previous broad capability runner was not
rerun; its implementations did not change.

From the migration library checkout:

```sh
../oldap-api/.venv/bin/python tools/migration/probe_fuseki_identity.py \
  --jar '/Users/rosenth/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar' \
  --output '/absolute/path/to/new/output'

../oldap-api/.venv/bin/python -m pytest --noconftest \
  oldaplib/test/test_authentication.py \
  ../oldap-api/oldap_api/test/test_authentication_boundary.py -q
```

## Remaining gates

The tests use loopback HTTP and process-owned fixtures; deployment requires
protected TLS/service networking, secret management/rotation, maintained build
packaging and removal of fault-injection hooks. The Python verification peer is
an additional per-request dependency: latency, availability and operational
integration in the actual API must be evaluated before selecting production
configuration. No second user/permission database is proposed.

Session admission, idle expiry and request-body limits are not query execution
limits. Long-running query/update cancellation, durable client/session recovery,
receipt retention/maintenance and uncertain-commit cache reconciliation remain
open. Full resource/model loading, RDF 1.2 permission representation and real
CRUD/Redis coordination still need parity tests. None of the existing GraphDB,
Redis or API services was switched to this backend.

Next: connect the real Connection initialization/user-model path to Jena in an
isolated integration test, keeping the current token and policy semantics. The
server/identity proof now provides the concrete transport boundary for that work.
