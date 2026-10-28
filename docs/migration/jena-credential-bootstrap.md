# Existing Connection login with Jena user data

## Outcome and scope

The actual `Connection.__init__` can initialize namespaces, read a user from Jena,
check the bcrypt password and issue an OLDAP access token without copying that
logic into a new backend implementation. A test-only subclass overrides two
internal methods; public constructor arguments and existing token behavior stay
unchanged. Production Connection still defaults to GraphDB.

This is a credential/bootstrap integration proof, not a complete Jena Connection:
resource CRUD, full DataModel loading, inference, cache/Redis coordination and
all other connection methods remain outside this milestone. The bootstrap test
subclass is not an application-selectable backend.

## Library changes

`oldaplib/src/connection.py` now contains two protected extension points:

- `_bootstrap_query`: executes initialization reads with backend service
  credentials. Its default retains the original GraphDB URL, form body, Accept
  header, basic authentication and error propagation.
- `_bootstrap_user_query`: selects the user query. Its default calls the unchanged
  public `UserData.sparql_query`, preserving the legacy RDF* query.

The constructor still performs project namespace setup, active-user checks,
bcrypt, AuthorizationContext construction, authVersion handling and TokenCodec
issuance. Existing access-token reconstruction still skips database bootstrap;
anonymous login still loads the `unknown` user; disabling token issuance still
permits credential login without an access signing key.

`helpers/jena_user_query.py` is an opt-in RDF 1.2 query builder with the same result
columns consumed by QueryProcessor/UserData. Reifiers carry project permission
and role-default annotations. The underlying membership must also be asserted:
a reifier describing an absent membership must not grant permissions. Memberships
without annotations remain present with empty permissions/no role default.
Valid migrated data must preserve both asserted membership and its annotations;
this is not an automatic RDF* data converter.

## Existing parser correction

A focused test demonstrated that UserData could lose permissions when ordinary
membership rows arrived after their annotation rows. SPARQL does not guarantee
row order. The parser now preserves previously read project permissions and role
defaults instead of resetting them. The test checks all 24 permutations of four
membership/annotation rows. This correction also applies to GraphDB users; no
signature or result shape changes. Conflicting role-default annotations remain
invalid model data and are not resolved by this order fix.

## Credential bootstrap transport

`tools/migration/probe_jena_login.py` runs the real constructor against an owned
Fuseki process. The probe servlet has an optional `/tx/bootstrap` read route:

- Both the normal backend service credential and a separate bootstrap credential
  are required. A user token is not required because login has not happened yet.
- Only read queries (ASK/SELECT, and now CONSTRUCT) are available; mutation is rejected.
- Reads use the protected application dataset, so internal commit receipts remain
  hidden. The privileged reader can read administrative user/password-hash data;
  it must never be accessible with ordinary end-user credentials.
- Without the separate bootstrap secret in server configuration this route rejects
  all requests. No production API login/introspection endpoint was installed.

The test uses synthetic bcrypt hashes (low test-only work factor), users and
keys in a fresh dataset. No existing password database or service is contacted.
This controlled service credential read follows the existing GraphDB login's
separation between backend credentials and user password validation. It is not
a public arbitrary-query endpoint or a per-resource authorization layer.

## Verification

Accepted run: `~/Library/Application Support/OLDAP-Jena/probes/j11-login-20261028-01`.
`jena-credential-bootstrap-results.json` records 20 checks:

- Real constructor password authentication and project namespace initialization.
- Multiple/duplicate RDF 1.2 grants, membership without grants, role defaults,
  unasserted membership rejection and authVersion.
- Existing token issuance, claims and acceptance by the native Fuseki endpoint.
- IRI lookup, a custom user class and additional profile property; reversed actual
  Jena result rows preserve permissions.
- Wrong password, inactive user and missing user preserve existing error behavior.
- Anonymous login, missing authVersion default, no-token issuance without signing
  key and access-token reconstruction without bootstrap.
- Separate bootstrap credential, mutation rejection and hidden receipt graph.

45 focused offline tests plus 15 subtests pass, covering GraphDB bootstrap wire
compatibility, result-order permutations, token/API authentication boundaries and
previous revocation/journal behavior. The native Fuseki identity/session/callback
suite also passes again (20 + 20 + 11 checks) after adding the disabled-by-default
bootstrap route. The service-dependent legacy connection suite was intentionally
not run against any existing GraphDB dataset.

From the migration library checkout:

```sh
../oldap-api/.venv/bin/python tools/migration/probe_jena_login.py \
  --jar '/Users/rosenth/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar' \
  --output '/absolute/path/to/new/output'

../oldap-api/.venv/bin/python -m pytest --noconftest \
  oldaplib/test/test_connection_bootstrap.py oldaplib/test/test_userdata_order.py \
  oldaplib/test/test_authentication.py \
  ../oldap-api/oldap_api/test/test_authentication_boundary.py \
  oldaplib/test/test_authentication_revocation_unit.py \
  oldaplib/test/test_jena_authentication_revocation.py oldaplib/test/test_revocation_journal.py -q
```

## Next steps and limits

Connect full model/resource reads to the new backend, including inference and
remaining RDF* query producers. The fixture explicitly types users as oldap:User;
it does not establish subclass inference parity. Keep the existing requirement
that SHACL is model documentation rather than server-side validation.

The bootstrap route is privileged test infrastructure. Production packaging,
private TLS networking, service-secret lifecycle, query execution/network limits,
real API integration, durable recovery and cache semantics remain open. No backend
switch, release, commit or deployment was performed in this step.
