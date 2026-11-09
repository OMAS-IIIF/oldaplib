# Protected transaction metadata on Jena/Fuseki

Follow-up: [Fuseki sessions with OLDAP identity validation](fuseki-session-identity.md)
now mounts the shared session engine in Fuseki and reuses the existing Python
TokenCodec through a private verification peer. The earlier milestone below
remains the evidence for the dataset boundary.

## Implemented boundary

`tools/migration/ProtectedApplicationDataset.java` separates application access
from the internal commit receipt graph while keeping both in the same TDB2
transaction. Application queries cannot see that graph. Explicit mutations of
it fail; wildcard deletion and bulk clear operate on application data only.
The transaction owner still writes the receipt directly to the backing dataset
immediately before the one atomic commit.

This is a dataset view, not a SPARQL text filter. Graph variables, FROM clauses,
property paths and graph-management operations pass through the same boundary.
Graph objects returned to Jena also refer back to the view. The class extends
DatasetGraphBase rather than a transparent wrapper so optimizers cannot simply
unwrap it to the backing TDB2 store. Union access explicitly combines only
visible named graphs and deduplicates triples.

The existing experimental HTTP session server now executes application queries
and updates through this view. STATUS and COMMIT use the private backing store.
Neither public Python signatures nor production Connection/API code changed.

## Actual Fuseki integration proof

`tools/migration/JenaProtectedDatasetProbe.java` registers the protected view on
an embedded Fuseki 6.2.0 server using its installed builder API. It exposes
standard query, update and Graph Store endpoints on an ephemeral loopback port.
The raw backing dataset is never registered on an HTTP route.

This proves that the metadata boundary works with real Fuseki request execution,
not just with the earlier custom HTTP handler. It does **not** yet mount the
interactive session protocol inside Fuseki. That remains a separate integration
step; the current session handler still uses the local experimental HTTP server.
No endpoint here is a public deployment or an OLDAP resource-ACL boundary.

## Verification

- 37 real Fuseki checks cover ordinary default/named data, explicit/variable graph
  access, subqueries, FROM/FROM NAMED, property paths, the ARQ union graph,
  direct and variable writes, COPY/MOVE/ADD in both directions, bulk operations,
  complete rollback of mixed requests, and Graph Store GET/PUT/POST/DELETE.
- 20 interactive HTTP checks cover receipt hiding/forgery/bulk-clear protection
  as well as the previous actor binding, idle expiry, lost commit replies and
  server SIGKILL recovery.
- The same 11 Python audit/mobile callback checks pass over the protected HTTP
  transport. Production callbacks remain imported unchanged.

Reports: `protected-fuseki-results.json`, `protected-http-session-results.json`,
`protected-http-callback-results.json`. Accepted local datasets are under:

- `~/Library/Application Support/OLDAP-Jena/probes/j9-protected-fuseki-20261028-06`
- `~/Library/Application Support/OLDAP-Jena/probes/j9-protected-sessions-20261028-03`

Initial tests exposed missing Quad overloads and a recursive union delegation;
both were corrected. The Fuseki test also needed an explicit JSON Accept header.
Expected rejected-write stack traces in the server log are not failed assertions.
No production GraphDB or Redis service is involved. The earlier main capability
runner and Python unit suites were not rerun because their implementations did
not change in this step.

From the migration library checkout (Java 25 source launcher resolves the sibling
Java source file; no new installed build tool required):

```sh
java --class-path '/Users/rosenth/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar' \
  tools/migration/JenaProtectedDatasetProbe.java '/absolute/new/dataset/path'

../oldap-api/.venv/bin/python tools/migration/probe_http_sessions.py \
  --jar '/Users/rosenth/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar' \
  --output '/absolute/new/probe/output'
```

## Existing authentication boundary

Source inspection shows two distinct responsibilities already exist:

- Library `connection.py` uses triplestore service credentials separately from
  OLDAP user credentials. Credential login reads UserData, checks active status
  and bcrypt, then builds AuthorizationContext and optionally issues a token.
- Library `authentication.py` owns purpose-specific TokenCodec validation
  (signature, issuer, audience, token type, required claims and expiry).
- API `authentication.py::require_auth` constructs Connection from the access
  token and exposes that authenticated connection to request handlers. Refresh
  routes additionally compare current user state/authVersion.

Preserve this source of truth. Do not invent Java passwords or a second OLDAP
permission model, and do not accept an arbitrary actor header as authenticated
identity. A future service-to-service session binding must carry a verified
actor, use distinct credentials/audience, and remain inaccessible to ordinary
API clients. Choosing and implementing that binding is still open; current
probe credentials remain synthetic. This inspection does not claim that actual
OLDAP login has been migrated to Jena.

## Remaining limits and next step

The reserved graph is protected only when **all** application access goes through
this view. Java code, another endpoint or direct disk access to the backing store
would bypass it. This is not general per-resource authorization or a sandbox for
untrusted SPARQL: remote SERVICE/LOAD access, execution limits and deployment
network policy require separate decisions. The generic view may change query
performance; no performance parity is claimed yet.

Keep receipt retention, durable client/session recovery, cache reconciliation and
query timeouts from the previous milestone open. Bulk application CLEAR ALL now
intentionally preserves server metadata; privileged maintenance/backup requires
an explicit administrative path rather than exposure of the raw dataset.

Next: mount the existing session state machine on the maintained Fuseki server
boundary and connect verified OLDAP actor identity without duplicating Python
business authorization. Full CRUD/model and Redis coordination parity still need
independent checks before activating the new backend.
