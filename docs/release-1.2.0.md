# OLDAP 1.2.0 — assertion annotations

This coordinated minor release adds named reifier shapes to project models,
YAML authoring/import/export, typed annotation instance lifecycle and history,
and explicit annotation filters/projection in searches. OLDAP performs validation.
API and tools require oldaplib >=1.2.0,<2.0.0; released images pin exactly 1.2.0.

Existing read/search query text and counts are preserved. The final review
includes cached model reconstruction, authorization revocation, graph ownership,
transaction completion and malformed-input regressions. See the library's
`docs/reification-final-check.md` for the source review and its scope limits.

All three reviewed feature branches were fast-forwarded into main and tagged
v1.2.0. oldaplib's wheel and sdist are published on PyPI with verified hashes.
API/tools publication uses the existing wheel-only AMD64/ARM64 pipeline and the
previously accepted third-party constraints. Latest/existing tags are preserved.

Home rollout includes the nine additive ontology triples for AssertionAnnotation,
ReifierShape and historyReifierSnapshot. Save the existing oldap:onto graph and
exact DELETE DATA rollback before applying. Existing model/data graphs are not
replaced. Jena service 1.1.0 already installed on home supplies the required
capabilities; the backend binary is not changed by this release.

External/blank/shared reifiers remain read-only. Annotated transformations,
instance-data YAML v1 and specialized annotated hierarchy restores explicitly
reject unsupported operations. Rollback to an older writer after annotations
have been created requires preserving data and preventing incompatible writes.

Release evidence is retained privately under
`~/Library/Application Support/OLDAP/releases/20261114-1.2.0/`.
Publication and home acceptance are complete. Production is outside this rollout.

## Publication and home result

Both API and tools v1.2.0 images are published for AMD64 and ARM64. Installed
API/library regressions: 99 passed on each architecture. Packaged Jena identity,
transaction, persistence, restart and network-isolation acceptance passed on both.
Tools CLI and travel-YAML syntax/field checks passed on both architectures.
All 155 library runtime/data files in the image build match the published PyPI
wheel byte-for-byte; wheel builder metadata and an excluded HTTP scratch file differ.

Home now runs API/library 1.2.0; the on-demand tools selection also uses 1.2.0.
Only API and identity container IDs changed. Jena, Redis, Caddy and all three
frontends retained their container IDs. Public health/status and Fasnacht return
200; health reports Jena reachable and v1.2.0. The new model endpoint rejects
anonymous access with 401. The final image plan is unchanged. Ontology readback
shows 75 triples (66 + 9) and no missing additions. No live business-data writes
were used for acceptance. Production remains unchanged.

Use the explicit home release selection for subsequent home deployments:
`make deploy-home RELEASE_FILE=/Users/rosenth/ProgDev/OLDAP/oldap-setup/releases/home-1.2.0.json`.
Do not reuse the older default/1.1.0 selection for this home release.

Image/config rollback is retained at
`/opt/oldap/compose/routine-update-20261114T182634810080Z`.
The ontology before-graph and additive rollback are retained at
`/srv/storage/oldap-releases/20261114-reification-1.2.0/`.
Reverting application images never authorizes removing annotation data.

Digests, exact source commits, validation and recovery references:
[release receipt](release-1.2.0-results.json).
