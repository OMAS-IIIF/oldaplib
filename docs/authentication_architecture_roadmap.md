# Authentication Architecture and Roadmap

Status: **In progress — work packages 1–5 completed through 2026-07-15**

This document defines the target architecture and implementation roadmap for
replacing OLDAP's current 24-hour bearer JWT with short-lived access tokens,
refresh tokens, and lightweight global session revocation. It is the planning
source of truth for coordinated changes in `oldaplib`, `oldap-api`, deployment
configuration, and browser clients.

## 1. Goals

The change must:

- reduce the useful lifetime of a stolen access token;
- allow a browser client to remain signed in without keeping a long-lived
  access token;
- revoke the ability to refresh after logout, password changes, user
  deactivation, or authorization changes;
- keep normal authenticated API requests stateless and free of database
  lookups for token validation;
- avoid a server-side session table or refresh-token blocklist;
- centralize token creation, validation, and HTTP authorization handling;
- minimize personal and mutable data stored in JWT payloads; and
- provide a clear future path to per-device sessions if they become necessary.

## 2. Non-goals

The first implementation will not provide:

- per-device session management;
- immediate revocation of an already issued access token;
- refresh-token rotation or refresh-token reuse detection;
- a general OAuth 2.0 authorization server;
- third-party identity providers or federated login; or
- durable session state in Redis or GraphDB.

These exclusions are deliberate. They keep the first design proportionate to
the current OLDAP authentication model.

## 3. Current state and problems

`oldaplib.src.connection.Connection` currently performs both credential
authentication and JWT handling. A successful login loads `UserData`, embeds a
serialized authorization snapshot in an HS256 JWT, and gives the token a
one-day lifetime. `Connection(token=...)` verifies the signature and expiry,
then reconstructs the authorization data directly from the token.

This has several consequences:

- user activity and permissions are not read again for the token lifetime;
- disabling a user, changing a password, or removing permissions does not
  invalidate an existing token;
- logout only removes the token in the client, while the API logout endpoint
  performs no revocation;
- issuer and token purpose are not explicitly verified;
- the token contains profile and mutable user data that authorization does not
  require; and
- API views repeatedly parse the `Authorization` header and construct a
  `Connection` independently.

The password hash is part of the in-memory `UserData` object but is already
excluded from its serialized JWT representation. That exclusion must be
preserved.

## 4. Target architecture

### 4.1 Token model

The browser authentication model uses two distinct signed JWTs. Media delivery
uses a third, independently signed capability token so that a token embedded in
an asset or IIIF URL cannot be reused as an API Bearer credential:

| Token | Lifetime | Transport | Purpose |
| --- | --- | --- | --- |
| Access token | 15 minutes | `Authorization: Bearer ...` | Authorize normal API requests without backend state |
| Refresh token | 14 days | Secure `HttpOnly` cookie | Obtain a new access token from the authentication endpoint |
| Media token | 1 hour | Asset/IIIF URL `token` query parameter | Authorize delivery of one media asset without exposing the API access key |

The lifetimes must be configurable, with 15 minutes and 14 days as production
defaults. Refresh lifetime is absolute in the first implementation; successful
refresh does not extend it.

The anonymous `unknown` pseudo-login receives only a short-lived access token.
It does not receive a refresh token because it can be recreated without user
credentials.

### 4.2 Lightweight revocation state

Each user gains one non-negative integer property:

```turtle
oldap:authVersion
```

The value starts at `0` and is included in refresh tokens. Refresh succeeds
only when the token version equals the current user version in GraphDB.

```text
User in GraphDB:  authVersion = 4
Refresh token:    authVersion = 4  -> accepted

Logout increments GraphDB value to 5
Old refresh token authVersion = 4  -> rejected
```

This is global revocation: incrementing the version invalidates refresh tokens
on every device. An access token that was already issued remains valid until
its short expiry, for at most 15 minutes with the default configuration.

### 4.3 Request flows

#### Login

1. Validate the user ID and password as today.
2. Reject inactive users.
3. Load the current authorization context and `authVersion`.
4. Return a 15-minute access token in the JSON response.
5. Set a 14-day refresh token in an `HttpOnly` cookie.

#### Normal authenticated request

