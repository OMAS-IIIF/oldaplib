# Library merge preparation — 2026-11-03

This records a local checkpoint on `migration/jena`, not final 1.0 approval.
The coordinated sequence is in sibling setup's
[release plan](../../../oldap-setup/docs/jena-1.0-merge-plan.md).

## Scope and review

The checkpoint captures the previously uncommitted Jena adapter, RDF 1.2 grants,
archive/model reads and writes, configured fulltext, hierarchy/inverse-path query
helpers, read-side validation optimizations, Java service, backup tooling,
conversion scripts, tests and migration evidence. Existing public function
argument lists in modified Python modules were compared with HEAD by AST: no
existing public signatures changed. New methods/fields and changed semantics
still require consumer acceptance; this is not a blanket compatibility guarantee.

Changed Python files parse successfully. Candidate text files were checked for
private-key/JWT/token patterns; no matches were found. Migration evidence and
synthetic fixture files are retained, but local distributions, generated data,
private service configuration and wheel output are outside the repository.
The service source set is explicit and reuses the transaction engine rather than
forking it. Authorization remains separate from query entailment; explicit BEGIN
refusal retries do not replay UPDATE/COMMIT or uncertain admission.

Two small review corrections: move the property-path import below PropertyClass's
module docstring so Python documentation tools can see it; identify the semantics
profile's old status paragraph as historical. Legacy inverse compatibility still
exists; do not describe all OWL inverse support as removed.

## Verification

- Focused Jena/construct/model-scope/XSD-schema/archive/transaction and offline
  backup suite: 198 passed, 14 subtests. RDFLib deprecation warnings remain.
- Additional `test_xsd*.py` run: 47 passed. **This selection included 44 GraphDB
  integration tests**, whose setup clears and rewrites the designated `test:test`
  graph on the default local endpoint `localhost:7200`. It was not fully offline;
  no production endpoint was selected. Do not repeat a broad test glob on a shared
  database. The XSD-schema tests overlap the focused suite above.
- After the docstring import correction, entailment/model-scope tests: 25 passed.
- `poetry check`, Python syntax parsing and `git diff --check` pass.
- Wheel builds successfully, contains new Jena modules and seed ontologies, and
  excludes test packages. Imports were checked from an extracted wheel outside
  the checkout using the existing API test environment's dependencies.
- The private Java service builds against the checksum-pinned Fuseki 6.2.0
  distribution with JDK 25. The offline legacy converter passes all eight CLI
  checks (plain/gzip input, bounds, malformed input, output non-overwrite and
  source preservation).
- Fresh service acceptance results are recorded separately in
  `jena-merge-service-results.json`; all data is synthetic and storage is owned
  by that probe. This is a separate local instance, not the installed home service.

The library's own venv currently has no pytest. The focused run used
`../oldap-api/.venv/bin/python -m pytest` from this checkout. Make pytest an
explicit reproducible development dependency during release packaging; the
current successful run is not evidence of a clean standalone dev installation.
No broad legacy suite or production migration was run as part of this checkpoint.

## Remaining release work

Keep 0.7.29 until the coordinated version/dependency change. Do not publish this
wheel under that existing version: it is a local build artifact only. Before 1.0,
resolve editable/0.7-only dependencies, verify consumers with installed packages,
retain the actual deployed GraphDB baseline and complete final home acceptance.
Remote main has no independent commits at preparation time, but repeat fetch and
merge simulation before the actual merge. Main, tags and remote branches have
not been changed by this checkpoint.
