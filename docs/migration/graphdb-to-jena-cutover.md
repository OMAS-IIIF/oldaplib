# GraphDB to Jena cutover: retained migration knowledge

## Home archive structure enabled — 2026-11-03

At the user's request, Fasnacht structure management is now enabled through the
server-owned structure-only policy in sibling setup. Home previously had no
policy configured; the UI's disabled message was therefore accurate. The policy
uses established ArchiveStructureEditor/ArchiveMediaEditor roles and existing
creation-grant rules, with no publication block. No role assignment or archive
data was changed. All role/model/property references were validated against Jena
before the API was recreated with a read-only policy mount.

Setup `oldap-jena-archive-enable.yml` preserves the Jena namespace, keys and data;
`archive-policy-compose.yml` is now part of home COMPOSE_FILE. Policy configuration
is shared by API and future direct clients, but no tools/harvesters were started.
[Capabilities](../../../oldap-setup/docs/jena-archive-policy-results.json) confirm
admin manage/create access, no anonymous manage/create access, and the user's
existing structure role. Actual editing/creation remains manual home acceptance;
publication and production are unchanged. Preserve this policy and overlay in
future updates and backups.

## Home upload authentication correction — 2026-11-03

The user's real upload returned 401 because initial activation rotated the API
access key but left mediahelper's access verifier unchanged. IIIF delivery had
passed because it uses a different, unchanged media signing key. This was a
cross-host deployment omission, not token expiration or an RDF migration error.

Sibling setup now shares `tasks/jena-home-media-access.yml` between activation
and the home-only `oldap-jena-media-access.yml` repair. It privately copies the
active API access key/issuer/audience only into media environment files that
already held that key, preserving private backups. Runtime inventory found only
`mediahelper-access.env` needs these credentials; worker files remain unchanged.
Changed containers must be recreated, not merely restarted. API and independent
identity verifier were unchanged; no data, images or media signing key changed.

[Verification](../../../oldap-setup/docs/jena-media-access-results.json) confirms
fresh access-token acceptance at `/upload`, exact form-validation rejection before
any write, and missing/invalid-token 401 rejection. Stories still match the frozen
baseline; fulltext, signed media and frontend checks pass. User acceptance of an
actual image upload remains separate. Every future key rotation or full provision
must coordinate API, identity verifier and mediahelper and align private deployment
inputs; do not infer upload acceptance from signed-media delivery alone.

## Home archive concurrency correction — 2026-11-03

The first browser archive load exposed a deployment capacity cycle missed by the
sequential cutover checks: public API workers waited for Jena, while Jena's token
callback waited for those same workers. A 16-request burst reproduced nine 503
responses at approximately two/four seconds; the Jena process had not crashed.
Stories could fail concurrently because they shared the exhausted pool.

The corrected setup runs `oldap-jena-identity` in the same private network
namespace, bound only to `127.0.0.1:8001`. It uses the existing pinned API image
and `scripts/jena_identity.py` to mount only the installed identity blueprint,
with its own Gunicorn pool. It does not initialize the full API or connect to
Redis/Jena and receives only callback/access signing credentials and issuer/
audience. Authentication logic is reused, not reimplemented. Namespace restarts
must include this consumer; access-key rotations must update it with the API.
The native/non-container deployment must preserve the same capacity independence.

The home-only `oldap-jena-identity-install.yml` retained old settings, verified
the new callback, drained writers/API and recreated the namespace and consumers.
No data or published image changed. All services resumed. Actual browser checks
show 665 archive media groups, 422 objects, 15 events and populated stories.
The [parallel evidence](../../../oldap-setup/docs/jena-concurrency-semantic-results.json)
records 48 HTTP 200 responses at concurrency 16 with equivalent complete content;
[public acceptance](../../../oldap-setup/docs/jena-home-after-identity-results.json)
also repeats exact story parity, login, fulltext, signed media and proxy checks.

Earlier strict parallel comparisons returned HTTP 200 throughout but differed
for list nodes represented as full IRIs versus equivalent QNames. The final
verifier expands only reviewed list prefixes in known IRI-valued properties;
text and other values remain untouched, with regression coverage. These naming
variations depend on worker prefix state and remain a separate serialization
consistency follow-up. Production acceptance must include parallel loads and the
real browser page, not only sequential endpoint checks.

## Home.org activated on Jena — 2026-11-03

The user authorized replacing the home test system and stopping its GraphDB
variant. **home.org now serves Jena through the existing public API URLs.**
Production was not changed. The persistent service uses an 8 GiB Java heap;
API and media VMs each have 16 GB assigned. Candidate/runtime root:
`/srv/storage/oldap-jena-home-20261102`. The public Compose project remains
`compose`; the private `oldap-jena-review` containers/network were removed after
acceptance, retaining their bind-mounted data. GraphDB is stopped and its
original storage is preserved. Normal DockerHub release/latest tags are unchanged.

### Source, import and approved account corrections

- Frozen source: 23 named graphs, six projects and 16 users, including operational
  graphs and external vocabularies. Whole native TriG-star export (`infer=false`)
  SHA-256: `a4593dfa78a6ac136fa67ed8dadc9124db9b82975f9e26c50e2cc736d70fcb67`.
  Both final frozen exports exactly matched the initial rehearsal snapshot.
- Native conversion: 3,139 membership reifiers and 65,377 converted quads;
  converted SHA-256: `bf1ff204f4eb531d7e1d3d700de098817cc95f5494d325141f1714d4bce5c705`.
  Four orphan membership annotations are preserved but inactive; no asserted
  memberships are synthesized.
- User selected DATA_PERMISSIONS for the conflicting WriterRecoveryOperator
  default. Guarded target-only correction
  `tools/migration/sparql/home-writer-recovery-default.ru` removes its duplicate
  DATA_VIEW value. Final application dataset: **65,376 quads and 16 users**.
  Source export remains unchanged. Temporary API write-test account was deleted.
- `JenaInitialImport` imports converted TriG into a NEW absolute dataset path,
  verifies its checksum, commits once, closes/reopens and verifies cross-graph
  RDF isomorphism before publishing the service marker. Existing targets, legacy
  syntax, side-channel accounts and reserved receipt graphs are refused.
  Failed storage remains unmarked for inspection.
- TDB2 shortens two timestamp fractional spellings (for example `.342000` to
  `.342`). Verification permits only insignificant fractional zeros in
  `xsd:dateTimeStamp`; datatypes, timezones and other RDF must match.
- Packaged service jar SHA-256:
  `4fdf005d19d5667dbe4f2fba0544a26bcba34533e8be26483aef08aec241751a`.
  Real source import passed locally and on native AMD64; importer refusal tests
  and 300-transaction/service crash-recovery checks passed.

