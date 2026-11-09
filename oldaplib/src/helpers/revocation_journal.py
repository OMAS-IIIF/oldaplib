"""Durable prepared revocations on the existing designated AOF writer store.

This is an internal command journal, not a replacement for WriterRecovery's
operator fencing protocol. No cache store, TTL, cleanup, background retry or
endpoint discovery is provided. The caller authenticates operators and binds
its configured dataset identity to the supplied transport. Use a new identity
for a replaced/restored dataset; never replay into an unrelated database.
"""
from collections.abc import Callable, Iterator
from dataclasses import asdict
from hashlib import sha256
import json
import re
from typing import Any
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError

from oldaplib.src.helpers.authentication_revocation import AuthenticationRevocation
from oldaplib.src.helpers.jena_authentication_revocation import RevocationAttempt
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapErrorNotFound
from oldaplib.src.mutation_gate import MutationGateUnavailable, _durable, _validate_store
from oldaplib.src.writer_recovery import encoded


class RevocationJournal:
    """Retain exact commands before transmission, scoped to a configured dataset.

    Args:
        client: Dedicated writer-store Redis client (not a resource-cache client).
        dataset_id: Stable deployment/dataset-generation identity from trusted
            server configuration, not an HTTP request. Must match the transport.

    Acknowledgement covers the designated primary's local AOF, not asynchronous
    replica failover or loss of the storage volume. Records are retained forever
    until a separately designed receipt/journal retention policy exists.
    """

    def __init__(self, client: Redis, dataset_id: str):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', dataset_id):
            raise ValueError('A stable dataset-generation identity is required.')
        self.client = client
        self.dataset_id = dataset_id
        self.prefix = 'oldap:jena:revocation-journal:' + sha256(dataset_id.encode()).hexdigest() + ':'

    def _key(self, receipt_id: UUID) -> str:
        return self.prefix + str(UUID(str(receipt_id)))

    def _record(self, attempt: RevocationAttempt) -> dict[str, Any]:
        """Bind the serialized snapshot and exact generated update to this build."""
        return {
            'schema': 1, 'dataset': self.dataset_id, 'receiptId': str(attempt.receipt_id),
            'command': asdict(attempt.command), 'digest': attempt.command.digest,
            'updateSha256': sha256(attempt.command.sparql_update(
                receipt_id=attempt.receipt_id).encode()).hexdigest(),
        }

    def save(self, attempt: RevocationAttempt) -> None:
        """Durably insert an immutable attempt, or confirm an exact repetition.

        A different payload under the same ID fails closed. Use one pinned
        physical connection for SET and WAITAOF: a pooled read/new connection
        cannot attest another connection's write offset. Exact repeats also
        rewrite identical bytes so this connection has an offset to confirm.
        No database command may be sent if any step raises.
        """
        raw = encoded(self._record(attempt))
        with self.client.client() as pinned:
            _validate_store(pinned)
            incarnation = pinned.info('server')['run_id']
            connection_id = pinned.client_id()
            changed = pinned.eval(
                "local old=redis.call('GET',KEYS[1]); "
                "if old and old~=ARGV[1] then return 0 end; "
                "redis.call('SET',KEYS[1],ARGV[1]); return 1",
                1, self._key(attempt.receipt_id), raw,
            )
            if changed != 1:
                raise OldapErrorInconsistency('Revocation identity already contains another command.')
            _durable(pinned)
            # redis-py may reconnect/retry even a pinned client. A new server
            # connection cannot acknowledge the original connection's offset.
            if pinned.client_id() != connection_id or pinned.info('server')['run_id'] != incarnation:
                raise MutationGateUnavailable('Journal durability connection changed; do not transmit.')

    def load(self, receipt_id: UUID) -> RevocationAttempt:
        """Reconstruct only an exact compatible snapshot; never silently upgrade.

        Changed schema, digest, generated SPARQL, dataset or ID blocks recovery.
        Journal data is trusted private state, not signed against a malicious
        Redis administrator. Missing records do not establish database rollback.
        """
        raw = self.client.get(self._key(receipt_id))
        if raw is None:
            raise OldapErrorNotFound('Prepared revocation was not found in this dataset journal.')
        try:
            record = json.loads(raw)
            if type(record['schema']) is not int or record['schema'] != 1:
                raise ValueError('Unsupported journal schema')
            command = record['command']
            if not all(isinstance(value, str) for value in command.values()):
                raise ValueError('Invalid command fields')
            attempt = RevocationAttempt(AuthenticationRevocation(**command), UUID(record['receiptId']))
            if attempt.receipt_id != UUID(str(receipt_id)) or record != self._record(attempt):
                raise ValueError('Incompatible revocation snapshot')
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise OldapErrorInconsistency('Stored revocation is corrupt or incompatible with this build.') from error
        return attempt

    def retained_ids(self) -> Iterator[UUID]:
        """Discover retained attempts after restart; not a queue or pending status.

        SCAN can repeat IDs during concurrent writes. Consumers must tolerate
        duplicates and inspect receipts; committed/denied attempts remain here.
        """
        for key in self.client.scan_iter(match=self.prefix + '*'):
            if isinstance(key, bytes):
                key = key.decode('ascii')
            yield UUID(key[len(self.prefix):])

    def execute(self, attempt: RevocationAttempt, *, update: Callable[[str], Any],
                query: Callable[[str], dict[str, Any]]) -> None:
        """Persist before any transport call; leave identity retained on all outcomes.

        Recovery should first load the attempt and call its confirmed(query).
        False means unresolved; only an explicitly chosen exact retry calls
        execute again. A retry reaffirms journal durability before sending.
        Object/cache reconciliation remains the owner’s responsibility.
        """
        try:
            self.save(attempt)
        except RedisError as error:
            raise MutationGateUnavailable(
                'Cannot durably journal revocation; no database update sent.') from error
        attempt.execute(update=update, query=query)
