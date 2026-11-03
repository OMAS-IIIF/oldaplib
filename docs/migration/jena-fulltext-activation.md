# Durable fulltext configuration and controlled rebuild

## Scope

Implemented and exercised in the isolated migration Fuseki service, not in the
production API. The real `oldap-tools ontology fulltext-plan` output supplies the
normalized graph and field paths used for activation. Existing public API and
oldaplib signatures are unchanged. The normal Connection remains GraphDB-backed.

`tools/migration/JenaManagedText.java` owns configuration and index lifetime.
`JenaSessionEngine.java` serializes activation with interactive writers and
protects readers during index replacement. `JenaTextFixture.java` supplies the
same allowlisted document producer for rebuilds and subsequent transactional
writes. These responsibilities remain explicit; no background-job registry or
second copy of text values in RDF is introduced.

## Lifecycle

1. Validate the fully resolved project configuration and compare its reviewed
   revision (null asserts initial absence). Changed configuration with an old
   revision returns 409. An identical configuration with the current revision
   returns unchanged state without a rebuild.
2. Refuse administration while an interactive writer or reader is active.
   During rebuild, new readers receive 503; writer commands serialize behind
   maintenance on the existing owner thread. No writer is aborted for a rebuild.
3. Build a fresh Lucene directory from one committed TDB2 snapshot. Only configured
   project-graph/terminal-predicate pairs enter the index. All configured projects
   are rebuilt together, so a replacement preserves unrelated projects. Paths
   preceding the terminal predicate are still evaluated at query time.
4. Commit the candidate index, flush the new configuration file, atomically rename
   it to `managed-text/configuration.json`, and flush its parent directory. There
   is no non-atomic rename fallback. The manifest contains version 1, project
   configurations and opaque UUID revisions, not credentials or caller-selected
   file paths.
5. Switch the protected dataset view under the maintenance lock, close the old
   index and remove its derived files. Failed candidates before publication leave
   the old configuration and search available. Failure during/after publication
   fences service operations until restart; no automatic mutation replay occurs.

On **every startup**, rebuild derived indexes from committed RDF and the durable
configuration **before opening the HTTP listener**. This deliberate recovery rule
avoids claiming crash atomicity between TDB2 and Lucene. A killed uncommitted
writer cannot become a search result after restart. Malformed configuration
refuses startup; it never silently disables configured search. Existing durable
managed configuration also prevents reopening the engine without managed mode.
A failed managed transaction commit fences further operations for the same
reason; commit receipts remain authoritative after recovery.

The initial implementation uses a blocking, whole-index rebuild and therefore
requires maintenance time proportional to configured data. It does not promise
zero downtime or production-scale throughput. Old derived indexes are removed;
the RDF database and durable configuration must be backed up together by a future
service backup workflow. Indexes are reproducible, not a substitute for backups.

## Private service protocol

Opt in with `PROBE_MANAGED_TEXT=yes`, mutually exclusive with the older
`PROBE_TEXT_FIXTURE=yes` fixture mode. The existing loopback-only servlet mounts
POST `/tx/<operation>/<uuid>` and requires a transport service key plus an access
token verified by the existing Python TokenCodec peer. No raw Fuseki dataset or
admin endpoint is mounted.

`FULLTEXT_STATE` and `FULLTEXT_APPLY` additionally require the separately configured
`PROBE_FULLTEXT_ADMIN_SECRET` in `X-Oldap-Fulltext-Admin-Key`. This is a **service
maintenance capability**, not public OLDAP model-administration authorization.
The future API must check current ADMIN_MODEL/ADMIN_OLDAP permissions and resolve
the project's authoritative namespace before invoking it. Project labels and
graphs in this private protocol are trusted administration input; suffix checks
and unique graph ownership are structural guards, not an authorization policy.
Do not expose this servlet or distribute its maintenance credential to clients.

State request:

```json
{"project": "demo"}
```

Activation request (configuration is the graph and fields from the tools plan):

```json
{
  "project": "demo",
  "configuration": {
    "graph": "https://example.org/demo/data",
    "fields": {
      "title": ["https://schema.org/name"],
      "representedTitle": ["https://example.org/demo/link", "https://schema.org/name"]
    }
  },
  "expectedRevision": null
}
```

State returns `project`, `configuration`, `revision` and `status` (`absent` or
`active`). Revisions are opaque UUIDs, not GraphDB connector content hashes.
Requests are bounded by the servlet's existing 256 KiB limit; configuration is
bounded to 128 projects, 256 fields/project and 16 predicates/path. No native
GraphDB analyzer/language/type options, project disable/delete, or asynchronous
job controls are implemented. Removing an individual field is supported through
replacement. Field aliases and new projects require no new Java field mappings.

`FULLTEXT_READ` accepts `project`, `revision` and a trusted compiled SPARQL query.
It checks the revision and executes the query while retaining the same read lock.
This prevents an intervening configuration change from silently applying stale
field paths. A stale query receives 409 and must be recompiled from current
configuration. Raw READ remains the existing trusted general SPARQL interface;
future managed fulltext adapters must use the revision-bound operation.

The ordinary `oldap-tools ontology load` guard intentionally remains in place.
A private lifecycle proof does not provide a public authorized import endpoint,
round-trip dump support or backups. Next connect the API administration boundary,
then enable tools planning/apply and dump with the corresponding contracts.

## Evidence

`probe_fulltext_activation.py` passes **35 integration checks**, including actual
tools CLI normalization, pre-existing data, chained paths, field addition/removal,
independent projects, private-graph exclusion, stale revisions, active-writer
refusal, post-activation writes/deletes/rollback, clean restart, SIGKILL with a
pending writer, corrupt manifest and recovery after uncertain publication.
The two deliberate publication failure points exist only when
`PROBE_FULLTEXT_FAULTS=yes`; all datasets and keys are private fixtures.

Acceptance output: `jena-fulltext-activation-results.json`. Original owned run:
`~/Library/Application Support/OLDAP-Jena/probes/j13-managed-text-06`.
These are process-crash and explicit I/O-failure-path checks, not a power-loss or
filesystem-corruption proof. Public model-admin authorization, live metadata,
large-dataset timing, general query budgets and deployment packaging remain open.

The existing 126 model/search/list/fulltext checks and 51 identity/session/callback
checks were rerun to protect the pre-existing transport behavior. Redis cache I/O
in the model probe remains replaced by cache misses/no-op writes. No shared Redis,
GraphDB, application service or real project data was modified.

Reproduce from the library checkout after creating the sibling tools environment
as documented in `../oldap-tools/docs/jena-fulltext.md`:

```sh
../oldap-api/.venv/bin/python tools/migration/probe_fulltext_activation.py \
  --java /opt/homebrew/Cellar/openjdk/25.0.2/libexec/openjdk.jdk/Contents/Home/bin/java \
  --jar "$HOME/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar" \
  --output "$HOME/Library/Application Support/OLDAP-Jena/probes/j13-new-owned-run"
```

The output directory must not already exist. Owned processes are stopped when
the runner ends; no production activation or automatic service startup is added.

## Follow-up: public authorization and import contracts

The additive API endpoint, fresh project/admin checks and explicit tools
preflight/apply/dump/backup are now implemented and exercised through the owned
Jena adapter (46 integration checks). See
[the API report](../../../oldap-api/doc/jena-fulltext-api.md). Normal API startup
remains GraphDB-backed; this does not claim a production Jena connection or full
live ontology CRUD migration.
