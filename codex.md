# OLDAPlib Project Context

OLDAPlib is the Python library layer for OLDAP, a linked-open-data middleware and REST API backend. It models OLDAP projects, users, permissions, lists, resource classes, property classes, XML Schema datatypes, RDF/SHACL structures, and GraphDB/Redis-backed persistence helpers.

## Repository State

- Package source lives under `oldaplib/src`, with ontology fixtures in `oldaplib/ontologies`, test data in `oldaplib/testdata`, and unit/integration tests in `oldaplib/test`.
- Documentation is built with MkDocs from `docs` and `mkdocs.yml`; API pages use mkdocstrings.
- Poetry is the package/build manager. `pyproject.toml` carries package metadata, dependency declarations, dependency groups, build-system configuration, and bump-my-version settings.
- Tests are driven through `make test`/`make test-secure` and expect GraphDB at `localhost:7200`; Redis is configured through `OLDAP_REDIS_URL`.

## Architecture And Style

- The project is an object-oriented Python 3.12 library with explicit domain classes for RDF resources, SHACL/data-model objects, users, projects, permissions, and XSD datatypes.
- Runtime code relies on `rdflib`, `requests`, `pyshacl`, `redis`, `pyjwt`, and validation/datatype helpers such as `xmlschema`, `isodate`, `yamale`, `validators`, `shapely`, and `convertdate`.
- Code favors typed, maintainable domain objects and structured docstrings. Public classes and functions should document purpose, inputs, outputs, raised errors, and important side effects.

## Current Roadmap / Next Steps

- Keep packaging metadata aligned with modern Poetry/PEP 621 conventions.
- Keep documentation and API doc generation synchronized with public API changes.
- When changing behavior around GraphDB, Redis, ontologies, or public model classes, update tests and relevant docs together.
