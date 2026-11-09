"""Native fencing acceptance uses only UUID-owned disposable LaunchAgents."""

from hashlib import sha256
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4

from oldaplib.src.writer_recovery_macos import LaunchdDomain, process_identity
from oldaplib.src.writer_recovery_operator import inventory_digest


@unittest.skipUnless(sys.platform == "darwin", "macOS launchd required")
class NativeRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="oldap-wr04-native-")
        self.path = Path(self.directory.name)
        self.services = []
        for kind in ("writer", "database"):
            label = f"org.oldap.wr04-{uuid4().hex}-{kind}"
            path = self.path / f"{label}.plist"
            path.write_bytes(
                plistlib.dumps(
                    {
                        "Label": label,
                        "ProgramArguments": [
                            sys.executable,
                            "-c",
                            "import time; time.sleep(600)",
                        ],
                        "KeepAlive": True,
                        "RunAtLoad": True,
                        "AbandonProcessGroup": False,
                        "ExitTimeOut": 2,
                    }
                )
            )
            path.chmod(0o600)
            self.services.append(
                {
                    "label": label,
                    "plist": str(path),
                    "sha256": sha256(path.read_bytes()).hexdigest(),
                }
            )
            LaunchdDomain.run("bootstrap", f"gui/{os.getuid()}", str(path))
        self.config = {
            "domain": "fixture",
            "runtime": "macos-launchd-v1",
            "nativeServices": self.services,
            "databaseService": self.services[-1]["label"],
            "queryEndpoint": "http://127.0.0.1:1/repositories/fixture",
        }
        self.domain = LaunchdDomain(self.config)
        for _ in range(100):
            try:
                for item in self.services:
                    self.domain.identity(item)
                break
            except ValueError:
                time.sleep(0.05)

    def tearDown(self):
        for item in self.services:
            subprocess.run(
                ["/bin/launchctl", "bootout", f"gui/{os.getuid()}/{item['label']}"],
                capture_output=True,
            )
        self.directory.cleanup()

    def test_real_kernel_exit_and_restart_checkpoint(self):
        runtime = self.domain.fence()
        self.domain.verify(runtime)
        self.assertEqual(runtime["exitObservation"], "kqueue-NOTE_EXIT")
        self.assertNotEqual(runtime["terminatedServices"], runtime["restartedServices"])
        # Reused PID alone cannot match the recorded kernel start generation.
        runtime["restartedServices"][self.services[0]["label"]]["microseconds"] += 1
        with self.assertRaises(ValueError):
            self.domain.verify(runtime)

    def test_changed_plist_rejected_before_control(self):
        Path(self.services[0]["plist"]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            LaunchdDomain(self.config)

    def test_unreachable_job_never_stops_database(self):
        before = self.domain.identity(self.services[1])
        LaunchdDomain.run("bootout", f"gui/{os.getuid()}/{self.services[0]['label']}")
        with self.assertRaises(subprocess.CalledProcessError):
            self.domain.fence()
        self.assertEqual(before, self.domain.identity(self.services[1]))

    def test_inventory_binds_native_plists(self):
        before = inventory_digest(self.config)
        self.services[0]["sha256"] = "0" * 64
        self.assertNotEqual(before, inventory_digest(self.config))

    def test_live_unmanaged_owner_or_other_host_is_refused(self):
        import socket

        for owner in (
            {"host": socket.gethostname(), "pid": os.getpid()},
            {"host": "unreachable-other-host", "pid": os.getpid()},
        ):
            with self.assertRaises(ValueError):
                self.domain.validate_owner(owner)

    def test_missing_process_is_not_evidence(self):
        with self.assertRaises(ValueError):
            process_identity(99999999)


if __name__ == "__main__":
    unittest.main()
