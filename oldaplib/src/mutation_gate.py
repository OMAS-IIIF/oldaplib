"""Persistent single-writer coordination for opt-in archive deployments.

Ownership never expires. A crash or uncertain database outcome intentionally
requires operator recovery. All writers must use the same dedicated Redis store;
mixed old/new workers, automatic failover and deleting the store are unsupported.
The store must acknowledge durable AOF writes and must never evict ownership.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
import json
import logging
import os
import socket
import time
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from oldaplib.src.helpers.oldaperror import OldapError

GATE_KEY = "oldap-api:staging:mutation"
WAIT_SECONDS = 30


class MutationGateUnavailable(OldapError):
    """Writer coordination is unavailable or requires controlled recovery."""


@dataclass
class _Owner:
    client: Redis
    record: dict
    transactions: set[str] = field(default_factory=set)
    uncertain: bool = False


_owner: ContextVar[_Owner | None] = ContextVar("oldap_mutation_gate", default=None)


def archive_coordination_enabled() -> bool:
    """Enable shared coordination when a deployment selects archive policy."""
    return bool(os.environ.get("OLDAP_ARCHIVE_POLICY_FILE"))


def require_separate_cache(cache: Redis) -> None:
    """Prevent library cache clearing from deleting persistent writer ownership.

    Compare Redis database numbers and server identities, including aliases and
    Unix sockets. An unavailable identity check fails closed before cache use.
    """
    if not archive_coordination_enabled():
        return
    gate = Redis.from_url(
        os.getenv("OLDAP_STAGING_LOCK_REDIS_URL", "redis://localhost:6379/1"),
        socket_connect_timeout=5,
        socket_timeout=10,
    )
    try:
        cache_db = int(cache.connection_pool.connection_kwargs.get("db", 0))
        gate_db = int(gate.connection_pool.connection_kwargs.get("db", 0))
        if cache_db != gate_db:
            return
        cache_id = cache.info("server").get("run_id")
        gate_id = gate.info("server").get("run_id")
        if not cache_id or not gate_id or cache_id == gate_id:
            raise MutationGateUnavailable(
                "Archive coordination and resource cache require separate Redis databases."
            )
    except RedisError as error:
        raise MutationGateUnavailable(
            "Cannot verify writer-store isolation."
        ) from error
    finally:
        gate.close()


def _durable(client: Redis) -> None:
    # Require Redis >= 7.2 and an acknowledged local AOF fsync. Replica failover
    # is deliberately not inferred safe from an asynchronously replicated key.
    result = client.execute_command("WAITAOF", 1, 0, 5000)
    if not result or int(result[0]) != 1:
        raise MutationGateUnavailable("Writer ownership persistence is unconfirmed.")


def _validate_store(client: Redis) -> None:
    settings = client.config_get("appendonly", "appendfsync", "maxmemory-policy")
    if settings != {
        "appendonly": "yes",
        "appendfsync": "always",
        "maxmemory-policy": "noeviction",
    }:
        raise MutationGateUnavailable(
            "Archive coordination requires appendonly=yes, appendfsync=always and noeviction."
        )
    if client.info("replication").get("role") != "master":
        raise MutationGateUnavailable(
            "Archive coordination requires the designated primary store."
        )


def _persist(owner: _Owner) -> None:
    record = {
        **owner.record,
        "transactions": sorted(owner.transactions),
        "uncertain": owner.uncertain,
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"))
    changed = owner.client.eval(
        "local v=redis.call('GET',KEYS[1]); "
        "if not v then return 0 end; "
        "local ok,r=pcall(cjson.decode,v); "
        "if not ok or r.token~=ARGV[1] then return 0 end; "
        "redis.call('SET',KEYS[1],ARGV[2]); return 1",
        1,
        GATE_KEY,
        owner.record["token"],
        encoded,
    )
    if changed != 1:
        owner.uncertain = True
        raise MutationGateUnavailable(
            "Writer ownership was lost; recovery is required."
        )
    _durable(owner.client)


def mark_gate_uncertain() -> None:
    """Retain ownership after an ambiguous database outcome or failed rollback."""
    owner = _owner.get()
    if owner is not None:
        owner.uncertain = True
        try:
            _persist(owner)
        except (RedisError, MutationGateUnavailable):
            # The already durable non-expiring record must remain in place.
            pass


def transaction_opened(transaction_url: str) -> None:
    """Record a database transaction before any update can be issued through it."""
    owner = _owner.get()
    if owner is not None:
        owner.transactions.add(transaction_url)
        try:
            _persist(owner)
        except (RedisError, MutationGateUnavailable) as error:
            owner.uncertain = True
            raise MutationGateUnavailable(
                "Cannot journal the database transaction."
            ) from error


def transaction_closed(transaction_url: str) -> None:
    """Record an acknowledged transaction end; uncertainty is never cleared."""
    owner = _owner.get()
    if owner is not None:
        owner.transactions.discard(transaction_url)
        try:
            _persist(owner)
        except (RedisError, MutationGateUnavailable) as error:
            owner.uncertain = True
            raise MutationGateUnavailable(
                "Cannot journal the transaction outcome."
            ) from error


def track_transaction_end(method: Callable) -> Callable:
    """Retain the gate if Connection commit/abort has an uncertain outcome."""

    @wraps(method)
    def tracked(connection, *args, **kwargs):
        transaction_url = connection._transaction_url
        try:
            result = method(connection, *args, **kwargs)
        except BaseException:
            mark_gate_uncertain()
            raise
        if transaction_url is not None:
            transaction_closed(transaction_url)
        return result

    return tracked


@contextmanager
def mutation_gate(
    *, client: Redis | None = None, wait_seconds: float = WAIT_SECONDS
) -> Iterator[None]:
    """Hold durable ownership across a complete domain operation.

    Waits at most ``wait_seconds`` for a predecessor, but never expires its
    ownership. Transaction URLs remain available to controlled crash recovery.
    No recovery operation is exposed through ordinary client APIs.
    """
    existing = _owner.get()
    if existing is not None:
        if existing.uncertain:
            raise MutationGateUnavailable("Writer recovery is required.")
        try:
            _persist(existing)
        except RedisError as error:
            existing.uncertain = True
            raise MutationGateUnavailable(
                "Writer coordination is unavailable."
            ) from error
        yield
        return
    client = client or Redis.from_url(
        os.getenv("OLDAP_STAGING_LOCK_REDIS_URL", "redis://localhost:6379/1"),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=10,
    )
    owner = _Owner(
        client,
        {
            "version": 1,
            "token": str(uuid4()),
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "transactions": [],
            "uncertain": False,
        },
    )
    try:
        _validate_store(client)
        deadline = time.monotonic() + wait_seconds
        while not client.set(GATE_KEY, json.dumps(owner.record), nx=True):
            if time.monotonic() >= deadline:
                raise MutationGateUnavailable(
                    "Another writer is active or requires controlled recovery."
                )
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        _durable(client)
    except RedisError as error:
        raise MutationGateUnavailable(
            "Durable writer coordination is unavailable."
        ) from error
    token = _owner.set(owner)
    try:
        yield
    finally:
        _owner.reset(token)
        if owner.uncertain or owner.transactions:
            logging.getLogger(__name__).error(
                "Writer gate retained for controlled recovery."
            )
        else:
            try:
                released = client.eval(
                    "local v=redis.call('GET',KEYS[1]); if not v then return 0 end; "
                    "local ok,r=pcall(cjson.decode,v); "
                    "if not ok or r.token~=ARGV[1] then return 0 end; "
                    "return redis.call('DEL',KEYS[1])",
                    1,
                    GATE_KEY,
                    owner.record["token"],
                )
                if released != 1:
                    raise MutationGateUnavailable(
                        "Writer gate release could not be confirmed."
                    )
                _durable(client)
            except (RedisError, MutationGateUnavailable):
                # Do not replace a durable success or the original domain error
                # with an ambiguous release error. A retained gate fails closed.
                logging.getLogger(__name__).error(
                    "Writer gate release requires inspection."
                )


def inspect_gate(client: Redis) -> dict | None:
    """Read operator-only recovery facts; never expose these through public APIs."""
    raw = client.get(GATE_KEY)
    if raw is None:
        return None
    try:
        record = json.loads(raw)
        if record.get("version") != 1 or not isinstance(
            record.get("transactions"), list
        ):
            raise ValueError()
        return record
    except (ValueError, TypeError, AttributeError) as error:
        raise MutationGateUnavailable(
            "Unrecognised writer record; manual inspection is required."
        ) from error


def recover_gate(
    client: Redis,
    *,
    expected_token: str,
    writer_terminated: bool,
    outcomes_reconciled: bool,
    confirm_transaction_ended: Callable[[str], bool],
) -> None:
    """Release an inspected gate only after controlled operational recovery.

    This is an operator primitive, not an automatic timeout or client endpoint.
    The operator must first terminate/quarantine the recorded worker, reconcile
    ambiguous committed results against GraphDB receipts, and confirm every
    recorded transaction is ended (aborted or already committed). An HTTP 404
    alone cannot establish whether a transaction committed; reconciliation is
    separately required. The exact token prevents releasing a successor's gate.
    """
    if writer_terminated is not True or outcomes_reconciled is not True:
        raise MutationGateUnavailable(
            "Worker termination and outcome reconciliation are required."
        )
    _validate_store(client)
    record = inspect_gate(client)
    if record is None or record.get("token") != expected_token:
        raise MutationGateUnavailable("The inspected writer record changed.")
    for transaction in record["transactions"]:
        if confirm_transaction_ended(transaction) is not True:
            raise MutationGateUnavailable(
                "A recorded database transaction has not been confirmed ended."
            )
    encoded = client.get(GATE_KEY)
    if encoded is None or json.loads(encoded) != record:
        raise MutationGateUnavailable("The writer record changed during recovery.")
    released = client.eval(
        "if redis.call('GET',KEYS[1])~=ARGV[1] then return 0 end; return redis.call('DEL',KEYS[1])",
        1,
        GATE_KEY,
        encoded,
    )
    if released != 1:
        raise MutationGateUnavailable("The writer record changed during recovery.")
    _durable(client)