### Activation and acceptance evidence

See [public home acceptance](../../../oldap-setup/docs/jena-home-results.json)
for image digests, backup hashes and sanitized checks. The complete operator
sequence is in the [setup README](../../../oldap-setup/README.md), with
`oldap-jena-prepare.yml`, `oldap-jena-rehearse.yml`, `oldap-jena-freeze.yml` and
`oldap-jena-activate.yml`. Preparation explicitly sets `release/start` to 0755.

The first private activation detected a missing staging Redis URL in the legacy
base Compose configuration and automatically restored the GraphDB services.
The corrected base explicitly configures that coordinator and was retested in
the private full API. A second complete freeze/backup preceded successful public
activation. Rehearsal now uses this exact base without masking missing settings.
Redis uses AOF `appendfsync=always` and `noeviction` as required by the library's
mutation guard. Original coordination DB 1 was empty; observed source import and
export jobs were terminal. No application schedulers were found on the home VMs.

Acceptance completed:

- Existing administrator and anonymous login work; API create/login/update/delete
  was verified privately before activation. Access/refresh signing keys were
  rotated at activation: users must log in again; their passwords are unchanged.
- All six project and model responses match. Before the explicit account repair,
  15/16 user responses matched; the remaining difference was the reviewed default
  permission/orphan memberships. Fresh target login verifies the selected default.
- All 30 published story responses match the frozen GraphDB baseline after array
  ordering normalization: SHA-256
  `26975a21d9088bdb0a86dc185120881b8b6ac2c4e40579f223a1e3337b52f012`.
  The new acceptance script initially lost scalar values while normalizing; this
  verifier defect was corrected and covered by a content-difference regression.
- Nine Fasnacht fulltext fields were resolved from the tools ontology YAML and
  activated through the normal API. `Laterne` returns 21 matches;
  `Laterne Stamm` and `Stamm Laterne` return the same 10 complete results.
  Source home GraphDB had no Lucene connectors: this is positive Jena search
  acceptance, **not** a fulltext equivalence claim.
- Public API, app and Fasnacht routes respond; signed IIIF metadata and an actual
  JPEG are delivered by media.home.org. Local HTTPS API status succeeds with
  certificate verification. All four media workers run; the Jena API is healthy.
- Jena publishes no backend ports; external GET/POST identity callbacks return
  404. Public Python/API signatures remain unchanged.

### Backups, rollback boundary and remaining production gates

Final backup paths:

- API: `/srv/storage/oldap-jena-backup-20261103/api.tar`, plus original frozen
  `source.trig`, `manifest.json` and original environment/proxy/Compose files.
- Media: `/data/oldap-jena-backup-20261103/media.tar`.
- Earlier complete backups dated `20261102` are retained on both hosts.
- Runtime `activation.json` records acceptance; backup `target-opened.txt` marks
  the point after which target writes may exist. Returning to GraphDB now requires
  explicit reconciliation, not simply restoring endpoints.

These are same-host recovery copies. Production still needs independent off-host
backup/restore acceptance, its dedicated writer configuration and migrated direct
harvester releases, and coordinated routine Jena update automation. Legacy update
commands refuse the Jena overlay. The installed mediahelper v0.2.17 does not include
all reviewed local authorization changes; passing positive media delivery is not
full authorization certification. The mobile worker needed forced termination
at the 90-second shutdown deadline; operational folders were empty. Resolve its
graceful shutdown before relying on the same production freeze procedure.

Canonical model/relationship cleanup is deferred; bounded legacy inverse reads
remain for compatibility with existing ontologies. No general OWL reasoner is
introduced. Other projects' fulltext configuration still needs inventory.
Private source and account evidence is outside Git under
`~/Library/Application Support/OLDAP-Jena/probes/home-source-inventory-01`.

The dated sections below retain the history leading to this activation.

## Matched candidate image publication — 2026-11-02

API/tools migration candidates are now published with separate Jena RC tags and
exact shared library wheels. Their multiarch digests and before/after protected
tag checks are retained in [image evidence](../../../oldap-setup/docs/jena-images-results.json).
The [setup release workflow](../../../oldap-setup/README.md) builds locally,
checks installed images and publishes those same IDs without rebuilding or
writing normal version/latest tags. Source snapshots/per-file hashes identify
uncommitted migration work; a base Git commit alone is insufficient provenance.
Candidate preparation requires explicit API/tools digest references.

Packaged real identity/transaction/isolation/recreation tests pass for both local
architectures and the published API digest on native x86_64 home.org. The fixture
uses the installed identity blueprint, not full API application initialization.
Tools direct GraphDB commands and harvester release migration remain separate.
Next: full API startup, real source identities/data, writer reconciliation and
coordinated activation. Existing home.org GraphDB stack remains active.

## Container deployment foundation — 2026-11-02

The dedicated `../oldap-setup` migration checkout now carries the opt-in
`jena-compose.yml`, private configuration templates and candidate-only Ansible
preparation. See [deployment/migration workflow](../../../oldap-setup/README.md)
and [transport evidence](../../../oldap-setup/docs/jena-network-results.json).
Jena owns a network namespace shared with API/direct writers; its listener and
identity callback remain loopback-only. Existing frontend API DNS is preserved.
The Caddy template rejects external `/internal/jena/*` requests. Backend container
replacement requires coordinated replacement of every namespace consumer.

Actual Jena transactions, real API identity verification, credential rejection,
bridge isolation and persisted RDF after namespace replacement pass locally on
ARM Docker and on the x86_64 API VM. The fixture mounts migration source into an
existing API runtime image and does not start the full application. Nine
configuration/writer tests pass; Ansible preparation is syntax checked only.
Owned test containers, temporary datasets and remote uploads were removed; the
running GraphDB stack remains unchanged. The runtime image is cached on the VM.
The earlier loopback/container-topology question is resolved for this slice;
full API startup, release packaging, source/account migration, writer recovery,
coordinated activation/update and production acceptance remain open.


## home.org memory allocation follow-up — 2026-11-02

After the user increased both VMs to 16 GB and restarted them, read-only SSH
verification reports `free -h` total 15 GiB on each guest, with 12 GiB available
on API and 14 GiB on media. Both report zero swap use. All previously inventoried
containers are running; the API container reports healthy. This removes the
observed memory blocker for the initial parallel test; it is not load acceptance
or verification of Proxmox ballooning configuration. The earlier inventory below
is retained as historical evidence. Private Docker/loopback topology, JDK 25 and
consistent source backup remain deployment prerequisites. No remote mutations
were performed by the agent.

## home.org read-only deployment inventory — 2026-11-02

