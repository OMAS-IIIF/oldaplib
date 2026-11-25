# oldaplib 1.2.5

Allow Redis Python clients `>=7.4.1,<9.0.0` instead of pinning 7.4.0;
the library lock selects 8.2.0. Other dependency entries and runtime APIs are
unchanged. No data migration or Redis server upgrade is required.

Redis-py 8 changes default protocol, socket timeouts and retry settings;
see [compatibility and verification](redis-client-compatibility.md).
The isolated Redis/cache/recovery/transaction suite passes with both 7.4.1 and
8.2.0 (73 tests plus 9 subtests each). Release artifact verification and hashes
are recorded in `release-1.2.5-results.json` after publication.

Consumer images and live deployment remain separate from this Python release.

Published on 2026-11-25: GitHub source/tag and both PyPI distributions verified
against the tested local artifacts. No service deployment.
