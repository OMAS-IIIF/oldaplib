# OLDAPlib Project Context

OLDAPlib is the Python library layer for OLDAP, a linked-open-data middleware and REST API backend. It models OLDAP projects, users, permissions, lists, resource classes, property classes, XML Schema datatypes, RDF/SHACL structures, and GraphDB/Redis-backed persistence helpers.

## Repository State

- `oldaplib/ontologies/shared.trig` version 0.6.0 implements the archive model in both SHACL and OWL: one generic `shared:ArchiveUnit`, seven fixed `shared:ArchiveLevel` named individuals, a single-parent adjacency tree, explicit media links, optional description metadata, and optional multi-valued `schema:about` links to `oldap:Thing`. `shared:Item` is the smallest archival description unit rather than a replacement for project-domain objects or events. No shared marker class and no global OWL range are introduced for subjects; project-specific target selection stays outside the Shared ontology. Archive phases 1–3 are complete, and the generic relation foundation for Phase 4 is present. Generic CRUD/search remains the default, while `oldaplib/src/archive_tree.py` adds only ancestor-path traversal and cycle-safe moves. Access-condition text remains descriptive and never replaces OLDAP permissions. `ArchivStruktur.md` records the decisions and incremental roadmap; strict hierarchy profiles, physical location, permission inheritance, and standards mappings remain deferred.
- Authentication roadmap work packages 1–5 are complete: users support persisted `oldap:authVersion` revocation state, `authentication.py` provides strictly separated access, refresh, and media tokens, `oldap-api` implements login, refresh-cookie renewal, global logout, and centralized Bearer authentication, and `oldap-setup` supplies validated production secrets plus exact credentialed CORS/cookie configuration. Media capabilities use `typ=media`, audience `oldap-api-media`, a one-hour default lifetime, and `OLDAP_MEDIA_JWT_SECRET`; access/refresh/media keys must be distinct. The executable `connection.py` bootstrap uses an ephemeral access key when no production key is configured.
- Trusted direct GraphDB consumers that do not expose bearer tokens can use `Connection(issue_access_token=False)` to authenticate credentials and construct an authorization context without access to JWT signing secrets; `Connection.token` then remains `None`.
- `oldaplib/ontologies/shared.trig` defines shared media staging vocabulary for generic OAIS-style ingest preparation: `shared:StagingArea`, `shared:StagingFolder`, `shared:StagingMediaObject`, `shared:StagingStatus` named individuals, optional media `shared:checksum`, and mandatory positive integer `shared:stagingQuotaBytes` on every staging area.
- Manual archive-tree creation is now specified as a project-neutral recursive YAML workflow in `oldap-tools`. Multiple roots support one fonds per association without domain-specific schema fields; stable YAML IDs map to project IRIs. Loading is create-only, defaults to preflight, and may attach a new top-level YAML subtree below an explicitly named existing ArchiveUnit. A later Staging generator must emit this same format rather than introduce a second importer.
- `shared:MediaObject` distinguishes locally managed and externally referenced media through required `shared:mediaAccessMode` values `local` and `external`; external links can use optional `shared:mediaUrl` and `shared:thumbnailUrl`, while IIIF references continue to use `shared:serverUrl`, `shared:assetId`, and `shared:protocol`.
- `shared:assetId` is treated as a one-to-one identifier for a single `shared:MediaObject`; shared physical storage or reuse should be modeled explicitly instead of allowing multiple media objects with the same asset ID.
- `ResourceInstance.search()` applies API paging at distinct-resource level: an inner resource-selection subquery performs filtering, sorting, and `LIMIT/OFFSET`, while the outer query projects requested properties for the selected resources. It also supports one-hop linked-resource filters through `LinkedResourceSearchFilter`, optionally requiring `DATA_VIEW` permission on the linked resource.
- `ResourceInstance.transform_class()` supports atomic resource lifecycle transitions that keep the same IRI, preserve a caller-specified base class such as `shared:MediaObject`, remove source-specific properties, add target properties, optionally replace role attachments, and update modification metadata in one transaction.
- Package source lives under `oldaplib/src`, with ontology fixtures in `oldaplib/ontologies`, test data in `oldaplib/testdata`, and unit/integration tests in `oldaplib/test`.
- Documentation is built with MkDocs from `docs` and `mkdocs.yml`; API pages use mkdocstrings.
- Poetry is the package/build manager. `pyproject.toml` carries package metadata, dependency declarations, dependency groups, build-system configuration, and bump-my-version settings.
- Tests are driven through `make test`/`make test-secure` and expect GraphDB at `localhost:7200`; Redis is configured through `OLDAP_REDIS_URL`.

## Architecture And Style

- The project is an object-oriented Python 3.12 library with explicit domain classes for RDF resources, SHACL/data-model objects, users, projects, permissions, and XSD datatypes.
- Runtime code relies on `rdflib`, `requests`, `pyshacl`, `redis`, `pyjwt`, and validation/datatype helpers such as `xmlschema`, `isodate`, `yamale`, `validators`, `shapely`, and `convertdate`.
- Datatype dispatch preserves XML Schema numeric ranges: `xsd:integer` uses arbitrary-precision `Xsd_integer`, while `xsd:int` alone uses the signed 32-bit `Xsd_int` subtype.
- Code favors typed, maintainable domain objects and structured docstrings. Public classes and functions should document purpose, inputs, outputs, raised errors, and important side effects.

## Current Roadmap / Next Steps

- Integrate the generic `schema:about` relation into project-specific workflows only when their target selection and presentation are explicitly designed; keep hierarchy profiles, physical location, and permission inheritance deferred.
- Derive draft archive YAML from Staging folder trees using explicit collapse/review rules, after the manual YAML workflow has been exercised with representative structures.
- Continue the authentication roadmap with work package 6 (browser integration).
- Keep packaging metadata aligned with modern Poetry/PEP 621 conventions.
- Keep documentation and API doc generation synchronized with public API changes.
- When changing behavior around GraphDB, Redis, ontologies, or public model classes, update tests and relevant docs together.