1. Read the bearer access token.
2. Validate signature, token type, issuer, audience, and expiry.
3. Reconstruct the minimal authorization context from the token.
4. Execute the request without reading user authentication state from GraphDB.

#### Refresh

1. Read the refresh token from its cookie.
2. Validate signature, token type, issuer, audience, and expiry.
3. Load the user and authorization context freshly from GraphDB.
4. Reject a missing or inactive user.
5. Compare the stored `authVersion` with the token claim.
6. Return a new short-lived access token containing current permissions.
7. Keep the original refresh token and its absolute expiry.

#### Logout

1. Validate the refresh cookie sufficiently to identify the user and version.
2. Atomically increment the user's `authVersion`.
3. Clear the refresh cookie even if the server-side token is already invalid.
4. Return `204 No Content`.

The client must always clear its in-memory access token when logout is
requested, regardless of the API result.

## 5. Token contracts

### 5.1 Access-token claims

The access token must use explicit, stable claims rather than serializing a
complete `UserData` object:

```json
{
  "typ": "access",
  "sub": "rosenth",
  "userIri": "https://orcid.org/0000-0003-1681-4036",
  "iss": "https://oldap.org",
  "aud": "oldap-api",
  "iat": 1784050000,
  "exp": 1784050900,
  "jti": "generated-token-id",
  "auth": {
    "inProject": {},
    "hasRole": {}
  }
}
```

Only identity and data required for authorization belong in this token. It
must not contain names, email addresses, password-reset state, arbitrary
additional properties, or password hashes.

### 5.2 Refresh-token claims

```json
{
  "typ": "refresh",
  "sub": "rosenth",
  "authVersion": 4,
  "iss": "https://oldap.org",
  "aud": "oldap-api-refresh",
  "iat": 1784050000,
  "exp": 1785259600,
  "jti": "generated-token-id"
}
```

The refresh token must not contain profile data, roles, or permissions.

### 5.3 Token separation

Access, refresh, media, and password-reset tokens must be unambiguously
separated by:

- an explicit token type or purpose;
- a purpose-specific audience;
- purpose-specific decoding functions; and
- separate configured secrets.

No token decoder may accept a token intended for another purpose.

### 5.4 Media-token claims

Media lookup responses may include a short-lived capability JWT with
`typ=media`, audience `oldap-api-media`, and only the storage metadata required
to resolve the requested asset, such as `id`, `path`, `derivativeName`, and
`originalName`. `oldap-api` issues this token through `oldaplib` using
`OLDAP_MEDIA_JWT_SECRET`. Cantaloupe and the Flask media helper validate it with
the same media secret. The media helper validates upload Bearer credentials
separately with `OLDAP_ACCESS_JWT_SECRET`; the Cantaloupe container never
receives the access secret.

The media token is a delivery capability, not an authentication session. It
must not contain user permissions and must never be accepted by access,
refresh, or password-reset decoders.

## 6. Configuration and secret handling

Proposed environment variables:

```text
OLDAP_ACCESS_JWT_SECRET
OLDAP_REFRESH_JWT_SECRET
OLDAP_MEDIA_JWT_SECRET
OLDAP_PASSWORD_RESET_JWT_SECRET
OLDAP_ACCESS_TOKEN_TTL_SECONDS=900
OLDAP_REFRESH_TOKEN_TTL_SECONDS=1209600
OLDAP_MEDIA_TOKEN_TTL_SECONDS=3600
OLDAP_JWT_ISSUER=https://oldap.org
OLDAP_JWT_AUDIENCE=oldap-api
OLDAP_AUTH_ADMIN_USER
OLDAP_AUTH_ADMIN_PASSWORD
OLDAP_AUTH_ALLOWED_ORIGINS=
OLDAP_REFRESH_COOKIE_NAME=oldap_refresh
OLDAP_REFRESH_COOKIE_SECURE=true
OLDAP_REFRESH_COOKIE_SAMESITE=Lax
```

Production must fail closed when a required secret is absent. The current
hard-coded JWT fallback secret must be removed. HMAC secrets must contain at
least 32 bytes. Secret values must never be committed to a repository and must
follow the existing deployment-managed secret path.

Access-token and refresh responses must use `Cache-Control: no-store`.

