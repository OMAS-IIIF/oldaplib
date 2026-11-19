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

Validation and immutable publication evidence will be recorded after completion.
