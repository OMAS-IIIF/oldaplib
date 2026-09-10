"""Project-neutral, durable recovery journal; no runtime control in the API.

Normal writers read the maintenance barrier. A separate recovery Redis identity
can manage this journal but may only READ evidence produced by the offline
operator identity. All keys are persistent on the designated AOF primary.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError

from oldaplib.src.mutation_gate import (
    GATE_KEY,
    RECOVERY_BARRIER_KEY,
    MutationGateUnavailable,
    _durable,
    _validate_store,
)

PREFIX = "oldap-api:staging:recovery:"
CONTROLLER_KEY = PREFIX + "controller"


class RecoveryOutcomeUnknown(MutationGateUnavailable):
    """A recovery journal/release write lacks a durable acknowledgement."""


def _confirm_recovery_durable(client: Redis) -> None:
    """Distinguish an uncertain write result from a definite safety refusal."""
    try:
        _durable(client)
    except MutationGateUnavailable as error:
        raise RecoveryOutcomeUnknown(
            "Read the same recovery operation to resolve its outcome."
        ) from error


def encoded(value: dict) -> str:
    """Return the canonical journal representation used for compare-and-set."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def now() -> str:
    """Return an audit timestamp in UTC (never used as termination evidence)."""
    return datetime.now(timezone.utc).isoformat()


def operation_key(operation_id: str) -> str:
    """Validate an externally supplied operation ID before constructing a key."""
    if str(UUID(operation_id)) != operation_id:
        raise ValueError("A canonical UUID operation ID is required.")
    return PREFIX + "operation:" + operation_id


def evidence_key(operation_id: str) -> str:
    """Return the offline-operator-only evidence key."""
    operation_key(operation_id)
    return PREFIX + "evidence:" + operation_id


def revision(raw: str) -> str:
    """Bind recovery to every byte of the inspected writer record."""
    return sha256(raw.encode()).hexdigest()


