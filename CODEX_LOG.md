# CODEX_LOG

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
