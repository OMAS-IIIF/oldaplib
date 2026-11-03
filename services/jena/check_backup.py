"""Restore an owned stopped service, actual Redis AOF and representative media.

Extends the built-service acceptance fixture. Verifies byte integrity, admin RDF,
login/roles, transactions and text on a new dataset path; no remote host is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from uuid import uuid4
from unittest.mock import patch

import bcrypt
from redis import Redis

from backup import backup, restore, verify, digest
from check_service import run
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.revocation_journal import RevocationJournal
from oldaplib.src.jena_connection import JenaConnection
from oldaplib.src.helpers.oldaperror import OldapError


def rehearse(*, output, distribution, peer, config, start, stop, send, text_hits,
             committed, aborted, check, headers, base):
    """Freeze the complete fixture, restore a new copy, and compare before activation."""
    media, operations, coordinator = (output / name for name in ('media', 'operations', 'coordination'))
    for directory in (media, operations, coordinator):
        directory.mkdir(mode=0o700)
    (media / 'original.bin').write_bytes(bytes(range(256)) * 1024)
    (media / 'derivative.bin').write_bytes(b'owned derivative fixture\n')
    (operations / 'service.properties').write_bytes(config.read_bytes())
    (operations / 'api.env').write_text('OLDAP_BACKEND=jena\nOLDAP_JENA_URL=' + base + '/tx\n')
    (operations / 'policy.json').write_text(json.dumps({'archive': 'owned-fixture', 'publicRole': 'oldap:Unknown'}))
    # Real administrative RDF and login, not an account-shaped JSON sidecar.
    context = Context(name='SERVICE_BACKUP')
    password = 'owned-restore-password'
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    identifier = uuid4()
    send('BEGIN', identifier)
    send('UPDATE', identifier, context.sparql_context + '''INSERT DATA { GRAPH oldap:admin {
      <https://example.org/project> a oldap:Project ; oldap:projectShortName "demo"^^xsd:NCName ;
        oldap:namespaceIri <https://example.org/demo#> .
      <https://example.org/callback/restored> a oldap:User ; oldap:userId "restored"^^xsd:NCName ;
        dcterms:creator <https://example.org/callback/actor> ; schema:familyName "Restore" ;
        schema:givenName "Fixture" ; schema:email "restore@example.org" ; oldap:isActive true ;
        oldap:credentials "''' + hashed + '''" ; oldap:inProject <https://example.org/project> ;
        oldap:hasRole oldap:Editor .
      oldap:Editor a oldap:Role ; oldap:inProject <https://example.org/project> .
      <urn:restore:admin-grant> rdf:reifies <<( <https://example.org/callback/restored> oldap:inProject <https://example.org/project> )>> ;
        oldap:hasAdminPermission oldap:ADMIN_USERS .
      <urn:restore:role-grant> rdf:reifies <<( <https://example.org/callback/restored> oldap:hasRole oldap:Editor )>> ;
        oldap:hasDefaultDataPermission oldap:DATA_UPDATE .
    } }''')
    send('COMMIT', identifier)
    properties = dict(line.split('=', 1) for line in config.read_text().splitlines())
    environment = {'OLDAP_JENA_URL': base + '/tx', 'OLDAP_JENA_SERVICE_KEY': properties['serviceSecret'],
                   'OLDAP_JENA_BOOTSTRAP_KEY': properties['bootstrapSecret'],
                   'OLDAP_JENA_FULLTEXT_KEY': properties['fulltextSecret']}

    def login(password_value=password):
        with patch.dict(os.environ, environment):
            return JenaConnection(userId='restored', credentials=password_value,
                                  context_name='SERVICE_BACKUP', token_codec=peer.codec)

    claims = login().userdata.to_claims()
    check('Source fixture login includes actual admin and role grants',
          claims['hasRole']['oldap:Editor'] == 'oldap:DATA_UPDATE'
          and claims['inProject']['https://example.org/project'] == ['oldap:ADMIN_USERS'])
    rdf_query = 'SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?s ?p ?o } } ORDER BY ?g ?s ?p ?o'
    before_rdf = send('READ', body=rdf_query).json()
    roots = {'dataset': output / 'dataset', 'media': media, 'operations': operations,
             'coordination': coordinator, 'release': distribution}
    redis_process = None
    socket_dir = tempfile.TemporaryDirectory(prefix='oldap-restore-', dir='/tmp')
    socket = str(Path(socket_dir.name) / 'redis.sock')
    redis_log = (output / 'redis-recovery.log').open('w')

    def start_redis(directory):
        nonlocal redis_process
        redis_process = subprocess.Popen([shutil.which('redis-server'), '--port', '0', '--unixsocket', socket,
            '--unixsocketperm', '700', '--dir', str(directory), '--appendonly', 'yes',
            '--appendfsync', 'always', '--maxmemory-policy', 'noeviction', '--save', ''], stdout=redis_log, stderr=redis_log)
        client = Redis(unix_socket_path=socket, decode_responses=True, socket_timeout=3)
        for _ in range(100):
            if redis_process.poll() is not None:
                raise RuntimeError('Owned Redis failed to start')
            try:
                if client.ping():
                    return client
            except Exception:
                time.sleep(.05)
        raise TimeoutError('Owned Redis did not start')

    def stop_redis():
        nonlocal redis_process
        if redis_process is not None:
            redis_process.terminate()
            redis_process.wait(timeout=15)
            redis_process = None

    original_config = config.read_text()
    try:
        client = start_redis(coordinator)
        journal = RevocationJournal(client, 'source-generation')
        pending = uuid4()
        key = journal.prefix + str(pending)
        client.set(key, 'owned-pending-marker-not-an-executable-command')
        client.set('oldap:owned-writer-barrier', 'blocked-for-restore-review')
        check('Source Redis retains the owned pending-operation identity', pending in set(journal.retained_ids()))
        client.close()
        stop_redis()
        try:
            backup(roots, output / 'live-backup-refused', 'source-generation', quiesced=True)
        except ValueError as error:
            check('Backup refuses the live Jena storage lock', 'running' in str(error))
        else:
            raise AssertionError('Live backup accepted')
        stop()
        started = time.perf_counter()
        bundle = output / 'backup'
        backup(roots, bundle, 'source-generation', quiesced=True)
        backup_seconds = time.perf_counter() - started
        manifest = verify(bundle)
        check('Backup includes all five deployment components', set(manifest['components']) == set(roots))
        check('Derived Lucene indexes are omitted but configuration retained',
              'managed-text/configuration.json' in manifest['components']['dataset']['files']
              and not any('/index-' in name for name in manifest['components']['dataset']['files']))
        # Intentional corruption must be caught before destination creation.
        corrupt = bundle / 'media/original.bin'
        saved = corrupt.read_bytes()
        corrupt.write_bytes(saved + b'corrupt')
        try:
            restore(bundle, output / 'bad-restore')
        except ValueError:
            check('Corruption prevents any restore publication', not (output / 'bad-restore').exists())
        else:
            raise AssertionError('Corrupt backup restored')
        corrupt.write_bytes(saved)
        verify(bundle)
        # Show that restore means the backup recovery point, not later source data.
        start()
        later = uuid4()
        send('BEGIN', later)
        send('UPDATE', later, 'INSERT DATA { GRAPH <urn:service:test> { <urn:after-backup> <urn:value> 1 } }')
        send('COMMIT', later)
        stop()
        restored = output / 'restored'
        started = time.perf_counter()
        handoff = restore(bundle, restored)
        restore_seconds = time.perf_counter() - started
        check('Restore allocates a new quarantined generation', handoff['target_generation'] != handoff['source_generation']
              and handoff['state'] == 'quarantined-not-activated')
        check('Original media, derivative and policy bytes match', all(
            digest(restored / part / name) == digest(bundle / part / name)
            for part, name in [('media', 'original.bin'), ('media', 'derivative.bin'),
                               ('operations', 'policy.json'), ('operations', 'service.properties')]))
        # Read-only inspection of restored AOF; no worker is started or gate cleared.
        client = start_redis(restored / 'coordination')
        check('Redis AOF restore preserves pending state and closed writer barrier',
              client.get(key) == 'owned-pending-marker-not-an-executable-command'
              and client.get('oldap:owned-writer-barrier') == 'blocked-for-restore-review')
        check('New dataset generation does not discover the old journal',
              not list(RevocationJournal(client, handoff['target_generation']).retained_ids()))
        client.close()
        stop_redis()
        config.write_text(original_config.replace(str(output / 'dataset'), str(restored / 'dataset')))
        config.chmod(0o600)
        started = time.perf_counter()
        start()
        startup_seconds = time.perf_counter() - started
        check('All application and administrative RDF matches after restore', send('READ', body=rdf_query).json() == before_rdf)
        check('Restored credentials and role grants authenticate unchanged', login().userdata.to_claims() == claims)
        try:
            login('wrong-password')
        except OldapError:
            check('Restored account still rejects a wrong password', True)
        else:
            raise AssertionError('Wrong password accepted after restore')
        check('Commit receipt survives full restore', send('STATUS', committed).text == 'committed')
        send('BEGIN', aborted, expected=409)
        check('Aborted admission also survives full restore', send('STATUS', aborted).text == 'unknown')
        check('Post-backup commit is not invented at the recovery point', send('STATUS', later).text == 'unknown'
              and not send('READ', body='ASK { GRAPH <urn:service:test> { <urn:after-backup> ?p ?o } }').json()['boolean'])
        check('Fulltext index rebuild restores configured folded search', text_hits() == {'urn:text'})
        try:
            restore(bundle, restored)
        except FileExistsError:
            check('Restore refuses an existing target', True)
        else:
            raise AssertionError('Existing target overwritten')
        (output / 'backup-results.json').write_text(json.dumps({'status': 'passed',
            'backup_seconds': backup_seconds, 'restore_copy_seconds': restore_seconds,
            'restored_startup_seconds': startup_seconds,
            'files': {c: len(manifest['components'][c]['files']) for c in roots},
            'bytes': sum(f['bytes'] for c in roots for f in manifest['components'][c]['files'].values()),
            'scope': 'Owned local data/admin/media/config/release and real Redis AOF; no remote host, production accounts or real worker replay.',
            'home_org': 'Planned first remote test target; not contacted.'}, indent=2) + '\n')
    finally:
        stop()
        stop_redis()
        config.write_text(original_config)
        config.chmod(0o600)
        redis_log.close()
        socket_dir.cleanup()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distribution', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.distribution.resolve(), args.java_home.resolve(), args.output.resolve(), backup_check=rehearse, transaction_count=5)
