"""Exercise existing callbacks and HTTP session failures on an owned Jena dataset.

This is an experimental trusted-client transport, not a production connection.
Bearer tokens are fresh synthetic identities, not OLDAP login credentials.
"""
import argparse
from http.client import RemoteDisconnected
import json
import os
from pathlib import Path
import secrets
import selectors
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from probe_existing_callbacks import BridgeConnection, run as run_callbacks
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.iconnection import IConnection
from oldaplib.src.xsd.iri import Iri
from types import SimpleNamespace

# Shared only among processes owned by this probe; never persisted in result files.
TOKENS = ('Bearer ' + secrets.token_hex(32), 'Bearer ' + secrets.token_hex(32))


class HttpProbeConnection(BridgeConnection):
    """Reuse the IConnection test surface, replacing only its transport with HTTP.

    A transaction UUID is allocated before BEGIN and retained after uncertainty.
    Only a durable committed receipt converts a lost commit reply into success.
    UPDATE/QUERY requests are never automatically replayed.
    """
    lifetime_ms = 10000
    server_source = 'JenaHttpSessionProbe.java'
    route_prefix = ''

    def server_environment(self):
        """Supply only the credentials needed by this probe transport."""
        return dict(os.environ, PROBE_TOKEN_A=TOKENS[0], PROBE_TOKEN_B=TOKENS[1])

    def request_headers(self):
        """Additional service authentication, absent in the original experiment."""
        return {}

    def __init__(self, java, jar, directory, log, *, reopen=False):
        IConnection.__init__(self, context_name='JENA_CALLBACK_PROBE')
        self._userdata = SimpleNamespace(userIri=Iri('https://example.org/callback/actor'))
        self.active = False
        self.operations = []
        self.session = uuid4()
        self.lose_commit_reply = False
        environment = self.server_environment()
        self.process = subprocess.Popen([java, '-Xmx512m', '--class-path', str(jar),
            str(Path(__file__).with_name(self.server_source)), str(directory),
            'reopen' if reopen else 'new', str(self.lifetime_ms)], env=environment,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(self.process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=30):
                    raise TimeoutError('Owned HTTP server did not start')
            port = int(self.process.stdout.readline())
            self.base = f'http://localhost:{port}{self.route_prefix}'
        except Exception:
            self.process.kill()
            self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
            raise

    def send(self, operation, body='', *, session=None, token=None, lose_reply=False):
        """Send exactly one HTTP request; callers decide how to handle uncertainty."""
        headers = dict(self.request_headers(), Authorization=token if token is not None else TOKENS[0])
        if lose_reply:
            headers['X-Probe-Lose-Reply'] = 'yes' if lose_reply is True else lose_reply
        request = Request(f'{self.base}/{operation}/{session or self.session}',
                          data=body.encode(), headers=headers, method='POST')
        with urlopen(request, timeout=10) as response:
            return response.read().decode()

    def _request(self, operation, body=''):
        self.operations.append(operation)
        if operation == 'BEGIN':
            self.session = uuid4()
        try:
            result = self.send(operation, body, lose_reply=operation == 'COMMIT' and self.lose_commit_reply)
            if operation == 'COMMIT' and result != 'committed':
                raise ConnectionError('Commit response was not a confirmation')
            return result
        except HTTPError as error:
            if operation == 'COMMIT' and error.code >= 500:
                return self._reconcile_commit(error)
            raise OldapError(f'HTTP session refused ({error.code}): {error.read().decode()}') from error
        except (URLError, RemoteDisconnected, TimeoutError, ConnectionError) as error:
            if operation == 'COMMIT':
                return self._reconcile_commit(error)
            raise OldapError(f'HTTP {operation} outcome unknown; transaction {self.session}') from error

    def _reconcile_commit(self, error):
        """Confirm a receipt or retain uncertainty; never replay the mutation."""
        try:
            if self.send('STATUS') == 'committed':
                return 'committed'
        except (URLError, RemoteDisconnected, TimeoutError, ConnectionError):
            pass
        raise OldapError(f'HTTP COMMIT outcome unknown; transaction {self.session}') from error


def run(java, jar, output, *, connection_factory=HttpProbeConnection):
    """Run callback parity first, then transport-specific failure/isolation checks."""
    output.mkdir(parents=True, exist_ok=False)
    run_callbacks(java, jar, output / 'callbacks', connection_factory=connection_factory)
    checks = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print('PASS', name, flush=True)

    def refused(operation, code, **kwargs):
        try:
            con.send(operation, **kwargs)
        except HTTPError as error:
            return error.code == code
        return False

    update = 'INSERT DATA { GRAPH <urn:http:test> { <urn:item> <urn:value> 1 } }'
    ask = 'ASK { GRAPH <urn:http:test> { <urn:item> <urn:value> 1 } }'
    log = (output / 'http.log').open('a')
    con = connection_factory(java, jar, output / 'dataset', log)
    try:
        check('Unauthenticated request is rejected', refused('STATUS', 401, token='invalid'))
        con.transaction_start()
        first = con.session
        con.transaction_update(update)
        check('Owner reads uncommitted data over HTTP', con.transaction_query(ask)['boolean'])
        check('Independent HTTP reader sees committed snapshot only', not con.query(ask)['boolean'])
        check('Another identity cannot query or commit the session',
              refused('QUERY', 403, token=TOKENS[1], body=ask)
              and refused('COMMIT', 403, token=TOKENS[1])
              and refused('ABORT', 403, token=TOKENS[1]))
        check('Competing writer is rejected without disrupting owner',
              refused('BEGIN', 409, session=uuid4()) and con.transaction_query(ask)['boolean'])
        check('Missing receipt remains unknown while transaction is active', con.send('STATUS') == 'unknown')
        con.lose_commit_reply = True
        con.transaction_commit()
        check('Lost commit reply reconciles from atomic receipt', not con.active and con.send('STATUS') == 'committed' and con.query(ask)['boolean'])
        check('Committed identifier cannot begin again', refused('BEGIN', 409, session=first))
        check('Receipt cannot be read by another probe identity', refused('STATUS', 403, token=TOKENS[1]))
        # A hard stop after commit tests TDB2 recovery, not just graceful close.
        con.process.kill()
        con.process.wait(timeout=10)
        con.process.stdin.close()
        con.process.stdout.close()
        con = connection_factory(java, jar, output / 'dataset', log, reopen=True)
        check('Receipt and data survive server kill and restart', con.send('STATUS', session=first) == 'committed' and con.query(ask)['boolean'])
        check('Ordinary HTTP queries cannot read internal commit receipts',
              not con.query('ASK { GRAPH <urn:probe:http-commits> { ?s ?p ?o } }')['boolean'])
        con.transaction_start()
        try:
            con.transaction_update("INSERT DATA { GRAPH <urn:http:test> { <urn:partial> <urn:value> 9 } }; "
                                   "INSERT DATA { GRAPH <urn:probe:http-commits> { <urn:fake> <urn:owner> 'forged' } }")
        except OldapError:
            check('Receipt forgery aborts the complete HTTP transaction',
                  not con.query('ASK { GRAPH <urn:http:test> { <urn:partial> ?p ?o } }')['boolean']
                  and con.send('STATUS', session=first) == 'committed' and refused('COMMIT', 409))
        else:
            raise AssertionError('Receipt forgery was accepted')
        con.transaction_abort()

        con.transaction_start()
        con.transaction_update('INSERT DATA { GRAPH <urn:http:test> { <urn:uncertain> <urn:value> 4 } }')
        con.lose_commit_reply = 'before'
        commit_calls = con.operations.count('COMMIT')
        try:
            con.transaction_commit()
        except OldapError as error:
            check('Missing commit receipt raises uncertainty without automatic replay',
                  'outcome unknown' in str(error) and con.active
                  and con.operations.count('COMMIT') == commit_calls + 1
                  and con.send('STATUS') == 'unknown'
                  and not con.query('ASK { GRAPH <urn:http:test> { <urn:uncertain> ?p ?o } }')['boolean'])
        else:
            raise AssertionError('Unconfirmed commit reported success')
        con.transaction_abort()
        con.lose_commit_reply = False

        con.transaction_start()
        try:
            con.transaction_update('this is not SPARQL')
        except OldapError:
            pass
        else:
            raise AssertionError('Invalid update accepted')
        check('Query failure aborts the session', refused('COMMIT', 409))
        con.transaction_abort()

        con.transaction_start()
        con.transaction_update('INSERT DATA { GRAPH <urn:http:test> { <urn:crash> <urn:value> 2 } }')
        crashed = con.session
        con.process.kill()
        con.process.wait(timeout=10)
        con.process.stdin.close()
        con.process.stdout.close()
        con = connection_factory(java, jar, output / 'dataset', log, reopen=True)
        check('Server kill loses pending writes without inventing an abort receipt',
              not con.query('ASK { GRAPH <urn:http:test> { <urn:crash> ?p ?o } }')['boolean']
              and con.send('STATUS', session=crashed) == 'unknown')
        con.close()

        # A short absolute lifetime tests an abandoned HTTP client without
        # terminating the server. No activity extends the deadline.
        connection_factory.lifetime_ms = 500
        con = connection_factory(java, jar, output / 'dataset', log, reopen=True)
        con.transaction_start()
        expired = con.session
        con.transaction_update('INSERT DATA { GRAPH <urn:http:test> { <urn:expired> <urn:value> 3 } }')
        time.sleep(0.8)
        check('Abandoned session expires and cannot commit', refused('COMMIT', 409))
        check('Expiry rolls back pending writes', not con.query('ASK { GRAPH <urn:http:test> { <urn:expired> ?p ?o } }')['boolean'])
        con.transaction_start()
        check('Expiry releases writer and stale request cannot affect new session', refused('COMMIT', 409, session=expired))
        con.transaction_abort()
        check('Expired identifier cannot be reused within this server lifetime', refused('BEGIN', 409, session=expired))
        con.transaction_start()
        con.transaction_update('CLEAR ALL')
        con.transaction_commit()
        check('Application CLEAR ALL preserves earlier commit receipts',
              not con.query(ask)['boolean'] and con.send('STATUS', session=first) == 'committed')
        (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': checks}, indent=2) + '\n')
    finally:
        connection_factory.lifetime_ms = 10000
        if con.process.poll() is None:
            con.close()
        log.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', default='java')
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.java, args.jar, args.output.resolve())
