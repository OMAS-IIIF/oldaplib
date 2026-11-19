# oldaplib 1.2.2: coordinated superproperty support

Support complete sets of shared predicate superproperties in ordinary properties
and reifier fields, with ownership checks, stale-write protection and dependent
cache invalidation. HTTP retains strings for singleton parents and emits sorted
arrays for multiple parents. YAML accepts scalar, array and null inputs, and
compares parent sets without order sensitivity.

Compatibility: oldaplib 1.2.2 changes the Python `subPropertyOf` getter from a
scalar IRI to an ObservableSet (or None). Scalar setter inputs remain supported.
This is not a strictly backwards-compatible Python patch. Upgrade consumers
together: API 1.2.3 and tools 1.2.2 require oldaplib >=1.2.2,<2.0.0. Other Python
callers must adapt scalar reads to set iteration. Existing pinned images do not
change when the library is published. Client UIs need the matching array contract
before editing multiple parents. No frontend release or deployment is included.

Release scope: library wheel/sdist on PyPI, updated tools package and versioned
AMD64/ARM64 API/tools images. API wheel is only a Docker build input. No ontology
migration, service restart, deployment selection update or latest-tag change.

## Verified publication

Source commits and final tags are pushed. Library/tools wheels and source archives
are published on PyPI with verified SHA-256 hashes. API/tools multiarch images are
published and registry manifests match the accepted images; latest is unchanged.

Library: 223 source tests passed, three optional checks skipped; 88 tests passed
against the built wheel. API: 36 focused tests and OpenAPI validation passed.
Tools: all 201 tests plus seven subtests passed, including disposable native Jena
round trips. Installed API/library: 125 tests passed on each architecture. Packaged
Jena transaction, persistence, replacement and isolation checks passed on both,
as did tools CLI/TGB taxonomy and reifier checks. No service-backed legacy suite
was run against a live database.

Initial test setup issues were resolved: the API fixture now loads actual local
system/shared RDF without Redis, and the LangString expectation includes the
existing reifier field path. Some legacy datatype suites require a configured
service and were excluded after the network guard rejected their setup.

No deployment, service restart, frontend update or deployment-selection change
was performed. [Publication receipt](release-1.2.2-results.json).
