"""Persistent-gate tests using an isolated Redis process and AOF directory."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from redis import Redis

from oldaplib.src.mutation_gate import (
    GATE_KEY,
    MutationGateUnavailable,
    inspect_gate,
    mark_gate_uncertain,
    mutation_gate,
    recover_gate,
    transaction_opened,
    transaction_closed,
)


@unittest.skipUnless(
    shutil.which("redis-server"),
    "redis-server is required for isolated persistence tests",
)
class MutationGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="oldap-as02-redis-")
        cls.socket = str(Path(cls.directory.name) / "redis.sock")
        cls.start_server()

    @classmethod
    def start_server(cls):
        cls.server = subprocess.Popen(
            [
                shutil.which("redis-server"),
                "--port",
                "0",
                "--unixsocket",
                cls.socket,
                "--dir",
                cls.directory.name,
                "--appendonly",
                "yes",
                "--appendfsync",
                "always",
                "--maxmemory-policy",
                "noeviction",
                "--save",
                "",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cls.client = Redis(
            unix_socket_path=cls.socket, decode_responses=True, socket_timeout=5
        )
        for _ in range(200):
            try:
                if cls.client.ping():
                    return
            except Exception:
                time.sleep(0.02)
        raise RuntimeError("Isolated Redis did not start.")

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=10)
        cls.directory.cleanup()

    def tearDown(self):
        # This dedicated process contains only this suite's generated gate.
        self.client.delete(GATE_KEY)
        self.client.execute_command("WAITAOF", 1, 0, 5000)

    def test_cache_clear_cannot_remove_writer_ownership(self):
        from oldaplib.src.cachesingleton import CacheSingletonRedis

        url = f"unix://{self.socket}?db=0"
        # Construct before activation to exercise the clear-time check as well.
        with patch.dict(os.environ, {"OLDAP_REDIS_URL": url}):
            with patch.dict(os.environ, {"OLDAP_ARCHIVE_POLICY_FILE": ""}):
                cache = CacheSingletonRedis()
            with patch.dict(
                os.environ,
                {
                    "OLDAP_ARCHIVE_POLICY_FILE": "/operator/policy.json",
                    "OLDAP_STAGING_LOCK_REDIS_URL": url,
                },
            ):
                with mutation_gate(client=self.client, wait_seconds=0):
                    with self.assertRaises(MutationGateUnavailable):
                        cache.clear()
                    self.assertIsNotNone(inspect_gate(self.client))
                    with self.assertRaises(MutationGateUnavailable):
                        CacheSingletonRedis()
                with patch.dict(
                    os.environ, {"OLDAP_REDIS_URL": f"unix://{self.socket}?db=2"}
                ):
                    CacheSingletonRedis().clear()

    def test_ownership_has_no_expiry_and_normal_exit_releases(self):
        with mutation_gate(client=self.client, wait_seconds=0):
            self.assertEqual(self.client.pttl(GATE_KEY), -1)
            with mutation_gate(client=self.client, wait_seconds=0):
                self.assertEqual(self.client.pttl(GATE_KEY), -1)
        self.assertIsNone(inspect_gate(self.client))

    def test_validation_failure_without_open_transaction_releases(self):
        with self.assertRaises(ValueError):
            with mutation_gate(client=self.client, wait_seconds=0):
                raise ValueError("validation rejected")
        self.assertIsNone(inspect_gate(self.client))

    def test_confirmed_transaction_end_releases(self):
        with mutation_gate(client=self.client, wait_seconds=0):
            transaction_opened("http://test/transactions/1")
            self.assertEqual(
                inspect_gate(self.client)["transactions"],
                ["http://test/transactions/1"],
            )
            transaction_closed("http://test/transactions/1")
        self.assertIsNone(inspect_gate(self.client))

    def test_unclosed_transaction_retains_gate(self):
        with mutation_gate(client=self.client, wait_seconds=0):
            transaction_opened("http://test/transactions/1")
        with self.assertRaises(MutationGateUnavailable):
            with mutation_gate(client=self.client, wait_seconds=0):
                self.fail("A successor must not enter")

    def test_uncertainty_cannot_be_cleared_by_later_abort(self):
        with mutation_gate(client=self.client, wait_seconds=0):
            transaction_opened("http://test/transactions/1")
            mark_gate_uncertain()
            transaction_closed("http://test/transactions/1")
        record = inspect_gate(self.client)
        self.assertTrue(record["uncertain"])
        self.assertEqual(record["transactions"], [])

    def test_crashed_worker_record_survives_redis_restart(self):
        script = """import os,sys
from redis import Redis
from oldaplib.src.mutation_gate import mutation_gate,transaction_opened
with mutation_gate(client=Redis(unix_socket_path=sys.argv[1],decode_responses=True),wait_seconds=0):
    transaction_opened("http://test/transactions/crashed")
    os._exit(17)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, self.socket], timeout=15, capture_output=True
        )
        self.assertEqual(result.returncode, 17, result.stderr.decode())
        record = inspect_gate(self.client)
        self.server.kill()
        self.server.wait(timeout=10)
        self.start_server()
        self.assertEqual(inspect_gate(self.client), record)
        with self.assertRaises(MutationGateUnavailable):
            with mutation_gate(client=self.client, wait_seconds=0):
                pass
        recover_gate(
            self.client,
            expected_token=record["token"],
            writer_terminated=True,
            outcomes_reconciled=True,
            confirm_transaction_ended=lambda url: url.endswith("/crashed"),
        )
        with mutation_gate(client=self.client, wait_seconds=0):
            self.assertNotEqual(inspect_gate(self.client)["token"], record["token"])

    def test_recovery_requires_acknowledgements_and_ended_transactions(self):
        with mutation_gate(client=self.client, wait_seconds=0):
            transaction_opened("http://test/transactions/1")
        record = inspect_gate(self.client)
        for terminated, reconciled, ended in (
            (False, True, True),
            (True, False, True),
            (True, True, False),
        ):
            with self.subTest(
                terminated=terminated, reconciled=reconciled, ended=ended
            ):
                with self.assertRaises(MutationGateUnavailable):
                    recover_gate(
                        self.client,
                        expected_token=record["token"],
                        writer_terminated=terminated,
                        outcomes_reconciled=reconciled,
                        confirm_transaction_ended=lambda url: ended,
                    )
                self.assertEqual(inspect_gate(self.client), record)

    def test_recovery_rejects_old_token(self):
        with mutation_gate(client=self.client, wait_seconds=0):
            mark_gate_uncertain()
        with self.assertRaises(MutationGateUnavailable):
            recover_gate(
                self.client,
                expected_token="old",
                writer_terminated=True,
                outcomes_reconciled=True,
                confirm_transaction_ended=lambda url: True,
            )
        self.assertIsNotNone(inspect_gate(self.client))


if __name__ == "__main__":
    unittest.main()
