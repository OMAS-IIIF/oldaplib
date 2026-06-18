# CODEX_LOG

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