SSH as `rosenth` succeeds on both private LAN VMs. The user reports that the
GraphDB deployment was synchronized with production; this inventory does not
independently establish data parity. No remote configuration, data, services or
packages were changed. Secret environment/configuration contents were not read.

| Observed guest resource | api.home.org | media.home.org |
| --- | --- | --- |
| OS / architecture | Ubuntu 26.04 LTS / x86_64 | Ubuntu 26.04 LTS / x86_64 |
| Docker server | 29.6.2 | 29.6.2 |
| vCPUs | 4 | 4 |
| Guest-visible RAM | 1.60 GiB | 1.60 GiB |
| Swap used during inspection | about 1 GiB | about 24 KiB |
| Data filesystem free | 233 GiB at `/srv/storage` | 928 GiB at `/data` |
| Root filesystem free | 22 GiB | 7.9 GiB (82% used) |

API containers: GraphDB `ontotext/graphdb:11.3.0`, API
`lrosenth/oldap-api:v0.2.37`, Redis `redis:7-alpine`, Fasnacht frontend
`lrosenth/fasnachts-page:v0.1.49`, OLDAP frontend `lrosenth/oldap-app:v0.2.7`
and Caddy `2.8`. API runtime reports Python 3.13.17 and oldaplib 0.7.29.
GraphDB publishes port 7200; API and Redis expose internal container ports.
GraphDB's bundled Java is Temurin 21.0.10, not the JDK 25 required by the new
service artifact; no host Java executable was found on PATH.

Media containers: SIPI `lrosenth/sipi-2:0.1.0`; mediahelper, ingest, export and
mobile workers use `lrosenth/oldap-mediahelper:v0.2.17`; Caddy `2.8`.
An image tag alone does not verify inclusion of the reviewed asset-authorization
correction. SIPI's 2 GiB and ingest/mobile workers' 6 GiB container memory limits
exceed current guest-visible RAM; limits are not memory reservations.
Inspected containers use `unless-stopped` restart policies.

Observed persistent source paths (disk usage is a live inventory, not a backup):

- API GraphDB: `/srv/storage/graphdb` → `/opt/graphdb/home`, about 210 MiB.
- API application data: `/srv/storage/oldap-data/oldap-api` → `/data`;
  the enclosing `oldap-data` directory uses about 9.9 MiB.
- API Redis: `/opt/oldap/compose/redis-data` → `/data`, about 108 KiB.
- Media binaries: `/data/media`, about 20 GiB; mounted read-only by SIPI and
  read/write by mediahelper and the ingest/mobile workers.
- Media operation directories: `/data/oldap-import-records`, `/data/oldap-ingest`,
  `/data/oldap-mobile-uploads`, `/data/oldap-exports`, each about 4 KiB.
- SIPI cache: Docker volume `compose_sipi_cache`; derived cache, not source media.

**Next deployment prerequisites:**

1. Check Proxmox memory allocation and ballooning. Current guest-visible RAM is
   insufficient for the planned 8 GiB Jena heap alongside GraphDB and the API.
   16 GiB for the API VM is a reasonable initial parallel-test budget if the host
   has capacity, not a measured production requirement. Recheck guest RAM/swap
   after adjustment; size the media VM for actual worker concurrency separately.
2. Resolve private container networking before installation: the packaged Jena
   service and identity callback require loopback, whereas the existing API runs
   in Docker. A container's loopback is not the VM host's loopback. Choose and
   validate a compatible network topology without exposing the private service.
3. Prepare the Linux JDK 25 runtime and reviewed release/configuration through the
   existing deployment workflow. Preserve the GraphDB baseline for comparison.
4. Plan a consistent GraphDB/media/operations/Redis source backup and writer
   quiescence before migration. The new native Jena backup utility cannot back up
   GraphDB storage. Keep datasets/backups on the large data mounts, not root.

No remote installation, endpoint switch or migration has occurred. Runtime and
whole-system acceptance on these VMs remain open.

## Production target and readiness review — 2026-11-02

**Decision:** Jena/Fuseki is the production target. The user reports a discounted
GraphDB offer above EUR 8,500/year with 5% annual increases and rejects that cost.
Prioritize a reproducible, recoverable deployment over further comparative tuning.
This decision does not certify the present prototype as production-ready.

This review reads repository sources and retained evidence; it is not a new test
run. The gate table below is the current planning summary. Later sections retain
historical findings, including older "open" items subsequently addressed by linked
acceptance runs. Do not add historical test counts or treat them as one current
release acceptance run. General OWL inverse support still exists in the adapter;
removing Fasnacht's inverse axioms did not remove it globally.

### Persistent private backend service (implemented 2026-11-02)

The first readiness slice now has a built service and owned lifecycle acceptance.
The source review below describes the earlier probe; the service supersedes its
stdin lifetime, random port, in-memory identifier set and 256-admission budget.
It does not close full-system restore, migration or production-deployment gates.

Build and operator files live in `services/jena/`. `JenaService` owns startup,
configuration, loopback HTTP and shutdown; the shared engine, protected dataset,
servlet and managed-text implementation remain canonical in `tools/migration/`.
The explicit build source list reuses them without copying logic. The diagnostic
`FusekiSessionProbe` subclass is excluded from the service artifact. Its historical
source-launch interface remains available for existing acceptance runners.

**Transaction guarantee:** BEGIN first commits a small `reservedBy` admission record
in the existing protected receipt graph, then opens the application transaction.
A failure/expiry/abort still consumes that UUID. COMMIT stores the separate `owner`
receipt atomically with application changes, as before. Only that commit receipt
proves success; a reservation alone returns STATUS `unknown`. There is no automatic
mutation replay, time-based pruning or ever-growing in-memory identifier set.
Admission records and receipts grow on disk and must be included in backup; do not
clear them as cache. Legacy committed receipts also prevent reuse. Historical
probe-only aborted IDs that were never persisted cannot be recovered retroactively.
Each BEGIN adds one small durable storage commit; write throughput requires the
later production workload test. Application queries/updates cannot access this graph.

**Build (offline, JDK 25 and reviewed Fuseki 6.2.0 distribution):**

```sh
python3 services/jena/build.py \
  --java-home /absolute/path/to/jdk-25 \
  --fuseki-home /absolute/path/to/apache-jena-fuseki-6.2.0 \
  --output /absolute/path/to/new-release-directory
```

The builder checks the pinned Fuseki jar SHA-256, compiles the allowlisted sources,
copies Apache license/notice files and writes `build.json` with source/dependency
and artifact hashes. Output must not exist. The release has no editable Python
or local source-tree dependency. Identical reviewed sources/JDK/dependency produce
the same service jar; dependency upgrades require deliberate pin/revalidation.
`JenaTextFixture` remains a compile dependency of the legacy engine constructor,
but the production entry point explicitly selects managed text and cannot enable
fixture mode. All `PROBE_*` environment flags are ignored by that entry point.

