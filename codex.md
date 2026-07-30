# OLDAPlib Project Context

OLDAPlib is the Python library layer for OLDAP, a linked-open-data middleware and REST API backend. It models OLDAP projects, users, permissions, lists, resource classes, property classes, XML Schema datatypes, RDF/SHACL structures, and GraphDB/Redis-backed persistence helpers.

## Repository State

- `ArchivStruktur.md` is the architecture and development working document for OLDAP archival organization. Its current direction uses one generic `shared:ArchiveUnit`, a controlled archive-level property, and a single-parent adjacency tree while keeping archival description separate from staging and digital `shared:MediaObject` representations. Strict hierarchy profiles, permission inheritance, and standards mappings remain deferred until concrete use cases justify them.
- Authentication roadmap work packages 1–5 are complete: users support persisted `oldap:authVersion` revocation state, `authentication.py` provides strictly separated access, refresh, and media tokens, `oldap-api` implements login, refresh-cookie renewal, global logout, and centralized Bearer authentication, and `oldap-setup` supplies validated production secrets plus exact credentialed CORS/cookie configuration. Media capabilities use `typ=media`, audience `oldap-api-media`, a one-hour default lifetime, and `OLDAP_MEDIA_JWT_SECRET`; access/refresh/media keys must be distinct. The executable `connection.py` bootstrap uses an ephemeral access key when no production key is configured.
- Trusted direct GraphDB consumers that do not expose bearer tokens can use `Connection(issue_access_token=False)` to authenticate credentials and construct an authorization context without access to JWT signing secrets; `Connection.token` then remains `None`.
- `oldaplib/ontologies/shared.trig` now defines shared media staging vocabulary for generic OAIS-style ingest preparation: `shared:StagingArea`, `shared:StagingFolder`, `shared:StagingMediaObject`, `shared:StagingStatus` named individuals, and optional media `shared:checksum`.
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
- Code favors typed, maintainable domain objects and structured docstrings. Public classes and functions should document purpose, inputs, outputs, raised errors, and important side effects.

## Current Roadmap / Next Steps

- Resolve the Phase 0 questions in `ArchivStruktur.md` against a small real Fasnacht reference tree before implementing the shared archive ontology MVP.
- Continue the authentication roadmap with work package 6 (browser integration).
- Keep packaging metadata aligned with modern Poetry/PEP 621 conventions.
- Keep documentation and API doc generation synchronized with public API changes.
- When changing behavior around GraphDB, Redis, ontologies, or public model classes, update tests and relevant docs together.
