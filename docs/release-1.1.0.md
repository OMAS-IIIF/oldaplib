# OLDAP 1.1.0 release

Release 1.1.0 includes business-property history, permission-checked history
reads and ordinary validated restores. Only model-permitted business properties
of Thing instances participate, independent of namespace. Internal OLDAP fields
are excluded. Creation has no initial snapshot; history starts with a change.

Native Jena project dumps include history with data; --no-data excludes both.
Imports preserve old RDF values and Dating snapshots. Older data-only dumps
remain supported. Raw transfer stays root-only, additive and bounded by the
existing request limit. Deploy Jena service 1.1.0 for this transfer capability.

Published artifacts:

- oldaplib 1.1.0 wheel and sdist on PyPI, with verified SHA-256 values.
- lrosenth/oldap-api:v1.1.0 and lrosenth/oldap-tools:v1.1.0: AMD64/ARM64.
- lrosenth/oldap-harvesters:0.1.15: AMD64/ARM64; 0.1.15-ocr: AMD64 CPU OCR.
- Jena service 1.1.0: versioned offline distribution and portable tar archive.

The three core source releases are tagged v1.1.0; harvesters are tagged v0.1.15.
API/tools Python wheels are Docker build inputs; only oldaplib was uploaded to
PyPI in this release. Consumer locks change only oldaplib. Existing/latest Docker
tags are preserved. Harvesters keep their independent version series.

Validation: 133 focused cross-project tests, 169 tools tests, five native graph
transfer checks, persistent Jena service acceptance (including 300 commits and
crash/restart recovery), 113 installed API/library tests on each architecture,
136 installed harvester tests on each architecture, CPU OCR imports, package
checks, and packaged API/Jena identity/transaction/network/restart checks.
AMD64 tests ran under local emulation. No external harvest or production write
test was performed.

Evidence, frozen wheels/contexts, constraints and service distribution:
`/Users/rosenth/Library/Application Support/OLDAP/releases/20261111-1.1.0`.
The core Docker workflow is oldap-setup/scripts/jena-images.py with --final;
its build, accept and publish gates use the frozen core-images bundle.

No live deployment or current release-selection change was performed. Home and
production retain the existing property-history candidate and already contain
the history ontology definitions. Their next coordinated deployment must also
install the new Jena service for history-aware transfer. Frontend work is separate.

Registry digests and source/artifact hashes: [release receipt](release-1.1.0-results.json).