**First initialization and normal start:** copy
`services/jena/service.properties.example` to a private 0600 file, replace all
placeholders, create its private parent directories, and choose a new absolute
dataset path. Generate separate random transport, bootstrap, fulltext and identity
secrets; map them to the corresponding existing API variables documented in
`oldap-api/doc/jena-api-startup.md`. Do not store this file in Git. The API's identity
callback must be reachable on loopback and the API must support concurrent requests.

```sh
export JAVA_HOME=/absolute/path/to/jdk-25
export JAVA_HEAP_MB=8192
/absolute/path/to/release/start /absolute/private/service.properties --init
# After stopping that first process with SIGTERM/Ctrl-C:
/absolute/path/to/release/start /absolute/private/service.properties
```

Initialization creates an empty dataset, never demonstration users or data.
Without `--init`, missing/unrecognized storage is refused rather than replaced
with a new empty database. Provisioning/migration is the next stage; this does not
make a newly initialized dataset an immediately usable OLDAP system. Do not point
this command at a probe or existing production dataset. A failed initialization
requires inspection, not deleting a possibly populated directory and retrying.

The configured port is fixed and loopback-only. `/tx` retains the existing private
protocol; `/health` reports local readiness, not successful API identity verification
or end-to-end application health. No raw Fuseki query/update/admin routes are mounted.
Bootstrap, identity and fulltext credentials remain separate. Test fault/timing
headers have no effect. SPARQL reads have a 60-second execution timeout; request
bodies retain the 256-KiB boundary. These limits do not provide streaming import.

SIGTERM stops the listener/drains requests, aborts an outstanding write on its
owner thread, then closes the text index and TDB2. Stdin EOF has no effect. Use
one service process per dataset. The supplied Linux `oldap-jena.service` and macOS
`org.oldap.jena.plist.example` are supervisor templates, not installed jobs; replace
paths/user/JDK and provision directory ownership before use. Neither includes
`--init` on automatic restart. Allow 90 seconds for shutdown; unusually long
updates/rebuilds can exceed graceful shutdown and then require ordinary crash
recovery. The tested macOS process lifecycle does not certify a Linux deployment.
Keep the API and this service on the same host for this first supported topology;
remote/TLS/container-network deployment is not silently enabled.

**Owned acceptance:** run `services/jena/check_service.py` using the sibling API's
Python environment (it supplies the existing token-validation test peer):

```sh
../oldap-api/.venv/bin/python services/jena/check_service.py \
  --java-home /absolute/path/to/jdk-25 \
  --distribution /absolute/path/to/built-release \
  --output /absolute/path/to/new-private-test-directory
```

[Retained acceptance evidence](jena-service-results.json): 22 packaged-service
checks (including 300 commits), 20 identity, 20 session, 11 callback and 50
managed-fulltext checks pass, plus 18 offline connection/API tests. Two builds
produce identical manifests/service jars. The initial reservation-refusal test
found an internal end-without-abort error; explicit abort restores the expected
409 conflict. The corrected suites were rerun successfully. Supervisor template
installation and full production acceptance remain separate.

This starts its own identity peer, fixed loopback port, credentials and dataset,
then shuts them down. It exercises 300 commits, abort/expiry/replay/ownership,
SIGTERM and SIGKILL, hidden metadata, disabled test hooks, startup refusal and
managed fulltext recovery. The existing identity/callback and managed-text suites
also remain applicable. This is not a complete backup restoration or deployment
acceptance. The original GraphDB/API/Redis services are not changed.

### Offline backup/restore and first remote target — 2026-11-02

**Deployment direction:** the user names `home.org` as the first test host, before
production cutover. No connection, upload, installation, DNS change or remote
service operation has been performed by this local implementation. Confirm its
OS/JDK, storage, private API/backend topology, Redis persistence, media paths and
available backup space before planning the host-specific rehearsal.

`services/jena/backup.py` is now included in the built service distribution with
its checksum in `build.json`. It creates directory bundles with five explicitly
required components:

| Component | Required deployment scope |
| --- | --- |
| dataset | Complete stopped TDB2 state, admin/users/roles, protected transaction admissions/receipts, service marker and managed fulltext configuration. |
| media | All original files and required derivatives referenced by this deployment. Include every configured media volume in the collected directory. |
| operations | Private service/API configuration and secrets, archive/server policy, supervisor/proxy settings and the reviewed path/version inventory. |
| coordination | Complete stopped Redis persistence directory, including AOF manifest/base/incremental files or the configured persistence state. |
| release | Exact built service, dependency jar, startup script, backup operator and version/hash manifest. Retain matching API/library/tools/media release identities in operations too. |

The command cannot discover missing external volumes or forgotten configuration
files; the operator inventory defines completeness. No account side-channel
export is needed for native TDB2 restore: administrative RDF is included. Object
cache is disposable. If its DB shares a Redis persistence directory with writer
coordination, its bytes may be captured too, but never reactivate that stale cache.
Use a fresh isolated cache or clear only the explicitly identified cache DB after
inspection. Never use FLUSHALL or clear coordinator gates as a restore shortcut.

**Consistency boundary:** stop/fence API workers, harvesters, media writers and
all other writers; stop Jena cleanly and stop coordination Redis after its final
persistence acknowledgement. Retain the existing recovery-controller evidence
where that deployment uses one. The explicit `--writers-stopped` argument is an
operator assertion, not automatic distributed fencing. The tool additionally holds
TDB's POSIX file lock throughout the copy and refuses a live service. Copy hashes
are checked against source bytes, but cannot establish a coherent live snapshot
across external services. Do not use this as an online-backup command.

```sh
python3 /absolute/release/backup.py backup \
  --dataset /absolute/stopped/dataset \
  --media /absolute/collected/media \
  --operations /absolute/private/operations \
  --coordination /absolute/stopped/redis-data \
  --release /absolute/release \
  --source-generation reviewed-source-generation \
  --writers-stopped --output /absolute/backups/new-backup
python3 /absolute/release/backup.py verify /absolute/backups/new-backup
python3 /absolute/release/backup.py restore /absolute/backups/new-backup \
  --output /absolute/isolated/new-restore
```

All paths are operator-owned local directories. Symlinks and special files are
refused. Use a new output path outside source directories. Source and backup are
not overwritten. Files are copied with private permissions and content checksums;
bytes/directories are fsynced before atomic publication and the parent afterwards.
A publication durability error must be inspected rather than retried over the
existing destination. This is not a power-loss or storage-hardware certification.
The bundle contains credentials and therefore belongs on private, appropriately
protected backup storage; it is not an export for public Git/artifact hosting.

