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
