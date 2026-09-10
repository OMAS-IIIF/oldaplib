"""Offline recovery controller for a reviewed Docker/SSH or native macOS domain.

Run outside all managed containers. This module is NEVER called by an API view.
The protected config and operator Redis credential are an operational trust
boundary. No shell, container target, evidence or query is accepted from a browser.
"""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import socket
import stat
import subprocess
from uuid import uuid4
from urllib.parse import urlsplit

from redis import Redis
import requests
from rdflib.plugins.sparql.parser import parseQuery

from oldaplib.src.mutation_gate import (
    GATE_KEY,
    RECOVERY_BARRIER_KEY,
    MutationGateUnavailable,
    _durable,
    _validate_store,
)
from oldaplib.src.writer_recovery import (
    WriterRecovery,
    encoded,
    evidence_key,
    now,
    operation_key,
    PREFIX,
    CONTROLLER_KEY,
)


def inventory_digest(config: dict) -> str:
    """Bind the API's reviewed topology to the exact offline runtime targets.

    Credential rotation is separate; the runtime checkpoint additionally binds
    the complete private config. Publish this digest only after inventory review.
    """
    fields = ("domain", "nodes", "databaseNode", "databaseService", "queryEndpoint")
    if config.get("runtime") == "macos-launchd-v1":
        fields = (
            "domain",
            "runtime",
            "nativeServices",
            "databaseService",
            "queryEndpoint",
        )
    elif config.get("runtime") not in (None, "docker"):
        raise ValueError("Unsupported runtime control topology.")
    return sha256(encoded({key: config[key] for key in fields}).encode()).hexdigest()


class DockerDomain:
    """Fixed inventory runtime control; fail closed on every missing/unreachable host.

    Config names all domain members, their Compose project and direct-writer
    services. SSH destinations come only from the protected operator config.
    Docker's socket is used by this operator command, never mounted in the API.
    """

    def __init__(self, config: dict):
        self.config = config
        nodes = config["nodes"]
        if not nodes or len({n["name"] for n in nodes}) != len(nodes):
            raise ValueError("A unique, complete member inventory is required.")
        for node in nodes:
            for name in (node["name"], node["project"], *node["writerServices"]):
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name):
                    raise ValueError("Invalid inventory identifier.")
            if not node["writerServices"] or node["transport"] not in ("local", "ssh"):
                raise ValueError(
                    "Explicit writer services and local/ssh transport are required."
                )
            if node["transport"] == "ssh" and not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,253}", node["target"]
            ):
                raise ValueError("Invalid SSH target.")
        self.database_node = next(
            n for n in nodes if n["name"] == config["databaseNode"]
        )
        if not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", config["databaseService"]
        ):
            raise ValueError("Invalid database service.")
        if config["databaseService"] in self.database_node["writerServices"]:
            raise ValueError("Database and writer services must be distinct.")

    def run(self, node: dict, *args: str) -> str:
        """Execute only internally constructed Docker argv with bounded waits."""
        command = ["docker", "--host", "unix:///var/run/docker.sock", *args]
        if node["transport"] == "ssh":
            command = [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                "--",
                node["target"],
                shlex.join(command),
            ]
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=180, check=True
        )
        return result.stdout.strip()

    def containers(self, node: dict, service: str) -> list[str]:
        """Find all regular and one-off containers for one configured service."""
        output = self.run(
            node,
            "ps",
            "-aq",
            "--no-trunc",
            "--filter",
            f"label=com.docker.compose.project={node['project']}",
            "--filter",
            f"label=com.docker.compose.service={service}",
        )
        ids = output.splitlines() if output else []
        if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in ids):
            raise ValueError("Docker returned an invalid container identity.")
        return ids

    def fence(self) -> dict:
        """Remove old writers everywhere, stop the database process, then restart it.

        If any command fails, no proof is produced. A repeat may safely remove new
        blocked writers and restart the database again. No container is paused and
        no PID is trusted across namespaces or process generations.
        """
        database_ids = self.containers(
            self.database_node, self.config["databaseService"]
        )
        if len(database_ids) != 1:
            raise ValueError("Exactly one configured GraphDB container is required.")
        database_id = database_ids[0]
        # Reach every member before the first destructive step. Capture IDs first.
        found = [
            (node, service, self.containers(node, service))
            for node in self.config["nodes"]
            for service in node["writerServices"]
        ]
        before = json.loads(self.run(self.database_node, "inspect", database_id))[0]
        removed = []
        for node, service, ids in found:
            for container in ids:
                self.run(node, "rm", "--force", container)
            removed.append(
                {"member": node["name"], "service": service, "containers": ids}
            )
        for node, service, _ in found:
            if self.containers(node, service):
                raise ValueError(
                    "A writer was recreated during maintenance; stop its orchestrator."
                )
        self.run(self.database_node, "stop", "--time", "60", database_id)
        stopped = json.loads(self.run(self.database_node, "inspect", database_id))[0]
        if stopped["State"]["Running"] or stopped["State"]["Pid"] != 0:
            raise ValueError("GraphDB process termination was not verified.")
        self.run(self.database_node, "start", database_id)
        after = json.loads(self.run(self.database_node, "inspect", database_id))[0]
        if (
            not after["State"]["Running"]
            or after["State"]["StartedAt"] == before["State"]["StartedAt"]
        ):
            raise ValueError("GraphDB restart was not verified.")
        return {
            "removedWriters": removed,
            "databaseMember": self.database_node["name"],
            "databaseContainer": database_id,
            "previousStartedAt": before["State"]["StartedAt"],
            "stoppedAt": stopped["State"]["FinishedAt"],
            "startedAt": after["State"]["StartedAt"],
            "observedAt": now(),
        }


