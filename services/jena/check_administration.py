"""Exercise the official Fuseki UI/protocols on an owned, disposable dataset.

Verifies shared transactions, protected receipts, uploads, text-index replacement,
authentication and restart without touching an installed service or real data.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
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


def run(distribution, java_home, output, *, compaction=False, loopback=False):
    """Start the built artifact; retain sanitized evidence and private diagnostics."""
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=False)
    peer = IdentityPeer()
    def port():
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]
    service_port, admin_port = port(), port()
    base, admin = f'http://127.0.0.1:{service_port}', f'http://127.0.0.1:{admin_port}'
    origin = 'http://127.0.0.1:3030' if loopback else 'https://fuseki.home.org'
    key, bootstrap, fulltext = (secrets.token_urlsafe(32) for _ in range(3))
    auth = {'X-Oldap-Admin-Key': key, 'Origin': origin}
    api_auth = {'X-Oldap-Service-Key': peer.transport_secret, 'Authorization': 'Bearer ' + peer.token('actor')}
    config = output / 'service.properties'
    config.write_text(f'''dataset={output / 'dataset'}
port={service_port}
transactionLifetimeMillis=10000
identityUrl={peer.url}
identitySecret={peer.secret}
serviceSecret={peer.transport_secret}
bootstrapSecret={bootstrap}
fulltextSecret={fulltext}
adminPort={admin_port}
adminSecret={key}
adminOrigin={origin}
''')
    if loopback:
        with config.open('a') as stream:
            stream.write('adminLoopback=true\n')
    if compaction:
        from datetime import datetime, timedelta, timezone
        instant = datetime.now(timezone.utc)
        window_start = (instant - timedelta(hours=2)).strftime('%H:%M')
        window_end = (instant + timedelta(hours=2)).strftime('%H:%M')
        with config.open('a') as stream:
            stream.write('compactionCheckSeconds=60\ncompactionMinSeconds=60\ncompactionGrowthBytes=1048576\ncompactionGrowthRatio=2.0\n')
            stream.write(f'compactionZone=UTC\ncompactionWindowStart={window_start}\ncompactionWindowEnd={window_end}\n')
    config.chmod(0o600)
    checks, process = [], None
    log = (output / 'service.log').open('w')
    def check(name, condition):
        assert condition, name
        checks.append(name)
        print('PASS', name, flush=True)
    def start(init=False):
        nonlocal process
        process = subprocess.Popen([str(distribution / 'start'), str(config), *(['--init'] if init else [])],
            env={**os.environ, 'JAVA_HOME': str(java_home), 'JAVA_HEAP_MB': '512'}, stdout=log, stderr=log)
        for _ in range(200):
            if process.poll() is not None:
                raise RuntimeError('Startup failed; see private service log')
            try:
                if requests.get(admin + '/$/ping', headers=auth, timeout=.3).status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(.1)
        raise TimeoutError('Administration startup')
    def api(op, body='', identifier=None, extra=None):
        r = requests.post(base + '/tx/' + op + '/' + str(identifier or uuid4()), data=body,
                          headers={**api_auth, **(extra or {})}, timeout=20)
        r.raise_for_status()
        return r
    def update(text):
        r = requests.post(admin + '/oldap/update', headers={**auth, 'Content-Type':'application/sparql-update'}, data=text.encode(), timeout=20)
        r.raise_for_status()
        return r
    def query(text):
        r = requests.post(admin + '/oldap/query', headers={**auth, 'Accept':'application/sparql-results+json'}, data={'query':text}, timeout=20)
        r.raise_for_status()
        return r.json()
    try:
        if loopback:
            accepted_config = config.read_text()
            for name, invalid in (
                ('HTTP requires explicit loopback', accepted_config.replace('adminLoopback=true', 'adminLoopback=false')),
                ('Loopback HTTP rejects nonlocal origins', accepted_config.replace(origin, 'http://example.org')),
            ):
                config.write_text(invalid)
                refused = subprocess.run([str(distribution / 'start'), str(config)],
                    env={**os.environ, 'JAVA_HOME': str(java_home), 'JAVA_HEAP_MB': '512'},
                    capture_output=True, text=True, timeout=20)
                check(name, refused.returncode != 0 and 'Administrator origin requires' in refused.stderr)
            config.write_text(accepted_config)
        start(True)
        check('Native Apache UI', 'Apache Jena Fuseki' in requests.get(admin, headers=auth).text)
        for path in ['/', '/$/server', '/oldap/query', '/$/datasets']:
            check('Private administrator credential: ' + path, requests.get(admin + path).status_code == 401)
        server = requests.get(admin + '/$/server', headers=auth).json()
        check('Native server description', server['version'] == '6.2.0' and server['datasets'][0]['ds.name'] == '/oldap')
        check('Dataset lifecycle protected', requests.delete(admin + '/$/datasets/oldap', headers=auth).status_code == 403)
        check('Cross-origin writes refused', requests.post(admin + '/oldap/update', headers={**auth, 'Origin':'https://evil.example'}, data='CLEAR ALL').status_code == 403)
        update('INSERT DATA { GRAPH <urn:admin:data> { <urn:admin:item> <urn:value> 1 } }')
        check('Admin update visible through API', api('READ', 'ASK { GRAPH <urn:admin:data> { <urn:admin:item> <urn:value> 1 } }').json()['boolean'])
        identifier = uuid4()
        api('BEGIN', identifier=identifier)
        api('UPDATE', 'INSERT DATA { GRAPH <urn:admin:data> { <urn:api:item> <urn:value> 2 } }', identifier)
        check('Console cannot see uncommitted API writes', not query('ASK { GRAPH <urn:admin:data> { <urn:api:item> ?p ?o } }')['boolean'])
        # Native writes serialize with the existing API writer instead of opening
        # another TDB instance or bypassing its transaction boundary.
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(update, 'INSERT DATA { GRAPH <urn:admin:data> { <urn:parallel:item> <urn:value> 3 } }')
            time.sleep(.3)
            check('Native writer waits for API transaction', not pending.done())
            api('COMMIT', identifier=identifier)
            pending.result(timeout=20)
        check('API commit visible through console', query('ASK { GRAPH <urn:admin:data> { <urn:api:item> ?p ?o } }')['boolean'])
        r = requests.post(admin + '/oldap/data?graph=urn:upload:test', headers={**auth, 'Content-Type':'text/turtle'}, data='<urn:upload:item> <urn:value> "uploaded" .', timeout=10)
        check('Native Graph Store upload', r.status_code in [200,201,204] and query('ASK { GRAPH <urn:upload:test> { <urn:upload:item> ?p ?o } }')['boolean'])
        check('RDF 1.2 query', query('SELECT ?t { BIND(<<( <urn:s> <urn:p> <urn:o> )>> AS ?t) }')['results']['bindings'][0]['t']['type'] == 'triple')
        check('Receipt graph hidden', not query('ASK { GRAPH <urn:probe:http-commits> { ?s ?p ?o } }')['boolean'])
        denied = requests.post(admin + '/oldap/update', headers={**auth, 'Content-Type':'application/sparql-update'}, data='CLEAR GRAPH <urn:probe:http-commits>')
        check('Receipt graph write refused', denied.status_code >= 400 and api('STATUS', identifier=identifier).text == 'committed')
        cfg = {'graph':'urn:admin:data', 'fields':{'title':['http://schema.org/name']}}
        extra = {'X-Oldap-Fulltext-Admin-Key':fulltext}
        state = api('FULLTEXT_APPLY', json.dumps({'project':'demo','configuration':cfg,'expectedRevision':None}), extra=extra).json()
        update('INSERT DATA { GRAPH <urn:admin:data> { <urn:text> <http://schema.org/name> "Zürich" } }')
        fields = jena_fulltext_fields({'fields':cfg['fields']}, Context(name='ADMIN_CHECK'))
        pattern = jena_fulltext_pattern('<'+cfg['graph']+'>', [FTSearchFilter('title','zurich')],fields,'score')
        text_query = 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> SELECT ?res WHERE { '+pattern+' }'
        check('Native writes update managed text index', any(r['res']['value']=='urn:text' for r in query(text_query)['results']['bindings']))
        cfg['fields']['extra'] = ['http://schema.org/description']
        api('FULLTEXT_APPLY', json.dumps({'project':'demo','configuration':cfg,'expectedRevision':state['revision']}), extra=extra)
        check('Console follows index replacement', any(r['res']['value']=='urn:text' for r in query(text_query)['results']['bindings']))
        if compaction:
            deadline = time.monotonic() + 90
            completed = output / 'dataset/compaction.properties'
            while (not completed.exists() or (output / 'dataset/compaction.pending').exists()) and time.monotonic() < deadline:
                assert process.poll() is None, 'Service exited during scheduled compaction'
                time.sleep(.5)
            check('Periodic check completed native compaction', completed.exists())
            check('Old generation retired after native switch', not (output / 'dataset/Data-0001').exists())
            check('Managed fulltext survives scheduled compaction', any(r['res']['value']=='urn:text' for r in query(text_query)['results']['bindings']))
            check('API receipt survives scheduled compaction', api('STATUS', identifier=identifier).text == 'committed')
            update('INSERT DATA { GRAPH <urn:admin:data> { <urn:after-compact> <http://schema.org/name> "Zürich" } }')
            check('Managed writes after compaction stay indexed', any(r['res']['value']=='urn:after-compact' for r in query(text_query)['results']['bindings']))
        process.terminate();process.wait(timeout=80);process=None
        start()
        check('Native writes survive restart', query('ASK { GRAPH <urn:upload:test> { <urn:upload:item> ?p ?o } }')['boolean'])
        check('API receipts survive restart', api('STATUS', identifier=identifier).text == 'committed')
        if compaction:
            process.terminate(); process.wait(timeout=80); process = None
            (output / 'dataset/compaction.pending').write_text('interrupted-test\n')
            result = subprocess.run([str(distribution / 'start'), str(config)],
                env={**os.environ, 'JAVA_HOME': str(java_home), 'JAVA_HEAP_MB': '512'},
                stdout=log, stderr=log, timeout=30)
            check('Interrupted compaction fences service restart', result.returncode != 0)

    finally:
        if process is not None:
            process.terminate();process.wait(timeout=80)
        peer.close()
        log.close()
        (output / 'results.json').write_text(json.dumps({'checks':checks}, indent=2)+'\n')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['distribution','java-home','output']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument("--compaction", action="store_true")
    parser.add_argument("--loopback", action="store_true")
    args=parser.parse_args()
    run(args.distribution.resolve(),args.java_home.resolve(),args.output.resolve(), compaction=args.compaction, loopback=args.loopback)
