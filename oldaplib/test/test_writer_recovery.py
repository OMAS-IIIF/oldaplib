"""Recovery races, durability and ACL boundaries on disposable AOF Redis."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch, Mock
from uuid import uuid4

from redis import Redis
from redis.exceptions import ResponseError
from oldaplib.test import test_mutation_gate as gate_fixture
from oldaplib.src.mutation_gate import (
    GATE_KEY,
    RECOVERY_BARRIER_KEY,
    MutationGateUnavailable,
    mutation_gate,
    mark_gate_uncertain,
    transaction_opened,
)
from oldaplib.src.writer_recovery import (
    WriterRecovery,
    PREFIX,
    CONTROLLER_KEY,
    evidence_key,
    operation_key,
    encoded,
)
from oldaplib.src.writer_recovery_operator import (
    DockerDomain,
    prepare_evidence,
    read_reconciliation,
)


class WriterRecoveryTest(gate_fixture.MutationGateTest):
    def setUp(self):
        self.recovery = WriterRecovery(
            self.client, "test-domain", inventory_digest="d" * 64
        )
        self.id = str(uuid4())

    def tearDown(self):
        for key in self.client.scan_iter(PREFIX + "*"):
            self.client.delete(key)
        super().tearDown()

    def retain(self):
        with mutation_gate(client=self.client, wait_seconds=0):
            mark_gate_uncertain()
        return self.recovery.status()["revision"]

    def begin(self, revision=None, operation_id=None):
        return self.recovery.begin(
            operation_id=operation_id or self.id,
            expected_revision=revision or self.retain(),
            actor="urn:test:operator",
            reason="Investigate interrupted archive write",
        )

    def proof(self):
        operation = self.recovery.operation(self.id)
        proof = {
            "version": 1,
            "inventoryDigest": "d" * 64,
            "method": "docker-domain-restart-v1",
            "domain": "test-domain",
            "operationId": self.id,
            "revision": operation["request"]["revision"],
            "runtime": {"fixture": "verified separately"},
            "reconciliation": {"fixture": "verified separately"},
        }
        self.client.set(evidence_key(self.id), encoded(proof))
        return proof

    def test_barrier_freezes_live_owner_release_and_successors(self):
        with mutation_gate(client=self.client, wait_seconds=0):
            status = self.recovery.status()
            self.assertEqual(status["state"], "occupied")
            self.begin(status["revision"])
            frozen = self.client.get(GATE_KEY)
            with self.assertRaises(MutationGateUnavailable):
                transaction_opened("http://unregistered/transaction")
            self.assertEqual(self.client.get(GATE_KEY), frozen)
        self.assertEqual(self.recovery.status()["state"], "recovery_in_progress")
        with self.assertRaises(MutationGateUnavailable):
            with mutation_gate(client=self.client, wait_seconds=0):
                self.fail("Barrier must block new writers")

    def test_recovery_never_infers_death_from_age_or_uncertainty(self):
        self.begin()
        with self.assertRaises(MutationGateUnavailable):
            self.recovery.finish(operation_id=self.id, actor="urn:test:operator")
        self.assertIsNotNone(self.client.get(GATE_KEY))

    def test_exact_begin_retry_and_conflicting_retry(self):
        first = self.begin()
        self.assertEqual(self.begin(first["request"]["revision"]), first)
        with self.assertRaises(MutationGateUnavailable):
            self.recovery.begin(
                operation_id=self.id,
                expected_revision=first["request"]["revision"],
                actor="urn:other",
                reason=first["request"]["reason"],
            )

    def test_two_recoverers_only_one_freezes_owner(self):
        revision = self.retain()
        ready = threading.Barrier(2)

        def begin(_):
            ready.wait()
            try:
                return self.begin(revision, str(uuid4()))["operationId"]
            except MutationGateUnavailable:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(begin, range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_old_revision_and_legacy_protocol_are_refused(self):
        old = self.retain()
        record = json.loads(self.client.get(GATE_KEY))
        record["revision"] += 1
        self.client.set(GATE_KEY, encoded(record))
        with self.assertRaises(MutationGateUnavailable):
            self.begin(old)
        record.pop("recoveryProtocol")
        self.client.set(GATE_KEY, encoded(record))
        with self.assertRaises(MutationGateUnavailable):
            self.begin(self.recovery.status()["revision"])

    def test_release_audit_survives_lost_response_and_successor(self):
        self.begin()
        self.proof()
        with patch(
            "oldaplib.src.writer_recovery._durable",
            side_effect=MutationGateUnavailable("lost acknowledgement"),
        ):
            with self.assertRaises(MutationGateUnavailable):
                self.recovery.finish(operation_id=self.id, actor="urn:test:operator")
        result = self.recovery.operation(self.id)
        self.assertEqual(result["state"], "completed")
        with mutation_gate(client=self.client, wait_seconds=0):
            successor = self.client.get(GATE_KEY)
            self.assertEqual(
                self.recovery.finish(operation_id=self.id, actor="urn:test:second"),
                result,
            )
            self.assertEqual(self.client.get(GATE_KEY), successor)
        self.server.kill()
        self.server.wait(timeout=10)
        self.start_server()
        self.assertEqual(
            WriterRecovery(
                self.client, "test-domain", inventory_digest="d" * 64
            ).operation(self.id),
            result,
        )

    def test_active_or_uncertain_controller_prevents_release(self):
        self.begin()
        self.proof()
        self.client.set(CONTROLLER_KEY, "active controller")
        with self.assertRaises(MutationGateUnavailable):
            self.recovery.finish(operation_id=self.id, actor="urn:test:operator")
        self.assertIsNotNone(self.client.get(GATE_KEY))

    def test_evidence_bound_to_exact_domain_and_revision(self):
        self.begin()
        proof = self.proof()
        self.assertEqual(
            self.recovery.readiness(self.recovery.operation(self.id)), "ready"
        )
        for field, value in (
            ("domain", "other"),
            ("revision", "0" * 64),
            ("operationId", str(uuid4())),
        ):
            with self.subTest(field=field):
                self.client.set(evidence_key(self.id), encoded({**proof, field: value}))
                with self.assertRaises(MutationGateUnavailable):
                    self.recovery.finish(
                        operation_id=self.id, actor="urn:test:operator"
                    )

    def test_bad_store_or_malformed_record_is_not_free(self):
        self.client.set(GATE_KEY, "corrupt")
        self.assertEqual(self.recovery.status()["state"], "store_unavailable")

    def test_controller_failure_retains_its_nonexpiring_record(self):
        self.begin()
        with (
            patch(
                "oldaplib.src.writer_recovery_operator.inventory_digest",
                return_value="d" * 64,
            ),
            patch(
                "oldaplib.src.writer_recovery_operator.DockerDomain",
                side_effect=RuntimeError("unreachable member"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                prepare_evidence(self.client, {"domain": "test-domain"}, self.id)
        self.assertEqual(self.client.ttl(CONTROLLER_KEY), -1)
        self.assertIsNotNone(self.client.get(GATE_KEY))

    def test_real_deployment_acl_prevents_api_manufacturing_evidence(self):
        # Read the actual Jinja template so protocol additions cannot silently
        # outrun the deployed Redis permissions. Only test credentials are used.
        import jinja2
        import hashlib

        template = (
            Path(__file__).resolve().parents[3]
            / "oldap-setup/templates/writer-users.acl.j2"
        )
        env = jinja2.Environment()
        env.filters["hash"] = lambda value, name: hashlib.new(
            name, value.encode()
        ).hexdigest()
        acl = env.from_string(template.read_text()).render(
            oldap_writer_password="a" * 64,
            oldap_writer_recovery_enabled=True,
            oldap_writer_recovery_password="b" * 64,
            oldap_writer_operator_password="c" * 64,
        )
        for line in acl.splitlines():
            if line.startswith("user ") and not line.startswith("user default"):
                _, name, *rules = line.split()
                self.client.execute_command("ACL", "SETUSER", name, "reset", *rules)
        api = Redis(
            unix_socket_path=self.socket,
            decode_responses=True,
            username="recovery-api",
            password="b" * 64,
        )
        operator = Redis(
            unix_socket_path=self.socket,
            decode_responses=True,
            username="recovery-operator",
            password="c" * 64,
        )
        writer = Redis(
            unix_socket_path=self.socket,
            decode_responses=True,
            username="writer",
            password="a" * 64,
        )
        for client, key in (
            (api, evidence_key(self.id)),
            (writer, RECOVERY_BARRIER_KEY),
            (operator, GATE_KEY),
        ):
            with self.assertRaises(ResponseError):
                client.set(key, "forged")
            with self.assertRaises(ResponseError):
                client.eval(
                    "return redis.call('SET',KEYS[1],ARGV[1])", 1, key, "forged"
                )
        with mutation_gate(client=writer, wait_seconds=0):
            mark_gate_uncertain()
        api_recovery = WriterRecovery(api, "test-domain", inventory_digest="d" * 64)
        api_recovery.begin(
            operation_id=self.id,
            expected_revision=api_recovery.status()["revision"],
            actor="urn:test:operator",
            reason="Inspect interrupted operation",
        )
        self.assertEqual(
            api_recovery.readiness(api_recovery.operation(self.id)), "awaiting_operator"
        )
        domain = Mock()
        domain.fence.return_value = {
            "databaseContainer": "f" * 64,
            "startedAt": "new-process",
        }
        domain.containers.return_value = ["f" * 64]
        domain.run.return_value = json.dumps(
            [{"State": {"Running": True, "StartedAt": "new-process"}}]
        )
        with (
            patch(
                "oldaplib.src.writer_recovery_operator.inventory_digest",
                return_value="d" * 64,
            ),
            patch(
                "oldaplib.src.writer_recovery_operator.DockerDomain",
                return_value=domain,
            ),
            patch(
                "oldaplib.src.writer_recovery_operator.read_reconciliation",
                return_value={"observed": "reviewed RDF"},
            ),
        ):
            config = {"domain": "test-domain", "databaseService": "graphdb"}
            prepare_evidence(operator, config, self.id)
            prepare_evidence(operator, config, self.id, report={"review": "fixture"})
        self.client.execute_command(
            "ACL",
            "SETUSER",
            "recovery-api",
            "resetkeys",
            "~" + GATE_KEY,
            "~" + RECOVERY_BARRIER_KEY,
            "%R~" + PREFIX + "operation:*",
            "%R~" + PREFIX + "evidence:*",
            "%R~" + CONTROLLER_KEY,
        )
        with self.assertRaises(ResponseError):
            api_recovery.finish(operation_id=self.id, actor="urn:test:operator")
        self.assertIsNotNone(self.client.get(GATE_KEY))
        self.assertEqual(self.client.get(RECOVERY_BARRIER_KEY), self.id)
        self.client.execute_command(
            "ACL", "SETUSER", "recovery-api", "~" + PREFIX + "operation:*"
        )
        self.assertEqual(
            api_recovery.finish(operation_id=self.id, actor="urn:test:operator")[
                "state"
            ],
            "completed",
        )
        for client in (api, operator, writer):
            client.close()


class DockerDomainTest(unittest.TestCase):
    def test_reconciliation_observes_configured_endpoint_and_rejects_mismatch(self):
        operation = {
            "request": {"revision": "r"},
            "owner": {"transactions": ["http://untrusted.invalid/transaction"]},
        }
        conclusion = {
            "outcome": "committed",
            "explanation": "The affected RDF and operation receipt match the intended change.",
            "checks": ["state"],
        }
        report = {
            "revision": "r",
            "operator": "fixture-operator",
            "checks": [
                {
                    "label": "state",
                    "query": "ASK { GRAPH <urn:test:data> { <urn:test:item> <urn:test:status> <urn:test:archived> } }",
                    "expected": {"boolean": True},
                }
            ],
            "transactions": {"http://untrusted.invalid/transaction": conclusion},
            "unregisteredRequests": conclusion,
        }
        for observed in (True, False):
            response = Mock(status_code=200)
            response.iter_content.return_value = [
                json.dumps({"boolean": observed}).encode()
            ]
            with patch("oldaplib.src.writer_recovery_operator.requests.post") as post:
                post.return_value.__enter__.return_value = response
                if observed:
                    result = read_reconciliation(
                        {
                            "queryEndpoint": "https://configured.test/repositories/fixture"
                        },
                        report,
                        operation,
                    )
                    self.assertEqual(
                        result["checks"]["state"]["result"], {"boolean": True}
                    )
                else:
                    with self.assertRaises(ValueError):
                        read_reconciliation(
                            {
                                "queryEndpoint": "https://configured.test/repositories/fixture"
                            },
                            report,
                            operation,
                        )
                self.assertEqual(
                    post.call_args.args,
                    ("https://configured.test/repositories/fixture",),
                )
                self.assertIs(post.call_args.kwargs["allow_redirects"], False)

    def config(self):
        return {
            "nodes": [
                {
                    "name": "one",
                    "transport": "local",
                    "project": "oldap",
                    "writerServices": ["oldap-api"],
                },
                {
                    "name": "two",
                    "transport": "ssh",
                    "target": "ops@vm2",
                    "project": "oldap",
                    "writerServices": ["oldap-api"],
                },
            ],
            "databaseNode": "one",
            "databaseService": "graphdb",
        }

    def test_unreachable_member_prevents_first_destructive_step(self):
        domain = DockerDomain(self.config())

        def list_containers(node, service):
            if node["name"] == "two":
                raise TimeoutError("unreachable")
            return ["a" * 64]

        with (
            patch.object(domain, "containers", side_effect=list_containers),
            patch.object(domain, "run") as run,
        ):
            with self.assertRaises(TimeoutError):
                domain.fence()
            run.assert_not_called()

    def test_all_member_removal_precedes_verified_database_stop_start(self):
        domain = DockerDomain(self.config())
        calls = []

        def containers(node, service):
            if service == "graphdb":
                return ["d" * 64]
            return (
                [node["name"][0] * 64] if not any(c[0] == "rm" for c in calls) else []
            )

        states = iter(
            [
                {"State": {"StartedAt": "before"}},
                {"State": {"Running": False, "Pid": 0, "FinishedAt": "stopped"}},
                {"State": {"Running": True, "StartedAt": "after"}},
            ]
        )

        def run(node, *args):
            calls.append(args)
            return json.dumps([next(states)]) if args[0] == "inspect" else ""

        with (
            patch.object(domain, "containers", side_effect=containers),
            patch.object(domain, "run", side_effect=run),
        ):
            proof = domain.fence()
        self.assertEqual(
            [c[0] for c in calls],
            ["inspect", "rm", "rm", "stop", "inspect", "start", "inspect"],
        )
        self.assertEqual(proof["startedAt"], "after")

    def test_reconciliation_rejects_updates_and_wrong_revisions_before_network(self):
        operation = {"request": {"revision": "r"}, "owner": {"transactions": []}}
        report = {"revision": "wrong", "checks": []}
        with patch("oldaplib.src.writer_recovery_operator.requests.post") as post:
            with self.assertRaises(ValueError):
                read_reconciliation({}, report, operation)
            report.update(
                revision="r",
                checks=[{"label": "bad", "query": "DELETE WHERE { ?s ?p ?o }"}],
            )
            with self.assertRaises(Exception):
                read_reconciliation(
                    {"queryEndpoint": "http://graphdb:7200/repositories/test"},
                    report,
                    operation,
                )
            post.assert_not_called()
