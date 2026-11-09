"""Offline launchd fencing for explicitly reviewed, foreground MacBook services.

Only same-user GUI LaunchAgents are supported. Managed programs must not daemonize,
spawn detached writers or be started outside this inventory. API uses one threaded
process without the development reloader; GraphDB Desktop runs in one JVM. Runtime
control addresses launchd jobs, never a PID obtained from a stale Redis record.
"""

from contextlib import closing
import ctypes
from hashlib import sha256
import os
from pathlib import Path
import plistlib
import re
import select
import stat
import socket
import subprocess
import sys
import time


class _BSDInfo(ctypes.Structure):
    # Darwin SDK sys/proc_info.h, PROC_PIDTBSDINFO. Start time includes microseconds.
    _fields_ = [
        ("prefix", ctypes.c_uint32 * 12),
        ("names", ctypes.c_char * 48),
        ("suffix", ctypes.c_uint32 * 6),
        ("seconds", ctypes.c_uint64),
        ("microseconds", ctypes.c_uint64),
    ]


def process_identity(pid: int) -> dict:
    """Read a live kernel process generation; refuse missing/inaccessible processes."""
    library = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    library.proc_pidinfo.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    library.proc_pidinfo.restype = ctypes.c_int
    info = _BSDInfo()
    if library.proc_pidinfo(
        pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info)
    ) != ctypes.sizeof(info):
        raise ValueError("Cannot establish native process identity.")
    if info.prefix[3] != pid or info.prefix[5] != os.getuid():
        raise ValueError("Native process is not owned by this operator.")
    return {"pid": pid, "seconds": info.seconds, "microseconds": info.microseconds}


