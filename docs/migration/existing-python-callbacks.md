# Existing Python callbacks on Jena

## Decision and scope

Preserve the Python transaction owner and its intermediate reads/callbacks. The
single-request composition proof is useful for bounded commands, but translating
arbitrary Python callbacks into a large SPARQL command would obscure the business
logic and change the public contract. This probe tests an interactive boundary
with the existing library and API functions instead.

`tools/migration/JenaCallbackBridge.java` is a private stdin/stdout test bridge:
one process owns one fresh TDB2 dataset, and one Java thread owns the write
transaction from BEGIN through COMMIT/ABORT. A separate reader thread observes
only committed data. EOF aborts pending work. It is **not** an HTTP extension,
a production connection, or a deployment architecture.

`tools/migration/probe_existing_callbacks.py` implements only the necessary
IConnection methods and imports the existing implementations directly:

- Library `resource_transaction`, `resource_operation`, and `resource_query`.
- Library `audit_resource_operation` and `audit_command`.
- API `instance_views._mobile_lifecycle_hook`.
- API `GraphDbMobileMediaLifecycleOutbox`, including claim and completion.

Despite its historical class name, the exercised outbox queries work unchanged
with Jena. No production Python implementation or public signature changed in
this step; harvester/tool callers need no adjustment for this proof.

## Evidence

The 11 checks in `existing-python-callbacks-results.json` pass against Jena 6.2.0:

- The actual callback reads a mobile receipt inserted earlier in the same
  transaction. Reusing its closure does not duplicate the event.
- Resource changes, actual structural audit JSON, and mobile outbox work share
  one outer commit; independent readers cannot see staged data.
- A late callback failure rolls back the complete named-graph snapshot. Catching
  an inner exception does not make the poisoned outer transaction committable.
  A final owner veto also rolls back successful inner callbacks.
- The actual worker claims and completes an event; a wrong claim is rejected,
  an exact repeated completion is accepted, and non-mobile media add no event.
- Closing the client pipe with uncommitted work aborts it; reopening the dataset
  confirms the previous committed snapshot.

Additionally, 53 existing library transaction/archive tests (plus 7 subtests)
and 9 API mobile lifecycle tests pass. They ran with `--noconftest` in the API
virtualenv, avoiding service integration fixtures. The library environment has
no pytest installation. The earlier full HTTP runner was not rerun or changed
for this independent proof.

## Reproduce

From the migration library checkout, use the sibling API environment (its
editable library dependency must point to this checkout):

```sh
../oldap-api/.venv/bin/python tools/migration/probe_existing_callbacks.py \
  --jar '/Users/rosenth/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar' \
  --output '/absolute/path/to/a/new-probe-directory'

../oldap-api/.venv/bin/python -m pytest --noconftest \
  oldaplib/test/test_resource_transaction.py oldaplib/test/test_archive_domain.py -q
```

From the sibling API checkout:

```sh
.venv/bin/python -m pytest --noconftest oldap_api/test/test_mobile_media_lifecycle.py -q
```

The output directory must not exist. The probe owns and closes its Java process
and retains the dataset, log, and results for inspection. Accepted local run:
`~/Library/Application Support/OLDAP-Jena/probes/j7-callbacks-20261027-03`.

## Limits and next step

Folder/media model objects and the resource mutation body are synthetic. The
real audit and mobile callbacks are composed explicitly; this is not a full
ResourceInstance CRUD/ontology/authorization test. Identity is a fixture and
Redis archive coordination is disabled. No cache, login, Flask server, or media
filesystem operation is exercised. Real GraphDB and Redis are not involved.

A local pipe EOF is not proof of HTTP disconnect, network timeout, SIGKILL, or
ambiguous commit recovery. A production interactive transport still needs
bounded session lifetimes, transaction-thread ownership, authenticated session
binding, concurrency limits, and a defined way to reconcile a lost commit reply.
The revocation journal must not be assumed to solve arbitrary interactive
transaction recovery. Resolve these boundaries in a small transport prototype
before connecting general CRUD; retain the readable Python business logic.
