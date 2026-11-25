# Redis client compatibility

The library accepts `redis>=7.4.1,<9.0.0`; `poetry.lock` currently selects
8.2.0. Applications should lock their chosen version. The original 7.4.0 exact
pin was introduced with the April 2026 dependency refresh; its commit does not
record a Redis-specific compatibility requirement.

This changes the Python client dependency, not the Redis server. Writer-store
requirements remain in [writer recovery](writer_recovery.md), including Redis
7.2+ and durable AOF configuration.

Redis-py 8 defaults to RESP3 with legacy-compatible Python response shapes,
5-second socket/connect timeouts, and ten retry attempts. OLDAP retains its
explicit coordination timeouts (5-second connect / 10-second socket) and
32-connection cache pool; otherwise the selected client defaults apply. Failure
latency can therefore differ between 7.x and 8.x. No change is made to the gate,
Lua ownership checks, recovery protocol, or cache serialization.

Upstream references:
- [8.0 migration changes](https://github.com/redis/redis-py/releases/tag/v8.0.0)
- [8.2 release notes](https://github.com/redis/redis-py/releases/tag/v8.2.0)

## Verification — 2026-11-25

On Python 3.14.8 / macOS with isolated Unix-socket Redis server 8.6.3,
**73 tests plus 9 subtests pass for each client version 7.4.1 and 8.2.0**:

```sh
python -m pytest --noconftest -q \
  oldaplib/test/test_mutation_gate.py \
  oldaplib/test/test_writer_recovery.py \
  oldaplib/test/test_read_cache_optimization.py \
  oldaplib/test/test_resource_transaction.py
```

Each client was installed in a separate temporary package directory and selected
through `PYTHONPATH`; the shared development environment was not changed. Gate
and recovery tests own their temporary Redis process/AOF directory and never use
the configured application server. Coverage includes ownership persistence,
recovery/ACL boundaries, cache database isolation, JSON round trips, aliases,
deletion, clearing, pool reuse, and resource transaction failures.

Poetry lock consistency and wheel build pass; wheel metadata contains the new
range. Only the Redis package entry changes in the lock. PyPI and OSV queries for
both tested client versions return no advisories. Other Python/server/platform
combinations and transport-failure latency were not tested.

The range is introduced in oldaplib 1.2.5. Published 1.2.4 remains unchanged.
Consumer applications must update their dependency constraints and lockfiles;
server upgrades and deployment are separate operations.
