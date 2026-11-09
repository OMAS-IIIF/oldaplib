"""Exercise the built persistent service on owned storage and real token validation.

No installed service or source dataset is touched. Checks admission beyond the
old budget, durable replay protection, hidden metadata, signals, hard crashes,
fulltext recovery, private routes and disabled diagnostic headers.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/migration'))
from probe_fuseki_identity import IdentityPeer
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_fulltext import jena_fulltext_fields, jena_fulltext_pattern
from oldaplib.src.objectfactory import FTSearchFilter


def run(distribution, java_home, output, *, backup_check=None, transaction_count=300):
    """Run actual HTTP against the packaged artifact; retain sanitized evidence."""
    if transaction_count < 1:
        raise ValueError('Positive transaction count required')
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=False)
    peer = IdentityPeer()
    process = None
    log = (output / 'service.log').open('w')
    checks = []
    report = {'status': 'failed', 'checks': checks,
              'build': json.loads((distribution / 'build.json').read_text())}
    with socket.socket() as available:
        available.bind(('127.0.0.1', 0))
        port = available.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    headers = {'Authorization': 'Bearer ' + peer.token('actor'), 'X-Oldap-Service-Key': peer.transport_secret}
    other = {**headers, 'Authorization': 'Bearer ' + peer.token('other')}
    bootstrap, fulltext = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    config = output / 'service.properties'
    config.write_text(f'''dataset={output / 'dataset'}
port={port}
transactionLifetimeMillis=500
identityUrl={peer.url}
identitySecret={peer.secret}
serviceSecret={peer.transport_secret}
bootstrapSecret={bootstrap}
fulltextSecret={fulltext}
''')
    config.chmod(0o600)

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print('PASS', name, flush=True)

    def start(init=False):
        nonlocal process
        environment = {**os.environ, 'JAVA_HOME': str(java_home), 'JAVA_HEAP_MB': '512',
                       'PROBE_FULLTEXT_FAULTS': 'yes', 'PROBE_TEXT_FIXTURE': 'yes'}
        process = subprocess.Popen([str(distribution / 'start'), str(config), *(['--init'] if init else [])],
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=environment)
        for _ in range(300):
            if process.poll() is not None:
                raise RuntimeError('Service failed startup; inspect private log')
            try:
                if requests.get(base + '/health', timeout=.3).status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(.1)
        raise TimeoutError('Service startup timed out')

    def stop(hard=False):
        nonlocal process
        if process is not None:
            process.kill() if hard else process.terminate()
            process.wait(timeout=80)
            process = None

    def send(operation, identifier=None, body='', expected=200, extra=None):
        response = requests.post(base + '/tx/' + operation + '/' + str(identifier or uuid4()),
                                 data=body, headers=extra or headers, timeout=15)
        if response.status_code != expected:
            raise AssertionError(f'{operation}: expected {expected}, got {response.status_code}')
        return response

    def ask(subject):
        return send('READ', body=f'ASK {{ GRAPH <urn:service:test> {{ <{subject}> ?p ?o }} }}').json()['boolean']

    try:
        start(True)
        check('Closed stdin does not stop the service', process.poll() is None)
        check('No raw SPARQL route', requests.post(base + '/query', data='ASK {}', timeout=5).status_code == 404)
        check('Transport credential required', send('READ', body='ASK {}', expected=401, extra={'Authorization': headers['Authorization']}).status_code == 401)
        peer.mode = 'unavailable'
        send('READ', body='ASK {}', expected=503)
        peer.mode = 'normal'
        check('Unavailable identity verification fails closed', True)
        ids = []
        for number in range(transaction_count):
            identifier = uuid4()
            send('BEGIN', identifier)
            send('UPDATE', identifier, f'INSERT DATA {{ GRAPH <urn:service:test> {{ <urn:record:{number}> <urn:value> {number} }} }}')
            # Neither commit-loss nor debug flags can alter the built service.
            reply = send('COMMIT', identifier, extra={**headers, 'X-Probe-Lose-Reply': 'before', 'X-Probe-Timing': 'yes'})
            assert reply.text == 'committed' and 'X-Probe-Dispatch-Nanos' not in reply.headers
            ids.append(identifier)
        check(f'{transaction_count} sequential commits succeed', ask(f'urn:record:{transaction_count - 1}'))
        check('Probe fault flags and diagnostic headers are inert', True)
        committed = ids[0]
        send('BEGIN', committed, expected=409)
        send('STATUS', committed, expected=403, extra=other)
        check('Committed identifier and receipt remain actor-bound', send('STATUS', committed).text == 'committed')
        aborted = uuid4()
        send('BEGIN', aborted)
        send('UPDATE', aborted, 'INSERT DATA { GRAPH <urn:service:test> { <urn:aborted> <urn:value> 1 } }')
        send('ABORT', aborted)
        send('BEGIN', aborted, expected=409)
        check('Abort consumes identifier without committing data', not ask('urn:aborted') and send('STATUS', aborted).text == 'unknown')
        expired = uuid4()
        send('BEGIN', expired)
        time.sleep(.7)
        send('COMMIT', expired, expected=409)
        send('BEGIN', expired, expected=409)
        check('Expiry releases writer but consumes identifier', True)
        active = uuid4()
        send('BEGIN', active)
        send('UPDATE', active, 'INSERT DATA { GRAPH <urn:service:test> { <urn:stopped> <urn:value> 1 } }')
        send('ABORT', active, expected=403, extra=other)
        stop()
        start()
        for identifier in (committed, aborted, expired, active):
            send('BEGIN', identifier, expected=409)
        check('Graceful restart preserves all admissions and committed data', ask(f'urn:record:{transaction_count - 1}') and not ask('urn:stopped'))
        check('Restart does not invent a commit receipt', send('STATUS', active).text == 'unknown')
        crashed = uuid4()
        send('BEGIN', crashed)
        send('UPDATE', crashed, 'INSERT DATA { GRAPH <urn:service:test> { <urn:crashed> <urn:value> 1 } }')
        stop(True)
        start()
        send('BEGIN', crashed, expected=409)
        check('Hard crash preserves reservation and rolls back pending data', not ask('urn:crashed') and send('STATUS', crashed).text == 'unknown')
        check('Committed receipt survives hard crash', send('STATUS', committed).text == 'committed')
        hidden = send('READ', body='ASK { GRAPH <urn:probe:http-commits> { ?s ?p ?o } }').json()
        check('Admission and receipt metadata stay invisible', not hidden['boolean'])
        forbidden = uuid4()
        send('BEGIN', forbidden)
        send('UPDATE', forbidden, 'CLEAR GRAPH <urn:probe:http-commits>', expected=400)
        send('COMMIT', forbidden, expected=409)
        check('Application cannot clear protected admission metadata', send('STATUS', committed).text == 'committed')
        # Inspect empty managed configuration through its private credential path.
        admin = {**headers, 'X-Oldap-Fulltext-Admin-Key': fulltext, 'X-Probe-Fulltext-Failure': 'after-publish'}
        state = send('FULLTEXT_STATE', body=json.dumps({'project': 'demo'}), extra=admin).json()
        check('Managed fulltext administration is enabled', state['configuration'] is None)
        configured = {'graph': 'https://example.org/demo/data',
                      'fields': {'title': ['https://schema.org/name']}}
        state = send('FULLTEXT_APPLY', body=json.dumps({'project': 'demo',
            'configuration': configured, 'expectedRevision': None}), extra=admin).json()
        check('Production ignores fulltext fault injection', state['status'] == 'active')
        text_id = uuid4()
        send('BEGIN', text_id)
        send('UPDATE', text_id, 'INSERT DATA { GRAPH <https://example.org/demo/data> { <urn:text> <https://schema.org/name> "Zürich" } }')
        send('COMMIT', text_id)

        def text_hits():
            fields = jena_fulltext_fields({'fields': configured['fields']}, Context(name='SERVICE_CHECK'))
            pattern = jena_fulltext_pattern('<' + configured['graph'] + '>',
                [FTSearchFilter('title', 'zurich')], fields, 'score')
            query = 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> SELECT DISTINCT ?res WHERE { ' + pattern + ' }'
            result = send('FULLTEXT_READ', body=json.dumps({'project': 'demo',
                'revision': state['revision'], 'query': query})).json()
            return {row['res']['value'] for row in result['results']['bindings']}

        check('Managed index and folding analyzer serve committed text', text_hits() == {'urn:text'})
        stop(True)
        start()
        restored = send('FULLTEXT_STATE', body=json.dumps({'project': 'demo'}), extra=admin).json()
        check('Fulltext configuration and searchable data survive hard restart',
              restored['revision'] == state['revision'] and text_hits() == {'urn:text'}
              and send('STATUS', text_id).text == 'committed')
        check('Fulltext administration requires its separate key', send('FULLTEXT_STATE', body=json.dumps({'project': 'demo'}), expected=403).status_code == 403)
        response = requests.post(base + '/tx/bootstrap', data='ASK {}', headers={
            'X-Oldap-Service-Key': peer.transport_secret, 'X-Oldap-Bootstrap-Key': bootstrap}, timeout=5)
        check('Credential bootstrap remains available', response.status_code == 200)
        if backup_check is not None:
            backup_check(output=output, distribution=distribution, peer=peer,
                         config=config, start=start, stop=stop, send=send,
                         text_hits=text_hits, committed=committed, aborted=aborted,
                         check=check, headers=headers, base=base)
        stop()
        # Reopen fails instead of silently creating an empty replacement dataset.
        missing = output / 'missing.properties'
        missing.write_text(config.read_text().replace(str(output / 'dataset'), str(output / 'missing-dataset')))
        missing.chmod(0o600)
        result = subprocess.run([str(distribution / 'start'), str(missing)], env={**os.environ, 'JAVA_HOME': str(java_home)}, stdout=log, stderr=log, timeout=30)
        check('Missing storage requires explicit initialization', result.returncode != 0 and not (output / 'missing-dataset').exists())
        report['status'] = 'passed'
    finally:
        stop()
        peer.close()
        log.close()
        (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distribution', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.distribution.resolve(), args.java_home.resolve(), args.output.resolve())
