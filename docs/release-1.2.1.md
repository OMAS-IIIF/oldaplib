# OLDAP 1.2.1 - taxonomy model read compatibility

Fix DataModel.read failing on generated taxonomy node shapes with sh:hasValue
when a project includes taxonomies and reifier definitions. OldapList-managed
shapes are excluded from the editable ResourceClass parser; stored RDF and
application model semantics are unchanged.

The mixed taxonomy/resource/reifier RDF round-trip test reproduces the original
failure and verifies that domain classes and reifier policies still load. The
local TGB import and persisted RDF readback passed; repeat import plans no changes.

Release order: publish oldaplib 1.2.1 on PyPI, then API/tools 1.2.1 requiring
oldaplib >=1.2.1,<2.0.0. Final AMD64/ARM64 images pin oldaplib exactly to 1.2.1
through the existing source-matched release builder. Retain accepted third-party
constraints. No deployment, database migration or changes to latest tags.

Publication receipts are recorded in release-1.2.1-results.json after verification.
Private build evidence: ~/Library/Application Support/OLDAP/releases/20261115-1.2.1/.

## Verified publication

All three source commits and annotated v1.2.1 tags are pushed. Package wheel and
sdist files are published on PyPI and their SHA-256 hashes verified. API/tools
versioned Docker images are published for linux/amd64 and linux/arm64, including
build attestations. Registry manifests match the accepted images; latest is unchanged.

Installed library/API regressions: 99 passed per architecture. Packaged Jena
transaction, persistence, namespace replacement and network-isolation checks pass
on both architectures. Both tools images parse the TGB ontology, seven taxonomy
files and route-point reification. The image-built library has 155 runtime/data
files identical to the PyPI wheel. Source checks: library 34 passed / 25 opt-in
integration skipped; API 23 passed; tools 186 passed / 1 skipped / 7 subtests.
The isolated published-library wheel checks pass (19 tests).

No deployment was performed and no active environment was restarted. This release
does not change deployment selections. Exact source commits, package hashes and
image digests are in [the publication receipt](release-1.2.1-results.json).