def protected_json(path: str) -> dict:
    """Read a private operator file owned by this user/root, without symlink following."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid not in (0, os.geteuid())
            or info.st_mode & 0o077
        ):
            raise ValueError(
                "Operator files must be regular, owned by this user/root and mode 0600 or stricter."
            )
        with os.fdopen(fd, "r", closefd=False) as stream:
            return json.load(stream)
    finally:
        os.close(fd)


def read_reconciliation(config: dict, report: dict, operation: dict) -> dict:
    """Verify operator-reviewed outcomes against actual read-only GraphDB results.

    Semantic conclusions remain the trained operator's responsibility. Each known
    transaction and the unregistered-request window must reference passing checks.
    URLs in the journal are labels only; no request is sent to a transaction URL.
    """
    if report.get("revision") != operation["request"]["revision"]:
        raise ValueError("Reconciliation belongs to a different writer revision.")
    checks = report.get("checks", [])
    if not 1 <= len(checks) <= 50:
        raise ValueError("One to fifty concrete reconciliation checks are required.")
    endpoint = config["queryEndpoint"]
    url = urlsplit(endpoint)
    if (
        url.scheme not in ("http", "https")
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError("A fixed direct GraphDB query endpoint is required.")
    results = {}
    auth = (
        (config["databaseUser"], config["databasePassword"])
        if config.get("databaseUser")
        else None
    )
    for check in checks:
        label = check["label"]
        if not isinstance(label, str) or not label or label in results:
            raise ValueError("Every check needs a unique label.")
        query = check["query"]
        if len(query) > 32000 or parseQuery(query)[1].name not in (
            "SelectQuery",
            "AskQuery",
        ):
            raise ValueError(
                "Only bounded SELECT/ASK reconciliation queries are supported."
            )
        # Direct endpoint only. No redirects and bounded response size/time.
        with requests.post(
            endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            auth=auth,
            timeout=(5, 30),
            allow_redirects=False,
            stream=True,
        ) as response:
            if response.status_code != 200:
                raise ValueError("GraphDB reconciliation query was not acknowledged.")
            chunks, size = [], 0
            for chunk in response.iter_content(8192):
                size += len(chunk)
                if size > 65536:
                    raise ValueError(
                        "Reconciliation result is too large; use a focused query."
                    )
                chunks.append(chunk)
            observed = json.loads(b"".join(chunks))
        if observed != check["expected"]:
            raise ValueError(
                "Observed GraphDB state differs from the reviewed reconciliation."
            )
        results[label] = {"query": query, "result": observed}
    outcomes = report["transactions"]
    if set(outcomes) != set(operation["owner"]["transactions"]):
        raise ValueError("Every journaled transaction must be reconciled exactly once.")
    for conclusion in [*outcomes.values(), report["unregisteredRequests"]]:
        if (
            conclusion.get("outcome")
            not in ("committed", "rolled_back", "no_write", "mixed_reconciled")
            or len(conclusion.get("explanation", "").strip()) < 20
            or not conclusion.get("checks")
            or not set(conclusion["checks"]).issubset(results)
        ):
            raise ValueError(
                "Every outcome needs a concrete explanation and observed checks."
            )
    return {
        "operator": report["operator"],
        "transactions": outcomes,
        "unregisteredRequests": report["unregisteredRequests"],
        "checks": results,
        "observedAt": now(),
    }


def _prepare_evidence(
    client: Redis, config: dict, operation_id: str, *, report: dict | None = None
) -> dict:
    """Perform fencing or attach reconciliation to a previously persisted fence.

    Two phases let the operator inspect the restarted database without repeating
    fencing. Neither phase releases the gate. The offline Redis ACL may write
    evidence/runtime keys, but cannot delete the gate or modify the API journal.
    """
    _validate_store(client)
    recovery = WriterRecovery(client, config["domain"])
    operation = recovery.operation(operation_id)
    if inventory_digest(config) != operation.get("inventoryDigest"):
        raise ValueError(
            "Operator runtime inventory differs from the API's reviewed inventory."
        )
    if (
        operation["state"] != "awaiting_operator"
        or client.get(RECOVERY_BARRIER_KEY) != operation_id
        or client.get(GATE_KEY) != operation["ownerRaw"]
    ):
        raise MutationGateUnavailable("Recovery barrier or owner changed.")
    existing = client.get(evidence_key(operation_id))
    if existing:
        return json.loads(existing)
    config_hash = sha256(encoded(config).encode()).hexdigest()
    runtime_key = PREFIX + "runtime:" + operation_id
    if config.get("runtime") == "macos-launchd-v1":
        from oldaplib.src.writer_recovery_macos import LaunchdDomain

        domain = LaunchdDomain(config)
        domain.validate_owner(operation["owner"])
    else:
        domain = DockerDomain(config)
    if report is None:
        runtime = {"configHash": config_hash, **domain.fence()}
        client.set(runtime_key, encoded(runtime))
        _durable(client)
        return runtime
    raw = client.get(runtime_key)
    if not raw:
        raise ValueError("Run the fencing phase first.")
    runtime = json.loads(raw)
    if runtime["configHash"] != config_hash:
        raise ValueError("Runtime inventory changed after fencing.")
    if config.get("runtime") == "macos-launchd-v1":
        domain.verify(runtime)
    else:
        ids = domain.containers(domain.database_node, config["databaseService"])
        if ids != [runtime["databaseContainer"]]:
            raise ValueError("Database identity changed after fencing.")
        state = json.loads(domain.run(domain.database_node, "inspect", ids[0]))[0][
            "State"
        ]
        if not state["Running"] or state["StartedAt"] != runtime["startedAt"]:
            raise ValueError(
                "Database process changed after fencing; repeat the fencing phase."
            )
    proof = {
        "version": 1,
        "method": (
            "macos-launchd-restart-v1"
            if config.get("runtime") == "macos-launchd-v1"
            else "docker-domain-restart-v1"
        ),
        "domain": config["domain"],
        "inventoryDigest": operation["inventoryDigest"],
        "operationId": operation_id,
        "revision": operation["request"]["revision"],
        "runtime": runtime,
        "reconciliation": read_reconciliation(config, report, operation),
    }
    if config.get("runtime") == "macos-launchd-v1":
        domain.verify(runtime)
    value = encoded(proof)
    if len(value.encode()) > 256000:
        raise ValueError("Evidence exceeds 256 KB; narrow the reconciliation queries.")
    changed = client.eval(
        "if redis.call('GET',KEYS[1])~=ARGV[1] or redis.call('GET',KEYS[2])~=ARGV[2] "
        "or redis.call('GET',KEYS[4])~=ARGV[4] then return 0 end; "
        "if redis.call('GET',KEYS[3]) then return 2 end; "
        "redis.call('SET',KEYS[3],ARGV[3]); return 1",
        4,
        GATE_KEY,
        RECOVERY_BARRIER_KEY,
        evidence_key(operation_id),
        runtime_key,
        operation["ownerRaw"],
        operation_id,
        value,
        raw,
    )
    if changed not in (1, 2):
        raise MutationGateUnavailable("Recovery changed while collecting evidence.")
    _durable(client)
    return json.loads(client.get(evidence_key(operation_id)))


def prepare_evidence(
    client: Redis, config: dict, operation_id: str, *, report: dict | None = None
) -> dict:
    """Serialize offline controllers and prevent release while runtime control runs.

    Controller ownership never expires. If this process crashes, a host operator
    must terminate/reap it and any SSH/Docker command children before removing ONLY
    the controller record. The original recovery barrier remains throughout.
    """
    operation_key(operation_id)
    _validate_store(client)
    token = encoded(
        {
            "token": str(uuid4()),
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "operationId": operation_id,
            "startedAt": now(),
        }
    )
    claimed = client.eval(
        "if redis.call('GET',KEYS[3]) then return 2 end; "
        "if redis.call('GET',KEYS[2])~=ARGV[2] then return 0 end; "
        "if redis.call('SET',KEYS[1],ARGV[1],'NX') then return 1 end; return 0",
        3,
        CONTROLLER_KEY,
        RECOVERY_BARRIER_KEY,
        evidence_key(operation_id),
        token,
        operation_id,
    )
    if claimed == 2:
        _durable(client)
        return json.loads(client.get(evidence_key(operation_id)))
    if claimed != 1:
        raise MutationGateUnavailable(
            "An offline controller is active or requires host-operator inspection."
        )
    _durable(client)
    # Do not unlock on exceptions: a timed-out SSH/Docker command may still run
    # remotely. Even a failed phase requires the host operator to rule that out.
    result = _prepare_evidence(client, config, operation_id, report=report)
    client.eval(
        "if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) end; return 0",
        1,
        CONTROLLER_KEY,
        token,
    )
    _durable(client)
    return result


def main() -> None:
    """Run trusted offline maintenance explicitly, without exposing credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", required=True, help="Private, reviewed domain inventory JSON"
    )
    parser.add_argument("--operation", required=True)
    parser.add_argument(
        "--report", help="Private reconciliation JSON; omit to fence/restart first"
    )
    args = parser.parse_args()
    operation_key(args.operation)
    config = protected_json(args.config)
    report = protected_json(args.report) if args.report else None
    client = Redis.from_url(
        config["operatorRedisUrl"],
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=10,
    )
    try:
        result = prepare_evidence(client, config, args.operation, report=report)
        print(encoded(result))
    except Exception:
        # Transport exceptions can contain credentials/URLs. Detailed inspection is
        # an offline operator responsibility, not an API response or log payload.
        raise SystemExit(
            "Recovery remains blocked. Inspect runtime/configuration and reconciliation; no release was requested."
        ) from None
    finally:
        client.close()


if __name__ == "__main__":
    main()
