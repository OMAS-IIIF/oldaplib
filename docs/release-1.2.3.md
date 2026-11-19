# oldaplib 1.2.3

Fix attaching a property with existing shared superproperties to a persisted
resource class. Adopting inherited metadata now preserves the pending CREATE
action instead of converting it into MODIFY and rejecting it as stale.
Shared predicate declarations remain unchanged; normal subsequent edits persist.

Regression reproduces the original failure with one and multiple parents. The
isolated suite passes 68 tests and two subtests with network access blocked;
seven opt-in integration tests are skipped. No public API or data migration is
required. API 1.2.4 and tools 1.2.3 adopt this patch.

Publication and production deployment completed on 2026-11-20. Source/tags,
PyPI packages and AMD64/ARM64 images are verified. Only production API/identity
changed; home and business data are unchanged. See the adjacent release-results
JSON for exact digests, tests and rollback provenance.
