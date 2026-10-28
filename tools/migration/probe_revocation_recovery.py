"""Crash/restart acceptance using owned Unix-socket Redis and owned Fuseki.

Child writers abruptly exit without Python cleanup at selected boundaries.
Redis is killed and restarted against its retained AOF. This is process-crash,
not power-loss or replica-failover testing. No installed Redis service is used.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from uuid import UUID
from unittest.mock import patch

from redis import Redis
from redis.exceptions import RedisError
from oldaplib.src.helpers.authentication_revocation import AuthenticationRevocation
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_authentication_revocation import RevocationAttempt
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission
from oldaplib.src.helpers.revocation_journal import RevocationJournal
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from probe_revocation_connection import RevocationProbeConnection


def child_writer():
    """Save before transmission, then terminate at the requested crash boundary."""
    socket, dataset, operation, mode, endpoint = sys.argv[2:]
    command = AuthenticationRevocation(**json.loads(sys.stdin.read()))
    attempt = RevocationAttempt(command, UUID(operation))
    client = Redis(unix_socket_path=socket, decode_responses=True, socket_timeout=5)
    journal = RevocationJournal(client, dataset)
    if mode == 'before-send':
        journal.save(attempt)
        os._exit(71)
    def send(body):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        req = urllib.request.Request(endpoint, data=body.encode(), headers={'Content-Type': 'application/sparql-update'})
        with opener.open(req, timeout=15) as response:
            assert 200 <= response.status < 300
        # Database has answered, but execute never gets to read the receipt.
        os._exit(72)
    journal.execute(attempt, update=send, query=lambda _: (_ for _ in ()).throw(AssertionError('Unexpected query')))


def run_recovery_checks(update, query, check, output, base):
    """Own Redis; rediscover crash-interrupted attempts using only durable state."""
    executable = shutil.which('redis-server')
    if not executable:
        raise RuntimeError('redis-server required for isolated durable recovery acceptance')
    directory = output / 'revocation-redis'
    directory.mkdir(mode=0o700)
    # Keep the macOS Unix socket below its path-length limit.
    socket_dir = tempfile.TemporaryDirectory(prefix='oldap-j5-', dir='/tmp')
    socket = str(Path(socket_dir.name) / 'redis.sock')
    process = None
    log = (directory / 'redis.log').open('a')
    client = None

    def start():
        nonlocal process, client
        process = subprocess.Popen([executable, '--port', '0', '--unixsocket', socket,
            '--unixsocketperm', '700', '--dir', str(directory), '--appendonly', 'yes',
            '--appendfsync', 'always', '--maxmemory-policy', 'noeviction', '--save', ''], stdout=log, stderr=log)
        client = Redis(unix_socket_path=socket, decode_responses=True, socket_timeout=5)
        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError('Owned Redis exited')
            try:
                if client.ping():
                    return
            except (OSError, RedisError):
                pass
            time.sleep(.02)
        raise RuntimeError('Owned Redis readiness timeout')

    def restart_after_crash():
        nonlocal process, client
        client.close()
        process.kill()
        process.wait(timeout=10)
        start()

    context = Context(name='JENA_RECOVERY_PROBE')
    before = Xsd_dateTime('2026-10-27T13:00:00Z')
    after = Xsd_dateTime('2026-10-27T13:01:00Z')
    dataset = 'j5-owned-probe'

    def seed(name, denied=False):
        user = Iri(f'https://example.org/jena-recovery/{name}')
        update(context.sparql_context + f'''INSERT DATA {{ GRAPH oldap:admin {{
            {user.toRdf} a oldap:User ; oldap:authVersion "0"^^xsd:nonNegativeInteger ;
                dcterms:modified {before.toRdf} . }} }}''')
        command = AuthenticationRevocation.prepare(context=context, user=user,
            actor=Iri('https://example.org/unprivileged') if denied else user,
            expected=Xsd_nonNegativeInteger(0), previous_modified=before, modified=after)
        return RevocationAttempt.prepare(command)

    try:
        start()
        for name, mode, denied in [('before', 'before-send', False),
                                  ('after', 'after-send', False), ('denied', 'after-send', True)]:
            attempt = seed(name, denied)
            child = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--child',
                socket, dataset, str(attempt.receipt_id), mode, base + '/update'],
                input=json.dumps(asdict(attempt.command)), text=True, capture_output=True, timeout=25)
            assert child.returncode == (71 if mode == 'before-send' else 72), child.stderr
            restart_after_crash()
            journal = RevocationJournal(client, dataset)
            recovered = journal.load(attempt.receipt_id)
            assert recovered == attempt and attempt.receipt_id in set(journal.retained_ids())
            if denied:
                try:
                    recovered.confirmed(query)
                except OldapErrorNoPermission:
                    pass
                else:
                    raise AssertionError('Denial was lost across restart')
                check('Recovery: denied outcome survives writer exit and Redis SIGKILL')
            elif mode == 'before-send':
                assert not recovered.confirmed(query)
                check('Recovery: prepared unsent command survives writer exit and Redis SIGKILL')
                journal.execute(recovered, update=update, query=query)
                journal.execute(journal.load(attempt.receipt_id), update=update, query=query)
                check('Recovery: explicit exact retry after restart commits only once', recovered.confirmed(query))
            else:
                check('Recovery: committed outcome discovered after writer exit and Redis SIGKILL', recovered.confirmed(query))
            rows = query(context.sparql_context + f'''SELECT ?version WHERE {{ GRAPH oldap:admin {{
                {attempt.command.user} oldap:authVersion ?version . }} }}''')['results']['bindings']
            assert len(rows) == 1 and int(rows[0]['version']['value']) == (0 if denied else 1)

        # Actual public call: the test connection journals before handing off
        # to HTTP, and object/cache publication remains after known commit.
        attempt = seed('public')
        actor = Iri('https://example.org/jena-recovery/public')
        journal = RevocationJournal(client, dataset)
        con = None
        def verified_send(body):
            assert journal.load(con.attempt.receipt_id) == con.attempt
            update(body)
        con = RevocationProbeConnection(actor, verified_send, query, journal=journal)
        user = User(con=con, userIri=actor, userId='probe', familyName='Probe', givenName='Synthetic',
                    email='probe@example.org', credentials='$2b$unused', modified=before)
        with patch('oldaplib.src.user.CacheSingletonRedis') as cache, \
                patch('oldaplib.src.user.Xsd_dateTime.now', return_value=after):
            result = user.revoke_authentication()
            check('Recovery: public User call durably journals before HTTP and invalidates after commit',
                  int(result) == 1 and cache.return_value.delete.call_count == 1)
    finally:
        if client is not None:
            client.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        log.close()
        socket_dir.cleanup()


if __name__ == '__main__':
    child_writer()