## 7. Repository responsibilities

### 7.1 `oldaplib`

`oldaplib` owns authentication-domain and token primitives:

- the `oldap:authVersion` ontology property;
- `UserAttr`, `User`, and `UserData` support for the version;
- defaulting missing versions to zero for existing users;
- atomic version increment and automatic increment for security-relevant user
  changes;
- a minimal, typed authorization context independent of full `UserData`;
- access- and refresh-token creation and validation;
- configuration validation and purpose-specific token errors; and
- integration of access-token validation with `Connection(token=...)`.

The token module must remain focused. It must not become a generic identity
provider framework or introduce speculative registries and service layers.

### 7.2 `oldap-api`

`oldap-api` owns HTTP and browser-session orchestration:

- login response and refresh-cookie creation;
- refresh and logout endpoints;
- cookie clearing and HTTP cache headers;
- loading fresh user authorization data during refresh;
- uniform HTTP authentication errors;
- centralized bearer-header parsing;
- CORS, credential, and origin policy; and
- OpenAPI documentation.

### 7.3 Browser client

The browser client owns transient access-token use:

- keep the access token in memory rather than persistent browser storage;
- include the refresh cookie through `credentials: "include"` where required;
- coordinate concurrent requests so that only one refresh runs at a time;
- retry an original request at most once after successful refresh;
- return to login when refresh fails; and
- always clear local authentication state on logout.

### 7.4 Deployment

Deployment configuration owns secrets and origin-specific settings. A
same-origin frontend/API setup through the existing reverse proxy is preferred.
If cross-origin operation is required, allowed origins must be explicit and
credentialed CORS must never use `*`.

## 8. API changes

### 8.1 Login

Existing endpoint:

```http
POST /admin/auth/{userId}
```

Target response:

```json
{
  "message": "Login succeeded",
  "accessToken": "...",
  "tokenType": "Bearer",
  "expiresIn": 900,
  "token": "..."
}
```

`token` is retained temporarily as an alias of `accessToken` for one transition
release. New clients must use `accessToken`.

### 8.2 Refresh

New endpoint:

```http
POST /admin/auth/refresh
```

The endpoint reads only the refresh cookie and returns a new access-token
response. Authentication failures return a uniform `401` without exposing
whether the user is missing, inactive, expired, or version-revoked.

### 8.3 Logout

New preferred endpoint:

```http
POST /admin/auth/logout
```

The existing `DELETE /admin/auth/{userId}` endpoint is deprecated. During the
transition it may delegate to the new behavior, but the path user ID must not
be trusted; token identity is authoritative.

## 9. Central API authentication boundary

Bearer parsing and access-token validation must move into one explicit API
boundary, preferably a `require_auth` decorator or equally small request
helper. A global `before_request` hook is not preferred because login,
password reset, status, health, and deliberately public endpoints have
different rules.

The migration order is:

1. `user_views`;
2. `project_views`;
3. `role_views`;
4. `resource_views`;
5. `hierarchical_list_views`;
6. `datamodelling_views`; and
7. `instance_views`.

After migration, no individual view may split the `Authorization` header or
independently define malformed-token responses.

## 10. `authVersion` update rules

The version must increment in the same transaction as any of these changes:

- password change;
- successful password reset;
- transition to inactive;
- role assignment or removal;
- project membership change; or
- project-level administrative-permission change.

Logout uses a dedicated atomic revocation operation. Concurrent revocation
requests must not lose an increment. A plain unprotected read-increment-write
sequence is not acceptable.

Changing names, email addresses, or other non-authorization profile data does
not require a version increment.

For migration safety, absent `oldap:authVersion` values are interpreted as
zero. The SHACL property remains optional initially, while all newly created
users receive an explicit zero. A later data migration may backfill existing
users, but it is not a prerequisite for the first deployment.

## 11. Cookie, CORS, and request-forgery policy

The refresh cookie defaults to:

```text
HttpOnly
Secure
SameSite=Lax
Path=/admin/auth
Max-Age=<configured refresh lifetime>
```

Before implementation, deployment topology must confirm whether frontend and
API use the same public origin. If they are cross-origin:

