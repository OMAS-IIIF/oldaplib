# CODEX_LOG

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
