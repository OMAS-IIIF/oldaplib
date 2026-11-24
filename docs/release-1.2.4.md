# oldaplib 1.2.4

Security maintenance release with unchanged runtime APIs and no data migration.
Published requirements now require PyJWT >=2.15.1 and Requests >=2.34.2 so
downstream installations cannot retain the previously permitted vulnerable versions.
The runtime versions in the project lockfile are unchanged.

Documentation/development dependencies receive security updates, with a compatible
mkdocstrings update and a declared pytest dependency for existing regressions.
The private Java service now builds against checksum-pinned Fuseki 6.3.0, including
Jetty 12.1.14, and was validated with Temurin 25.0.5.1+2. Native acceptance fixtures
use the current dependency pin and explicit patched-JDK selection.

The Python wheel does not distribute or deploy the Java service/JDK. Existing
services and downstream API/tools environments need separate rebuild/deployment.
Shiro 2.2.1 remains bundled in Fuseki with a conditional RememberMe advisory;
use of that feature in OLDAP authentication has not been established.

Security-update verification covers 82 source and 82 installed-wheel unit tests,
21 focused Python tests, 42 native annotation/search tests (three benchmark skips),
and native service, administration, compaction, backup/restore and import checks.
The Python advisory scan has no matches across 94 checked package versions.
Documentation builds successfully with content warnings. See
[Python evidence](security-python-update-20261125.json) and
[Java evidence](security-java-update-20261125.json) for scope and limitations.

Release-specific artifact hashes, installed-package verification and publication
results are recorded in `release-1.2.4-results.json`.

Published on 2026-11-25: GitHub source/tag and both PyPI distributions verified
against the tested local artifacts. No consumer image or service deployment.