- configure exact allowed frontend origins;
- enable credentialed requests only for those origins;
- remove wildcard credential access;
- validate `Origin` on refresh and logout; and
- use `POST` for both state-sensitive operations.

`SameSite=None` is allowed only when cross-site deployment genuinely requires
it, and then only together with `Secure` and strict origin validation.

## 12. Implementation roadmap

### Work package 1: model and ontology

Status: **Completed**

- Add `oldap:authVersion` to the OLDAP ontology and SHACL shape.
- Extend `UserAttr`, `UserData`, and `User`.
- Default missing persisted values to zero.
- Add atomic explicit revocation.
- Increment the version for security-relevant user changes.
- Add focused model and GraphDB tests.

Exit gate: existing users remain readable, new users receive version zero,
and concurrent revocation cannot silently lose an update.

Implemented result: missing persisted values read as zero, new users persist an
explicit zero, security-relevant updates increment the version in the existing
optimistic user transaction, and `User.revoke_authentication()` performs an
explicit version- and timestamp-guarded global revocation. Focused GraphDB
tests, the complete user test class, ontology parsing, and the existing
connection-token test pass.

### Work package 2: token core

Status: **Completed**

- Introduce the minimal authorization-context type.
- Add purpose-specific access and refresh token codecs.
- Validate type, issuer, audience, signature, and expiry.
- Remove hard-coded production secret fallback.
- Update `Connection` to consume access tokens through the new codec.
- Preserve the existing `Connection.token` access-token API temporarily.

Exit gate: token types cannot be interchanged and decoded access tokens contain
no unnecessary profile or reset data.

Implemented result: `AuthorizationContext` contains only user identity,
project permissions, and roles. `TokenCodec` issues and validates distinct
15-minute access and 14-day refresh JWTs using explicit claims, separate
secrets, audiences, and decode paths. Missing or short secrets fail closed,
and `Connection(token=...)` now reconstructs its authorization context through
the access-token decoder while preserving `Connection.token`.

### Work package 3: authentication endpoints

Status: **Completed**

- Update login to issue access and refresh tokens.
- Add refresh and logout endpoints.
- Add secure cookie handling and `no-store` headers.
- Keep the transitional `token` login response alias.
- Add endpoint and integration tests.

Exit gate: login, refresh, global logout, password-change revocation, and
inactive-user rejection work end to end.

Implemented result: login returns `accessToken` and its transitional `token`
alias, while authenticated users receive a secure HttpOnly refresh cookie.
`POST /admin/auth/refresh` reloads active user permissions and checks the
persisted `authVersion`; `POST /admin/auth/logout` atomically revokes the
current version and always clears the cookie. The deprecated DELETE route
delegates without trusting its path user ID. Exact optional origins,
credentialed CORS, `no-store` responses, password-change/reset revocation, and
the complete cookie contract are covered by GraphDB-backed API tests.

### Work package 4: centralize API authorization

Status: **Completed**

- Add the shared bearer-authentication boundary.
- Migrate every protected blueprint in the defined order.
- Standardize `401` responses.
- Remove local header splitting and duplicate token handling.
- Run the existing authorization regression suite after each blueprint.

Exit gate: all protected views use one authentication path with no duplicate
header parsing.

Implemented result: `oldap-api` now authenticates every protected user,
project, role, resource, hierarchical-list, datamodel, and instance route
through one `require_auth` decorator. The boundary strictly parses Bearer
credentials, validates access tokens through `Connection`, exposes one
request-scoped connection, and returns the same cache-safe `401` challenge for
missing, malformed, expired, wrong-purpose, or invalid tokens. A route-registry
test prevents protected endpoints from bypassing the boundary, and legacy
invalid-token regressions now assert the uniform response.

### Work package 5: contracts and operational configuration

Status: **Completed**

- Update the OpenAPI login contract.
- Document refresh and logout endpoints and cookie behavior.
- Add required environment variables to deployment templates.
- Configure same-origin or explicit credentialed CORS.
- Verify that no secret value is stored in Git.

Exit gate: rendered deployment configuration contains every required variable,
and OpenAPI validation succeeds.