class LaunchdDomain:
    """Fence a closed inventory through launchd plus kernel exit notifications.

    Config contains nativeServices (label, plist, sha256), databaseService and
    runtime='macos-launchd-v1'. Plists are private and hash-pinned in the reviewed
    inventory. Every service is booted out before the database is bootstrapped;
    fresh API processes can then serve recovery reads behind the persistent barrier.
    """

    method = "macos-launchd-restart-v1"

    def __init__(self, config: dict):
        if sys.platform != "darwin":
            raise ValueError("Native control requires macOS.")
        self.config = config
        self.target = f"gui/{os.getuid()}"
        self.services = config["nativeServices"]
        labels = [item["label"] for item in self.services]
        if (
            len(labels) < 2
            or len(set(labels)) != len(labels)
            or config["databaseService"] not in labels
        ):
            raise ValueError(
                "A unique database and explicit writer inventory are required."
            )
        for item in self.services:
            if not re.fullmatch(r"org\.oldap\.[A-Za-z0-9.-]+", item["label"]):
                raise ValueError(
                    "Only explicitly managed OLDAP LaunchAgents are supported."
                )
            path = Path(item["plist"])
            if not path.is_absolute():
                raise ValueError("LaunchAgent path must be absolute.")
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                info = os.fstat(fd)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.getuid()
                    or info.st_mode & 0o077
                ):
                    raise ValueError("LaunchAgent must be private and operator-owned.")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    raw = stream.read()
            finally:
                os.close(fd)
            if sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("LaunchAgent differs from reviewed inventory.")
            plist = plistlib.loads(raw)
            if (
                plist.get("Label") != item["label"]
                or plist.get("AbandonProcessGroup") is not False
                or plist.get("KeepAlive") is not True
                or not 1 <= plist.get("ExitTimeOut", 0) <= 60
                or not plist.get("ProgramArguments")
                or not Path(plist["ProgramArguments"][0]).is_absolute()
            ):
                raise ValueError(
                    "LaunchAgent requires foreground supervision and bounded shutdown."
                )

    @staticmethod
    def run(*args: str) -> str:
        """Execute fixed launchctl argv; never shell commands or browser input."""
        return subprocess.run(
            ["/bin/launchctl", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        ).stdout

    def identity(self, item: dict) -> dict:
        """Match the loaded job to its pinned file and a live kernel generation."""
        output = self.run("print", f"{self.target}/{item['label']}")
        path = re.search(r"^\s*path = (.+)$", output, re.MULTILINE)
        pid = re.search(r"^\s*pid = (\d+)$", output, re.MULTILINE)
        if (
            not path
            or Path(path[1]).resolve() != Path(item["plist"]).resolve()
            or not pid
        ):
            raise ValueError(
                "Configured native job is not running from its reviewed plist."
            )
        return process_identity(int(pid[1]))

    def validate_owner(self, owner: dict) -> None:
        """Refuse a still-live writer outside this single-host service inventory.

        Missing PID is never release evidence: all services still need fencing,
        GraphDB restart and outcome reconciliation. A reused unrelated PID blocks
        conservatively rather than risking termination of that unrelated process.
        """
        if owner.get("host") != socket.gethostname():
            raise ValueError("Writer belongs to a different native host.")
        pid = owner.get("pid")
        if not isinstance(pid, int) or pid <= 1:
            raise ValueError("Invalid native writer identity.")
        managed = {
            self.identity(item)["pid"]
            for item in self.services
            if item["label"] != self.config["databaseService"]
        }
        if pid not in managed:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            raise ValueError("A live writer is outside the managed native inventory.")

    def verify(self, runtime: dict) -> None:
        """Reject checkpoint reuse after any managed service generation changes."""
        if {item["label"]: self.identity(item) for item in self.services} != runtime[
            "restartedServices"
        ]:
            raise ValueError("Native services changed after fencing; repeat fencing.")

    def fence(self) -> dict:
        """Observe exact old process exits, then start database followed by writers.

        All jobs must be reachable before any stop. kqueue subscriptions attach to
        process instances before control; a reused PID cannot satisfy NOTE_EXIT.
        A fork during control is outside this non-daemonizing topology and refuses
        proof. Any failure leaves the persistent offline-controller claim in place.
        """
        before = {item["label"]: self.identity(item) for item in self.services}
        pids = {entry["pid"] for entry in before.values()}
        processes = subprocess.run(
            ["/bin/ps", "-axo", "pid=,ppid=,pgid="],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        for line in processes.stdout.splitlines():
            pid, parent, group = map(int, line.split())
            if (parent in pids or group in pids) and pid not in pids:
                raise ValueError(
                    "Native topology contains child processes; foreground services are required."
                )
        with closing(select.kqueue()) as queue:
            events = [
                select.kevent(
                    identity["pid"],
                    filter=select.KQ_FILTER_PROC,
                    flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE,
                    fflags=select.KQ_NOTE_EXIT | select.KQ_NOTE_FORK,
                )
                for identity in before.values()
            ]
            queue.control(events, 0, 0)
            if {item["label"]: self.identity(item) for item in self.services} != before:
                raise ValueError(
                    "Native process changed while arming exit observation."
                )
            ordered = sorted(
                self.services,
                key=lambda item: item["label"] == self.config["databaseService"],
            )
            for item in ordered:
                self.run("bootout", f"{self.target}/{item['label']}")
            remaining = {entry["pid"] for entry in before.values()}
            deadline = time.monotonic() + 65
            while remaining and time.monotonic() < deadline:
                for event in queue.control(None, len(before), 1):
                    if (
                        event.flags & select.KQ_EV_ERROR
                        or event.fflags & select.KQ_NOTE_FORK
                    ):
                        raise ValueError(
                            "Unexpected process activity during native shutdown."
                        )
                    if event.fflags & select.KQ_NOTE_EXIT:
                        remaining.discard(event.ident)
            if remaining:
                raise ValueError("Kernel did not confirm all old native process exits.")
        # launchd can acknowledge bootout before the job record disappears.
        # Wait for both kernel exits above and namespace removal before bootstrap.
        for item in self.services:
            deadline = time.monotonic() + 15
            while True:
                result = subprocess.run(
                    ["/bin/launchctl", "print", f"{self.target}/{item['label']}"],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 113:
                    break
                if result.returncode != 0 or time.monotonic() >= deadline:
                    raise ValueError("Native job removal is unverifiable.")
                time.sleep(0.1)
        after = {}
        for item in reversed(ordered):
            self.run("bootstrap", self.target, item["plist"])
            deadline = time.monotonic() + 30
            while True:
                try:
                    after[item["label"]] = self.identity(item)
                    break
                except ValueError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)
            if after[item["label"]] == before[item["label"]]:
                raise ValueError("Native process generation did not change.")
        return {
            "terminatedServices": before,
            "restartedServices": after,
            "exitObservation": "kqueue-NOTE_EXIT",
            "observedAt": time.time(),
        }
