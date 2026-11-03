### Update 2026-11-03 22:27
- Decisions: Checkpoint the outstanding library migration on migration/jena before coordinated 1.0 packaging. Preserve public signatures and existing version; no merge, tag, push or deployment.
- Implementation: Reviewed candidate file inventory, backend/query/permission boundaries and explicit Java build sources; AST comparison found no changed existing public argument lists. Corrected PropertyClass module-docstring placement and marked historical semantics status. Retained source/tests/service/conversion tools and evidence, with a merge-readiness record.
- Open: Standalone pytest dev dependency, 1.x consumer constraints, final versioned artifacts and complete home/recovery acceptance. Existing broad GraphDB suites require an explicitly disposable database.
- Risks/Assumptions: 198 focused tests + 14 subtests, 25 targeted rechecks, eight real converter checks, fresh Java service acceptance including 300 commits and crash/fulltext recovery pass. Wheel contents/imports, Poetry and diff checks pass. Additional XSD run passed 47 tests but included 44 GraphDB tests that clear/rewrite test:test on localhost:7200; no production endpoint selected. Library venv lacks pytest, so tests used sibling API environment. RDFLib deprecations remain. This checkpoint is not production release approval.

### Update 2026-11-03 19:33
- Decisions: Accept and deploy RC4 bounded BEGIN-only retry on home. No public signature, GraphDB, worker event, lease or uncertain-write semantics change.
- Implementation: Library retries explicit BEGIN 409 with fresh journaled IDs, at most five attempts and 50/100/200/400 ms backoff. Published isolated API/tools RC4 fingerprint e3903e70a220, stable/latest unchanged; bounded client playbook updated API/identity, retained Jena/Redis/data/policy and timestamped environment backup. Real contender test passes on both local architectures and isolated native home before/after replacement, with exactly one UPDATE and COMMIT. Public home checks pass; 30-story response equals RC3, fulltext/media unchanged, 3 IMPORTED/1 INVALID and no active claims, normal worker polling.
- Open: User may run a ZIP practice test. Persistent contention and other failures still surface normally; worker lease recovery remains a separate policy. The original unlogged validation callback cause cannot be proven retroactively.
- Risks/Assumptions: Explicit BEGIN 409 proves no admission; every other admission failure retains uncertain ownership and is not retried. No UPDATE/COMMIT replay. Tests: 61 library + 3 subtests, 54 API, 29 packaged transport; native acceptance used temporary separate data and cleaned its containers/storage. Two stale resource test doubles gained the existing resolved_properties method; no resource runtime change. Evidence: sibling setup docs/jena-begin-retry-rc4-home-results.json. Production and media image unchanged.

### Update 2026-11-03 19:00
- Decisions: Retry only explicit HTTP 409 refusal of BEGIN, at most five attempts with 50/100/200/400 ms backoff. Keep public signatures and GraphDB unchanged; never replay UPDATE/COMMIT or uncertain admission.
- Implementation: Jena transaction_start closes ownership after each known refusal, clears the rejected ID, and journals a fresh ID before retrying. All other transport failures retain uncertain ownership. Twenty-nine offline transport tests pass, covering exhausted admission, unique IDs, journal balance, timeout/connection/401/403/500/503 after zero/one refusal, nested start, UPDATE conflict and lost commit/abort replies. Added synchronized real-service admission recovery to sibling setup network acceptance.
- Open: Build RC4, complete both-architecture packaged acceptance, then deploy bounded home client update. No current claim of deployed behavior.
- Risks/Assumptions: Backoff totals 750 ms plus HTTP round trips; persistent contention still fails normally. Worker five-minute lease/recovery policy remains unchanged. Server BEGIN 409 contract refuses admission before application writes; each attempt uses a new identifier.

### Update 2026-11-03 18:35
- Decisions: Retain migration knowledge from the import diagnostic investigation; no library behavior changes.
- Implementation: Cutover guide records RC3 private-safe diagnostics, observed BEGIN refusal, confirmed five-minute worker lease wait and safe future retry boundaries. User confirmed corrected ZIP import and browser export download.
- Open: Historical callback exception is not recoverable; admission contention is confirmed on current home but not proven for that earlier request.
- Risks/Assumptions: No automatic replay of uncertain writes or lease-policy change. See sibling setup diagnostic evidence.

### Update 2026-11-03 14:54
- Decisions: Complete the existing stalled home export, without cancellation/recreation; keep worker JWTs and public/library signatures unchanged. Production and stable/latest image tags untouched.
- Implementation: Deployed narrow Caddy Jena-only matcher and API RC2 service-account access tokens. Separate API/tools AMD64/ARM64 images use fingerprint 95c8b339149f; bounded playbook updated identity/API only, preserving Jena storage/Redis/policy. Fixed network acceptance to use the independent identity sidecar and remove both consumers before namespace replacement. Existing worker claimed the original job and reached READY: 13 files, 12,724,905 ZIP bytes, CRC/integrity and SHA256 match; build ~0.37 s, claim-to-worker completion ~1.84 s. Evidence: sibling setup docs/jena-service-rc2-home-results.json.
- Open: User downloads the ready artifact in the browser; delivery itself has not been exercised as the owner. Full import/mobile workflows remain separate acceptance work. Frozen story hash differs; RC1 and RC2 read-only requests against current data return identical 30-story responses, so no exact frozen-source parity is claimed.
- Risks/Assumptions: Original delay was queue blockage, not ZIP compression throughput. Public login/upload-auth/fulltext/media/frontend checks pass; 43 focused API tests and both-architecture packaged transport acceptance pass. New access tokens stay inside API. Caddy recreation is required after atomic bind-file replacement; reload alone sees the old inode.