Dataset locks and derived managed Lucene indexes are omitted. RDF and
`managed-text/configuration.json` are authoritative; the service rebuilds the index
before accepting traffic. Other files, empty directories and executable launchers
are retained. Verification rejects missing/extra/changed files, unsafe manifest
paths, symlinks and mismatched release artifacts before restoring any target.

**Restore is deliberately not activation.** The new directory contains
`RESTORE_REVIEW.json` with a fresh target-generation ID and required review steps.
That file documents the handoff; no runtime currently reads it as an enforcement
barrier. The command starts no services and does not rewrite saved secrets or
endpoint paths. Keep restored Redis offline until reconciliation; fence old writers,
rebind deployment paths/endpoints and the caller's dataset-generation identity,
review/rotate credentials as appropriate, and use an isolated empty cache. Do not
point an existing worker at this state merely because its process can start.
Retained old commands must be inspected against receipts, never automatically
replayed into a new generation. A missing receipt after restore may mean a commit
occurred after the recovery point, not that it never happened. Reconcile such
operations separately before enabling writers.

**Local evidence:** [backup/restore acceptance](jena-backup-results.json) retains
40 service/recovery checks plus seven offline bundle tests. The owned test covers
real bcrypt login and role/admin grants from restored RDF, complete application
and admin query equality, committed and aborted transaction identities, searchable
folded text rebuilt from RDF, exact representative media/config bytes, and a real
Redis AOF restored into a separate owned process. A synthetic pending marker and
closed barrier are preserved; a new journal generation does not discover old IDs.
No production worker replay or operator-recovery integration is claimed.

Live-Jena backup refusal, corrupt-input refusal, existing-target refusal and the
explicit loss of a post-backup commit at the earlier recovery point also pass.
The fixture uses five initial transactions; the preceding service acceptance
separately retains its 300-commit test. The source fixture and restored target
never write concurrently. Both processes and the owned Redis/identity peer stop
at completion. Local timings are recorded for reproduction only, not as an RTO
promise for real media volumes or `home.org` storage.

Reproduce using the sibling API Python environment and the same built service:
`services/jena/check_backup.py --java-home ... --distribution ... --output ...`.
Run offline checks with `python3 -m unittest discover -s services/jena -p test_backup.py`.
The next gate is an actual source/account/media inventory and a host-specific
isolated rehearsal plan for `home.org`, followed by the same restore acceptance
on that host before any production traffic switch.

### What is already demonstrated locally

- Real Fasnacht model/data conversion, canonical part relationships and unchanged
  unrelated triples; preserve the reviewed archive-assignment semantics.
- Existing API/library contracts, normal resource/model/list/user writes, rollback,
  authorization and warm-cache revocation checks in owned acceptance fixtures.
- YAML-configured fulltext, new fields, AND words, approved accent folding, deep
  100-row paging, metadata/date search and bounded concurrent-reader workloads.
- Browser navigation, image/PDF/original reads and corrected asset authorization.
- Latest mixed public-read comparison: 624 successful requests over two runs;
  confirming GraphDB/Jena medians 57/73, 117/139, 203/250 ms at 1/4/8 readers.
  This is local evidence, not a production response-time guarantee.

### Required gates, in implementation order

| Priority | Gate and current gap | Acceptance before cutover |
| --- | --- | --- |
| 1 | **Persistent backend service — implemented locally.** See the service section above. The historical probe remains a test-only entry point. | Reproducible versioned artifact, explicit private endpoint/configuration, normal supervised startup/shutdown/reopen, test hooks disabled in production. Run more than 256 sequential transactions and replay/ownership/expiry/restart checks. Preserve receipts and uncertain-outcome handling; do not merely delete the limit or clear identifiers periodically. |
| 2 | **Offline recovery — implemented and rehearsed locally.** The five-component bundle and restore checks are described above; the actual deployment inventory, fencing and `home.org` rehearsal remain open. | Stop writers and take a consistent backup of RDF/admin/receipts, fulltext configuration, media, deployment policy and required durable coordination state. Restore into a separate empty target; rebuild indexes and compare inventories, permissions and search. Define dataset-generation/coordination reconciliation so stale operations cannot enter a restored target. Record restore time and recovery point. |
| 3 | **Full source migration.** Existing real-export runs retain account headers but use owned fixture users. Converter and HTTP transfer have 16 MiB and 256 KiB bounds respectively. | Inventory the actual source, users/roles/namespaces and binary references; demonstrate a consistent final export and an appropriately sized import path. Preserve credential/role semantics without printing secrets. Verify canonical part transformation and explicit expected ontology differences. No blind append/retry on uncertain import. |
| 4 | **Application release.** Local API dependency is editable `../oldaplib`; Java is launched from migration sources. Mediahelper correction was tested using a source overlay. | Build matching versioned library/API/tools/backend/media artifacts without local checkout dependencies; verify installed versions. Rehearse actual worker count, private identity callback, Redis cache versus durable writer state and process restarts. |
| 5 | **Target acceptance.** Local public-reader measurements do not cover the full production workload. | On representative copied data, run public/restricted/revoked users, mixed reads/writes, upload/derivatives, model/list changes and the harvester/tools paths intended for launch. Include sustained load, service interruptions and resource monitoring. Record agreed acceptable latency and tested capacity. |
| 6 | **Controlled switch.** No production cutover/recovery procedure has been executed. | Retain final backup/checksums and release versions; freeze old writers, migrate and validate before routing clients to Jena. Specify who accepts the switch. After Jena accepts writes, reverting to the old GraphDB snapshot loses those changes unless they are reconciled; do not promise a simple endpoint rollback. |

### Scope decisions for the earliest sound release

- Keep public signatures and validate-on-write/trusted-database-read behavior.
- Start with the existing single-writer architecture; do not add clustering or a
  new transaction protocol merely to package the service.
- Do not remove existing request bounds without a measured import requirement;
  a controlled offline initial import may be simpler than a new streaming API.
- General modeled inverse fields and other projects require a source/consumer
  audit. They are not automatically prerequisites for a Fasnacht-only first
  deployment, nor implicitly approved for a deployment containing Chama.
- Frontend grouped paging still has a 5000-row window. Before deferring it,
  demonstrate that the initial production dataset's required workflows are complete;
  otherwise it becomes a launch blocker.
- Further GraphDB benchmarks and marginal query optimizations are secondary to
  these gates. No new target latency or cutover date has been agreed.

**Next implementation slice:** inventory the actual source/accounts/media and prepare
an isolated deployment/restore rehearsal on `home.org`, the user-selected first
test host. Local service and backup acceptance do not close host-specific fencing,
worker, capacity or production cutover gates.

