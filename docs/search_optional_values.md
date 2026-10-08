# Optional property comparisons in structured search

`ResourceInstance.search` keeps property bindings optional so that a resource
missing one property can still satisfy another branch of an OR filter. Every
ordinary value-comparison branch now explicitly requires `BOUND(?value)`.
The guard belongs inside that branch, not around the complete filter.
`NOT_EXISTS` remains an absence test; Dating comparisons retain their existing
normalized interval handling. The same expression builder serves linked-resource
comparisons, result pages and `countOnly`.

## Regression found on 2026-10-07

A live direct-parent search in Chama returned both the expected child and the
archive root, even though the root has no parent triple. This reproduced directly
with the generated SPARQL against local GraphDB, independently of Flask and SALSAH.
The combination of OPTIONAL and equality admitted the unbound root; adding an
explicit BOUND condition removed it. Making the triple mandatory also removed it,
but would incorrectly exclude valid alternatives in OR searches. No archive-data
change or special handling of project identifiers is needed.

Focused query-generation/model tests: 18 passed. Read-only live checks cover an
existing parent, nonexistent parent, NOT_EXISTS roots, OR and AND, each sorted and
unsorted, with result/count agreement (20 queries). Repeated checks through the
API's installed Python environment passed after the guarded local API restart.
No destructive integration suite or repository reload was run.

## Local activation

Built and installed an unpublished development wheel with the existing version
0.7.25 in the native API environment, then used `make restart` in oldap-api.
The source contains this fix; the published 0.7.25 package does not. Publish a new
normal oldaplib release and update downstream locks before external deployment.
No remote service, dependency constraint or lockfile was changed here.