### Update 2026-11-03 14:42
- Decisions: Repair stalled home ZIP export without replacing/cancelling the user's queued job. Narrow proxy isolation to the Jena namespace; service-authenticated import/export/mobile routes must remain reachable. Keep GraphDB non-token service behavior; API-owned Jena service connections issue an internal transport token using existing API signing access.
- Implementation: Corrected Caddy matcher/template and added home proxy repair playbook; atomically replaced bind-mounted configuration requires Caddy recreation, not in-container reload of its old inode. Live unauthenticated export claims now return 401 instead of proxy 404; Jena callback remains blocked. Corrected four API service-connection constructors and added both-backend regression coverage (43 focused tests pass). Preparing new isolated RC2 API/tools images and a bounded home client-update playbook; no library API/signature or worker credentials changed.
- Open: RC2 build/accept/publication/deployment running; verify existing job reaches READY and ZIP integrity/download afterwards. Extend acceptance to worker-authenticated paths, not only public read/upload probes.
- Risks/Assumptions: Original job remained QUEUED, 13 files / 12,721,419 bytes, no attempt progress. Two independent blockers: broad /internal/* proxy rule and explicit issue_access_token=False incompatible with Jena. Production and normal image tags remain untouched; internal API tokens are never returned to media workers.

### Update 2026-11-03 14:18
- Decisions: User requested enabling archive structure management on home. Activate only Fasnacht structure policy using established ArchiveStructureEditor/ArchiveMediaEditor roles; do not enable the separate publication policy or assign users new roles.
- Implementation: Added reviewed structure-only policy, optional read-only Compose policy mount for API and future direct clients, and home-scoped enable playbook. Validated every referenced role/class/property against the live Jena model before activation, retained original environment, then recreated only API. Runtime capabilities report enabled/manage/create for admin, enabled but no manage/create for anonymous; user's existing structure role confirmed. Evidence: setup docs/jena-archive-policy-results.json.
- Open: User reloads archive management and exercises actual edits/creation in home testing. No test archive records were created and no end-to-end structure mutation is claimed. Production unchanged; direct writer release gates remain.
- Risks/Assumptions: Home had no OLDAP_ARCHIVE_POLICY_FILE, so the disabled message was accurate. Policy preserves existing data-level permission checks; role membership alone does not replace them. API, tools and harvester configuration share the read-only policy; only API runs/recreated. Fifteen focused setup tests and playbook syntax pass. Policy deployment and Jena overlay selection must be preserved on future updates.

### Update 2026-11-03 14:00
- Decisions: Synchronize the active API access-token verification key/issuer/audience to existing home media consumers after cutover rotation; never distribute refresh/admin secrets or introduce new access-token consumers.
- Implementation: Added shared home media-access tasks and a bounded repair playbook. Inventoried five environment files; only mediahelper-access.env contains the access key. Privately backed up and updated its three settings; Compose recreated the helper to load the new environment, other workers remained unchanged. First activation now synchronizes media before reopening and uses Compose recreation instead of docker start. Added valid/missing/invalid-token upload checks to the public acceptance runner.
- Open: User retries the real image upload. Acceptance intentionally omits project/file fields and verifies the exact form-validation response, proving authentication without creating data; it is not an end-to-end conversion/storage test. Production release/recovery gates remain. Any future full provisioning must use coherent signing keys for API, identity verifier and mediahelper.
- Risks/Assumptions: The initial activation rotated API access/refresh keys but omitted the media access verifier, causing HTTP 401 for newly issued valid tokens. Runtime verification settings now match exactly; media-token key and all images/data remain unchanged. Fresh admin-token upload reaches HTTP 400 Missing projectId field, missing/invalid tokens return 401. Full public smoke passes: 30-story digest unchanged, fulltext AND search, signed IIIF/JPEG and frontend availability. Evidence: setup docs/jena-media-access-results.json. No credentials/token bodies are retained in repository evidence.

### Update 2026-11-03 00:41
- Decisions: Accept the separate private identity pool after native home parallel/browser tests; retain access verification semantics and public API signatures. No data import, cache clearing, credential rotation or registry publication.
- Implementation: Home repair completed with oldap-jena-identity healthy on loopback 8001; API/backend/identity namespace recreated together and media resumed. Public smoke rerun passes including exact 30-story baseline, fulltext and signed image. Browser shows archive 665 media/422 objects/15 events and populated stories. Final parallel test: all 48 responses HTTP 200 at concurrency 16 and equivalent complete content. Updated lifecycle, templates, README, master context and evidence. Fourteen focused tests, four playbook syntax checks and both diff checks pass.
- Open: Production gates from the preceding activation remain. API workers can emit full list IRIs or equivalent QNames depending on loaded prefixes; deterministic serialization can be addressed separately. Native/non-container deployments must also avoid sharing a bounded public worker pool with callbacks.
- Risks/Assumptions: Initial strict parallel hashes differed solely for known list IRI/QName spellings; retained those reports and added property-scoped normalization using the frozen export's namespaces, with a regression ensuring changed resources/literal text are still detected. Successful evidence: setup docs/jena-concurrency-semantic-results.json and docs/jena-home-after-identity-results.json. Private callback startup works with network disabled; no admin/database secrets are distributed to it. Existing mobile shutdown delay remains unchanged.

### Update 2026-11-03 00:36
- Decisions: Isolate private identity callbacks from the public API worker pool; increasing public worker counts cannot remove the cyclic capacity dependency. Public API signatures, data and published images remain unchanged.
- Implementation: Added a minimal deployment WSGI entry point reusing the installed identity blueprint and TokenCodec, in a separate loopback-only container on port 8001 with only access-token/callback credentials. Updated Compose, preparation and activation lifecycle; added a coordinated home repair playbook and representative sequential/parallel archive acceptance runner. Added topology assertions; installed-image verifier passes with networking disabled.
- Open: Home repair is running; complete 16-way archive/story/taxonomy acceptance and browser verification, then record final evidence.
- Risks/Assumptions: Original 16-way Agent burst reproduced nine HTTP 503 responses at roughly 2/4 seconds while Jena remained running. Sequential initial cutover checks missed this capacity cycle. Namespace owner and all persistent consumers must be recreated together; no GraphDB rollback or data import is involved.

### Update 2026-11-03 00:30
- Decisions: Activate only home.org; retain GraphDB data/backups and preserve normal DockerHub tags. User-approved DATA_PERMISSIONS correction and inactive orphan memberships are applied. Rotate access/refresh keys; passwords are unchanged.
- Implementation: Completed two-host frozen backup and public Jena activation with pinned images. First private activation rolled back successfully after detecting missing explicit staging Redis configuration in the legacy Compose base; fixed API/tools/harvester settings, retested the exact base privately, then repeated freeze/backup and activated successfully. Removed stopped rehearsal containers/network, retaining all bind data. Added public acceptance runner and scalar-preservation regression; recorded sanitized evidence in setup docs/jena-home-results.json. Final 12 deployment/image/content-verifier tests and both repository diff checks pass.
- Open: Production-specific writer/harvester releases, reviewed mediahelper authorization fix, graceful mobile-worker shutdown, independent off-host backup/restore and coordinated Jena routine updates. Canonical ontology cleanup and other projects' fulltext field inventory remain separate. No production deployment or Git commit/push.
- Risks/Assumptions: Final source SHA matches rehearsal; 65,376 target application quads, 16 users; synthetic write-test user removed. All 30 story responses match GraphDB; fulltext AND search yields 10 equal hits in either word order; real login, signed IIIF/JPEG and frontends pass, local HTTPS status passes. New verifier initially dropped scalar values; corrected and exact baseline hash now matches. Source GraphDB had no fulltext connectors, so no fulltext parity claim. Backup directories dated 20261103 on API/media; earlier 20261102 copies retained. Mobile worker required forced stop after 90s with no queued operation files; all media workers now run. Reopened target writes prevent blind GraphDB rollback.

### Update 2026-11-03 00:01
- Decisions: User selected DATA_PERMISSIONS for the duplicate WriterRecoveryOperator default; four orphan annotations remain inactive. Preserve the original source export. Target API rotates access/refresh keys at cutover so stale claims cannot survive.
- Implementation: Added target-only guarded SPARQL correction and applied it to the candidate. Corrected Redis durability to appendfsync=always/noeviction after the library rejected default configuration. Candidate API create/login/update/delete acceptance passes; synthetic user removed. Added home-only freeze/backup and rollback-protected activation playbooks; documented operator sequence.
- Open: Media backup is running with source API/GraphDB/Redis and media writers stopped; activate only after successful two-host manifest. Final public endpoint/media verification and production-specific release/update gates remain.
- Risks/Assumptions: Final frozen RDF hash equals the initial source export exactly. Source coordination DB 1 empty; two imports IMPORTED, one export DELETED; no application timers found. Jena and GraphDB story responses match (30). Source GraphDB has zero Lucene connectors; Jena has nine configured fields and positive search results, so no fulltext parity claim. Installed mediahelper auth functions differ from reviewed local fixes; media release acceptance remains a production gate.

### Update 2026-11-02 23:45
- Decisions: Add an offline, checksum-bound whole-dataset first import; keep domain/account remediation separate from syntax conversion.
- Implementation: Packaged JenaInitialImport reuses cross-graph RDF verification, refuses existing targets and reserved receipts, and publishes the service marker only after persisted-data comparison. Narrow comparison allowance covers insignificant dateTimeStamp fractional zeros. Real home.org read-only export converted/imported locally and natively on server: 23 graphs, 65377 converted quads, 16 users. Added executable importer acceptance checks.
- Open: Source has four orphan admin membership annotations and one conflicting role default (DATA_VIEW/DATA_PERMISSIONS). User decision pending; full cutover backup, model migrations, worker reconciliation and public activation remain open.
- Risks/Assumptions: Initial snapshot is a live rehearsal, not a consistent cutover backup. Existing GraphDB/API remain active. Full candidate API starts and accepts real admin/anonymous login. 15/16 users and all 6 projects/models match after RDF array-order normalization; one role-map difference awaits remediation.

### Update 2026-11-02 23:25
- Decisions: Package the migration library privately into source-matched API/tools candidate images; leave normal library versions and PyPI untouched.
- Implementation: Sibling setup builds an exact local-version wheel 0.7.29+jena.rc1.c1cb0919375a from an allowlisted source snapshot. Both client wheels pin that version. No library runtime/source/version-file changes; packaging provenance and immutable image digests are retained in setup release evidence.
- Open: Full API startup with real accounts/data, migration and coordinated activation/update; harvester release remains separate. Preserve source snapshots because these checkouts contain uncommitted work.
- Risks/Assumptions: Ten publication/deployment tests, wheel inspection, both-architecture imports/dependency/CLI/UID checks and packaged real-Jena transport acceptance pass. Published API digest also passes on native x86_64 api.home.org. Registry multiarch indexes verified; current normal version/latest digests unchanged. Initial candidates superseded to preserve runtime UID contracts; only final c1cb0919375a candidates published. Existing GraphDB/API unchanged; owned test resources removed. No Git/PyPI publication. Evidence: oldap-setup/docs/jena-images-results.json.

### Update 2026-11-02 22:58
- Decisions: Retain production migration/deployment knowledge in sibling oldap-setup migration/jena and the central cutover guide.
- Implementation: Linked the tested shared container namespace, candidate preparation and explicit migration/activation lifecycle. Updated central cutover status in oldaplib; no API/library runtime code changes.
- Open: Matched application/writer releases, full API and source/account migration, coordination recovery and automated activation/update acceptance.
- Risks/Assumptions: Bounded real identity/transaction/isolation/recreation tests pass on local ARM and remote x86_64 with synthetic data; not full application certification. Remote GraphDB stack unchanged; owned test resources cleaned up. Evidence: ../oldap-setup/docs/jena-network-results.json.

### Update 2026-11-02 22:46
- Decisions: Proceed with both user-resized VMs at 16 GB assigned for initial testing.
- Implementation: Read-only SSH verification: both guests report 15 GiB total, zero swap use; API/media have 12/14 GiB available. All inventoried containers running, API healthy. Updated cutover guide and master context.
- Open: Private Docker/loopback topology, JDK 25, consistent source backup and deployment acceptance; Proxmox ballooning settings were not inspected.
- Risks/Assumptions: Idle post-restart observation, not load sizing or full application acceptance. No remote changes or runtime code changes; documentation-only update.

### Update 2026-11-02 22:24
- Decisions: Inventory home.org read-only over SSH as rosenth before deployment; preserve the synchronized GraphDB baseline.
- Implementation: Recorded both Ubuntu/Docker VMs, image/runtime versions, persistent mounts, live disk usage and guest memory in the cutover guide; updated master context. No runtime code changes.
- Open: Proxmox allocation/ballooning (both guests expose 1.60 GiB), compatible Docker API/loopback Jena topology, Linux JDK 25, consistent source backup and remote acceptance.
- Risks/Assumptions: API already uses about 1 GiB swap; 8 GiB heap cannot fit current visible RAM. Data volumes have space; media root is 82% used. User-reported production synchronization is not independently verified. No remote mutations, secret reads, deployments or service restarts; no tests needed for this documentation-only inventory.

### Update 2026-11-02 12:18
- Decisions: First remote test target is home.org; no remote access in this step. Use an explicitly quiesced offline bundle, preserving admin RDF and private receipts while rebuilding derived text indexes. Restore remains isolated until operator reconciliation.
- Implementation: Added packaged backup.py with five required component directories, native TDB lock exclusion, private copy/hash/fsync/manifest verification, new-target restore and generation handoff. Extended owned service fixture for backup checks; recorded instructions and sanitized evidence in oldaplib/docs/migration/jena-backup-results.json.
- Open: Actual source/media/config inventory, home.org topology and restore acceptance, real worker fencing/coordinator reconciliation, cache isolation, matching API/tools/media releases and production cutover. Handoff metadata alone is not runtime enforcement.
- Risks/Assumptions: 40 owned service/recovery checks and seven offline tests pass. Real bcrypt user/admin-role grants, complete application/admin RDF, receipts/reservations, folded text, media/config hashes and Redis AOF recovered; post-backup commit intentionally absent. Redis pending record is a synthetic marker, not an executable production command. First harness run corrected userdata accessor; successful reruns retained. No production data/service change; owned processes stopped. Existing source generation must never be reused blindly after restore.

### Update 2026-11-02 12:01
- Decisions: Retain the private /tx protocol and single owner-thread writer; reserve each transaction UUID durably before application BEGIN. Only the separate atomic commit receipt proves success; no automatic replay or receipt expiry.
- Implementation: Shared servlet separates production from probe fault/timing hooks; built JenaService adds private strict config, fixed loopback endpoint, explicit initialization/reopen, health and signal shutdown. Pinned offline JDK25/Fuseki6.2.0 build, manifest/hashes, launcher and uninstalled systemd/launchd templates. Query execution bounded to 60 s; fulltext unavailability is visible across threads. Context/operator docs updated.
- Open: Full backup/restore including reservations/receipts, actual account/data migration, supervisor/worker deployment acceptance and sustained mixed-write load. Receipts/admissions grow on disk; no pruning policy. Service initialization is empty and is not a production switch.
- Risks/Assumptions: 22 packaged checks incl. 300 commits and fulltext/crash restart; 20 identity, 20 session, 11 callback, 50 managed-text checks and 18 offline tests pass. Two identical builds verified. Initial reservation-conflict cleanup corrected and suites rerun; library-only environment lacked pytest/API fixture dependencies, so tests used sibling API environment. Evidence: oldaplib/docs/migration/jena-service-results.json. Existing GraphDB/API/Redis untouched; owned processes stopped. No public signatures changed.

### Update 2026-11-02 11:38
- Decisions: Jena/Fuseki is the production target; prioritize deployment and recovery readiness over marginal benchmark gains.
- Implementation: Reviewed migration/service/deployment sources and retained acceptance evidence; added ordered launch gates, acceptance criteria and next service slice to the shared cutover index; linked stable context in all three migration repositories.
- Open: Persistent service/identifier lifecycle, full restore rehearsal, actual accounts and source migration, versioned artifacts including mediahelper, production worker/write/soak acceptance and controlled cutover.
- Risks/Assumptions: Documentation/source review only; no tests rerun, services changed or production migration performed. Java probe stops admitting new transactions after 256 identifiers, uses stdin lifecycle and retains test hooks. Historical evidence is not current release acceptance; initial project scope remains to be confirmed.

### Update 2026-11-02 01:34
- Decisions: Repeat the unchanged six-case read-only GraphDB/Jena workload after Python/model/payload optimizations, with 8 GiB Jena and 1/4/8 reader waves. Repeat once more because GraphDB run 1 had slow tails; retain both runs.
- Implementation: Measurement/documentation only, existing harness unchanged. 624 timed requests pass; all six cross-backend cases agree and complete per-backend responses stay stable. Evidence: ../oldap-api/doc/graphdb-jena-python-comparison.md.
- Open: Counts and dated searches still favor GraphDB; larger paired data, authenticated roles, equal-deployment and write/soak studies. No engine-only or production-capacity conclusion.
- Risks/Assumptions: Confirming GraphDB/Jena medians 57/73, 117/139, 203/250 ms at 1/4/8 readers; Jena ~19–28% slower versus prior ~2–2.5×. Jena repeats stable; GraphDB run-1 p95 outliers did not recur. Source unchanged; owned services stopped, original GraphDB/deployment untouched. No runtime changes; diff checks pass.

### Update 2026-11-02 01:27
- Decisions: Keep JSON-LD/decoder: exploratory format switching was not faster. Reduce redundant graph data instead; materialize Jena summary role/permission nodes in a bounded independent subquery before property/type joins. Preserve GraphDB expression and all outer authorization checks.
- Implementation: Commented summary builder change; native regression checks four independent grant nodes for two multi-role resources. Evidence: ../oldap-api/doc/jena-summary-payload.md; no public signatures, stored RDF or transport changes.
- Open: Concurrent performance, optional single-resource payload optimization and deferred GraphDB countercheck. The former date UNION rewrite remains rejected; no general decoder/format machinery introduced.
- Risks/Assumptions: Two ABBA runs preserve 120 complete API responses; dated pages 306→231 / 320→241 ms (~24–25%). Graph 4799→1799 triples; response 575509→195509 bytes. Larger copied 12000-extra-record fixture remains faster (~48→39 ms bounded native summary). 209 native and 29 focused checks pass; missing test import corrected and native suite rerun. Source unchanged; owned services stopped; original GraphDB/deployment untouched. Compilation/diff checks pass.

### Update 2026-11-02 01:18
- Decisions: Fresh post-validation profile identifies repeated superclass/model reconstruction; per-result class/property resolution is too small to optimize. Reuse independent copies of Redis-loaded ResourceClass snapshots only during synchronous factory/model construction, following the existing project-read scope.
- Implementation: Context-local connection/project/class scope, copy isolation/current connection, exception cleanup and forced-reload/transaction bypass; three behavioral tests. Test-only previous-reader ABBA control and sanitized evidence: ../oldap-api/doc/jena-model-read-reuse.md.
- Open: JSON-LD transport/decoding and native dispatch remain larger costs; concurrent performance and later GraphDB countercheck. No public signatures, SPARQL or API runtime changes; original GraphDB/deployments untouched.
- Risks/Assumptions: Two ABBA runs preserve 120 full responses; dated page medians 322→281 and 300→271 ms (~10–13%), other cases broadly unchanged. 42 profiling requests, 208 native checks, 32 library tests and six API tests pass. Scope copies mutable models, never authorization/resource results; only successful Redis hits retained. Source unchanged; owned services stopped. No production-capacity claim.

### Update 2026-11-02 01:08
- Decisions: Trust database RDF after write-time validation; use existing validate=False/fromRdf on reads, preserving new-input/token validation and authorization. Retain bounded compiled datatype schemas, never values or access results. Reject both count EXISTS and date UNION query experiments; original objectfactory fully restored.
- Implementation: Explicit trusted CONSTRUCT decoding, gMonthDay honors validate, date expansion preserves typed RDF class names; finite XMLSchema reuse and focused tests. Same-target profiler controls and sanitized evidence: ../oldap-api/doc/jena-validation-performance.md.
- Open: Concurrent/load measurement of retained changes and later GraphDB countercheck; comprehensive repository-wide validation-boundary audit. Legacy datatype integration requires missing GraphDB oldap-test fixture (44 setup errors).
- Risks/Assumptions: 208 native PASS checks (including growth/revocation), 41 library tests, six API tests and 60 equal HTTP responses pass. Serial count 82→60 ms; date page 367→278 ms; timings isolate schema reuse, not read-path changes. EXISTS regresses at 12000 records; UNION regresses date HTTP. Source unchanged; no public signature, original GraphDB or deployment change.

### Update 2026-11-02 00:43
- Decisions: Repeat the unchanged six-case GraphDB/Jena comparison after dating precheck, using 8 GiB Jena and fresh measurements of both backends. No runtime changes in this step.
- Implementation: Retained 312 successful measured requests with six-case equivalence and exact per-backend stability. GraphDB/Jena medians at 1/4/8 readers: 57/118, 132/270, 199/488 ms. See ../oldap-api/doc/graphdb-jena-precheck-comparison.md.
- Open: Actual dated hydration/count-query costs; larger/role/write/soak and equal-deployment studies. Jena medians are 14–22% below the previous 8 GiB run, but GraphDB also varied; backend ratio does not improve uniformly.
- Risks/Assumptions: Same small real-data source; two serial samples/case, empirical p95. Unequal deployments, no production-capacity claim. Source hash unchanged; owned services stopped; no deployed changes. Diff checks pass.

### Update 2026-11-02 00:39
- Decisions: Use a conservative live SHACL eligibility ASK before constructing the dating factory. Match requested direct/inverse fields across project/shared/base shapes regardless of owning class; preserve all positive-case hydration and permission checks.
- Implementation: API helper/early return, focused model/batch/permission tests, same-target ABBA profiler mode and retained evidence: ../oldap-api/doc/jena-dating-precheck.md. Library runtime unchanged; migration index updated.
- Open: Actual date model reconstruction/hydration and dated queries remain. Serial metadata median 157→119 ms (~24%), text 162→118 ms (~27%); dates ~361→357 ms, not an established improvement and now one extra ASK. No concurrent capacity claim.
- Risks/Assumptions: 60 full-response-equal API requests, 23 native fixture checks, ten focused tests and two read-only GraphDB ASK compatibility checks pass. Future/removed/inverse declarations verified on live owned model. Source unchanged; owned services stopped; no public signature or deployment change. Compilation/diff checks pass.

### Update 2026-11-02 00:33
- Decisions: Decompose the same six searches without changing application behavior. Measure private Java token verification/dispatch, backend HTTP, API processing and nested hydration separately; cProfile runs are excluded from timing medians.
- Implementation: Shared benchmark case definitions, owned sequential profiler and opt-in timing headers on all successful private probe routes. 42 full-response-stable requests, 23 fixture checks; source hash unchanged, owned services stopped. Evidence: ../oldap-api/doc/jena-backend-profile.md.
- Open: First remove model/factory/list preparation for searches without Dating-valued requested fields (~54–56 ms inclusive). Preserve inherited/future field support. Then model hydration and dated SELECT/CONSTRUCT profiling; no optimization applied yet.
- Risks/Assumptions: Five timing samples/case, 8 GiB local fixture. API-other includes Redis/instrumentation; dispatch includes parsing/serialization; nested spans cannot be added. Token verification ~6 ms/call, transport residual ~2–8 ms/request. GraphDB internals not profiled. Compilation/native fixture/diff checks pass; no public signature/security behavior change.

### Update 2026-11-02 00:12
- Decisions: Establish a bounded read-only GraphDB/current-Jena real-data baseline before further optimization. Compare all projected values and page order; exclude engine-specific relevance scores only across title-sorted backends, never within backend stability checks.
- Implementation: New owned comparison runner, six public ArchiveObject cases, warm alternating 1/4/8-reader waves, source export fingerprints and sanitized results. 312 timed HTTP requests pass; all six cases agree. See doc/graphdb-jena-performance.md (API repository).
- Open: Equal deployment/heap comparison, authenticated roles, media/linked text, larger paired datasets, soak/writes; profile measured API/transport/query costs next. GraphDB/Jena mixed medians: 61/164, 128/315, 205/579 ms.
- Risks/Assumptions: Existing GraphDB/API versus disposable 512 MiB Jena/threaded API; only two serial samples/case, empirical p95, no engine-only or production-capacity claim. Source byte-stable; owned services stopped. No application runtime/signature/deployment change.

### Update 2026-11-02 00:03
- Decisions: Rehearse optimized queries at 1/4/8 simultaneous requests with 100-row pages, readable dates and complete fulltext candidates. Preserve the old load report as historical evidence, not a controlled A/B comparison.
- Implementation: Test-only harness updates: explicit date grants/independent serialized-year validation, 100-row workload, fulltext total/tail assertions and help handling. Retained aggregate evidence in ../oldap-api/doc/jena-search-load-optimized.md; no application runtime changes.
- Open: Production CPU/memory/multi-process load, soak/concurrent writers, frontend grouped paging and GraphDB comparison. Medians 1.25/1.88/2.99 s; eight-request maximum 5.33 s. No production-capacity claim.
- Risks/Assumptions: 211 checks/209 measured HTTP requests pass, including all 130 reader-wave responses and post-wave revocation; 30 fulltext/23 API fixture checks pass. Local 512 MiB Java, two identities, unchanged timeouts. Source hash unchanged; owned services stopped. No public signature, shared-service or deployment change.

### Update 2026-11-01 01:31
- Decisions: Resolve schema relationships before instance joins uniformly; preserve every inverse/subproperty rule, scope and permission check. No schema cache or field-specific query branches.
- Implementation: Reordered modeled-inverse definitions, legacy inverse joins and subproperty branches in the shared Jena property pattern. Extended owned paging probe with trusted pre-edit helper comparison, ABBA order, full-response equality and private query plans. See ../oldap-api/doc/jena-search-candidates.md.
- Open: Production memory/concurrency, frontend grouped pagination and deferred GraphDB comparison. Local public metadata/date/text HTTP medians improve 3.31→0.53 / 5.59→1.27 / 3.34→0.77 s at the same 100 rows; production capacity is not established.
- Risks/Assumptions: 198 assertions/64 HTTP requests, 30 fulltext/23 API fixture checks, 208 native/growth and 24 focused offline tests pass. Two samples per plan/shape on owned 512 MiB Java. Shared helper also serves reads/summaries; no public signature or GraphDB query change. Source unchanged; owned services stopped.

### Update 2026-11-01 01:20
- Decisions: Keep this step in API/oldaplib; retain 100 as the existing default, with larger explicit limits supported. Fix correctness before tuning broad queries further.
- Implementation: Counts omit sort-value joins. Jena text requests explicitly cover the Lucene document domain: omitted/nonpositive limits silently capped candidates at 10000 before ACL checks. Added 12000-resource page-size/deep-page/count/revocation rehearsal; shared fixture seeding. See ../oldap-api/doc/jena-search-pagination.md.
- Open: Candidate/property/date joins before LIMIT dominate; frontend grouping/pagination, production memory/concurrency and GraphDB countertest remain separate. 214 checks/76 HTTP requests, 30 fulltext/23 API fixture checks, 189 native and 83 offline checks pass. Date pages public 8.83→5.25 s, audit 14.29→7.20 s at LIMIT 100 versus 5000; ordinary metadata/text latency changes little.
- Risks/Assumptions: Legacy control counts only 5000/7500 versus corrected 6000/9000. Full-index text candidates/collector remain memory-sensitive; no streaming claim. Two sequential timing samples per shape on local 512 MiB Java. No signature, ontology, index rebuild or frontend change. Source unchanged; owned services stopped.

### Update 2026-11-01 01:00
- Decisions: Test bounded growth and concurrent readers before further optimization; retain functional success and latency limits separately. Do not raise test-server limits or introduce a cache.
- Implementation: Owned API load harness with 1000/4000/12000 synthetic records, independent expected visibility/order, complete traversal, 5000 window and 1/4/8 concurrent requests. Evidence: ../oldap-api/doc/jena-search-load.md. Pilot setup exhausted the 256 completed-transaction budget; fixed fixture insertion to one transaction per stage.
- Open: All 207 load checks and 130 concurrent requests pass; 6000 public/9000 audit IDs traverse completely and revocation is immediate. Median broad-query latency 4.32/9.01/18.03 s at 1/4/8 requests. Frontend paging/completeness and broad date/property query profiling are next; production/soak/writes/GraphDB remain open.
- Risks/Assumptions: Local 512 MiB Java fixture and development API, two authorization profiles, broad synthetic matches. Pre-growth 30 fulltext/23 API checks pass. No runtime/public contract changes. Source hash unchanged; owned services stopped.

### Update 2026-11-01 00:42
- Decisions: Retain end-to-end browser acceptance after metadata and dating hydration changes.
- Implementation: Linked unchanged-frontend evidence in the cutover index; no runtime changes.
- Open: Per-request critical-path tracing, growth/concurrency, 5000-row cap and production/GraphDB gates.
- Risks/Assumptions: Two-word searches 2.73–3.31 s; combined date/text 2.65–2.91 s on owned export. Correct counts/order/visibility and 30 fulltext/23 API checks. Metadata-only, narrow viewport; source unchanged and owned services stopped.

### Update 2026-11-01 00:33
- Decisions: Reduce repeated namespace resolution inside one CONSTRUCT graph, without changing queries, permissions or batch limits. Keep fresh QName instances and discard the lookup after each graph.
- Implementation: Local known/unknown URI memoization plus processor documentation; new context/mutability regressions. Extended metadata profiler with a trusted pre-edit processor comparison and separate decoding timings. Evidence: ../oldap-api/doc/jena-dating-hydration.md.
- Open: Remaining transport/JSON-LD and model/date conversion costs; production/browser load and deferred GraphDB comparison. 188 native, 30 fulltext API, 23 export and 49 offline checks pass; all 24 comparative responses equal.
- Risks/Assumptions: Two local samples per shape; hydration ~1.00→0.76 s, whole object request ~1.60→1.36 s. Common processor affects both backends; no public contract change. Source hash unchanged; owned services stopped.

### Update 2026-11-01 00:27
- Decisions: Use whole-triple grant extraction for broad Jena searches; retain direct lookup for text/relationship candidates. Reject grouping-only plan and the growth regression from applying extraction to relationship searches.
- Implementation: Local ACL branch with shared relationship-candidate selection; six date boundary/operator checks and adversarial grant validation. Added owned six-case profiler, response equality and retained evidence in ../oldap-api/doc/jena-metadata-performance.md.
- Open: Broad object-list date hydration remains ~1 s; production load, browser timing and deferred GraphDB comparison remain open. 207 native/growth, 30 fulltext API, 23 export and 40 offline checks pass; 24 comparative responses agree.
- Risks/Assumptions: Local two-sample timing, uncontrolled host load; no production capacity claim. Public signatures, GraphDB path and source export unchanged. Owned services stopped; no deployment.

### Update 2026-11-01 00:07
- Decisions: Retain frontend end-to-end archive acceptance in the central cutover knowledge index.
- Implementation: Linked combined-filter, relevance, PDF/permissions and pagination evidence; no library runtime changes.
- Open: Browser metadata performance, 5000-row growth limit, PDF exact-page offsets and production/GraphDB gates.
- Risks/Assumptions: Acceptance uses the owned real-export stack; internal PDF query uses a synthetic fixture marker. Public contracts unchanged.

### Update 2026-10-31 23:55
- Decisions: User approved accent/umlaut/ß tolerance while keeping word forms distinct. Normalize canonical Unicode on both index/query paths; no stemming, compound splitting or ue transliteration.
- Implementation: Shared Lucene analyzer uses lowercase, NFC and ASCII folding for tokens and wildcard normalization. Python validates NFC input. Extended native language matrix and grammar regression.
- Open: 181 native, 50 managed lifecycle, 30 fulltext API, 23 real-export and 41 offline checks pass. Production load and deferred GraphDB comparison remain open.
- Risks/Assumptions: Existing managed indexes must rebuild on service startup; unchanged YAML alone does not trigger a rebuild. Stored RDF and public API signatures unchanged. Source SHA-256 unchanged; owned services stopped. Stored decomposed text survives indexing and restart unchanged; no deployment or shared-service changes.

### Update 2026-10-31 23:49
- Decisions: Characterize language behavior before choosing accent folding/stemming. Accept ordinary hyphenated/apostrophe words while preserving explicit AND semantics and rejecting Lucene operators.
- Implementation: Added disposable language matrix to native acceptance; extended query grammar and offline punctuation tests. Baseline records 27 cases including case, inflection, accents, compounds, phrases, Unicode representation and private text.
- Open: 175 native integration checks and 40 offline tests pass; user preference for accent/ß folding is pending. Canonically decomposed text and German word forms remain explicit findings.
- Risks/Assumptions: No index/analyzer or stored RDF change; current StandardAnalyzer semantics remain. Tests use synthetic disposable text, not a production corpus; fixture cleanup and owned process shutdown completed.

### Update 2026-10-31 23:43
- Decisions: Evaluate Jena text candidates before root ACL/property/list joins, after independent class selection. Preserve all permissions, scores, ordering and paging; use the simple reorder rather than an extra grouping layer.
- Implementation: Updated shared result/count query order with comments; added owned six-shape, three-plan HTTP profiler and retained timings. All 54 comparative responses are equal; per-shape medians improve from 1671–3303 ms to 56–143 ms. Updated native multiword expectations to the agreed AND semantics.
- Open: Production load and analyzer/language behavior; GraphDB countertest remains deferred. Browser timing also includes metadata requests/rendering.
- Risks/Assumptions: 169 native, 26 fulltext, 23 export and 27 offline checks pass. Final normal-adapter run: median 76 ms across 22 timed searches, maximum 493 ms. Browser confirms the same 20 matches. Source SHA-256 unchanged; owned services stopped. Public contracts and GraphDB query placement unchanged.

### Update 2026-10-31 23:28
- Decisions: Ordinary multiword fulltext uses AND within each configured field; quoted phrases remain single-value matches. Require DATA_VIEW for every referenced text source; preserve public signatures.
- Implementation: Added separate indexed word joins and asserted-role/reifier guards to the Jena fulltext adapter. FULLTEXT_STATE now reads owner-thread configuration without the exclusive rebuild lock; index apply and revision checks retain existing protection.
- Open: 26 fulltext and 23 real-export checks, 46 index lifecycle checks, and 61 offline tests pass. Browser confirms 20 matches (14 media, five objects, one event) with both word orders. Production performance/analyzer acceptance and GraphDB comparison remain open.
- Risks/Assumptions: API/lib/tools offline checks: 27/13/21 passed. Internal PDF text was absent in the export and was tested with a synthetic marker only in the disposable target. Source SHA-256 unchanged; owned API/Jena/Redis and Vite stopped. No live services or public signatures changed.

### Update 2026-10-31 22:59
- Decisions: Match existing SIPI minimum DATA_RESTRICTED=1; require valid numeric permission and asset binding. Only absent credentials may use public lookup; keep public API signatures unchanged.
- Implementation: Updated central cutover index: mediahelper source defect fixed and tested; rebuilt release/deployment still required. No library runtime changes. Full mediahelper suite: 374 passed, 20 skipped, four subtests; owned HTTP: 23 API, ten image and nine grouped asset checks pass. Black/Poetry/diff pass (existing Poetry deprecations).
- Open: Rebuild/version and explicitly deploy mediahelper to activate; no live service changed. Automatic token expiry renewal and uploads remain separate migration gates.
- Risks/Assumptions: Existing capabilities keep their bounded lifetime. Formerly tolerated malformed capabilities now return 403; callers must omit credentials for public lookup or obtain valid tokens. Source hashes unchanged; owned services stopped.

### Update 2026-10-31 22:49
- Decisions: Rehearse PDF/original delivery through unchanged installed Caddy/mediahelper using owned copies and keys; report policy differences separately from transport success.
- Implementation: Updated cutover index with PDF/original evidence and explicit mediahelper authorization blockers; no library runtime changes. Frontend local non-IIIF capability omission fixed; authorized PDF page navigation verified. 23 API, ten image and two offline checks pass; source hashes unchanged; owned services stopped.
- Open: Mediahelper accepts correctly signed permval=0 and falls back to public lookup for invalid supplied tokens. Enforce agreed permission threshold and fail-closed handling before cutover; automatic expiry renewal/uploads remain untested.
- Risks/Assumptions: No API signatures or live services changed. Existing frontend Map lint error reproduced before/after; production build passes. macOS Docker Desktop and installed image tags required.

### Update 2026-10-31 22:42
- Decisions: Validate signed image delivery using one copied real derivative and an owned loopback-only SIPI container; preserve public contracts.
- Implementation: Updated the migration cutover index with signed-image/browser evidence and remaining delivery gates; no library runtime changes. 23 API, ten media and two offline checks pass; browser image/zoom/reset verified; source hash unchanged and owned services stopped.
- Open: PDF/original downloads/uploads, anonymous fallback, automatic expiry renewal, production cache/load and remaining browser workflows.
- Risks/Assumptions: Requires installed SIPI 0.1.3 and the known Fasnacht derivative; issued capabilities remain valid until expiry. Private source/output stay outside Git.

### Update 2026-10-31 00:50
- Decisions: Verify existing FasnachtsPage against an owned real-export Jena/Redis target; retain public versus audit identity separation and leave source/live systems untouched.
- Implementation: Added bounded --browser-preview acceptance support, public fixture role, source Chama namespace registration and one private synthetic child. Browser verified overview counts, 48→96 expansion, title sorting, parent/child navigation, anonymous denial, audit access and logout isolation. No frontend/application runtime change.
- Open: Media binaries/capability integration, fulltext activation, direct archive-unit assignment UI fixture, real accounts and production acceptance. Denied detail wording is raw HTTP 404.
- Risks/Assumptions: Missing source-role namespace initially caused fresh audit-token rejection; disposable admin namespace provisioning fixes it without changing token format. Source has 20 readable units but zero direct archiveUnit assignments. Screenshots/evidence retained; owned processes are stopped after testing. No commit, push or production mutation.

### Update 2026-10-31 00:36
- Decisions: Check warm-cache reads across acknowledged permission mutations with four independent HTTP clients. Allow either committed snapshot only for overlapping requests; require fresh authorization for every post-acknowledgment request.
- Implementation: Extended owned --cache-only acceptance with barrier-started search/count/detail phases, distinct per-worker sessions, object/user-role revocation and restoration, and aggregate overlap evidence. No runtime or public API changes.
- Open: Production load capacity, multi-process/browser acceptance and real-user migration parity remain open. Existing stateless access-token deactivation policy is unchanged.
- Risks/Assumptions: All 26 focused HTTP checks pass, including 168 concurrent-phase requests. Mutation windows overlap 16 object-grant and 13 role-change requests; all 48 post-revocation requests deny visibility. This proves client-request overlap, not database internal parallel execution. Owned services stopped; no shared Redis access, commit or push. Syntax and whitespace checks pass.

### Update 2026-10-31 00:33
- Decisions: Accept warm-cache relationship search/detail authorization with actual isolated Redis; preserve the documented stateless access-token policy instead of introducing immediate account revocation silently.
- Implementation: API runner adds --cache-only using existing socket-only owned Redis (cache DB 0, coordination DB 1), with no mocked cache methods. New checks cover identity isolation, values, object grants, orphan annotations, existing-token role removal/restoration, login/refresh deactivation and documented access-token lifetime. No application runtime/signature changes.
- Open: Production cache/browser/concurrency and representative-user migration acceptance remain open; immediate account-wide access-token revocation remains outside the current authentication contract.
- Risks/Assumptions: 17 focused HTTP checks and 16 offline tests pass. Warm-cache phase records 45 Redis hits, 19 final cache keys. Existing access tokens remain valid until expiry (default 15 minutes) after account deactivation; login/refresh are refused. Initial fixture restored independent owner rights and corrected token-policy expectations. All services/data were owned and stopped; no shared Redis access, commit or push.

### Update 2026-10-31 00:28
- Decisions: Validate larger relationship result sets before further optimization. Keep independent class-set selection before relationship candidates, then preserve all original ACL/filter checks; no public signature changes.
- Implementation: Corrected query order after a 1,000-child count exceeded the 10-second timeout. Added opt-in --relationship-growth fixture with chunked rollback-only updates, 120-second test transaction lease (request timeout unchanged), complete tied-name paging, subproperties, orphan/restricted grants, AND order, revocation and rollback checks. Recorded aggregate timings and documentation.
- Open: Production concurrency, real identities and cache/browser acceptance remain open.
- Risks/Assumptions: All 185 native checks, 27 offline tests and 24 real-export API checks pass. Real Fasnacht HTTP medians remain 452 ms project-wide / 946 ms class/name/sorted; all five parent comparisons match. Synthetic median count 339 ms, first page 452 ms, ten-page traversal 477 ms/page; library transport, not HTTP API. Initial fixture request-size and total transaction-lease limits were corrected without changing production limits. No live data mutation, commit or push.

### Update 2026-10-31 00:21
- Decisions: Optimize mandatory root EQ-IRI/QName searches by selecting distinct relationship candidates before class/ACL joins; retain original filters, property semantics and permission checks. Skip candidate selection for expressions containing OR. No public signature or GraphDB behavior change.
- Implementation: Added one documented local query-builder function and ten native regression checks for permissions, subproperties, duplicate paths, Boolean filters, paging/counts, graph scope, revocation and rollback. Retained diagnostic profiling helpers/native benchmark, aggregate evidence and performance guide from the analysis. Updated cutover context.
- Open: Production load, cache/browser and real-user migration acceptance remain separate.
- Risks/Assumptions: First eligible relation is used without selectivity statistics. No permission cache or stored reverse edges. 166 native checks, 27 offline tests and 24 focused API checks pass. Real-export HTTP medians: project-wide 7355→524 ms, frontend shape 3054→924 ms; all five parent comparisons pass. Measurements use isolated owned data only. No live changes, commit or push.

### Update 2026-10-30 23:58
- Decisions: Use a fresh read-only local TriG-star export after archived gzip input was correctly refused for encoded RDF4J triple IRIs. Retain any original account header privately; never silently drop or activate accounts.
- Implementation: Added read-only exporter, private preparation/header retention, native instance extraction and real-data/API comparison in the owned fresh-model runner. Retained aggregate evidence and cutover guidance. No application API/signature change.
- Validation: Real local Fasnacht TriG-star export rehearsed on a fresh owned Jena target: 38,674 instance triples, two hasPart reversals, 11 canonical pairs, all 38,663 other triples unchanged. All 23 focused checks pass, including five parent API comparisons and a single-resource read. Source export byte-stable. Native conversion preserves 35,829 ordinary source quads and converts 2,919 annotations, with zero orphaned annotations or added memberships and successful structural round-trip. One subject link preserved; no direct archive assignments existed or were manufactured. Python compilation/whitespace pass; owned processes ended. Initial Java Dataset cleanup compile issue corrected before successful run.
- Open: Production snapshot rehearsal, actual-account/role provisioning and user-specific permission parity, binary/fulltext/cache/browser acceptance; reverse-search trace takes several seconds per request and needs performance work.
- Risks/Assumptions: Current local data, not production. Owned audit actor receives nine source role identities only in disposable admin graph; instance permissions unchanged. Old source model/lists retained privately; target uses revised YAML. No live mutation, cache flush, deployment, commit or push.

### Update 2026-10-30 23:46
- Decisions: Prove complete model provisioning on a fresh owned target before in-place cleanup or real-data cutover.
- Implementation: Added focused --fasnacht-only API acceptance and complete YAML/taxonomy CLI import, no-write replay, transactional part conversion and HTTP permission-filtered reverse lookup. Retained hashes, counts, evidence and cross-repository context. No runtime application change required.
- Validation: The actual migration YAML imports through tools/HTTP with 16 classes, 88 property declarations, 10 taxonomies and 3 external registrations. 224 operations, then zero-write replay. Canonical isPartOf reverse lookup excludes an ungranted child after transactional conversion. All 13 focused checks pass. Owned processes completed; Python compilation and whitespace checked.
- Open: Actual Fasnacht export comparison, in-place shape/restriction cleanup, fulltext activation and browser/cache acceptance. Chama relations remain separate.
- Risks/Assumptions: Fresh target and synthetic instances, not production acceptance. GraphDB connectors skipped. External registration does not imply graph content loading. Object-cache I/O suppressed; no live source/data/Redis changes, deployment, commit or push.

### Update 2026-10-30 23:37
- Decisions: Use only dcterms:isPartOf in Fasnacht models, storage and queries; replace hasPart consumers with reverse lookup rather than an inverse read field.
- Implementation: Added target-scoped SPARQL preflight/data conversion and native acceptance; revised semantics cases I1/I2, cutover guide and migration sequence.
- Validation: 156 native model/search checks pass (4 new): duplicate edges, conflicting Place parents, replay and graph isolation.
- Open: Fresh target model provisioning or explicit in-place field/restriction cleanup, migrated-data acceptance and authenticated browser smoke. YAML omission does not delete existing fields; do not bypass in-use guards.
- Risks/Assumptions: Data conversion is prepared and tested only on owned fixtures; run zero-row preflight and backup before application with writers stopped. Existing source/live data and services unchanged. hasPart consumers require migration; API signatures unchanged. No commit, push or deployment.

### Update 2026-10-30 23:28
- Decisions: Verify explicit inverse metadata removal through the actual tools CLI and normal HTTP model-update endpoint, without substituting SPARQL schema cleanup.
- Implementation: Updated semantics profile, cutover index and master context with the completed owned HTTP model-update acceptance and remaining full-project/reverse-axiom gates; corrected stale archive design-gate wording.
- Validation: 162 integration checks pass, including eight new archive checks. Legacy false assignment reproduced; preview, backup, metadata/RDF removal, stable direct response, unchanged instance triples and zero-write replay verified. Backup retains prior metadata and RDF. Syntax/whitespace checks pass; owned processes completed.
- Open: Full Fasnacht target import/real-data comparison, cache acceptance, reverse/external axiom inventory and general modeled inverse fields.
- Risks/Assumptions: Minimal demo namespace/class fixture uses actual Fasnacht target/cardinality/null declaration. Only forward axiom owned by the edited property is covered; object-cache I/O is suppressed. No live data/service changes, public signature changes, commit or push.

### Update 2026-10-30 23:20
- Decisions: Prove direct archive assignment independently of subject references in an owned Jena target; preserve generic subject imports and public contracts.
- Implementation: Added transaction-scoped native acceptance using the actual Fasnacht YAML declaration/predicate, synthetic test resources and real read/summary/search builders. Reproduces old inference, explicitly removes both legacy axiom orientations, verifies direct links, independent subjects, filters/counts, assignment deletion and abort. Linked retained results in profile, cutover index and master context.
- Validation: 152 native model/search checks (11 new) and 57 offline tests pass. Owned probe completed; no shared Redis or live service/data changes.
- Open: Complete HTTP model-update rehearsal on a representative Fasnacht target, current data audit and broader inverse-field acceptance. Fixture cleanup is explicit SPARQL, not the model-update endpoint.
- Risks/Assumptions: Synthetic model applicability uses test:Cat with the real archiveUnit field; no claim of full Fasnacht hydration/import parity. No public API changes, deployment, commit or push.

### Update 2026-10-30 23:17
- Decisions: Store fasnacht:archiveUnit directly as archival assignment; retain schema:about for subject matter and remove their legacy inverse axiom, as agreed with the user.
- Implementation: Replaced semantics acceptance case I3 with direct archive assignment, independent subject links, no automatic reversal, explicit target model cleanup and retained export evidence. Updated master context; generic archive importer remains unchanged.
- Open: Apply and verify the model change in an isolated migration target, inspect both axiom orientations, audit current live data and finish the separate inverse-read-field implementation. Raw append-only transfer does not remove old axioms.
- Risks/Assumptions: Local model/documentation change only; no live data/service writes, public signature changes, commit or push. Existing subject links are preserved and are not evidence of archival assignment.

### Update 2026-10-30 22:40
- Decisions: Implement step 2 of the agreed profile: subclass-only ancestry, forward subproperty expansion, stable modeled response keys and asserted-only search projection. Keep legacy inverses until step 3.
- Implementation: Updated the common Jena path/value helper and resource single/summary/search builders. Added scoped SHACL field eligibility for derived superproperty values and conservative exclusion of protected predicates anywhere on hierarchy routes. Added offline behavioral cases and transaction-scoped native fixtures; test transport supports transactional JSON-LD reads. Updated profile, implementation guide, cutover index and retained results.
- Validation: 57 offline tests, 141 native model/search checks (15 new) and 154 normal-adapter API regressions pass. Native checks cover direct/ancestor types, ignored equivalence, multilevel diamonds/cycles, filtering/counts/projection, modeled hydration, forged grants, all protected bridges and abort restoration. Initial offline graph-dereference setup and probe JSON-LD transport limitation corrected. Syntax, Markdown links and whitespace verified; owned test processes completed.
- Open: Step 3 inverse field metadata/applicability/source constraints and writer audit; own-model equivalence rejection; profile-aware real-project comparison and performance measurement. External axioms remain stored but equivalences are ignored.
- Risks/Assumptions: No general reasoner, new cache, public signature change or GraphDB behavior change. Hierarchy routes touching protected fields are conservatively refused even with a harmless alternate route. Earlier 120-match Chama parity and latency figures apply only to the old implementation. No source service/data changes, deployment, commit or push.

### Update 2026-10-29 17:35
- Decisions: Specify the agreed restricted semantics before implementation; keep uniform query construction and distinguish filter semantics from response projection.
- Implementation: Added step 1 behavioral specification with Fasnacht/Chama fixtures for ancestry, three subproperties, place/thing inverses, archive association, contribution/story backlinks and ignored equivalence. Linked from master context, cutover index and current entailment documentation.
- Open: Implement hierarchy changes in step 2; design inverse field identity/applicability and source constraints in step 3. Audit legacy directions and writers, resolve archive subject-versus-assignment semantics and multiplicity before migration.
- Risks/Assumptions: Documentation only; no runtime/data/API changes or test acceptance claimed. Previous 120 comparison matches remain historical baseline. Search projection stays asserted-only; derived fields must not expand authorization or silently discard legacy writes.

### Update 2026-10-29 00:45
- Decisions: Implement a limited, explicit read-entailment contract rather than enable general OWL reasoning. Keep public API/library signatures, GraphDB behavior and asserted-only authorization/provenance. Preserve existing asserted-only search projections while filters/summaries support derived links.
- Implementation: Added shared inverse/class/schema helpers and transaction-local external vocabulary discovery; wired resource reads/summaries/search and media/archive class checks. Class search preselects instantiated types before ACL joins to avoid repeated ontology walks. Rehearsal preserves used source prefixes, compares eight additional batch/search cases, verifies adversarial/transaction scenarios and measures isolated cache/scale/control cases.
- Validation: All 112 original plus eight extra GraphDB/Jena HTTP comparisons match; all source bracketing guards pass. Seven native entailment checks, 126 model/search checks, 154 API checks and 41 offline tests pass. Added scope/cycle/type/provenance/registration tests. Real Chama plus 1,000 synthetic people measured; paired search control requires identical pages. Syntax/whitespace checks pass; owned services closed after probes.
- Open: Broader real-project/load/concurrency acceptance; durable prefix/vocabulary provisioning for deployment, fulltext inverse-path decisions, large export/account/binary migration and production recovery. General OWL restrictions/domain/range/sameAs/property chains remain unsupported.
- Risks/Assumptions: Warm single read 141→175 ms and 54-resource summaries 311→414 ms; not negligible overhead. Cold means object cache only. Broad scaled search ~1.19 s; identical-page Person control 0.90 s new vs 1.72 s previous-rules control, not a historical release benchmark. Schema discovery and data read are separate outside a transaction. Source/user Redis untouched; private exports outside Git. No deployment, commit or push.

### Update 2026-10-29 00:04
- Decisions: Rehearse a real GraphDB project with an isolated Jena API, preserving asserted source data and public contracts. Keep content mismatches visible rather than accepting inferred-data loss or enabling general OWL reasoning.
- Implementation: Added repeatable Chama export/conversion/provisioning/import/API comparator, private evidence and sanitized report. Source schemas plus three vocabulary graphs, limited two-account bootstrap, normal API and owned Redis. Replaced exponential dataset tuple comparison with graph-based quad verification; reject RDF4J encoded triple URIs and use explicit star export formats.
- Validation: Real transfer succeeds; 112 API statuses match, 77 normalized bodies match and 35 differ (27 inferredTypes, eight knowledge backlinks, one story hasPart; overlapping fields). Source project/schema/admin exports and API baselines stable on reread. 28 native converter and eight CLI checks pass; syntax/whitespace checks pass. Owned services stopped.
- Open: Scoped external vocabulary hierarchy/equivalence and inverse-property reads; rerun the same comparator before claiming parity. Fulltext/binaries, further actors, writes, large packages, snapshot/recovery and production cutover remain separate gates.
- Risks/Assumptions: Rehearsal exits nonzero deliberately for content differences. Arrays compared without order; source uses existing cache. Bracketing stability is not a coordinated snapshot. Two pre-existing admin orphan grants preserved without memberships. Private exports/hashes/responses outside Git; no source data writes, deployment, commit or push.

### Update 2026-10-28 23:44
- Decisions: Retain GraphDB-to-Jena migration knowledge explicitly for the later system transition, as requested by the user.
- Implementation: Added a central cutover knowledge index in oldaplib and prominent links in all three repository master contexts. Records proven tools/evidence, compatibility/reasoning decisions, limits, administrative and binary/index gaps, rehearsal sequence and recovery prerequisites.
- Open: Representative source project export, controlled target provisioning/import/API comparison and remaining production cutover gates.
- Risks/Assumptions: Documentation only; checklist is future work, not production acceptance or authorization to switch systems. No runtime changes, service access, commit or push.

### Update 2026-10-28 23:41
- Decisions: Start the GraphDB-to-Jena data path with an offline, bounded, reviewable conversion; do not silently reinterpret unsupported RDF-star or discard legacy user side-channel records. Preserve asserted/orphan membership status and graph isolation.
- Implementation: Added native Jena tokenizer/parser-based converter, stable graph/membership reifier normalization, permission-kind validation, unchanged ordinary quads, strict UTF-8/gzip bounds and private no-overwrite output. Report records hashes/counts and dataset-isomorphic serialization round-trip. Added synthetic/legacy-seed/TDB2 probe, real CLI probe and documentation/results.
- Validation: 21 native checks and 8 CLI checks pass. Original GraphDB admin seed files produce the same permission relations as migrated seeds. Covers metadata/value union, ordinary quads, cross-graph blank nodes, orphan preservation, generated-ID collisions, malformed/mixed/nested/object quotations, wrong permission types, user side-channel refusal, gzip limit, private output and no partial publication. First probe compile corrected an atlas-json Number API call; final runs passed.
- Open: Representative GraphDB project export and target provisioning/import/API comparison; serialized user/account migration, large/streaming packages, index configuration and production recovery.
- Risks/Assumptions: Supports flat URI-based OLDAP membership annotations, not arbitrary RDF-star. 16 MiB decompressed/in-memory limit; existing HTTP 256 KiB limit unchanged. Output is plain native TriG, not the tools project wrapper. Reifier IDs differ from seed UUIDs but preserve relations; repeated blank-node imports are not generally idempotent. No live services, OWL reasoning, public signature changes, commit or push.

### Update 2026-10-28 23:31
- Decisions: Migrate initialization permission annotations to RDF 1.2 while preserving asserted memberships, all permission values and other data. Keep general OWL reasoning disabled; evaluate concrete inference dependencies separately.
- Implementation: Replaced 19 legacy annotation statements in admin.trig/admin-testing.trig with stable UUIDv5 reifiers for 18 memberships; duplicate Fornaro/HyperHamlet annotations share one identifier. Updated oldap.trig examples and statementShape descriptions without changing shape structure. Added native seed acceptance, original permission manifest and migration documentation/results. Shared/example/standard files need no syntax edits.
- Validation: 24 native Jena checks pass: all 10 ontology/vocabulary files parse, 29 original permission values preserved, asserted membership/exclusive reifier checks and reload stability. One-time baseline comparison proves remaining admin/default/model graphs unchanged by isomorphism. Nine offline shared-ontology/user-order/Jena-user-write tests pass; only existing RDFLib deprecation warnings.
- Open: Existing GraphDB project/account conversion and restore, larger transfer packages, remaining inference-dependency audit and production acceptance.
- Risks/Assumptions: Native RDF 1.2 files are for the Jena migration branch; legacy GraphDB seed loaders are not tested against them. Stable grant reload does not make arbitrary blank-node model reload idempotent. No user credentials changed, live data loaded, OWL reasoner enabled, public signatures changed, commit or push performed.

### Update 2026-10-28 23:16
- Decisions: Add a native RDF 1.2 graph-transfer boundary for provisioned projects; retain existing public signatures/GraphDB behavior. Require current root rights and explicitly exclude administrative identity restore. Preserve cross-graph blank nodes without Python RDF reserialization.
- Implementation: Added JenaProjectTransfer native parser/serializer and three session operations, private adapter export/import methods, explicit tools project routing and versioned gzip headers. Export replaces files atomically; import validates graph scope then appends within existing transaction ownership. Cache checked before import and cleared after commit with explicit committed-state errors. Added docs, offline tests and owned CLI/Redis acceptance.
- Validation: 154 integration checks pass (145 previous plus 9); 14 library and 17 tools tests pass. Covers four-graph RDF 1.2/language/blank-node round-trip, ordinary-user/root-revocation refusal, joined rollback, malformed/foreign/default/reserved input, and fulltext commit/rollback. Corrected initial fixture short-name datatype. Owned processes closed; whitespace checks clean.
- Open: Full administrative users/roles restore, legacy GraphDB RDF-star conversion, streaming/large projects, binary/export-job acceptance, production cache/concurrency and normal-adapter crash recovery.
- Risks/Assumptions: Jena --no-admin dumps are not complete backups; target project namespace/identities/configuration must be provisioned separately. Existing 262144-byte JSON request limit remains; server export uses memory. Import appends, so repeated blank-node payloads are not idempotent. CLI migration assumes quiesced application traffic; no production services, public signature changes, deployment, commit or push.

### Update 2026-10-28 23:00
- Decisions: Preserve public media signatures, serialization and token claims; select project-scoped media ancestry and asserted RDF 1.2 grants on Jena. Refuse ambiguous visible identities instead of merging token metadata.
- Implementation: Added documented private media query helper and backend routing for ID/IRI lookup. Bind selectors/caller inside permission aggregate. Added owned modeled-media/inventory acceptance, dedicated Redis fixture naming, isolated media JWT key, offline routing/ambiguity tests and retained results/documentation.
- Validation: 145 owned integration checks pass (132 earlier plus 13 new); 18 library tests plus 6 subtests and 10 API tests pass. Real HTTP covers metadata/signed claims, restricted grants, paginated hydrated inventory, entry capabilities, catalogue references, revocation/orphans, duplicate IDs and unrelated schema isolation. All owned processes closed; diff whitespace checks pass.
- Open: Raw project transfer/export, production object cache, normal-adapter crash/uncertain-outcome recovery and binary media delivery.
- Risks/Assumptions: Shared-model fixtures and real policy/coordination; object-cache I/O suppressed. Catalogue reference edge and malformed edge cases imported directly for acceptance. Candidate discovery and metadata reads are separate outside an existing transaction; metadata queries recheck rights. Existing tokens are not revoked by lookup changes. GraphDB query path unchanged; no public signature change, deployment, commit or push.

### Update 2026-10-28 22:50
- Decisions: Exercise full adoption through real policy-file loading, durable Redis coordination and HTTP endpoints; preserve existing transactions, audit, receipts and public signatures. Propagate only permissions attached to asserted source role memberships.
- Implementation: Scoped Jena archive-level and sibling-name validation to project/shared/base schemas; reused one private level query in preflight and domain guards. Fixed grant propagation so orphaned annotations retained in revision snapshots cannot become active rights on new units (both backends). Added owned socket-only Redis/AOF fixture and real coordinated-write acceptance, documentation/results.
- Validation: 132 owned checks pass (115 previous plus 17 coordinated writes); 106 library tests plus 24 subtests and 11 API tests plus 13 subtests pass. Covers duplicate siblings, actual parent/mapping/grant RDF, orphan exclusion, atomic audit/receipt, exact retry/conflicting IDs, session journaling, full rollback/retry, stale apply and structure-only provenance. Redis validates appendonly/always/noeviction and real WAITAOF; process closed after run.
- Open: Complete inventory/media hydration and specialized queries, raw project transfer/export, real object-cache behavior and normal-adapter crash/uncertain-outcome recovery.
- Risks/Assumptions: Synthetic owned resources, ordinary writer with explicit ADMIN_CREATE and role/data rights; normal policy loader and coordinator, only object-cache I/O suppressed. Confirmed commit/abort evidence is not crash/failover acceptance. User Redis untouched; no public signature change, deployment, commit or push.

### Update 2026-10-28 22:39
- Decisions: Migrate inventory/adoption read queries and canonical folder snapshots; preserve public signatures, creator/role semantics, distinct counts and stale-review guards. Select only project/shared/base schemas for Jena hierarchy paths.
- Implementation: Added three private query-building methods to ArchiveRepository for RDF 1.2 grants, schema dataset and exact/subclass matching; used by inventory/adoption/snapshots. Jena adoption visibility now uses direct subject-bound joins after the old correlated EXISTS/UNION shape admitted restricted/orphaned identities. Added offline dialect/routing tests and owned real-query/model/preflight/cursor acceptance; documented results and boundaries.
- Validation: 115 owned checks pass (102 earlier plus 13 archive reads), 62 library tests plus 21 subtests, 11 API tests plus 13 subtests. Covers schema scope/cross-schema ancestry, exact unknown classes, mixed keyset/counts, hidden/disconnected folders, hidden targets, fresh receipt-hint authorization, stale plans/cursors and transactional revisions. Existing RDFLib fixture emits deprecation warnings.
- Open: Coordinated staging/adoption writes, structural audit/receipts, complete inventory hydration/HTTP workflows, specialized media queries, raw project transfer and export jobs.
- Risks/Assumptions: Explicit fixture policy and imported owned RDF; real model/query/permission/transaction behavior. API staging creation correctly refused absent write coordination; no guard relaxed. Redis object-cache I/O suppressed. GraphDB tested offline only; no shared services, public signature changes, deployment, commit or push.

### Update 2026-10-28 22:26
- Decisions: Migrate archive publication as a bounded service workflow before inventory/adoption. Preserve public signatures, review/authorization rules and whole-command transactions; edit only the public role's permissions.
- Implementation: Added RDF 1.2 grant reads for publication/link reviews and explicit reifier writes for publication. Extended private cleanup helper with optional target; preserve internal grants and unrelated annotations. Shared reifiers raise existing PublicationConflict. Added Jena/offline publication tests, owned real-service acceptance and documentation/results.
- Validation: 102 owned integration checks pass (91 previous plus 11 publication/link checks); 50 library tests plus 14 subtests and 15 API route tests plus 13 subtests pass. Covers stale ACL review, rollback after first-resource write, no failed receipt, exact replay/conflicting IDs, internal grant/metadata preservation, additive links, restricted republishing and fresh publisher membership. Initial incomplete fixture property definition corrected through common base model.
- Open: Archive inventory/adoption/repository snapshots, complete policy-file/HTTP publication acceptance with coordination, raw project transfer and export jobs.
- Risks/Assumptions: Publication fixture supplies explicit server policy while using real authorization/model/query/transaction implementations. Redis object-cache I/O remains suppressed. GraphDB regressions offline only; no public signature change, shared service change, deployment, commit or push.

### Update 2026-10-28 22:20
- Decisions: Port the concrete all_resources bulk-query gap while preserving public signatures, exact asserted-class matching, role-only authorization and existing joined-row pagination. Track specialized workflows separately.
- Implementation: Added backend-selected RDF 1.2 permission annotation to all_resources; documented its contract and fixed undefined project name in error logging. Added offline dialect/routing/result/error tests, owned bulk acceptance and copy/export call-path inventory with retained results.
- Validation: 91 owned normal API/Fuseki checks pass (85 existing plus 6 bulk checks); 21 targeted library tests pass. Verifies projection/missing values, count/page, threshold, orphan/foreign-graph isolation and transaction/abort visibility. GraphDB syntax covered offline only.
- Open: Complete tools staging command, specialized archive/media queries, raw GraphDB project dump/restore, complete export jobs and legacy native fulltext search. Joined-row pagination can truncate multi-valued projections; unchanged in this compatibility step.
- Risks/Assumptions: Synthetic owned data; Redis object-cache I/O suppressed. No public signature change, shared service modification, deployment, commit or push.

### Update 2026-10-28 22:14
- Decisions: Verify normal API resource-to-index behavior before expanding migration scope. Keep authorization in current RDF checks and field meanings bound to managed revisions; no new application abstraction needed.
- Implementation: Added check_fulltext_writes to the owned API acceptance runner, exercising real writes/search and dynamic model/field configuration. Added retained results and updated migration status documentation. Application code unchanged.
- Validation: 85 owned API/Fuseki checks pass, including previous 69; 27 library fulltext/connection tests and 13 API fulltext tests pass. Covers commit/abort visibility, counts/pagination, ACL downgrade/restoration, late field activation, AND/projection, stale revisions, remapping and delete cleanup. First run caught untyped values in the test's direct library assignment; corrected to existing QName/DataPermission contract.
- Open: Bulk/copy/export RDF-star paths, specialized archive/media workflows, operational cache/load and normal-API restart recovery acceptance.
- Risks/Assumptions: Synthetic owned data, ordinary-user search and isolated service; only object-cache Redis I/O suppressed. No shared service change, public signature change, deployment, commit or push. Prior isolated crash/restart evidence is separate from this normal-API run.

### Update 2026-10-28 22:07
- Decisions: Preserve resource-operation transaction ownership and public signatures. Share RDF 1.2 permission generation/cleanup across users and resources with explicit graph scope; keep GraphDB branches and existing creator/role semantics.
- Implementation: Ported resource permission checks, create, role-map updates, class transformation grants and deletion. Renamed internal user helper to jena_permission_write and added graph selection/object grant predicate. Shared-reifier checks precede writes; API delete maps inconsistencies to 409. Added owned resource acceptance, offline dialect/routing tests and documentation/results.
- Validation: 69 owned API/Fuseki checks pass (including previous 52), plus 78 library tests with 14 subtests and 35 API tests. Covers non-admin permission thresholds, duplicate create, stale update, update/delete callback rollback, composed-create rollback, transformation, grant revocation, shared reifiers and foreign-graph isolation. Initial failures exposed missing numeric permissions and root role in the synthetic fixture; fixture corrected without altering access semantics.
- Open: Remaining RDF-star bulk/copy/export queries, specialized dating/list/media/archive writes and linked transforms, normal-adapter fulltext mutation/search acceptance, deployment/cache/recovery gates.
- Risks/Assumptions: Only ordinary modeled resources/basic transformation accepted here. factory.read retains role-based access even for admin/creator; read_data/class read preserve creator access. Object cache I/O mocked in owned runner; no live GraphDB regression, shared services, commit/push or deployment.

### Update 2026-10-28 21:56
- Decisions: Port user membership annotations explicitly, without rewriting arbitrary SPARQL. Replace only changed project/role maps in the existing optimistic transaction; retain bare memberships and current authorization/authVersion behavior. Reifiers must describe one membership for permission edits.
- Implementation: Added jena_user_write helpers and opt-in connection capability; User serialization/update/delete handles RDF 1.2 grants, duplicate cleanup and unrelated metadata preservation. Shared-reifier preflight runs inside the transaction; API reports its conflict as 409 with OpenAPI documentation. Removed raw user-update query printing on failure. Added normal-API user/role acceptance and GraphDB serialization regressions.
- Validation: 52 owned API/Fuseki integration checks pass (including the previous 33); 66 library tests with 9 subtests and 29 API tests pass. Covers role CRUD, user CRUD/login, grant replacement/removal, authVersion, invalid target rollback, stale edits, missing rights, shared-reifier refusal and graph isolation.
- Open: Resource-instance RDF-star write paths, extended user-class properties, refresh-cookie revocation acceptance on the normal adapter, remaining list/search/service operational gates.
- Risks/Assumptions: Whole changed membership maps are replaced after the timestamp check; reifier identifiers are internal and can change. Unrelated reifier annotations remain historical metadata without permissions. Cache Redis I/O is mocked only in the owned runner. No live GraphDB test, shared service change, commit, push or deployment.

### Update 2026-10-28 21:46
- Decisions: Select Jena explicitly through OLDAP_BACKEND; retain GraphDB default and existing public signatures. Reuse credential/JWT logic; keep the private identity callback database-free. Never replay updates after uncertain replies.
- Implementation: Added JenaConnection, central API backend selection/validation, identity endpoint and Jena health check; User.read uses a private backend query hook. Real API acceptance exposed and fixed duplicate list BEGIN, implicit default-graph reads, wrong index predicates and ancestor-move interval calculation. Invalid descendant moves abort. Added configuration/acceptance documentation and retained result artifact.
- Validation: 33 owned API/Fuseki checks pass without connection mocks: startup/login/refresh, model/property/list CRUD and moves with index/position assertions, fulltext activation, real tools import/update/TriG+fulltext backup/dump and zero-write replay. 63 library tests (9 subtests), 29 API tests and 76 tools tests (3 subtests) pass. Initial owned failing runs reproduced list defects before correction.
- Open: Remaining user/role/resource RDF-star writers, normal-adapter search acceptance, multi-node/concurrent list moves, isolated Redis/cache operational acceptance and production service packaging/recovery.
- Risks/Assumptions: Only object-cache Redis I/O mocked in owned integration. No live GraphDB regression for shared list corrections. Jena service still uses migration session protocol; maintenance operations explicitly unsupported. No shared service/data/environment switch, deployment, commit or push.

### Update 2026-10-28 21:26
- Decisions: Keep public fulltext administration bound to the authenticated connection, with fresh metadata and active-user asserted model/root permissions. Normal GraphDB connections explicitly refuse support; public signatures unchanged.
- Implementation: Added ProjectFulltext service and private IConnection capability/transport hook; expanded owned activation runner through the real Flask route, Project.read and current RDF authorization. API/tools provide additive endpoint and explicit import/dump/backup contracts.
- Validation: 46 owned integration checks pass, including orphaned grant after membership removal, inactive admin, system admin, graph mismatch, stale revision and normal-backend refusal; 21 API and 76 tools tests plus three subtests pass.
- Open: Normal Jena connection/startup, complete model/list write migration and live importer acceptance; large rebuild timing and whole-dataset recovery. Public request authorization is not atomic with later index publication.
- Risks/Assumptions: Probe replaces API Connection factory and cache I/O only. Synthetic URN project IRI exposed existing QName interpretation; HTTP fixture used, general URN support not changed. No shared services/data touched, deployment, commit or push.

### Update 2026-10-28 18:14
- Decisions: Keep RDF authoritative; synchronously rebuild all configured text predicates before activation and on every startup. Serialize maintenance with writers, exclude readers during swap, and bind compiled searches to configuration revisions. Private service administration remains separate from future public model-admin authorization.
- Implementation: Added JenaManagedText durable manifest/CAS/rebuild lifecycle, reusable allowlisted index producer, authenticated private FULLTEXT_STATE/APPLY and revision-bound READ, failure fencing and owned acceptance runner consuming actual oldap-tools YAML plan output. Added lifecycle/protocol/recovery documentation and results.
- Validation: 35 real Fuseki/TDB2 activation checks pass, covering existing text, changes across projects, writer refusal, stale reads, rollback/deletion, SIGKILL with pending writes, corrupt manifest and publication failure recovery. Existing 126 model/search and 51 identity/session/callback checks pass.
- Open: Public API ADMIN_MODEL authorization and authoritative project resolution, adapter/import/dump/backup wiring, production packaging and large-dataset timing. Whole-index rebuild needs maintenance time; disable-project operation not implemented.
- Risks/Assumptions: Durable manifest requires local atomic rename and fsync. Process-kill tests do not prove hardware power-loss behavior. Managed commit failures fence operations pending restart; no automatic replay. No public signature, production/shared service, real data or Redis change; no commit/push.

### Update 2026-10-28 14:39
- Decisions: Make fields/project paths data-driven from a portable fulltext YAML section; keep unknown native connector options explicit errors. Resolve fixed forward chains at query time; do not maintain copied root text. Public signatures unchanged.
- Implementation: Added field/path validation and QName expansion; generalized query helper and Java project/predicate allowlist from one YAML source. Added two-project/chain checks and read-only consumer/export inventory. Jena class filter now handles asserted class equality independently of schema presence.
- Validation: 126 integration checks (13 new configuration/chain checks) and 76 offline tests + 7 subtests pass. Fourteen GraphDB query comparisons unchanged. Second-project test reproduced schema-dependent direct-type failure before fix; QName test caught Context string conversion issue, handled using typed QName input.
- Open: oldap-tools YAML schema/import and admin persistence/activation/rebuild; native types/languages/analyzers and arbitrary consumer text grammar/ranking; index consistency/performance. No external checkout edits, commit, push or deployment.
- Risks/Assumptions: Configuration loaded before fixture data, not hot reload/reindex. Chains check root ACL only and stay within project data. Local fasnacht export is a snapshot, not live config; consumer archiveMediaObjectText is missing from that export. Multiterm user text remains unsupported. GraphDB/Redis untouched.

### Update 2026-10-28 14:21
- Decisions: Connect the unchanged public search via a concrete internal hook and explicit direct-field map. Support a validated atom/phrase/wildcard AND/OR subset; reject arbitrary Lucene/configuration rather than silently changing semantics. Preserve GraphDB defaults.
- Implementation: Added jena_fulltext query helper; wired search patterns and optional transactional TextDataset fixture into the authenticated engine. Project-only index producer excludes private/admin graphs; protected view receives only index context. Added real full-text integration checks and private canary fixture.
- Validation: 113 integration checks (27 additional) pass, including ACL/count/page, field/multivalue AND, structured/list filters, unsupported-input rejection before query HTTP, receipt exclusion and HTTP index commit/rollback/delete. Default identity/session/callback 51 checks and 60 offline tests + 7 subtests pass. Fourteen GraphDB query variants remain whitespace-equivalent to HEAD.
- Open: Actual connector/consumer inventory, property chains/type/analyzer/complex-query/ranking parity, production wiring/admin API, rebuild/concurrent visibility/resource bounds/hard-crash consistency. No deployment, commit or push.
- Risks/Assumptions: Explicit two-field test mapping, not production configuration translation. Sum for AND/MAX for OR ranking differs from GraphDB; unsupported inputs raise. Text index tests cover committed reads and normal transaction changes, not crash-atomicity. Shared GraphDB/Redis untouched.

### Update 2026-10-28 14:09
- Decisions: Establish text-index semantics/lifecycle before wiring public search. Keep existing connector and substring-search APIs unchanged; do not silently translate arbitrary GraphDB configurations.
- Implementation: Added standalone JenaTextProbe with owned persistent TDB2/Lucene, explicit direct-property/graph/language/UID mappings and documented compatibility findings. No application implementation changes.
- Validation: 24 runtime checks pass, including normal commit/rollback/replacement/deletion/clean reopen, synthetic RDF 1.2 ACL, distinct counts and final pagination. Demonstrated default cross-field/multivalue AND mismatch and successful independent joins. Fixed probe-only COUNT assertion to use typed integer instead of string formatting. Existing Python suites unchanged/not rerun.
- Open: Actual connector configuration inventory, public search integration, property chains/type/analyzer/query/ranking parity, protected dataset/HTTP sessions, rebuild/concurrency/hard-crash consistency. No commit, push or deployment.
- Risks/Assumptions: StandardAnalyzer and two direct fields are fixtures, not a production configuration decision. Separate index/storage clean reopen is not crash-atomicity proof. Default document limitations are expected observations, not full-text migration completion. No shared GraphDB/Redis accessed.

### Update 2026-10-28 01:27
- Decisions: Retain real list/node readers; use independent correlated EXISTS for each Jena hierarchical filter condition. Keep GraphDB queries and public interfaces unchanged.
- Implementation: Added owned two-list/tree acceptance fixture and Jena boolean filter branch with explanatory comments. Independent bindings support OR with absent properties and AND across multiple assigned nodes; refreshed docs/inventory.
- Validation: Pre-fix run reproduced OR failure. Final 86 integration checks (17 new list checks) and 60 offline tests + 7 subtests pass. Verified bounds/list/project isolation, mixed permissions, count/pagination, input forms, grouping and role removal. Fourteen GraphDB query comparisons match HEAD modulo whitespace.
- Open: Full-text, remaining media/read/write and inference paths; list mutation/index maintenance/concurrency/cache parity. No deployment, commit or push.
- Risks/Assumptions: Valid stable nested-set fixtures; list reads are real, Redis cache I/O mocked, fixture writes use private SPARQL. Boolean correction is Jena-specific; legacy GraphDB behavior needs separate review. Metadata loading and final search are separate reads.

### Update 2026-10-28 01:12
- Decisions: Share the search algorithm; explicitly scope Jena properties and derive class matches through selected schema paths. Keep GraphDB defaults and public signatures. Unsupported Jena connector full-text raises instead of silently returning no matches.
- Implementation: Added protected search capability, local data/class pattern helpers, RDF 1.2 root/linked grants and stable outer pagination order. Linked NOT_EXISTS in Jena requires a bound target. Extended owned model probe with separate search acceptance checks; refreshed inventory/docs.
- Validation: 69 integration checks (34 new search checks) pass; 60 offline tests + 7 subtests pass. Twelve GraphDB query variants match HEAD modulo whitespace. Checked duplicate grants/values, count parity, role revocation, projections, numeric/text/boolean/linked/Dating behavior and cross-schema superclass paths.
- Open: Real hierarchical-list acceptance, full-text/media paths, broader OWL corpus, remaining writes, production transport/cache/recovery/query limits. No deployment, commit or push.
- Risks/Assumptions: Limited subclass inference, not owl-max parity. Existing opt-in linked-permission policy preserved; bound-target absence guard is Jena-specific. Language boolean combinations, all Dating variants and multiple asserted classes need further corpus coverage. Only owned data/services used; Redis cache I/O mocked.

### Update 2026-10-28 00:57
- Decisions: Port bounded summaries before structured search; preserve the existing public contract and use the same concrete backend query boundary as single reads.
- Implementation: Added shared summary query builder and default IConnection hook; explicit RDF 1.2 reifiers, project-scoped data and limited subclass entailment. Extended real-model Fuseki probe with 16 batch checks and refreshed RDF* inventory.
- Validation: 35 owned-Fuseki checks pass, including maximum 100-resource batch in one READ after initialization, omission/creator/current-role rules, grant associations and input bounds. 60 offline tests + 7 subtests pass. Default GraphDB queries match HEAD modulo whitespace for zero/multiple projected properties.
- Open: Structured search/filter/count, media/full-text, broader inference, writes and production wiring/cache parity. No deployment, commit or push.
- Risks/Assumptions: Model/cache initialization is outside the one-query claim. Cache I/O remains mocked; Dating expansion not newly exercised. Subclass paths are not full OWL parity. Internal hooks only; no consumer signature changes.

### Update 2026-10-28 00:45
- Decisions: Keep real SHACL/OWL model parsing and resource hydration; select RDF 1.2 through a concrete internal query hook. Scope data per project and explicitly derive superclass types from selected ontology graphs; do not claim owl-max parity.
- Implementation: Added CONSTRUCT/JSON-LD transport, shared resource query builder/default hook, real-model/factory read probe and legacy RDF* AST inventory. Existing creator/threshold policies preserved. Fixture seeding is restricted to new owned datasets.
- Validation: 19 model/resource checks and 60 offline checks + 7 subtests pass; native identity/session/callback regression 20+20+11 passes. GraphDB read queries match HEAD modulo whitespace for both creator policies. Corrected test fixture timestamp type/collection expectations and adapted one mock to the default hook.
- Open: Batch/search/media reads, remaining user/archive/write RDF* paths, broader entailment corpus/runtime GraphDB baseline, production wiring and cache/recovery/query-limit parity. No deployment, commit or push.
- Risks/Assumptions: Cache I/O mocked only; real model/domain logic runs. 301 uncached reads are not a performance result. Scoped subclass path is not full OWL reasoning. Inventory has 49 lexical sites in 26 scopes, including legacy/default branches; not a count of independent remaining APIs.

### Update 2026-10-28 00:24
- Decisions: Reuse actual Connection initialization/password/token logic through protected transport/query hooks, keeping GraphDB defaults and public signatures. Require asserted membership for RDF 1.2 annotation grants.
- Implementation: Added opt-in Jena user query, separately credentialed read-only bootstrap probe route and real-constructor integration proof. Fixed UserData resetting permissions/defaults when membership rows follow annotation rows.
- Validation: Parser permutation regression failed before fix and passes afterward (24 orderings). 20 owned-Fuseki login checks and 45 offline tests + 15 subtests pass; native identity/session/callback suite 20+20+11 passes. Constructor signature matches HEAD. No existing GraphDB/Redis dataset touched.
- Open: Full model/resource reads, inference and remaining RDF* producers, production backend/API wiring, privileged bootstrap deployment controls, query limits and recovery/cache parity. No deployment, commit or push.
- Risks/Assumptions: Fixture users/password hashes; explicit base user typing, not inference proof. Existing token snapshot/anonymous/not-found semantics preserved. Bootstrap read can access admin hashes and requires separate backend credentials; no public route deployed. Conflicting default annotations remain invalid model data.

### Update 2026-10-28 00:17
- Decisions: Mount sessions directly in Fuseki; share one transaction engine with the earlier HTTP harness. Reuse TokenCodec through a protected Python verification peer, with distinct caller/peer service credentials and verified user IRI binding.
- Implementation: Added Fuseki servlet/identity integration probe; extracted JenaSessionEngine; generalized test connection factory and commit reconciliation for 5xx/malformed confirmations. No production API/library signature changes or deployment.
- Validation: 20 identity/boundary, 20 Fuseki session and 11 real callback checks pass. Legacy transport also passes 20+11 checks. Existing token/API boundary suite: 19 tests + 3 subtests pass; three unrelated API docstring escape warnings. Main capability runner not rerun.
- Open: Real credential login/user/model initialization on Jena, production private verification endpoint and packaging, TLS/secret rotation, query limits, durable client recovery and full CRUD/Redis parity.
- Risks/Assumptions: Fresh fixture users/keys and loopback HTTP only. Verification is an extra per-request dependency; no performance claim. Existing access-token snapshot semantics retained, not live authVersion enforcement. Resource authorization remains with trusted Python callers; no raw dataset route mounted. Fault hooks remain test-only.

### Update 2026-10-28 00:11
- Decisions: Protect transaction receipts at the dataset boundary, not with SPARQL text filtering or a second database. Preserve existing Python authentication/authorization ownership; no Java password/permission model introduced.
- Implementation: Added application DatasetGraph view, routed experimental HTTP queries/updates through it, and tested the same view behind actual embedded Fuseki query/update/Graph Store endpoints. Extended session probes for forgery rollback and bulk clear. Production signatures unchanged.
- Validation: 37 Fuseki boundary checks, 20 HTTP session checks and 11 unchanged callback checks pass. Initial missing Quad overloads, recursive union delegation and test Accept header corrected. Main capability/unit suites unchanged and not rerun.
- Open: Mount session protocol in Fuseki; authenticated service-to-service actor binding, protected administrative maintenance, durable client recovery, query limits and full CRUD/Redis parity. No deployment, commit or push.
- Risks/Assumptions: All application routes must use the view; direct backing-store access bypasses it. Not a general RDF ACL or SPARQL network sandbox. Generic-view performance is unmeasured. Synthetic probe identities remain; actual login not migrated.

### Update 2026-10-28 00:01
- Decisions: Keep Python business callbacks unchanged; pin interactive Jena writes to one owner thread. Commit application data and an owner-bound receipt together; absent receipt remains unknown and never triggers replay.
- Implementation: Added isolated HTTP session server and IConnection test transport, actor binding, one-writer admission, absolute idle cleanup, bounded request handling and commit-reply fault injection. Parameterized existing callback harness to reuse both transports.
- Validation: 17 HTTP/session checks plus 11 unchanged callback checks pass; original pipe proof also passes 11 checks. Includes SIGKILL before/after commit, lost responses before/after commit, expiry, wrong-actor requests, contention and SPARQL failure. Production code untouched; main runner not rerun.
- Open: Maintained server packaging, real identity/ACLs, protected receipts, query execution limits, durable client/aborted-session recovery, full CRUD/Redis coordination and uncertain-commit cache semantics. No deployment, commit or push.
- Risks/Assumptions: Trusted raw SPARQL can modify receipt graph; random probe credentials are not production authentication. Deadline cannot interrupt running statements; uncommitted ID tombstones are memory-only. Process crash tests are not storage/power-loss guarantees.

### Update 2026-10-27 23:41
- Decisions: Preserve existing Python callbacks and intermediate reads through an interactive boundary; do not compile arbitrary callbacks into monolithic SPARQL.
- Implementation: Added documented private-pipe Java/TDB2 bridge and probe importing real library ownership/audit and API lifecycle hook/worker methods. Production implementations and signatures unchanged.
- Validation: 11 callback/Jena checks, 53 library tests (7 subtests), and 9 API lifecycle tests pass. Probe method name corrected to claim_next after initial run. Tests use API virtualenv; library pytest unavailable. Full HTTP runner unchanged/not rerun.
- Open: Production session transport, authentication, thread ownership, bounded lifetime/concurrency and ambiguous commit reconciliation before general CRUD integration. No deployment, commit or push.
- Risks/Assumptions: Synthetic resource/model/identity; Redis coordination disabled. EOF rollback proof is local, not HTTP/network/crash recovery. Real audit/outbox queries and callback bodies are imported unchanged.

### Update 2026-10-27 23:33
- Decisions: Make readability explicit: visible owner and named steps, no monolithic SPARQL or generic workflow interpreter. Source inspection distinguishes structural audit from mobile lifecycle work; test a composed folder/media command rather than assume one resource always produces both.
- Implementation: Added commented, isolated Java HTTP/TDB2 proof with preconditions, resource changes, conditional audit/outbox, final assertion, replay receipt and one commit boundary. Production Python/API code and signatures untouched.
- Validation: 13 real-HTTP composition checks pass, including five full-rollback stages, concurrency, replay and conditional effects. Full migration runner has 69 top-level checks (composition nested); 53 existing Python ownership/domain tests pass. Initial Dataset AutoCloseable compile assumption corrected; final run passes. Owned processes stopped.
- Open: Map a real composed caller/dependencies; retain arbitrary Python callback and transaction-local read semantics through a compatible transport. No resource-port activation, server extension deployment, commit or push.
- Risks/Assumptions: Synthetic RDF/permission fixture and fixed command, not OLDAP schema/ACL parity. No production command journal or callback interpreter added. One-request optimization must yield to public compatibility and maintainability.

### Update 2026-10-27 23:14
- Decisions: Reuse designated writer-store AOF/WAITAOF validation for prepared revocations; keep operator recovery fencing separate. Persist immutable exact command before HTTP; no automatic retries, expiry or cleanup.
- Implementation: Added dataset-scoped Redis journal with collision checks, snapshot/query compatibility validation and retained-ID discovery. Pinned write/fsync sequence checks connection ID and Redis incarnation. Restricted public-call probe optionally journals before sending.
- Validation: 68 owned Fuseki/Redis integration checks and 34 targeted tests pass. Writer os._exit plus Redis SIGKILL/restart preserves unsent/committed/denied attempts; exact replay increments once. Missing fsync, unavailable store and reconnect block all transport. Initial redis-py test attribute mismatch corrected; final suites pass. Owned processes stopped.
- Open: Production recovery authorization/store/dataset binding, receipt/journal retention and cache reconciliation; next architectural proof is resource+audit+outbox composition. No deployment, commit or push.
- Risks/Assumptions: Local primary AOF only; no replica failover, volume loss or power-loss guarantee. Retained records are not a pending queue and have no TTL. Recovery fails closed across incompatible serializer/query changes. Normal GraphDB/API contracts unchanged.

### Update 2026-10-27 22:59
- Decisions: Check self/root/all-target-project administration inside the Jena mutation using current RDF 1.2 grants. Record denied outcomes atomically so existing permission errors and exact-replay decisions remain deterministic.
- Implementation: Added guarded write bindings and committed/denied receipt status; bumped experimental digest domain to v2; strict outcome decoding; public-call and concurrent permission-removal probes. GraphDB/public signatures unchanged.
- Validation: 63 isolated Fuseki checks and 26 offline tests pass; exact metadata cardinality verified on denial/success; receipt-free GraphDB query matches HEAD for versions 0/1/99. Initial frozen authorization-context fixture corrected. Test server stopped.
- Open: Durable recovery identity and receipt lifecycle/access, general Jena login/connection, then resource+audit+outbox atomicity. No deployment, commit or push.
- Risks/Assumptions: Trusted actor identity and valid singular user metadata; experimental v1 receipts are incompatible with v2 (fresh test datasets only). Denial records internal receipt data but no user/cache changes. Concurrent acceptance proves consistent serial decisions, not a guaranteed ordering.

### Update 2026-10-27 22:51
- Decisions: Add a concrete internal connection boundary with the legacy default; no new abstract requirement or public signature change. Keep Jena self-revocation opt-in; reject administrator commands until atomic grant checks exist.
- Implementation: User delegates persistence while retaining authorization and post-commit state/cache logic. Added strict receipt execution/reconciliation with retained command identity, fail-closed restricted probe connection and offline failure tests.
- Validation: 45 isolated Fuseki runner checks and 24 offline tests pass, including actual public User calls, stale conflicts, simulated lost/uncertain delivery, receipt validation and exact internal recovery. Syntax/diff checks pass; owned Fuseki stopped.
- Open: Atomic administrator authorization, durable recovery/receipt lifecycle, general Jena login/connection and composed resource+audit+outbox proof. No deployment, commit or push.
- Risks/Assumptions: Test connection trusts synthetic identity and mocks Redis. Attempt storage is in-memory; unknown outcomes are not resolved across process loss. No automatic retry or interactive transaction emulation. Production GraphDB path remains unchanged in behavior.

### Update 2026-10-27 22:46
- Decisions: Pilot authentication revocation with one stock Fuseki mutation plus a separate receipt read; retain public User/API contracts and existing GraphDB transaction behavior. Receipt absence after transport failure remains unknown.
- Implementation: Extracted shared immutable revocation query preparation; added optional experimental digest-bound receipts, isolated concurrency/replay probes and public-method regression tests. Documented outcome semantics and remaining integration gates.
- Validation: 40 owned Fuseki runner checks and 15 offline authentication tests pass; receipt-free query matches HEAD for versions 0/1/99 ignoring whitespace. No live GraphDB test or real-data mutation. Initial unit fixture omitted required User attributes; corrected before final passing run.
- Open: Internal Jena connection integration, authorization dependency checks, receipt retention/recovery and resource+audit+outbox composition; no activation, commit or push.
- Risks/Assumptions: Pilot assumes authorized callers and valid singular user metadata. Lost-response simulation discards a completed response; no network/crash fault injection. Experimental receipts do not yet define a production schema/lifecycle.

### Update 2026-10-27 22:40
- Decisions: Preserve HTTP API contracts and public oldaplib signatures and semantics throughout migration; internal transport/helper changes are preferred.
- Implementation: Recorded compatibility acceptance criteria and mandatory documentation/discussion for unavoidable public exceptions, including harvester and oldap-tools caller mapping.
- Open: Apply criteria to the revocation pilot and composed transaction/callback design.
- Risks/Assumptions: One-request optimization must not silently weaken transaction-local reads or callbacks. Documentation only; no application or external-consumer changes.

### Update 2026-10-27 22:36
- Decisions: Prefer one atomic mutation request per business operation; distinguish stock SPARQL Update from a server command with assertions/results. Keep dynamic Python/callback migration explicit; no generic session or workflow framework introduced.
- Implementation: Added AST inventory utility, source-hashed call-site snapshot and per-boundary migration table; analyzed real revocation, resource-hook, list, job and external-consumer flows. Extended isolated Fuseki probes for conditional batching.
- Validation: Parsed 620 Python files in eight repositories; 86 unique boundary-function rows (including infrastructure and operational probes), all snapshot-linked. All 27 capability/batch checks passed; stale-guard no-op hazard and guarded concurrent one-winner behaviour reproduced. Syntax/diff checks passed; test servers stopped.
- Open: Implement bounded revocation pilot with conflict/replay outcomes, then resource+audit+outbox and list/harvester composition. Existing double-start in list move and model-edit boundary need explicit treatment. Commit/push pending.
- Risks/Assumptions: Static syntax inventory cannot prove arbitrary downstream/dynamic callers. Synthetic receipts lack production request-digest semantics. No OLDAP application code, real data, Redis or service configuration changed.

### Update 2026-10-27 22:18
- Decisions: Keep the first Jena step isolated and synthetic. Explicit RDF 1.2 reifier identity is the working direction; defer transaction architecture selection until a real operation is mapped.
- Implementation: Installed checksum-verified Fuseki 6.2.0 outside Git using existing Java 25.0.2. Added reproducible Java TDB2 and Python-owned Fuseki HTTP probes plus report/results at docs/migration/j0-capability-probe.md.
- Validation: Final run passed 21 runner checks (including four Java transaction check groups). Covered read-own-writes, concurrent isolation/claims, rollback, request atomicity, restart persistence, all three grant patterns, revocation, graph scope, repeated insertion and Turtle round trip. No listener remains on test port 3031; syntax/diff checks pass.
- Open: Choose server-command versus multi-request transaction extension; test actual OLDAP workflows, failure recovery, inference and full text. Commit/push pending.
- Risks/Assumptions: Initial harness expected 404 but observed unsupported-route 405; corrected and rerun. Persistence tests use graceful restart, not crash injection. Anonymous annotation shorthand changes identity semantics. No OLDAP services or data changed.

### Update 2026-10-27 22:11
- Decisions: Treat SHACL only as model description/read metadata, per user clarification. Prioritize multi-request transaction feasibility and RDF 1.2 grant identity before backend implementation.
- Implementation: Added source-backed migration assessment at docs/migration/jena-assessment.md, covering transactions/recovery, RDF-star conversion, inference/graph scope, full text and model round trips; recorded phased acceptance gates and primary sources.
- Validation: Inspected both repositories and setup templates; local RDFLib 7.6.0 default Turtle parser rejected legacy RDF-star and RDF 1.2 triple-term probes. No Fuseki runtime or live database test performed.
- Open: Pin/install Jena and prove transaction and annotation contracts; choose transaction architecture, reifier identity and inference/search configuration.
- Risks/Assumptions: Standard remote SPARQL calls do not preserve existing interactive transaction semantics; runtime GraphDB ruleset not verified. No application code, data or services changed by this assessment.

### Update 2026-10-27 12:07
- Decisions: Isolate Jena development in sibling worktrees with Python 3.13 environments; use current ontology development as the library baseline.
- Implementation: Fast-forwarded the library migration branch from 0.4.27 to existing 0.7.29 history. Configured the API's editable sibling-library dependency and documented environment setup; retained PyCharm's in-project virtualenv setting.
- Validation: Poetry installation and lock checks passed in both Python 3.13 environments; API import resolves to the sibling migration library (0.7.29). API metadata deprecation warnings remain.
- Open: Separate Fuseki/Redis configuration, API ports and migration compatibility assessment; commit/push environment changes.
- Risks/Assumptions: Local path dependency is for migration development, not distributable releases. No services started or existing database configuration changed.

### Update 2026-10-24 12:42
- Decisions: Send transactional SPARQL updates as raw UTF-8 bodies, avoiding GraphDB servlet form-size limits for large text metadata.
- Implementation: transaction_update now uses PUT with action=UPDATE and application/sparql-update. Added Unicode/large-body/error/transaction-guard tests. 55 focused transport/transaction/publication tests pass. Real local harvester updates and API readback/replay pass for two historical PDFs.
- Open: Release the library and update consumers; validation used PYTHONPATH source override only.
- Risks/Assumptions: No server limits/auth/transaction ownership semantics changed. Nontransactional update/query transport is unchanged.

### Update 2026-10-23 23:48
- Decisions: Add one narrowly scoped published-media relation command; retain generic CRUD guard and avoid general merge machinery.
- Implementation: Added preview_link/apply_link with fresh publisher membership, UPDATE checks for all parents/media, equal public grants, model validation, bounded revision review and atomic idempotency receipts. Targeted publication/shared-sink suite: 32 tests pass. Local real transaction and exact receipt replay pass.
- Open: Release oldaplib before production use; HTTP exposure is not required by the direct-library harvester.
- Risks/Assumptions: No ontology/ACL changes. Local development build installed only in harvester venv. One-off duplicate deletion uses normal library inbound-reference guard, not this additive command.

### Update 2026-10-10 00:10
- Decisions: User role membership without a default data permission must not become an implicit object grant. Explicit object grants require a valid DataPermission; no permissions are invented or membership records changed.
- Implementation: Filter None defaults in ResourceInstanceFactory, allocate an independent default map per instance, and validate explicit constructor grants before conversion. Four offline regressions cover mixed/empty memberships, explicit grants and malformed/null inputs. Installed reviewed local 0.7.26 development wheel into the native API and used guarded make restart; writer gate released.
- Open: User upload retry is the final live acceptance. Publish a new oldaplib release before remote rollout; current local wheel differs from the published version. Mediahelper normalization deployment remains separate.
- Risks/Assumptions: 19 focused source tests and four installed-runtime regressions pass; installed objectfactory hash matches source. Poetry check and diff check pass. Previous installed package backed up under ~/.codex/backups/oldaplib-default-roles-20261010-001005. No stored data, memberships, grants, remote service or Docker container changed; no full live database test suite was run.

### Update 2026-10-07 23:45
- Decisions: Require a bound value inside each ordinary structured-search comparison; preserve OPTIONAL for OR and NOT_EXISTS for absence.
- Implementation: Fixed direct and linked comparison generation in objectfactory.py; added regression coverage for branch-local guards, count queries and NOT_EXISTS. Reproduced the original false root directly in local GraphDB; 18 focused tests and 20 read-only live queries pass. See docs/search_optional_values.md.
- Open: Publish a new library release before external rollout.
- Risks/Assumptions: Locally installed an unpublished 0.7.25 development wheel in the native API and performed guarded restart; published 0.7.25 lacks this fix. No data, permissions or remote services changed.

### Update 2026-10-01 11:50
- Decisions: Accept user-deployed project-identity optimization on the VM; retain four workers/two threads.
- Implementation: Recorded deployed API 0.2.31 / oldaplib 0.7.25 source verification and read-only before/after evidence; updated context and relevant performance/worker documentation. No application code or deployment configuration changed.
- Validation: 1,152 timed reads pass; all 17 baseline contents and public HTTPS checks match. Resource medians improve 10–13%, summaries 4–10%. At 16 readers: median/p95 167/591→143/559 ms, API CPU 1.78→1.57 cores. Existing 50,396-binding RDF fingerprint, containers and service PIDs unchanged; temporary VM files removed.
- Open: Larger representative data and sustained mixed-user sizing remain separate; no worker maintenance indicated by this workload.
- Risks/Assumptions: One sequential short warm anonymous comparison, not maximum capacity. Search/fresh-model gains not demonstrated; recovery p95 varies upward. Separate final verifier excludes the completed load-client process; within-run service-process guard passed. Existing local changes preserved.

### Update 2026-10-01 00:43
- Decisions: Retain a small project-identity projection; avoid broader model caching or generic copy changes. Gains are useful but below a consistent 15–20% across all endpoints.
- Implementation: Added internal Project._read_identity and used it in identifier-based PropertyClass construction. Deep-copy only three retained identity values; preserve full Project reads and snapshot lifetime. Added five offline regressions and updated strategy/context.
- Validation: 75 library, 14 API and 19 tool checks pass; 1,000 accepted timed reads return 200; 34 before/after contents match. Anonymous medium improves 13–16%; summaries improve 6–13% across users/rounds. Full Project copies 524→181; 3 GraphDB/42 Redis reads unchanged. All accepted RDF fingerprints unchanged (52,490 bindings).
- Open: Normal library release/consumer dependency update, then read-only VM comparison with existing worker settings. No installation, restart, version bump or deployment performed.
- Risks/Assumptions: Warm sequential laptop measurements, not concurrent production capacity. First direct-copy prototype discarded and excluded due closing source-inventory mismatch; final accepted source inventories stable. Existing user changes preserved.

### Update 2026-10-01 00:27
- Decisions: Record production read validation of released constructor-metadata optimization; keep worker settings unchanged.
- Implementation: Updated project context with effective oldaplib 0.7.24 deployment/source identity and linked the API repository's VM evidence. No library code changed.
- Validation: Complete VM rerun: 1,132 HTTP-200 reads, all 17 baseline contents and RDF fingerprint unchanged. Resource median 185→130 ms; 16-reader p95 649→591 ms, API CPU 2.13→1.78 cores. Public read checks pass; no service restart or data write by measurement.
- Open: Profile Project/model reconstruction and independent copying locally; larger-data sizing remains separate.
- Risks/Assumptions: Sequential short warm anonymous comparison, not maximum capacity. Initial sampler false-positive run excluded; corrected tooling and full rerun documented in oldap-api.

### Update 2026-09-30 23:50
- Decisions: Remove measured repeated constructor introspection without caching mutable domain objects or authorization context. Compare explicitly selected 0.7.23 source trees because the native API environment on disk still contains 0.7.22.
- Implementation: Added a 256-entry constructor-keyed LRU for immutable connection parameter names; preserve per-object connection/con rebinding and JSON format. Added eight offline regressions for caller/thread isolation, replacement/re-registration, bounded retention, mutable payloads and real Project roundtrips; documented cache lifetime/release boundary.
- Validation: 70 library, 14 API and 17 read-tool checks pass. Source A/B: resource 90.8→66.5 ms, 25 summaries 102.1→80.5 ms; one-worker/four-thread HTTP at 16 readers: 13.98→16.91 requests/s, p95 796→568 ms. 2,408 timed HTTP-200 reads; 34 full-catalog content comparisons and eight load-reference hashes match. Fingerprints retain 52,490 bindings; native service PIDs unchanged.
- Open: Publish a new library release, update consumers and repeat VM measurements with unchanged worker settings. Independent Project/model copying remains the next profile candidate.
- Risks/Assumptions: Short warm local source experiments, not installed/VM improvements. Constructor identity changes invalidate naturally; in-place signature edits require metadata-cache clear/restart. No package installation, service restart, cache flush, GraphDB update, version bump or publication.

### Update 2026-09-29 23:39
- Decisions: Address measured Redis connection churn and repeated project materialization before framework/database scaling. Keep object ownership and writer isolation unchanged.
- Implementation: Share bounded process-local Redis pools by exact URL with fork reset; avoid throwaway writer clients when parsed database numbers differ. Scope reusable project snapshots to DataModel.read/factory construction; return independent connection-bound copies, preserve fresh-read bypass, and repair Project deepcopy changeset/notifier ownership.
- Results: Activated an unpublished same-version 0.7.22 development wheel through writer-gated API restart. Exact 1,188-request warm replay passes; public media median 515 to 97 ms, 25 summaries 758 to 112 ms. Redis reads 563 to 42 with zero warm client creations. All explicit named-graph fingerprints unchanged. See ../oldap-api/doc/performance/2026-09-29-optimization.md.
- Open: Publish a normal versioned release when requested; mixed-user concurrency, Enterprise and FastAPI remain unmeasured. Backup and source hashes: /Users/rosenth/.codex/backups/oldap-performance-before-optimization/.
- Risks/Assumptions: Pools retain eight configurations, each with at most 32 connections. Snapshots expire after synchronous model construction and cannot cross requests/connections; mutations must remain outside this scope.
- Validation: 39 focused library/isolated writer-store tests and 10 API tests pass. All 34 baseline/optimized and 34 post-activation runtime response-content comparisons match; explicit named-graph fingerprint unchanged.

# CODEX_LOG

### Update 2026-09-22 23:06
- Decisions: Preserve complete Lucene creation options in native YAML; load remains opt-in and project-scoped. Existing shorthand and transport defaults remain supported.
- Implementation: Add lucene_connector.py and offline tests for permission, escaping, conflicts, unchanged state and recovery; retain existing datamodel/search behavior. 126 tools tests + 8 legacy tests + 25 targeted library/API/export/auth tests passed. Live Fasnacht dump retained 16 classes, 10 taxonomies and all options of the 8-field connector; replace dry-run planned zero operations. No live connector/model writes.
- Open: Publish paired releases before use outside this local development setup; no release/version bump performed.
- Risks/Assumptions: Connector commands are not RDF transactions. Failed replacement attempts restoration but may require reindexing; administrators outside configured writer coordination must serialize changes. Installed a local, unpublished oldaplib wheel still labelled 0.7.21 in the native API Python 3.13 environment; activated with writer-gated make restart. Production unchanged.

### Update 2026-09-22 22:29
- Decisions: Repair the canonical RDF exporter after oldap-tools API backup validation exposed invalid TriG; retain standalone SPARQL update behavior and existing API endpoints.
- Implementation: DataModel TriG uses ExternalOntology.create_shacl_triples and rdf:type for ontology declarations; ResourceClass.create_owl always terminates its class statement, including classes without properties. Three offline regressions verify SPARQL creation, named-graph string/file exports with multiple external ontologies, and adjacent empty-class fragments. Tests pass with the API source environment.
- Open: Publish a new version for other consumers; no version bump/publication performed. The user's nine pending Fasnacht ontology changes have not been applied.
- Risks/Assumptions: Source matched installed 0.7.21 before these fixes. Built/installed an unpublished same-version wheel without dependency changes into /Users/rosenth/Library/Caches/pypoetry/virtualenvs/oldap-api-69wuW7M7-py3.13 and restarted via the writer-gated oldap-api make restart. Read-only live verification: model export parses to 1,524 triples; API ZIP snapshot includes all ten taxonomies and passes ZIP integrity checking. No production or instance/model data mutation.

### Update 2026-09-18 23:47
- Decisions: Extend existing opt-in editorial creation grants to project-configured publication roots and subclasses.
- Implementation: Archive domain creation guard now adds editorial UPDATE to semantic archive roots, preserving readers and stronger grants; no updates/backfill. Publication capabilities expose automaticEditorialGrants separately from publication authority. Add root/subclass/opt-out and capability regressions.
- Open: Release and update normal consumers; no installed wheel or running service changed.
- Risks/Assumptions: 48 domain/publication tests passed with the API Python environment against this source. The local library venv lacks convertdate. No ontology or policy schema changes.

### Update 2026-09-14 22:50
- Decisions: Add generic permission-filtered direct media counts to folder-default proposals; use one aggregate query, never per-folder media reads. Counts are display-only and excluded from review hashes.
- Implementation: oldaplib COUNT(DISTINCT media) covers same-area staging media and configured archive references. Optional directMediaCount documented in shared JSON schema/OpenAPI; regenerated FP types; shared UI consumes counts with older-server fallback. 28 backend tests and browser count/recovery smoke pass. Local GraphDB: 46 folders/125 visible placements, 7–30 ms aggregation; three inventory comparisons agree. API HTTP 200 verified after safe restart (cold proposal 21.6 s, warm 1.86 s for sampled folder).
- Open: Normal version bumps/publication and consumer updates before production. Existing frontend/library check baselines remain; no ontology changes.
- Risks/Assumptions: Local API uses a development wheel still labelled 0.7.19, ahead of published 0.7.19; do not deploy that version as if released. Backup: BACKUP/local-media-counts-20260914-224638/installed-oldaplib.tar.gz. No archive data, role or production writes. Zero means no visible direct media, not proof of global emptiness.

### Update 2026-09-13 23:18
- Decisions: Activate publication on the local MacBook first; production remains unchanged. API-only media workers do not require an independent archive policy or Redis gate.
- Implementation: Verified installed oldaplib 0.7.19; replaced three local media containers using old :local/0.7.11 with v0.2.12/0.7.19, persisted Compose tag and backed up configuration. Validated/atomically added local publication policy and safely restarted native API under writer gate. Installed-library GraphDB success/retry/receipt and failure rollback pass; API capabilities 200, unauthenticated 401, authorized IIIF 200/unauthorized 401. BMG-Archivist publisher membership verified read-only.
- Open: User authenticated UI acceptance; separately coordinated production activation. Public archive viewer token propagation remains separate.
- Risks/Assumptions: No existing RDF resource, role assignment or public grant changed; fixtures/receipts rolled back. Backups in BACKUP/local-publication-20260913-231358 and local-publication-policy-20260913-231513.json. No CaptureApp, production, version or Git publication changes.

### Update 2026-09-13 00:58
- Decisions: Publication authority is generic opt-in policy; fresh publisher membership plus resource UPDATE; creator/admin CRUD exceptions cannot bypass domain protection.
- Implementation: Added ArchivePublication preview/apply/receipt command, closed configuration/model checks, bounded multi-parent review, restricted public ACL writes, stale/idempotent handling and CRUD/transform guard. Local GraphDB verifies root/media atomicity, exact retry and rollback on a second-write failure. Validation: 85 focused backend/gate tests and 4 frontend retry tests pass; local GraphDB success/replay and injected-failure rollback pass. Both frontend builds/lint pass; FP check baseline unchanged (23/37), SALSAH check clean.
- Open: Release matching library to all writers before policy opt-in; authenticated end-to-end and release concurrency acceptance remain.
- Risks/Assumptions: No ontology or globally active policy changes. Existing durable gate reused. Published relationship changes/unpublication deliberately require a separate workflow.

### Update 2026-09-10 19:32
- Decisions: Implement a separate folder-default tree; suggestions require a unique recorded structure-only origin and current target visibility. Save/remove one folder at a time, without changing media or archive structure.
- Implementation: Added default_proposal/read-only API route and generated client, shared source-choice loader, and ArchiveFolderDefaults below persisted management. Preflight/apply remains authoritative and exact pending requests survive reload. 28 backend/API tests plus 21 subtests, targeted lint, build, defaults desktop/mobile retry smoke and step-one/public regression pass; check baseline remains 23 errors/37 warnings in 15 files. Guarded API restart succeeded; live read-only response returned 44 folders/seven hints.
- Open: User acceptance; SALSAH-2 UI adaptation remains separate.
- Risks/Assumptions: Hints suppressed above 1,000 scanned receipts, capped at 500 with warnings. No guessed names/recency, ontology/Capture changes, live default writes, commit or production deployment. Existing unrelated changes preserved.

### Update 2026-09-10 19:12
- Decisions: Separate creating empty archive units from hierarchy editing and folder defaults. Keep old request semantics and exact uncertain retries compatible.
- Implementation: Added optional applyMappings=false in library/API/client contracts, suppressing folder writes while preserving creation grants and storing origin IDs in private receipts. Replaced the combined FasnachtsPage editor with a fixed-hierarchy source/placement/name/level/review flow. 26 backend/API tests plus 15 subtests, targeted lint, build and desktop/mobile/public fixture smoke pass; frontend baseline stays 23 errors/37 warnings. Local API restarted through its guarded Make target; live read-only preflight confirmed zero default changes.
- Open: Step-three default editor and retrieval of recorded provenance; user acceptance of step one. New operation IDs are separate imports, not cross-operation deduplication.
- Risks/Assumptions: No ontology/Capture changes or live archive writes; old SALSAH requests retain combined behavior. Match API/library release before deploying the new frontend. No commit/push or production deployment; unrelated work preserved.

### Update 2026-09-10 12:10
- Decisions: Complete WR-04 local operational acceptance; enable only the explicitly authorized rosenth operator. Production remains a separate target-specific rollout.
- Implementation: Added reviewed native inventory, kernel exit observation, owner/service scope checks and post-query generation checks; tested isolated native GraphDB faults and actual MacBook lifecycle. Acceptance: 50 recovery/native, 19 deployment, 49 authentication/Capture transport and 8 frontend tests pass; 10 native and 15 pinned Redis checks pass. Both live/fixture UI flows and builds pass; FP typecheck baseline remains 23 errors/37 warnings, SALSAH is clean.
- Open: Production multi-host/SSH partition, whole-host reboot and independent-storage restore acceptance; native Capture acceptance retains the user's local waiver.
- Risks/Assumptions: Native services must remain foreground and within the reviewed inventory; unmanaged direct writers are maintenance-only. Persistent controller/gate state never expires. No commit, push or production deployment.

### Update 2026-09-10 01:32
- Decisions: Provide one advisory evidence-binding predicate for UI diagnosis and authoritative release; distinguish an unconfirmed durability acknowledgement from a safety refusal.
- Implementation: Added WriterRecovery.readiness and RecoveryOutcomeUnknown. Added optional Connection.query(timeout=) with unchanged default behavior for existing callers. Verified recovery ACL readiness and query timeout compatibility; documented the WR-03 projection.
- Open: WR-04 real GraphDB/multi-host failure rehearsal and native MacBook runtime control before activation.
- Risks/Assumptions: 44 focused HTTP/library/service tests and eight auth-boundary tests pass. No ontology, ordinary write policy, Capture contract or application-data change. Existing uncommitted work retained.

### Update 2026-09-10 01:05
- Decisions: Implement an explicit maintenance barrier and evidence-backed recovery; never infer safe release from age/PID or caller booleans.
- Implementation: Added process-instance/revision diagnostics, barrier-aware acquire/journal/release, persistent recovery journal with exact-owner/idempotency checks, ACL-preflight audited release, and a separate Docker/SSH operator with two-phase runtime proof and reviewed read reconciliation. Added real Redis/ACL/race/failure tests and operator documentation.
- Open: WR-03 HTTP/UI adapters; WR-04 real GraphDB/multi-host fault rehearsal and native MacBook controller before activation. Legacy recovery remains trusted/offline only.
- Risks/Assumptions: 51 focused backend tests pass; deployment suite and pinned Redis 7.4.6 probe pass. Recovery stays disabled. Controller errors retain ownership because remote commands may still run. Existing dirty archive/coworker changes preserved.

### Update 2026-09-09 23:19
- Decisions: Preserve permission filtering and audit behavior while fixing defects exposed by real local migration.
- Implementation: Alias only requested full-IRI subjects already present in permission-filtered construct results; preserve original dictionary ACL snapshots across replacement edits and execute both DELETE and INSERT for replacements; parse xsd:int including zero correctly. Added regressions. Installed current source editable into actual API Python 3.13 runtime.
- Open: Publish a reviewed versioned release for production; local editable state is not a release.
- Risks/Assumptions: 93 combined focused tests and 64 isolated ObjectFactory tests pass. Actual migration verified all final grants and unchanged non-permission metadata. See FasnachtsPage/docs/as-09/local-rollout.md.

### Update 2026-09-09 21:57
- Decisions: Add opt-in project creation grants independently of capability membership; retain legacy behavior without the flag and reject invalid explicit media grants.
- Implementation: Policy accepts optional strict boolean grantEditorRolesOnCreation. Shared creation rule supplies unit DELETE/media UPDATE across generic creation, reviewed adoption and catalogue transfer; review digest binds the flag. Fixed ObjectFactory ObservableDict callback keyword on ACL replace/reset/delete. Added six focused tests and disposable GraphDB/AOF Redis probe (FasnachtsPage/docs/as-09).
- Open: Versioned deployment and existing-resource ACL migration; private mapping rights/native acceptance remain rollout concerns. The policy does not sanitize invalid caller/user-default ACLs or regrant on updates.
- Risks/Assumptions: 90 combined library/API tests, 63 isolated ObjectFactory tests, real creation/adoption/transfer/rollback/non-admin checks and Capture transport contracts pass. No ontology, application RDF or runtime configuration changes. Matching source required before selecting the new policy field.

### Update 2026-09-08 16:12
- Decisions: Integrate coworker commit 689faf5 (resource hooks/version 0.7.17) with all local archive work. Preserve callback API, tests, archive guards/retention and one transaction owner; no duplicated commits or manual inner rollback.
- Implementation: Resolved ObjectFactory/log conflicts; invoke resource callbacks after domain retention/audit inside resource_operation. Documented operation-level versus outer final callbacks. Added four composition/order/rollback/rejection tests. 76 focused library tests and all 63 ObjectFactory tests pass in isolated GraphDB/Redis.
- Open: Follow-up: oldap-api conflicts also resolved with user authorization; 236 API tests plus 22 subtests, real lifecycle/adoption and Capture contract checks pass. Library integration rechecked after Tower reset and intact. No library publication or runtime activation.
- Risks/Assumptions: Hooks remain trusted synchronous transaction-local code; nested failure poisons the outer scope. Original local tracked/untracked work retained in a named safety stash; no application data changes. Working changes remain uncommitted.

### Update 2026-09-08 00:08
- Decisions: Complete AS-04 source work with frozen wire contracts, source-scoped grants and unchanged guarded CRUD; AS-05 mixed ZIP export is next.
- Implementation: Added reviewed adoption/API/schema/docs and correlated receipts/audit; eliminated repeated vocabulary/ACL/QName validation and redundant read aggregation. 174 focused tests plus 42 subtests, all 61 ObjectFactory tests and real adoption/lifecycle/HTTP/concurrency/rollback/deletion regressions pass; 500 actions commit in 55.733 seconds. Build, OpenAPI/schema checks and final wheel verification pass. Evidence: FasnachtsPage docs/as-04.
- Open: AS-05–AS-09 export, admin UI, SALSAH, native Capture acceptance, production ACL/coordination migration and activation. Production depth/contention/latency acceptance remains necessary.
- Risks/Assumptions: With explicit user approval, backed up GraphDB Desktop cfg and changed heap from automatic 9 GiB to explicit 12 GiB, then restarted/verified service. No API timeout change, live RDF/ontology/role/policy change, CaptureApp edit or deployment. All disposable test repositories/caches removed; previous unrelated working changes preserved.

### Update 2026-09-07 23:42
- Decisions: Implement AS-04 reviewed structure adoption with project-neutral backend and no ontology/CaptureApp changes; retain all pre-existing work.
- Implementation: Added ArchiveAdoption, frozen request schema/runtime dependencies, source-derived ACL defaults, durable scoped receipts and operation-correlated atomic audit. Replaced redundant maximum-permission aggregation in resource reads with equivalent EXISTS threshold checking; 172 combined focused tests pass.
- Open: Complete isolated maximum-envelope and full ObjectFactory/lifecycle regression verification before marking AS-04 complete; subsequent export/UI/SALSAH/activation remain later steps.
- Risks/Assumptions: Local GraphDB at 9 GiB heap encountered free-heap guards/interrupted queries during large tests. User explicitly approved increasing to 12 GiB and clean restart; configuration backed up. No application RDF, role, policy or deployment change. The permission-query simplification still needs full real regression verification.

### Update 2026-09-07 22:59
- Decisions: Extend the existing opt-in transform transaction rather than introduce a new lifecycle API. Retain organisation read access, never automatically grant non-editorial archive writes, and permit narrow automatic retention in VIEW-only Mobile.
- Implementation: Added archive_transfer/archive_inventory, transaction hooks, expected-source conflict guard, signed context/revision/keyset paging and bounded visible identity selection. Fixed uncorrelated BNODE role joins in resource/summary CONSTRUCTs. Added cursor tests and lifecycle documentation; parent evidence records 187 focused/regression tests, 61/61 ObjectFactory tests and actual transfer/move/delete/note races/mobile replay.
- Open: AS-04 reviewed adoption; later mixed export, clients, production ACL/recovery acceptance and release. Omitted target grants do not invent editorial write access; clients still choose authorized editorial grants.
- Risks/Assumptions: Same writer gate/policy on all resource workers; ordinary rights still apply. Cursor keys are server-owned and shared; key rotation invalidates old cursors. Source models unchanged, no live data/cache mutation or package release.

### Update 2026-09-07 22:23
- Decisions: Complete AS-02 with project-neutral opt-in archive policy plus ordinary permissions; use durable non-expiring shared ownership with operator recovery, as accepted by the user.
- Implementation: Added archive_policy/archive_domain/archive_repository/mutation_gate, generic/subclass CRUD/transform and tree guards, structural audit and reference receipts, fresh state/grant checks, transaction outcome journaling, safe deletion without mandatory ACL annotations, and cache/store isolation. Added MkDocs policy/recovery guides and tests. Parent evidence: 129 focused/regression tests pass; real isolated role/replay/rollback/concurrency and 500-unit batch checks pass.
- Open: AS-03 retained-reference transfer/inventory; package release, ACL migration and production recovery acceptance. Existing full TestObjectFactory suite has one failure (test_change_permissions_A) reproduced with original HEAD source; 60 other tests pass.
- Risks/Assumptions: All resource writers share policy/gate; privileged raw SPARQL/model/admin writes require quiescence. Redis must provide acknowledged AOF persistence/noeviction without automatic failover. Crashed/uncertain writers require controlled recovery. No live application data/ontology or running cache changes.

### Update 2026-09-07 21:07
- Decisions: Introduce explicit resource transaction ownership; atomic composition does not imply serializable isolation. Nested failures mark the outer transaction for rollback even if caught; ambiguous commits are never retried.
- Implementation: Added resource_transaction/resource_operation/resource_query, integrated CRUD/transform and resource reads/searches, removed duplicated inner commits/aborts, and made unknown property assignment a typed value error. Added transaction documentation and 19 offline tests; 24 existing archive/staging/YAML/import tests pass. Real temporary-graph probe verifies composed creates, read-own-writes, rollback and commit.
- Open: AS-02 archive policy/domain guards and stronger writer coordination. Parallel conditional GraphDB claims both committed; recovery architecture decision is pending in FasnachtsPage docs/as-02. No package release or runtime activation.
- Risks/Assumptions: Connections are task-local; discard mutable instances after rollback. Unmanaged active transactions are rejected. The complete destructive GraphDB fixture suite was not run; probe graph cleaned and existing data untouched.

### Update 2026-09-07 20:36
- Decisions: Complete AS-01 using only two optional folder-owned Shared links; keep lifecycle/authorization in later backend steps and leave existing archive/media constraints intact.
- Implementation: Updated both Shared graph versions to 0.7.0; added defaultArchiveUnit and referencedMediaObject with four-language labels and documented semantics. Added eight SHACL/inference tests, updated the version assertion, and registered MkDocs documentation.
- Open: AS-02 domain/authorization implementation; coordinated ontology loading, package release and live model/cache acceptance remain pending.
- Risks/Assumptions: Fifteen offline ontology tests pass. Unchanged Fasnacht/Chama YAML models validate and resolve fixture links; removing additions/version metadata restores isomorphic old graphs. Setup copy is byte-identical. No database write or CaptureApp change.

### Update 2026-09-02 18:08
- Decisions: Provide a narrow additive transaction extension point instead of moving OLDAP lifecycle persistence into API-side follow-up writes.
- Implementation: Added an optional keyword-only before_commit callback to resource update, delete, and class transformation; callback failures abort the complete active transaction. Added update, delete, transform-success, and transform-rollback regressions without weakening the pre-existing exact transformed-type assertion, documented the contract, and prepared oldaplib 0.7.17.
- Open: Publish 0.7.17 and update oldap-api's dependency lock before deploying API 0.2.22.
- Risks/Assumptions: Calls that omit the callback retain their existing signatures and behavior. The hook is synchronous and intentionally owns no business semantics; callers must keep callback work transaction-local.

### Update 2026-08-27 00:07
- Decisions: Apply generic archive-tree behavior to direct and transitive project subclasses of `shared:ArchiveUnit`; preserve each resource's concrete project class and the existing HTTP contract.
- Implementation: Centralized dynamic resource-class ancestry checks, reused them in class transformation, archive import external-parent validation, and cycle-safe archive moves; added GraphDB-independent direct/transitive/rejection regressions and prepared oldaplib 0.7.16.
- Open: Publish 0.7.16, update oldap-api, restart it, and retry moving `chama:LobatoTrestlePhotograph1981` below the Ruedi Singer series.
- Risks/Assumptions: The active Chama ontology correctly declares `chama:PhotographicWork` as a `shared:ArchiveUnit` subclass; no API payload or response shape changes.

### Update 2026-08-26 01:01
- Decisions: Introduce a reusable bounded library batch instead of an API-owned SPARQL shortcut; preserve permission semantics and hide the distinction between absent and unreadable resources.
- Implementation: Added `ResourceInstanceFactory.read_summaries()` for up to 100 distinct IRIs and 32 properties, selected-property/type/role/Dating construction in one GraphDB query, concrete-model filtering, ordered omission semantics, public docstrings, performance-strategy context, focused query/result/bound regressions, and prepared version 0.7.15.
- Open: Publish the next oldaplib patch and install it in oldap-api before live endpoint verification.
- Risks/Assumptions: Datamodel classes are still resolved through the factory cache. Batch size is intentionally bounded; clients must chunk larger sets.

### Update 2026-08-26 00:38
- Decisions: Preserve the complete public `oldap:attachedToRole` map while folding its retrieval into the permission-checked resource CONSTRUCT; keep access-control variables separate from public role-map variables.
- Implementation: Construct all attached role/permission annotations with dedicated variables, extract them through one shared helper for factory/class/raw reads, and remove the standalone roles SELECT from every generic resource read path; added two-role extraction and one-query SPARQL regressions.
- Open: Publish the updated oldaplib release, install it in oldap-api, restart, and compare representative Chama/Fasnacht resource reads before starting search summaries.
- Risks/Assumptions: The optional role branch executes only after read access succeeds. Separate variables are essential because the access branch intentionally binds only the caller's effective maximum permission role.

### Update 2026-08-26 00:24
- Decisions: Preserve explicit-versus-inferred `rdf:type` semantics while removing the standalone API type query; carry explicit project-graph types as an internal marker in the permission-checked resource CONSTRUCT.
- Implementation: Added `ResourceReadResult` and `ResourceInstanceFactory.read_data()` with concrete-class selection, resolved properties, asserted type provenance, and filtered data; factored shared CONSTRUCT conversion; excluded the internal marker from public data; added focused single-CONSTRUCT regressions.
- Open: Publish the updated oldaplib release and consume it from oldap-api; then measure the live endpoint before designing search summaries/batching.
- Risks/Assumptions: The attached-role lookup remains a separate query to preserve the existing complete permission-map response; changing that contract is outside this optimization step.

### Update 2026-08-26 00:11
- Decisions: Optimize OLDAP from shared backend layers outward; keep list-prefix discovery connection-scoped instead of adding a stale process-global cache.
- Implementation: Documented the incremental performance roadmap; made list-node QName discovery idempotent per connection/project; removed full-list loading from generic resource reads; reused resolved projects in `DataModel.read()`; added GraphDB-independent query-count and retry tests.
- Open: Measure and simplify the single-resource API read path next, then add search summaries/batching before SALSAH-specific request reuse.
- Risks/Assumptions: A new connection intentionally refreshes list IDs; direct list mutations update the shared named Context through existing list construction. Cross-process freshness remains bounded by connection lifetime.

### Update 2026-08-13 23:58
- Decisions: Model a Staging subtree move as one parent-relation update on its root; keep descendants and physical media untouched, and enforce integrity in oldaplib rather than relying on a frontend.
- Implementation: Added `StagingFolderTree` with class/cardinality, same-area, system-folder, cycle, and portable sibling-name checks plus four GraphDB-independent unit tests.
- Open: Publish the next oldaplib patch release before deploying the dependent oldap-api endpoint.
- Risks/Assumptions: Direct-child collision inspection is bounded at 10,000 visible folders, matching the existing ZIP-import inventory boundary; normal resource update permissions remain authoritative. Four focused tests and Python compilation pass.

### Update 2026-08-12 00:04
- Decisions: Materialize resources exclusively from the concrete OLDAP class model, including inherited properties; ignore GraphDB-inferred predicates outside that model rather than extending the API shape from external ontology equivalences.
- Implementation: Added resolved direct/inherited property maps, applied model filtering to generic instance reads and factory materialization, and added regressions for both unknown-IRI `og:description` and known-QName `dcterms:description` equivalents of modeled `schema:description`.
- Open: Publish a patch release and update/restart oldap-api before retrying the affected Fasnacht archive draft GET.
- Risks/Assumptions: The user's independent uncommitted Schema.org refresh remains untouched. Two focused regressions and all nine GraphDB-backed oldap-api instance-read tests pass.

### Update 2026-08-10 23:18
- Decisions: Permit `xsd:anyURI` construction from another typed XSD value by validating its lexical string form; retain the existing URI/URN validation and do not weaken invalid-value handling.
- Implementation: Normalized non-`Xsd_anyURI` constructor inputs before scheme checks, added regression coverage for an URI-shaped `Xsd_string`, passed the focused GraphDB-backed unittest, and installed the local checkout editably into the oldap-api Poetry environment for local verification.
- Open: Restart the user-managed oldap-api process and retry the Staging cross-folder move. Publish a patch release before deployment so environments do not depend on a sibling editable checkout.
- Risks/Assumptions: ZIP-imported `shared:serverUrl` values currently exist as `xsd:string` although the active shape expects `xsd:anyURI`; lexical coercion is safe for valid URI strings and still rejects non-URI values.

### Update 2026-08-10 21:57
- Decisions: Keep Staging-to-archive generation project-neutral and advisory; omit technical folders, never create Item units from media, and bind two-step HTTP imports to the exact UTF-8 YAML hash.
- Implementation: Added deterministic Staging proposal generation with warning taxonomy, stable collision-resistant IDs, position preservation, alias/depth protections, exact SHA-256 binding, visible reference validation, tests, and synchronized public documentation/context.
- Open: Publish a future oldaplib version before installing the API/tools changes without sibling `PYTHONPATH`; exercise authenticated GraphDB preflight/apply against a development repository.
- Risks/Assumptions: Generator media counts reflect only caller-visible media. Create-only apply remains best-effort rollback across per-resource transactions and reports any rollback failure explicitly.

### Update 2026-08-10 21:35
- Decisions: Make oldaplib the sole authority for archive YAML version 1; separate the nested editable document from project-resolved import plans and require `ADMIN_CREATE` plus `DATA_UPDATE` on external ArchiveUnit attachment points.
- Implementation: Added canonical bundled schema, safe string/file parser and stable serializer, project resolution, read-only create-only preflight, parent-first apply with repeated checks and structured rollback outcomes, 11 focused unit tests, and MkDocs documentation.
- Open: Complete the oldap-tools adapter verification, then build Staging export and HTTP/UI preflight/apply workflows on the central API.
- Risks/Assumptions: Full GraphDB integration remains pending; focused tests are GraphDB-independent and preserve concrete OLDAP permission errors.

### Update 2026-08-09 23:20
- Decisions: Preserve the standalone `ExternalOntology.create_shacl()` contract while separating reusable SHACL triples from the surrounding SPARQL update and graph clauses.
- Implementation: Added `create_shacl_triples()`, changed `DataModel.create()` to embed that fragment instead of a complete nested `INSERT DATA`, added a GraphDB-independent parser regression test for datamodel creation with external ontologies, and prepared patch release 0.7.6.
- Open: Publish `oldaplib` 0.7.6, update and release `oldap-tools`, rebuild its image, and repeat the failed Fasnacht ontology replacement on `api.home.org`.
- Risks/Assumptions: The failed `--mode replace` invocation probably left the Fasnacht SHACL/OWL model graphs empty after committing their deletion; project data and list graphs are outside the failed creation transaction.

### Update 2026-08-09 00:00
- Decisions: Keep cross-resource linkage as an optional generic extension of `ResourceInstance.transform_class()`. Validate the source shape, object-property range, and maximum cardinality before mutation, then recheck source permission inside the transaction.
- Implementation: Added paired `link_from_iri`/`link_from_property` arguments, atomic relation insertion and source modification metadata, transaction-time `DATA_UPDATE` enforcement, and integration coverage transforming a media object into an archive unit's `shared:hasMediaObject` relation.
- Open: Publish the prepared oldaplib 0.7.5 patch release and update the oldap-api dependency lock before deploying the frontend workflow.
- Risks/Assumptions: Both resources are in the same project data graph. Callers that omit both link arguments retain the existing transform behavior.

### Update 2026-08-07 01:13
- Decisions: Preserve the XML Schema distinction between arbitrary-precision `xsd:integer` and signed 32-bit `xsd:int`; byte quotas and other legitimate large integers must not be narrowed during resource conversion.
- Implementation: Corrected `convert2datatype()` to construct `Xsd_integer` for `XsdDatatypes.integer` and added a focused regression test using 10,000,000,000 while retaining the `xsd:int` range failure.
- Open: Publish a new `oldaplib` release, update the dependency in `oldap-api`, restart the API, and retry the StagingArea permission update.
- Risks/Assumptions: This restores XML Schema semantics and is backward-compatible for existing in-range `xsd:integer` values; callers that incorrectly depended on receiving the narrower subclass may now observe the correct concrete type. Both focused regression tests and all 44 existing XSD datatype tests pass; the corrected local library also reads the live 10,000,000,000-byte BMG StagingArea quota as `Xsd_integer`.

### Update 2026-08-04 23:42
- Decisions: Make extracted-byte quota an explicit project-neutral property of each `shared:StagingArea`; require exactly one positive integer byte value so API admission fails closed and remains configurable per staging area.
- Implementation: Bumped the working Shared ontology to 0.6.0; added `shared:stagingQuotaBytes` to StagingArea SHACL and OWL; added GraphDB-independent structural coverage while preserving the concurrent archive/schema changes already present.
- Open: Existing staging-area instances must receive a quota before the 0.6.0 shape is deployed; deployment ordering must update data before or atomically with strict validation.
- Risks/Assumptions: The required property is intentionally a schema change. Values represent retained extracted original bytes, not compressed ZIP bytes or temporary derivative overhead.

### Update 2026-08-03 12:07
- Decisions: Make manually authored, project-neutral YAML the canonical bulk archive-tree input; allow multiple roots and create-only attachment below an explicit existing parent; keep Staging conversion as a later generator for the same format.
- Implementation: Documented the recursive YAML contract, stable project-IRI mapping, dry-run/preflight safety, additive extension boundary, rollback behavior, and the new `oldap-tools archive validate/load` workflow in `ArchivStruktur.md` and project context.
- Open: Exercise an applied import against a running development GraphDB, then design the Staging-to-YAML draft generator and its technical-folder collapse/report rules.
- Risks/Assumptions: Existing archive units are never updated or merged; explicit permission profiles remain outside YAML version 1 and new units use the authenticated user's normal default OLDAP role assignments.

### Update 2026-08-03 00:32
- Decisions: Keep project-domain objects and events separate from `shared:ArchiveUnit`; use optional multi-valued `schema:about` with local SHACL class `oldap:Thing`; introduce no Shared marker class, no global OWL domain/range, and no Fasnacht-ontology change.
- Implementation: Bumped `shared.trig` to 0.5.0; added `schema:about` to the ArchiveUnit SHACL shape and declared it as an OWL object property without global restrictions; extended structural and generic CRUD coverage and recorded the resolved boundary in `ArchivStruktur.md` and stable project context.
- Open: Design project-specific selection, display, and search behavior for `schema:about` separately; the Shared ontology deliberately does not enumerate eligible project classes.
- Risks/Assumptions: The relation is optional and additive, so existing archive units remain valid without migration. `oldap:Thing` is the universal OLDAP resource boundary; project UIs may narrow choices without changing the ontology. All five GraphDB-independent archive ontology tests pass; the live development repository was intentionally not modified.

### Update 2026-08-02 22:45
- Decisions: Complete archive Phase 3B with only optional multilingual `dcterms:provenance` and `schema:conditionsOfAccess`; keep access-condition prose strictly informational and separate from OLDAP permissions; defer the `shared:Item` versus Fasnacht object/media boundary to a dedicated design step.
- Implementation: Bumped `shared.trig` to 0.4.0; registered and declared both standard datatype properties in synchronized SHACL/OWL, extended structural and generic CRUD coverage, exposed both values in the FasnachtsPage archive-unit editor, and updated the architecture working document plus stable project contexts.
- Open: Resolve the precise relationship between `shared:ArchiveUnit` at `shared:Item`, `fasnacht:ArchiveObject`, and `fasnacht:ArchiveMediaObject` before integrating existing archive-domain records into the tree.
- Risks/Assumptions: Both fields remain optional and therefore require no migration. `schema:conditionsOfAccess` does not enforce access; any real restriction still requires explicit OLDAP role/DataPermission configuration. The five GraphDB-independent ontology structure tests pass; the live development repository was intentionally not modified or exercised.

### Update 2026-08-02 00:23
- Decisions: Permit explicit deletion of empty archive leaves while retaining the no-cascade rule; descriptive metadata does not make a leaf structurally non-empty, but children, linked media, and incoming references block deletion.
- Implementation: Documented the FasnachtsPage delete action, its child/media prechecks, confirmation, and the existing backend reference guard in `ArchivStruktur.md`.
- Open: None for the empty-unit delete workflow.
- Risks/Assumptions: The media precheck is application-side; the generic backend remains authoritative for incoming references and concurrent child creation.

### Update 2026-08-01 23:30
- Decisions: Complete archive Phase 3A as an additive, backward-compatible metadata extension; keep title and archive level as the only required fields, permit multiple linked record creators, and leave later description areas to Phase 3B.
- Implementation: Bumped `shared.trig` to 0.3.0; added synchronized SHACL/OWL declarations for one optional `oldap:Dating` lifetime, multilingual extent/medium, and multi-valued `dcterms:Agent` creators; extended structural and GraphDB CRUD coverage and updated `ArchivStruktur.md` plus project context.
- Open: Decide Phase 3B only from concrete needs for access conditions, custody history, arrangement, or physical location; design and review the later selective cleanup of Fasnacht archive test data separately.
- Risks/Assumptions: Existing resources remain valid because no required field or existing property contract changed. The later cleanup must target archive classes narrowly and must preserve stories and other project data.

### Update 2026-08-01 00:29
- Decisions: Close archive phase 2 with generic lazy tree reads and one small `ArchiveTree` mutation service; keep signatures, links, and per-node permissions unchanged on moves, and rely on the existing incoming-reference guard instead of adding cascade deletion.
- Implementation: Added ancestor-path traversal, cycle-safe parent moves, and optional position updates in `oldaplib/src/archive_tree.py`; expanded the GraphDB archive test for path loading, non-empty deletion rejection, move/order persistence, root moves, and cycle rejection; documented the completed cross-repository phase in `ArchivStruktur.md` and project context.
- Open: Phase 3 must choose the smallest concrete set of archival description metadata; concurrent cross-node moves remain an operationally unlikely case that may need stronger serialization if real multi-editor contention appears.
- Risks/Assumptions: Normal archive hierarchy mutations must use `ArchiveTree`; trusted direct `ResourceInstance` or GraphDB writers can still bypass domain services. The KISS implementation checks the target ancestry immediately before the normal transactional resource update rather than introducing a global tree lock.

### Update 2026-08-01 00:04
- Decisions: Close archive phase 1 using the existing generic `ResourceInstance` API; do not introduce a dedicated archive service or persistent example-data fixture for the MVP.
- Implementation: Added a GraphDB integration test that creates a Fonds/Series/File/Item reference tree and verifies generic create, read, update, filtered/sorted search, and delete behavior; made the object-factory test setup load the current `shared.trig` deterministically; marked phase 1 complete in `ArchivStruktur.md` and synchronized project context.
- Open: Phase 2 must decide and implement the actually required tree navigation, cycle-safe move, delete, and permission behavior.
- Risks/Assumptions: The technical reference tree is isolated test data created and removed at runtime; phase 1 intentionally does not enforce parent/child level sequences, cycle prevention, or non-empty-parent deletion rules.

### Update 2026-07-30 23:55
- Decisions: Keep the archive MVP in `shared.trig`; model archive levels as seven fixed named individuals rather than an OLDAP taxonomy; reuse `schema:name`, `schema:identifier`, `schema:description`, and `schema:position`; keep hierarchy, media links, and validation deliberately minimal.
- Implementation: Bumped the shared ontology to 0.2.0; added matching SHACL and OWL definitions for `shared:ArchiveUnit`, `shared:ArchiveLevel`, `shared:archiveLevel`, `shared:parentArchiveUnit`, and `shared:hasMediaObject`; added a GraphDB-independent structural test; updated the architecture working document and stable project context.
- Open: Add a small technical archive fixture and verify generic `ResourceInstance` CRUD/search; cycle-safe moves and other tree services remain phase 2 work.
- Risks/Assumptions: Archive signatures and sibling positions are optional and not automatically generated or uniqueness-checked; the base model permits multiple roots and media reuse; specialized hierarchy profiles remain intentionally deferred.

### Update 2026-07-30 19:10
- Decisions: Use `ArchivStruktur.md` as the architecture/development working document; record the generic archive unit, controlled level values, single-parent adjacency tree, and separation of archival description, staging, and digital media as proposals pending Phase 0 confirmation.
- Implementation: Expanded the document with architecture principles, a minimal model proposal, a five-phase incremental roadmap, deliberately deferred scope, numbered open questions, decision status, and ICA references; synchronized the stable project context.
- Open: Resolve the Phase 0 questions using a small real Fasnacht reference tree before implementing ontology or API changes.
- Risks/Assumptions: The model and vocabulary names remain provisional; strict hierarchy profiles, permission inheritance, RiC-O mapping, and specialized services are intentionally deferred until justified by concrete use cases.

### Update 2026-07-15 21:54
- Decisions: Support trusted direct GraphDB consumers without weakening service token validation or distributing JWT signing secrets outside token-issuing services.
- Implementation: Added `Connection(issue_access_token=False)` for credential authentication and authorization-context construction without JWT issuance, corrected the optional token interface type, added integration coverage, documented the public security boundary, and prepared version 0.7.1.
- Open: Publish version 0.7.1 and verify downstream direct consumers during their dependency upgrades.
- Risks/Assumptions: Tokenless connections are for trusted direct consumers only; HTTP clients must continue through the API bearer/refresh boundary.

### Update 2026-07-15 17:56
- Decisions: Separate media delivery capabilities from API authentication with a dedicated `typ=media` token, derived media audience, one-hour default lifetime, and independent signing key.
- Implementation: Extended `TokenSettings`, `TokenCodec`, `IConnection`, and `Connection` with media-token issuance/validation; migrated MediaObject lookup token generation and tests; documented the cross-repository API/media-server trust contract and deployment key isolation.
- Open: Deploy matching newly generated media and access keys to `oldap-api` and `oldap-mediaserver`, then continue browser integration in work package 6.
- Risks/Assumptions: Media URLs remain bearer capabilities until expiry and should not be logged or shared; access, refresh, media, and reset secrets must remain distinct.

### Update 2026-07-15 17:34
- Decisions: Complete authentication roadmap work package 5 with separate deployment-managed token secrets, exact credentialed CORS, secure refresh-cookie defaults, and fail-fast rendered configuration validation.
- Implementation: Coordinated OpenAPI cookie contract completion, `oldap-api` local secret cleanup, and `oldap-setup` inventory/template/Compose/Ansible wiring for all authentication variables; removed retired tracked JWT literals and marked work package 5 complete in the roadmap.
- Open: Work package 6 must update browser clients to memory-only access tokens with coordinated refresh and one retry; deployment requires newly generated out-of-tree secrets and service credentials.
- Risks/Assumptions: Removed legacy secrets remain recoverable from Git history and must not be reused; `SameSite=Lax` assumes authenticated clients remain on same-site OLDAP subdomains.

### Update 2026-07-15 17:18
- Decisions: Complete authentication roadmap work package 4 in `oldap-api` with a small explicit decorator and one request-scoped oldaplib `Connection`, keeping login, password-reset, status, health, and public routes outside the boundary.
- Implementation: Coordinated the migration of every protected API blueprint to centralized access-token validation, uniform cache-safe `401` challenges, route-registry enforcement, OpenAPI documentation, and updated authorization regressions; marked work package 4 complete in the architecture roadmap.
- Open: Continue with work package 5 deployment/operational configuration and work package 6 browser integration.
- Risks/Assumptions: Invalid credentials now consistently return `401` instead of the legacy `403`; valid identities lacking domain permissions continue to receive `403` from existing view logic.

### Update 2026-07-14 23:41
- Decisions: Support work package 3 without adding session state; allow the API to build a minimal authorization context from either `UserData` or `User`, and keep production secret validation strict while making the standalone GraphDB bootstrap executable self-contained.
- Implementation: Added `AuthorizationContext.from_user()` and changed the `connection.py` main utility to use the configured access secret or an ephemeral process-local bootstrap secret. Coordinated the completed login/refresh/logout API contract and marked authentication roadmap work package 3 complete.
- Open: Work package 4 must centralize bearer parsing across protected API views; deployment must supply token secrets and authentication service credentials before rollout.
- Risks/Assumptions: The ephemeral main-module key is intentionally limited to the interactive bootstrap process and is not a runtime fallback; production `Connection` construction still fails closed without `OLDAP_ACCESS_JWT_SECRET`.

### Update 2026-07-14 23:11
- Decisions: Complete authentication roadmap work package 2 with one focused token module; keep access requests stateless, derive a dedicated refresh audience, require separate access/refresh secrets of at least 32 bytes, and retain `Connection.jwtkey` only as a legacy media-token compatibility boundary.
- Implementation: Added typed `AuthorizationContext`, `TokenSettings`, `TokenCodec`, refresh claim values, purpose-specific token errors, strict issuer/audience/type/signature/expiry/claim validation, and 15-minute/14-day defaults. `Connection` now issues and consumes minimal access JWTs through the codec, exposes the credential-login `auth_version` for work package 3, and preserves `Connection.token`. Added focused token tests, updated connection tests and test-only secrets, and marked work package 2 complete.
- Open: Work package 3 must update `oldap-api` login/refresh/logout behavior and deployment must provide `OLDAP_ACCESS_JWT_SECRET` plus `OLDAP_REFRESH_JWT_SECRET`; the legacy `OLDAP_JWT_SECRET` is intentionally ignored.
- Risks/Assumptions: Existing media JWT generation still uses the access key via `Connection.jwtkey` until that separate token purpose is migrated; existing long-lived JWTs and deployments without the new secret names are intentionally incompatible with the new decoder.

### Update 2026-07-14 19:30
- Decisions: Complete authentication roadmap work package 1 without introducing token/API behavior; use optional `oldap:authVersion` with migration default `0`, immutable public model access, transactional automatic increments, and explicit optimistic revocation.
- Implementation: Extended the User ontology, `UserAttr`, `UserData`, and `User`; new users persist version `0`, credential/role/project/deactivation changes increment it once, `User.revoke_authentication()` detects stale concurrent state, and user changesets are fully cleared after successful updates. Added migration, increment, immutability, and conflict tests and marked roadmap work package 1 complete.
- Open: Work package 2 must introduce the minimal authorization context and purpose-specific access/refresh token codecs; `oldap-api` and clients still use the existing 24-hour JWT behavior.
- Risks/Assumptions: Missing production triples intentionally read as version `0`; global revocation is conflict-detectable rather than silently retrying, so callers must treat a stale-update failure as already changed state or reload before retrying.

### Update 2026-07-14 19:12
- Decisions: Record the proposed authentication redesign before implementation; use 15-minute access JWTs, 14-day refresh JWTs, and one per-user `oldap:authVersion` for global refresh revocation while keeping normal API requests stateless.
- Implementation: Added `docs/authentication_architecture_roadmap.md` with architecture boundaries, token/API contracts, cookie and secret policy, phased work packages, verification gates, rollout order, and accepted trade-offs; linked it from MkDocs and the project roadmap.
- Open: Confirm same-origin versus cross-origin deployment topology before choosing final cookie `SameSite` and CORS settings; no authentication code, ontology, API, deployment, or client behavior has been changed yet.
- Risks/Assumptions: Global logout intentionally affects all devices, already-issued access tokens remain valid for at most their short lifetime, and refresh-token rotation/reuse detection remains deferred unless durable per-device sessions become a concrete requirement.

### Update 2026-06-18 22:50
- Decisions: Add linked-resource search as an explicit filter type instead of overloading property names or changing existing `SearchFilter` semantics.
- Implementation: Added `LinkedResourceSearchFilter` with optional `linkedClass` and `checkLinkedPermissions`; extended `ResourceInstance.search()` to filter by one property on one directly linked resource inside the resource-selection subquery, with optional linked-resource `DATA_VIEW` checks. Centralized filter expression rendering and added query-generation plus GraphDB-backed tests for linked title filtering and linked permission behavior.
- Open: Downstream APIs that serialize search filters need a matching structured request shape before clients can use this through HTTP.
- Risks/Assumptions: Linked filters intentionally support only one hop; linked permission checks can reduce results when the linked resource lacks explicit `oldap:hasDataPermission` triples.

### Update 2026-06-15 12:01
- Decisions: Cover the new user password-reset timestamp and email-search behavior with focused user tests.
- Implementation: Added `test_password_reset_request_at_lifecycle()` for setting, replacing, deleting, and rereading `oldap:passwordResetRequestAt`; extended user search tests with `email`, missing-email, and email injection cases.
- Open: Re-run the focused tests once the local test GraphDB contains the expected bootstrap user `fornaro` before `TestUser.setUp()` creates its unprivileged connection.
- Risks/Assumptions: Tests assume user email search uses the canonical stored `schema:email` property and that `passwordResetRequestAt` is a normal optional `UserAttr` value updated through the generic model changeset.

### Update 2026-06-14 22:33
- Decisions: Make `ResourceInstance.search()` paginate at resource level instead of SPARQL result-row level.
- Implementation: Refactored search query generation to use an inner resource subquery with distinct/grouped `?res`, aggregated sort/score keys, stable `ORDER BY`, and `LIMIT/OFFSET` before the outer include-property projection. Bound non-included sort properties for both sorting and result projection, kept unbound sort values last, and made `Context.iri2qname()` return `None` for known namespaces with invalid QName fragments so `QueryProcessor` keeps such values as `Iri`.
- Open: None.
- Risks/Assumptions: Multi-valued sort properties are ordered by `MIN` for ascending and `MAX` for descending; this gives deterministic resource-level ordering but collapses multiple sort values to one ordering key.

### Update 2026-06-14 22:20
- Decisions: Document the `ResourceInstance.search()` paging defect before changing production query generation.
- Implementation: Added focused query-generation tests showing that non-included `sortBy` properties are projected/ordered without being bound, that result deduplication happens after SPARQL `LIMIT`, and an expected-failure test for resource-level paging via subquery.
- Open: Superseded by the 2026-06-14 22:33 implementation entry.
- Risks/Assumptions: Current Fasnacht data only mildly reproduces include-property row inflation, but multi-valued properties can still produce short or shifted pages.

### Update 2026-06-10 00:39
- Decisions: Treat `shared:mediaAccessMode` as the required discriminator for local/external `shared:MediaObject` records while keeping optional external link fields scalar in media-object lookup results.
- Implementation: Extended `ResourceInstance.get_media_object_by_id()` and `get_media_object_by_iri()` to return `shared:mediaAccessMode`, `shared:mediaUrl`, and `shared:thumbnailUrl` as scalar values; made JWT payload path handling tolerant of external media without `shared:path`; updated MediaObject fixtures and tests for the new shared ontology shape.
- Open: Apply the corresponding `oldap-api` response/OpenAPI updates in a separate step.
- Risks/Assumptions: Existing persisted media objects must be migrated with `shared:mediaAccessMode "local"` before the stricter shape is enforced.

### Update 2026-06-09 00:09
- Decisions: Support lifecycle transitions by atomically reclassifying a resource while keeping its IRI, instead of delete/create.
- Implementation: Added `ResourceInstance.transform_class()` to preserve a caller-specified base class, remove source-specific properties, insert target properties, replace role attachments when supplied, update modification metadata, and commit all changes in one GraphDB transaction. Added an objectfactory regression test that transforms `shared:MediaObject` into `test:MediaLibraryEntry`.
- Open: Wire the new library operation through API clients/frontends for Staging-to-Archive publishing.
- Risks/Assumptions: The caller must supply a suitable `preserve_class`; payload properties targeting preserved base properties are rejected to keep technical media metadata stable.

### Update 2026-06-08 21:17
- Decisions: Preserve `shared:assetId` as a one-to-one identifier for a single `shared:MediaObject` instead of supporting duplicate media-object bindings.
- Implementation: Removed the plural asset lookup/count APIs and their focused tests; documented the unique asset-ID rule in `codex.md`.
- Open: Enforce the uniqueness rule at the ontology/API/data-validation boundary if duplicate asset IDs can still be created or imported.
- Risks/Assumptions: Shared physical storage should be modeled explicitly if needed.

### Update 2026-06-07 01:16
- Decisions: Model generic shared media staging in `shared.trig` with a StagingArea boundary, folder hierarchy, media staging subclass, and named-individual workflow states instead of project-specific hierarchical lists.
- Implementation: Corrected Staging SHACL/OWL typos in `oldaplib/ontologies/shared.trig`: fixed `shared:mediaPath`, `sh:targetClass shared:StagingMediaObject`, `sh:class shared:StagingFolder`, `sh:node shared:MediaObjectShape`, French `new` label, and added `shared:inStagingArea` links. Added `shared:checksum` to MediaObject shape/ontology as optional string metadata and removed redundant duplicate prefix declarations at the top of the TriG file.
- Open: Align FasnachtsPage and project-specific ontologies with the generic shared staging vocabulary after the shared ontology is loaded.
- Risks/Assumptions: Assumes `sh:node shared:MediaObjectShape` is the correct OLDAPlib superclass-shape pattern for `shared:StagingMediaObject`; the TriG parses successfully with rdflib.

### Update 2026-05-28 17:00
- Decisions: Dating sort order should place resources with bound normalized Dating values before resources without such values for both ascending and descending sorts.
- Implementation: Updated `ResourceInstance.search()` Dating `ORDER BY` generation to sort by `!BOUND(?*_start)` before normalized start/end values; added an objectfactory regression test for optional Dating values staying last in ascending and descending order.
- Open: Fasnacht event records such as `Fasnacht 1915` currently have no `fasnacht:dating` triple, so backend sorting cannot derive their chronological position until the data is populated or migrated.
- Risks/Assumptions: Assumes callers prefer dated records first and undated records last for explicit Dating sorts.

### Update 2026-05-28 14:27
- Decisions: Hierarchical resource search should match the selected list node itself and all descendant nodes, scoped to the selected list.
- Implementation: Changed `ResourceInstance.search()` HList SPARQL to bind `skos:inScheme` and filter resource-node indices inside the selected node interval; added a focused query-generation regression test.
- Open: None.
- Risks/Assumptions: The generated query still reuses property-fragment variable names, matching the existing search builder behaviour.

### Update 2026-05-26 12:14
- Decisions: Treat `rdf:type` from reasoned reads as an unordered set and choose the concrete resource class deterministically in `ResourceInstanceFactory`.
- Implementation: Added QName type extraction and factory-local resource-class selection that filters known project/shared classes and removes inferred superclass candidates.
- Open: Existing debug `print`/`pprint` output in `objectfactory.py` remains present from prior local changes and can be cleaned separately.
- Risks/Assumptions: Ambiguous multiple concrete classes now raise `OldapErrorInconsistency` instead of selecting one arbitrarily.

### Update 2026-05-26 11:42
- Decisions: Restored Dublin Core Elements as a predefined context namespace because reasoning can expose inferred `dc:*` predicates from `dcterms:*` subproperties.
- Implementation: Added `dc -> http://purl.org/dc/elements/1.1/` to `Context` default prefix and inverse namespace mappings.
- Open: None.
- Risks/Assumptions: `read_data()` intentionally reads inferred triples; callers may now receive `dc:type` alongside explicit `dcterms:type` where reasoning materializes the superproperty.

### Update 2026-05-26 01:00
- Decisions: Added a lightweight list-node context preparation API to `OldapList` instead of relying on full list reads as a side effect.
- Implementation: Introduced `OldapList.ensure_list_node_context()` to register all `L-<list_id>` prefixes for a project's hierarchical lists without loading their nodes.
- Open: Call sites such as resource/data-model read paths still need to invoke the new method before processing triples that may contain concrete list-node IRIs.
- Risks/Assumptions: The method assumes list IRIs are readable as project-prefixed QNames after registering the project namespace in the shared context.

### Update 2026-05-14 02:12
- Decisions: Added required project context files before making packaging changes.
- Implementation: Created `codex.md` with concise project context and initialized this technical work log.
- Open: `pyproject.toml` cleanup still in progress.
- Risks/Assumptions: Context is inferred from current repository files and may need refinement as project conventions evolve.

### Update 2026-05-14 02:13
- Decisions: Modernized package metadata with PEP 621 `[project]` fields and kept Poetry-only packaging controls under `[tool.poetry]`.
- Implementation: Split runtime dependencies from optional `docs` and `dev` dependency groups, removed redundant `[tool.mkdocs]` config, updated the build backend requirement to Poetry Core 2, and synchronized `oldaplib/src/version.py` with the package version.
- Open: Fresh local installs that need documentation or release tooling should use `poetry install --with docs,dev`.
- Risks/Assumptions: License was normalized to the SPDX expression `AGPL-3.0-only`, matching the previous "GNU Affero General Public License version 3" wording.

### Update 2026-05-14 02:20
- Decisions: Standard ontologies are not runtime package data for distribution artifacts.
- Implementation: Excluded `oldaplib/ontologies/standard` from Poetry builds.
- Open: Rebuild release artifacts before publishing so the old included standard ontology files disappear from `dist`.
- Risks/Assumptions: Code paths that need standard ontologies must obtain them outside the installed package, for example through repository checkout data or the existing ontology download workflow.