Source review: [service entry point](../../tools/migration/FusekiSessionProbe.java),
[transaction engine](../../tools/migration/JenaSessionEngine.java),
[API startup contract](../../../oldap-api/doc/jena-api-startup.md),
[development services](../../../oldap-api/doc/jena-local-development.md),
[project transfer limits](../../../oldap-tools/docs/jena-project-transfer.md),
[durable recovery boundary](revocation-durable-recovery.md), and
[media release requirement](../../../oldap-api/doc/jena-asset-delivery.md).

[Post-Python/payload GraphDB comparison](../../../oldap-api/doc/graphdb-jena-python-comparison.md)
retains two successful runs (624 timed requests). Jena mixed medians now trail
GraphDB by ~19–28%; count/date gaps and production sizing remain open.

[Smaller summary payloads](../../../oldap-api/doc/jena-summary-payload.md)
retains JSON-LD while removing duplicate permission-pair nodes before joins.
Full response/permission parity and a larger copied fixture pass.

[Operation-local superclass reuse](../../../oldap-api/doc/jena-model-read-reuse.md)
reduces repeated model reconstruction while retaining caller-owned copies and
fresh later loads. Two API comparisons show a modest ~10–13% dated-page gain.

[Trusted reads and datatype validation](../../../oldap-api/doc/jena-validation-performance.md)
records the general validate-on-write/read-without-revalidation boundary and
measured Python gains. Count EXISTS/date UNION experiments were reverted; keep
their growth/end-to-end evidence when planning future query changes.

[Post-optimization GraphDB/Jena comparison](../../../oldap-api/doc/graphdb-jena-precheck-comparison.md)
passes all 312 timed requests. Jena medians are 118/270/488 ms at 1/4/8 readers;
GraphDB remains faster. This is local read evidence, not production sizing.

[Dating eligibility optimization](../../../oldap-api/doc/jena-dating-precheck.md)
skips unnecessary model/list preparation on non-Dating pages; live model lookup
covers future/inherited fields. Positive cases retain full permission-aware hydration.

[Search decomposition](../../../oldap-api/doc/jena-backend-profile.md) identifies
unnecessary Dating/model preparation on name-only pages as the next focused
optimization. No authorization shortcut or runtime change applied.

[GraphDB/Jena read comparison](../../../oldap-api/doc/graphdb-jena-performance.md)
passes six public real-data cases and 312 timed requests. GraphDB is faster in
this local baseline (mixed medians 61/164, 128/315, 205/579 ms GraphDB/Jena at
1/4/8 concurrency). Source unchanged; no runtime changes. Equal deployment,
roles, large paired datasets and write/soak comparisons remain open.

[Optimized concurrent-reader rehearsal](../../../oldap-api/doc/jena-search-load-optimized.md)
passes 211 checks including 130 mixed-workload requests at 1/4/8 concurrent reads.
Median 1.25/1.88/2.99 s with 100-row pages; fulltext tails, date values and
post-read revocation pass. Local bounded evidence, not production capacity.

[Schema-first candidate joins](../../../oldap-api/doc/jena-search-candidates.md)
resolve property rules before instance links/types. Same read semantics and
permissions; 12000-resource A/B responses and 1000-child growth pass. No ontology
change, index rebuild or public contract migration.

[100-row search paging](../../../oldap-api/doc/jena-search-pagination.md) removes
useless sort joins from counts and corrects Jena Text's hidden 10000-candidate
window. Preserve the explicit full-index lookup before permissions/paging;
omitting the limit (or using -1) reintroduces incomplete totals and deep pages.
No reindex, ontology change or public signature change is required.

[Growth and concurrent-reader evidence](../../../oldap-api/doc/jena-search-load.md)
passes complete API paging and permission isolation at 12000 synthetic records.
Broad queries become slow at 4/8 simultaneous requests; the frontend 5000-row
window and production load remain open gates. No runtime change in this rehearsal.

[Browser performance follow-up](../../../../OLDAP/FasnachtsPage/docs/archive-browser-performance.md)
confirms backend gains reach the UI while preserving counts, sorting and
public/audit/logout visibility. Local metadata-only evidence, not production load.

[Dating hydration follow-up](../../../oldap-api/doc/jena-dating-hydration.md)
reduces repeated namespace conversion within each graph. No query, permission,
data-format or public contract migration is required for this optimization.

[Broad metadata/date query optimization](../../../oldap-api/doc/jena-metadata-performance.md)
retains permission semantics and API contracts. Whole-grant extraction is limited
to searches without text/relationship candidates; preserve that boundary during
future tuning. Native growth and real-export API evidence are linked there.

**Current semantics, step 2 (2026-10-30):** [OLDAP profile](oldap-semantics-profile.md)
now supports subclass/subproperty reads without equivalence expansion. Legacy
inverse handling remains until modeled inverse fields are implemented in step 3.
[Implementation and validation](jena-bounded-entailment.md).

**Historical acceptance:** [Bounded entailment](../../../oldap-api/doc/jena-bounded-entailment.md)
resolved the initial Chama differences with 120 matching comparisons under the
previous equivalence-aware behavior. This is no longer an exact-content parity
claim for the current profile. Real-project comparison must explicitly account
for the intentional changes; no production cutover has occurred.

Start here when resuming the actual system transition. This document records the
user's explicit requirement to retain migration knowledge across sessions. It is
a planning and evidence index, not an executable production cutover procedure.
No production migration has been completed or authorized by this document.

Relationship search now uses early mandatory IRI candidates before access joins.
See [performance and acceptance](../../../oldap-api/doc/jena-parts-performance.md);
production load/cache acceptance remains open.

Warm-cache search/detail acceptance now uses actual isolated Redis; see
[cache evidence and token lifetime boundary](../../../oldap-api/doc/jena-cache-reads.md).
This does not close production cache, concurrency or browser gates.

[Browser rehearsal](../../../oldap-api/doc/jena-browser-rehearsal.md) verifies metadata/navigation and identity separation. Provision namespaces for all retained role IRIs before issuing new tokens. [Signed image delivery](../../../oldap-api/doc/jena-media-browser.md) also passes with an owned SIPI copy and unchanged source hash. Other media paths (PDF/original/download/upload/anonymous fallback), fulltext and direct assignment UI gates remain open.

[PDF/original delivery](../../../oldap-api/doc/jena-asset-delivery.md) passes byte integrity, ranges, authorized PDF browser display and internal-file denial. Frontend now preserves local non-IIIF capabilities. **Source correction verified:** mediahelper now rejects invalid supplied tokens and signed zero/malformed permissions without anonymous fallback; genuine tokenless public lookup remains supported. Nine owned file-delivery checks pass with source overlaid in the installed runtime. A rebuilt/versioned mediahelper release and deployment are still required before production acceptance. No running media service was changed.