Implemented result: the OpenAPI contract documents the access-token response,
refresh and logout endpoints, refresh-cookie lifecycle, uniform unauthorized
response, and Bearer/refresh-cookie security schemes. `oldap-setup` now renders
four distinct signing secrets, token lifetimes, issuer/audience, service
credentials, exact allowed origins, secure cookie settings, and password-reset
configuration into the API container. Ansible rejects absent, short, or reused
secrets before deployment, writes the environment file with mode `0600`, and
validates the rendered Compose model before recreating containers. Caddy no
longer overrides Flask's credentialed exact-origin CORS policy. Production
secrets are supplied through an ignored vars file or Ansible Vault; the retired
tracked `OLDAP_JWT_SECRET` values were removed and must not be reused. Media
lookup capabilities are issued with the dedicated media key and purpose; the
same media key is supplied to the media deployment, while upload Bearer tokens
continue to use the access key and the Cantaloupe container is not given that
access key.

### Work package 6: browser integration

- Move access-token storage to memory.
- Add coordinated single-flight refresh handling.
- Retry requests once after refresh.
- Call the new logout endpoint and clear local state.
- Test direct navigation, reload, expired access tokens, and failed refresh.

Exit gate: the browser survives access-token expiry without exposing the
refresh token to JavaScript.

### Work package 7: release and migration

1. Complete and release `oldaplib`.
2. Update the pinned/resolved `oldaplib` version in `oldap-api`.
3. Deploy the compatible API contract with the transitional `token` alias.
4. Deploy the updated browser client and deployment secrets together.
5. Require one new login after cutover; legacy 24-hour tokens are not accepted.
6. Monitor refresh failures, unauthorized responses, and login frequency.
7. Remove the `token` alias and deprecated logout route in a later release.

Exit gate: all deployed clients use the new access/refresh flow and no legacy
token compatibility remains.

## 13. Verification plan

### `oldaplib`

Tests must cover:

- access- and refresh-token round trips;
- wrong signature, issuer, audience, type, and expiry;
- rejection of refresh and password-reset tokens as access tokens;
- minimal access-token payload contents;
- missing-secret startup/configuration failure;
- absent and explicit `authVersion` values;
- automatic version changes for every security-sensitive user change; and
- atomic or conflict-safe concurrent revocation.

### `oldap-api`

Tests must cover:

- login response and cookie attributes;
- anonymous login without a refresh cookie;
- successful and failed refresh;
- expired, malformed, wrong-purpose, and version-revoked refresh tokens;
- inactive and missing users;
- fresh permissions after refresh;
- logout version increment and cookie clearing;
- password-reset and password-change invalidation;
- the bounded lifetime of an access token after logout;
- consistent bearer-header failures across blueprints;
- allowed and rejected origins; and
- OpenAPI validation.

Token lifetimes must be configurable in tests so expiry tests do not wait for
production durations.

### End-to-end

The final verification must include:

- login, authenticated request, forced access expiry, refresh, and retry;
- concurrent browser requests during one refresh;
- logout followed by attempted refresh;
- password reset followed by attempted use of an older refresh token;
- permission reduction followed by refresh and authorization denial; and
- restart of API instances without loss of the intended revocation semantics.

## 14. Risks and accepted trade-offs

| Risk or trade-off | Treatment |
| --- | --- |
| Access token remains valid briefly after logout | Accepted; bounded by the 15-minute lifetime |
| Logout affects all devices | Accepted for the first version and documented explicitly |
| Stolen refresh-token reuse is not detected | Accepted initially; secure cookie, bounded lifetime, and global revocation reduce exposure |
| Cross-origin cookies are easy to misconfigure | Prefer same-origin routing; otherwise require exact origins and origin validation |
| Token-contract changes can break clients | Keep one-release `token` alias and coordinate deployment |
| Authorization-context refactor can affect model code | Audit all `connection.userdata` consumers and migrate behind tests before removing compatibility |
| Concurrent version changes can race | Use an atomic or optimistic-conflict-safe GraphDB operation |

## 15. Future extension: per-device sessions

If per-device logout or refresh-token reuse detection becomes a concrete
requirement, add a durable session record containing a session ID, user ID,
hashed refresh-token identifier, expiry, and revocation state. The access-token
contract and centralized API authentication boundary can remain unchanged.

This extension is intentionally deferred until its additional state, cleanup,
rotation, and recovery behavior has concrete product value.