class WriterRecovery:
    """Coordinate recovery without stopping processes or issuing database writes.

    Args:
        client: Dedicated recovery-service Redis client, with decoded responses.
        domain: Stable deployment coordination domain, supplied by server config.
        inventory_digest: SHA-256 of the reviewed offline control inventory.

    Methods require authorization by their caller. They never accept termination
    booleans or evidence in HTTP input; evidence is read from its separate ACL key.
    """

    def __init__(self, client: Redis, domain: str, *, inventory_digest: str = ""):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", domain):
            raise ValueError("Invalid coordination domain.")
        self.client = client
        self.domain = domain
        self.inventory_digest = inventory_digest

    def status(self) -> dict:
        """Read a consistent state; age is diagnostic and never means stale."""
        try:
            _validate_store(self.client)
            raw, barrier = self.client.eval(
                "return {redis.call('GET',KEYS[1]) or '', redis.call('GET',KEYS[2]) or ''}",
                2,
                GATE_KEY,
                RECOVERY_BARRIER_KEY,
            )
            if barrier:
                return {"state": "recovery_in_progress", "operationId": barrier}
            if not raw:
                return {"state": "free"}
            owner = json.loads(raw)
            if owner.get("version") != 1 or not isinstance(
                owner.get("transactions"), list
            ):
                raise ValueError("Unknown owner format.")
            return {
                "state": "recovery_required" if owner.get("uncertain") else "occupied",
                "revision": revision(raw),
                "owner": owner,
                "nextAction": "operator_maintenance",
            }
        except (
            RedisError,
            MutationGateUnavailable,
            ValueError,
            TypeError,
            AttributeError,
        ):
            return {"state": "store_unavailable", "nextAction": "inspect_writer_store"}

    def operation(self, operation_id: str) -> dict:
        """Read a retained audit result, including after a lost release response."""
        raw = self.client.get(operation_key(operation_id))
        if raw is None:
            raise MutationGateUnavailable("Recovery operation was not found.")
        result = json.loads(raw)
        if result.get("domain") != self.domain:
            raise MutationGateUnavailable("Recovery domain mismatch.")
        return result

    def begin(
        self, *, operation_id: str, expected_revision: str, actor: str, reason: str
    ) -> dict:
        """Freeze an exact owner and journal the request atomically; exact retries join.

        Freezing is NOT runtime fencing. Even a live writer may have an outstanding
        request, so release always requires the independent maintenance proof.
        """
        key = operation_key(operation_id)
        if not re.fullmatch(r"[0-9a-f]{64}", self.inventory_digest):
            raise MutationGateUnavailable(
                "A reviewed runtime inventory digest is required."
            )
        if (
            not actor
            or not isinstance(reason, str)
            or not 10 <= len(reason.strip()) <= 2000
        ):
            raise ValueError(
                "An actor and a reason of 10–2000 characters are required."
            )
        if not re.fullmatch(r"[0-9a-f]{64}", expected_revision):
            raise ValueError("Invalid inspected revision.")
        _validate_store(self.client)
        request = {
            "actor": actor,
            "reason": reason.strip(),
            "revision": expected_revision,
        }
        old = self.client.get(key)
        if old:
            result = self.operation(operation_id)
            if result["request"] != request:
                raise MutationGateUnavailable(
                    "Recovery ID was used for another request."
                )
            _confirm_recovery_durable(self.client)
            return result
        raw = self.client.get(GATE_KEY)
        if raw is None or revision(raw) != expected_revision:
            raise MutationGateUnavailable("The inspected writer changed.")
        owner = json.loads(raw)
        if owner.get("recoveryProtocol") != 2:
            raise MutationGateUnavailable(
                "Upgrade and reconcile the legacy writer before recovery."
            )
        result = {
            "version": 1,
            "domain": self.domain,
            "operationId": operation_id,
            "inventoryDigest": self.inventory_digest,
            "request": request,
            "owner": owner,
            "ownerRaw": raw,
            "state": "awaiting_operator",
            "requestedAt": now(),
        }
        changed = self.client.eval(
            "if redis.call('GET',KEYS[3]) then return 2 end; "
            "if redis.call('GET',KEYS[1])~=ARGV[1] or redis.call('GET',KEYS[2]) then return 0 end; "
            "if not redis.acl_check_cmd('SET',KEYS[2],ARGV[2]) or not redis.acl_check_cmd('SET',KEYS[3],ARGV[3]) "
            "then return redis.error_reply('Recovery journal permissions unavailable') end; "
            # Barrier first: an unexpected Redis script failure can only block.
            "redis.call('SET',KEYS[2],ARGV[2]); redis.call('SET',KEYS[3],ARGV[3]); return 1",
            3,
            GATE_KEY,
            RECOVERY_BARRIER_KEY,
            key,
            raw,
            operation_id,
            encoded(result),
        )
        if changed == 2:
            return self.begin(
                operation_id=operation_id,
                expected_revision=expected_revision,
                actor=actor,
                reason=reason,
            )
        if changed != 1:
            raise MutationGateUnavailable(
                "Another writer or recovery operation intervened."
            )
        _confirm_recovery_durable(self.client)
        return result

    def _proof_matches(self, result: dict, proof: dict) -> bool:
        """Check the same evidence binding for diagnosis and authoritative release."""
        return (
            isinstance(proof, dict)
            and proof.get("version") == 1
            and proof.get("domain") == self.domain
            and proof.get("inventoryDigest")
            == result.get("inventoryDigest")
            == self.inventory_digest
            and proof.get("operationId") == result["operationId"]
            and proof.get("revision") == result["request"]["revision"]
            and proof.get("method")
            in ("docker-domain-restart-v1", "macos-launchd-restart-v1")
            and bool(proof.get("runtime"))
            and bool(proof.get("reconciliation"))
        )

    def readiness(self, result: dict) -> str:
        """Return an advisory UI state; finish always repeats the atomic checks.

        No raw evidence, runtime addresses or owner secrets leave this projection.
        A controller record may represent a live or interrupted controller; age
        cannot distinguish them, so both require operator attention.
        """
        raw, barrier, controller, proof = self.client.eval(
            "return {redis.call('GET',KEYS[1]) or '',redis.call('GET',KEYS[2]) or '',"
            "redis.call('GET',KEYS[3]) or '',redis.call('GET',KEYS[4]) or ''}",
            4,
            GATE_KEY,
            RECOVERY_BARRIER_KEY,
            CONTROLLER_KEY,
            evidence_key(result["operationId"]),
        )
        if result["state"] == "completed":
            if barrier == result["operationId"] or raw == result["ownerRaw"]:
                raise MutationGateUnavailable("Inconsistent completed recovery.")
            return "completed"
        if raw != result["ownerRaw"] or barrier != result["operationId"]:
            raise MutationGateUnavailable("Recovery ownership changed.")
        if controller:
            return "controller_blocked"
        if proof and self._proof_matches(result, json.loads(proof)):
            return "ready"
        return "awaiting_operator"

    def finish(self, *, operation_id: str, actor: str) -> dict:
        """Release only with immutable offline proof and retain the full audit.

        Completion, gate deletion and barrier deletion share one Lua execution.
        A failed acknowledgement has an UNKNOWN outcome: read/retry this same ID.
        No new recovery or uncertain archive command is automatically replayed.
        """
        if not actor:
            raise ValueError("A completing actor is required.")
        _validate_store(self.client)
        result = self.operation(operation_id)
        if result["state"] == "completed":
            if (
                self.client.get(RECOVERY_BARRIER_KEY) == operation_id
                or self.client.get(GATE_KEY) == result["ownerRaw"]
            ):
                raise MutationGateUnavailable(
                    "Completed recovery has inconsistent retained ownership; inspect the store."
                )
            _confirm_recovery_durable(self.client)
            return result
        proof_raw = self.client.get(evidence_key(operation_id))
        if proof_raw is None:
            raise MutationGateUnavailable(
                "Offline maintenance and reconciliation evidence is required."
            )
        proof = json.loads(proof_raw)
        if not self._proof_matches(result, proof):
            raise MutationGateUnavailable(
                "Operational evidence does not match this recovery."
            )
        completed = {
            **result,
            "state": "completed",
            "completedAt": now(),
            "completedBy": actor,
            "evidence": proof,
        }
        changed = self.client.eval(
            "if redis.call('GET',KEYS[5]) then return 0 end; "
            "if redis.call('GET',KEYS[1])~=ARGV[1] or redis.call('GET',KEYS[2])~=ARGV[2] "
            "or redis.call('GET',KEYS[3])~=ARGV[3] or redis.call('GET',KEYS[4])~=ARGV[4] then return 0 end; "
            "if not redis.acl_check_cmd('SET',KEYS[3],ARGV[5]) or not redis.acl_check_cmd('DEL',KEYS[1]) "
            "or not redis.acl_check_cmd('DEL',KEYS[2]) then return redis.error_reply('Recovery audit/release permissions unavailable') end; "
            # SET and DEL cannot encounter key-type errors. Audit is written FIRST.
            "redis.call('SET',KEYS[3],ARGV[5]); redis.call('DEL',KEYS[1]); "
            "redis.call('DEL',KEYS[2]); return 1",
            5,
            GATE_KEY,
            RECOVERY_BARRIER_KEY,
            operation_key(operation_id),
            evidence_key(operation_id),
            CONTROLLER_KEY,
            result["ownerRaw"],
            operation_id,
            encoded(result),
            proof_raw,
            encoded(completed),
        )
        if changed != 1:
            latest = self.operation(operation_id)
            if latest.get("state") == "completed":
                _confirm_recovery_durable(self.client)
                return latest
            raise MutationGateUnavailable(
                "Recovery evidence or ownership changed; remain blocked."
            )
        _confirm_recovery_durable(self.client)
        return completed