## Decisions to preserve

- The goal is GraphDB → Jena/Fuseki, not merely Jena dump/load.
- Keep public API routes and public oldaplib function signatures compatible with
  oldap-tools and harvesters. Document any unavoidable change and its callers.
- Do not enable a general OWL reasoner. Use explicit project-scoped hierarchy
  paths; audit any remaining reliance on GraphDB inference with real data.
- SHACL is model documentation/read metadata, not runtime validation.
- Preserve asserted memberships separately from RDF 1.2 `rdf:reifies` grants.
  Never turn an orphaned annotation into an active role/project membership.
- Preserve graph boundaries, permission values, annotation metadata and blank-node
  identity. Converting syntax alone does not prove authorization equivalence.

## Archive assignment correction

`fasnacht:archiveUnit` is stored directly; `schema:about` remains independent
subject data. The Fasnacht YAML explicitly clears the old inverse axiom with
`inverse_of: null`. Inspect both axiom orientations in the target; append-only
project transfer cannot remove existing schema statements. Do not reverse subject
links into assignments. [Case I3 and native acceptance](oldap-semantics-profile.md#i3-archive-assignment--an-asserted-relation-not-an-inverse-field)
records the domain decision and 11 new checks within 152 passing native checks.
The [owned HTTP migration](../../../oldap-api/doc/jena-archive-assignment.md) now
verifies tools preview, backup, API removal, unchanged instances and zero-write
replay for the forward axiom. Full Fasnacht import, reverse/external axiom
inventory and live-data audit remain pending.

## Canonical Fasnacht part relationships

Use only `dcterms:isPartOf`; public child lists query it in reverse.
[Target preflight and conversion](fasnacht-parts.md) preserves existing edges and
checks Place multiplicity. Revised YAML omits hasPart fields; omission is not
in-place model deletion. Full target model cleanup and browser acceptance remain
open. No schema.org story relationships are automatically converted.

## Full Fasnacht model on a fresh target

[Complete YAML/HTTP rehearsal](../../../oldap-api/doc/jena-fasnacht-model.md)
passes with all declared classes, taxonomy files and external registrations.
The 224-operation import replays with zero writes; reverse lookup returns only
the granted child after canonical part conversion. Synthetic instances and
skipped GraphDB connectors: real data, fulltext and in-place cleanup remain open.

## Real Fasnacht source rehearsal

[Real-data comparison](../../../oldap-api/doc/jena-fasnacht-export.md) passes
against a fresh local native TriG-star export: 38,674 instance triples, exact
canonical part union and unchanged remaining data; five parent API lookups agree.
Archived gzip backups contain encoded RDF4J triple IRIs and are not accepted
converter inputs. Request application/x-trigstar with infer=false. Account headers
are retained, not restored. This is not production/account/fulltext/performance
acceptance; the owned audit identity differs from real users.

## Proven tools and evidence

1. [Initialization files](jena-seed-ontologies.md): native RDF 1.2 admin seeds,
   stable reifiers, 29 preserved permission values; 24 native checks and nine
   offline tests. Shared/example vocabularies needed no syntax rewrite.
2. [Legacy export converter](graphdb-rdfstar-conversion.md): local TriG/gzip →
   native RDF 1.2, private output, checksums and verification report. 21 native
   and eight CLI checks, including original GraphDB admin files and owned TDB2.
   Implementation: `tools/migration/ConvertLegacyRdfStar.java`.
3. [Scoped project transfer](../../../oldap-tools/docs/jena-project-transfer.md):
   existing tools project dump/load can use Jena for provisioned projects.
   [Acceptance](../../../oldap-api/doc/jena-project-transfer.md) records 154
   accumulated integration checks and 31 targeted offline tests, including native
   graph round-trip and fulltext commit/rollback.

4. [Real Chama rehearsal](../../../oldap-api/doc/graphdb-project-rehearsal.md):
   GraphDB export → conversion → isolated Jena/API with real owned Redis. 112 API
   statuses match, 77 bodies match, 35 differ in scoped inference/inverse-property
   behavior. Export/import is proven for this project; **content parity remains
   open**. External vocabularies must be provisioned and explicitly selected by
   bounded queries. Converter now has 28 native and eight CLI checks.

Test counts describe specific past runs, not production readiness. Re-run the
relevant acceptance on the actual versions and representative export at cutover.

## Important boundaries — do not forget

- The converter supports flat URI-based OLDAP membership annotations, not arbitrary
  RDF-star. Unsupported/mixed/nested forms fail explicitly.
- Old tools `#>>` user records are outside RDF and are refused. Do not strip them
  merely to bypass refusal: account migration is still required.
- Converter input is bounded to 16 MiB decompressed and processed in memory.
  The existing private HTTP transfer remains limited to 256 KiB per JSON request.
- Converter output is plain native TriG, **not** the versioned tools project-dump
  wrapper. Graph selection and packaging are still a separate step.
- Jena project dump currently requires `--no-admin`; the target project namespace,
  users and roles must already be provisioned. Import appends rather than replaces.
  Reimporting blank-node content is not generally idempotent; never blindly retry
  an uncertain commit.
- Native data export is not a complete backup. Binary media, index configuration,
  server/archive policy and administrative identities need separate handling.
- GraphDB's existing account restore can delete/recreate users. That behavior has
  not been enabled or accepted for Jena.
- Object cache, durable writer coordination and crash recovery require explicit
  deployment acceptance. Tests used owned services; the user's Redis was untouched.

## Resume sequence for a real migration rehearsal

1. Identify a representative GraphDB project, source dataset and isolated target.
   Inventory named graphs, annotations, accounts/roles, media and inference needs.
2. Retain an unchanged source export and its checksum. Establish how the source
   snapshot is kept consistent; do not rely on unrelated per-graph reads during
   concurrent writes.
3. Run offline conversion, review counts/orphans/refusals and retain its report.
   Resolve unsupported constructs and account side-channel records deliberately.
4. Provision the isolated target's base/shared models, project, accounts/roles and
   policy; then import the selected converted graphs through a verified path.
5. Restore/configure fulltext fields and verify rebuilding. Check media references
   and delivery separately from RDF metadata.
6. Compare source/target inventories and representative API responses, including
   ordinary, restricted and revoked-user permissions; test updates and rollback.
7. Only after rehearsal acceptance, prepare the actual cutover: write freeze,
   final consistent export, recovery plan, cache/worker configuration, validation
   and endpoint switch. Specify the rollback strategy before target writes begin.

The Chama rehearsal has executed steps 1–4 and compared basic API reads under
step 6; it found concrete remaining inference differences. The bounded-entailment follow-up has now completed scoped external vocabulary
superclass/equivalence and inverse-property reads, and all 120 API comparisons
match. Retain source namespace/prefix metadata as well as vocabulary graphs for
consistent API serialization; selecting a prefix must not implicitly enable its
ontology for inference. General account migration, fulltext/binaries, additional
permission actors, large-project transfer and production recovery remain open.
A real source export requires an RDF-star format: ordinary RDF4J N-Triples may
encode quoted subjects as `urn:rdf4j:triple:` URIs, which the converter now refuses.

## Real-project fulltext acceptance

See [Fasnacht YAML/API/browser rehearsal](../../../oldap-api/doc/jena-fasnacht-fulltext.md).
Apply the reviewed project field map after model/data import; a new searchable
property requires extending that map and applying it again. Ordinary words use
AND within a field; quoted phrases use a single text value. Every referenced
source must have explicit current DATA_VIEW. Do not silently inherit permissions
through embedded nodes. Rebuild the Java service with the configuration-read lock
correction before browser acceptance: simultaneous readers previously caused 409
configuration failures mapped to API 400. Index replacement remains exclusive and
queries retain configuration revision validation. Production performance,
analyzer/language parity and the deferred GraphDB countertest remain open.

Fulltext query placement is now optimized with unchanged responses: see
[measured plans and reproduction](../../../oldap-api/doc/jena-fulltext-performance.md).
Local search HTTP medians improve to 56–143 ms for six representative shapes;
this supersedes the earlier multi-second fulltext latency finding, not the
outstanding production load/analyzer acceptance gates.

Language behavior is now measured in a [34-case native matrix](jena-fulltext-language.md).
Hyphen/apostrophe queries are supported. Approved accent/ß folding and canonical
Unicode normalization require rebuilding the index; native, lifecycle and normal
API acceptance now pass.
Do not assume stemming, compound splitting or German transliteration support.

The approved [folding analyzer](jena-fulltext-language.md) now closes accent/ß
and canonical Unicode gaps without stemming. Ship OldapTextAnalyzer.java with the
service and rebuild indexes at managed startup; identical YAML replay is not an
analyzer upgrade. Stored RDF remains authoritative and unchanged. Production
load and the deferred GraphDB comparison remain open.

## Archive search workflow acceptance (2026-11-01)

See [frontend workflow evidence](../../../../OLDAP/FasnachtsPage/docs/archive-search-workflow.md).
Combined filters, relevance, PDF-to-object navigation, public/audit separation
and complete paging on this export pass. Frontend corrections retain public API
signatures. Whole-page readiness is about six seconds locally; repeated metadata
loading and the existing 5000-row cap remain explicit follow-up work. Whole-PDF
matches do not identify exact page offsets. No production deployment or GraphDB
countertest was performed.


### Worker export acceptance and RC2 repair — 2026-11-03

A real home staging export (13 files / 12,721,419 source bytes) stayed QUEUED
because Caddy shadowed worker `/internal/*` endpoints and the API service-account
connection explicitly disabled the access token required by Jena. Block only
`/internal/jena` and `/internal/jena/*`; retain the existing service JWT guards
for export/import/mobile routes. API-owned service connections request internal
access tokens only for Jena; signing keys are not sent to media workers.

Deploy the bounded proxy/client repair workflows in sibling setup. The proxy
repair must recreate Caddy after atomic bind-file replacement, not merely reload
its stale mount. RC2 fingerprint `95c8b339149f` passed both-architecture packaged
transport/recreation acceptance and was deployed to home. The existing export
then reached READY automatically: ZIP 12,724,905 bytes, all 13 sources complete,
CRC/integrity valid, SHA256 matches the API artifact record. Worker claim-to-finish
was approximately 1.84 seconds. Browser owner download remains user acceptance.
Public read/auth/media checks pass. The frozen story digest differs; direct RC1
and RC2 read-only responses on the current dataset are identical (30 stories).
No current frozen-source parity or full import/mobile workflow acceptance claimed.
See sibling setup `docs/jena-service-rc2-home-results.json`. Production is unchanged.


### Import diagnostics and transaction admission — 2026-11-03

Home RC3 (`55372bad3896`) adds safe API import 503 diagnostics: exception/cause
types and bounded code locations correlated with the response request ID; no
exception messages, source lines, locals, payloads or tokens. Public contracts
and library transaction behavior are unchanged. A real post-client-update import
claim failed at BEGIN with `OldapErrorAlreadyExists` (backend HTTP 409), then
polling recovered normally. Concurrent-BEGIN refusal also passes in isolated
real-service tests on both architectures. This proves admission contention occurs,
but cannot reconstruct the original unlogged 16:39 validation-result failure.

The worker stops its heartbeat when validation result publication fails; its
persisted default five-minute lease blocks re-claim until expiry. Retained results
avoid repeated ZIP extraction. Future improvement must distinguish known refused
BEGIN from uncertain writes, and preserve exact event/payload identity if retrying
result publication. Do not shorten leases or blindly retry UPDATE/COMMIT. See
sibling setup `docs/jena-diagnostics-rc3-home-results.json`. The user has confirmed
successful browser ZIP download and a corrected ZIP import.


### Bounded BEGIN admission retry — 2026-11-03

`JenaConnection.transaction_start()` now retries an explicit HTTP 409 from BEGIN
at most four times after the initial attempt (50, 100, 200, 400 ms pauses). Each
refusal closes its journaled ownership before a fresh ID is registered/sent.
The 750 ms bound applies to backoff; configured HTTP timeouts still apply to each
request. Persistent contention propagates the original refusal with no open owner.
Any other failure stops immediately and retains uncertain ownership. UPDATE and
COMMIT are never replayed by this change. GraphDB, public function signatures,
worker events and five-minute worker leases are unchanged.

Offline tests exercise failure after both zero and one prior refusal, exhausted
admission, journal accounting and non-replay. The setup network acceptance holds
one real session, waits for a second Python client's actual refusal, releases the
first, then verifies successful retry with exactly one UPDATE and COMMIT. RC4
packaged acceptance and home deployment are tracked in the setup log.


RC4 `e3903e70a220` is now published and active on home. The synchronized contender
test passed for packaged AMD64/ARM64 locally and against an isolated dataset on
the native home VM, both before and after namespace replacement. Exactly one
UPDATE and COMMIT followed successful admission. The actual home API uses library
`0.7.29+jena.rc4.e3903e70a220`; public checks pass, story responses equal RC3, and
existing import states are unchanged. Stable/latest tags and production are
untouched. Evidence: sibling setup `docs/jena-begin-retry-rc4-home-results.json`.
