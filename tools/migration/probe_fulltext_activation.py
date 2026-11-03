"""Exercise durable text administration on owned Fuseki/TDB2, never shared data.

The service-admin key is a private maintenance capability. This probe does not
claim public OLDAP ADMIN_MODEL authorization or a production API deployment.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
from urllib.error import HTTPError
from unittest.mock import patch
from flask import Flask
from oldap_api.views.fulltext_views import fulltext_bp
from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists, OldapErrorConfiguration

import probe_http_sessions as sessions
from probe_fuseki_identity import IdentityPeer
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_fulltext import jena_fulltext_fields, jena_fulltext_pattern
from oldaplib.src.objectfactory import FTSearchFilter


def run(java, jar, output):
    """Check pre-existing data, replacement, uncertainty and restart recovery."""
    output.mkdir(parents=True, exist_ok=False)
    peer = IdentityPeer()
    original = sessions.TOKENS
    sessions.TOKENS = ('Bearer ' + peer.token('actor'), 'Bearer ' + peer.token('other'))
    admin_secret = secrets.token_urlsafe(32)
    checks = []

    class ManagedConnection(sessions.HttpProbeConnection):
        _managed_fulltext = True
        server_source = 'FusekiSessionProbe.java'
        route_prefix = '/tx'
        admin = True
        fault = None

        def server_environment(self):
            environment = {k: v for k, v in os.environ.items()
                           if not (k.startswith('OLDAP_') or k.startswith('PROBE_'))}
            return dict(environment, PROBE_IDENTITY_URL=peer.url, PROBE_IDENTITY_SECRET=peer.secret,
                        PROBE_TRANSPORT_SECRET=peer.transport_secret, PROBE_MANAGED_TEXT='yes',
                        PROBE_FULLTEXT_ADMIN_SECRET=admin_secret, PROBE_FULLTEXT_FAULTS='yes')

        def _fulltext_admin(self, operation, payload):
            try:
                return json.loads(self.send(operation, json.dumps(payload)))
            except HTTPError as error:
                if error.code == 409:
                    raise OldapErrorAlreadyExists('Fulltext revision conflict.') from error
                raise OldapErrorConfiguration('Fulltext backend unavailable or result uncertain.') from error

        def request_headers(self):
            headers = {'X-Oldap-Service-Key': peer.transport_secret}
            if self.admin:
                headers['X-Oldap-Fulltext-Admin-Key'] = admin_secret
            if self.fault:
                headers['X-Probe-Fulltext-Failure'] = self.fault
            return headers

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print('PASS', name, flush=True)

    def state(project='demo'):
        return json.loads(con.send('FULLTEXT_STATE', json.dumps({'project': project})))

    def apply(config, revision=None, project='demo'):
        return json.loads(con.send('FULLTEXT_APPLY', json.dumps({
            'project': project, 'configuration': config, 'expectedRevision': revision})))

    def refused(call, status):
        try:
            call()
        except HTTPError as error:
            if error.code != status:
                print(error.read().decode(), flush=True)
            return error.code == status
        return False

    def update(sparql, commit=True):
        con.transaction_start()
        con.transaction_update(sparql)
        if commit:
            con.transaction_commit()
        else:
            con.transaction_abort()

    def hits(field, text, project='demo'):
        envelope = state(project)
        saved = envelope['configuration']
        fields = jena_fulltext_fields({'fields': saved['fields']}, Context(name='MANAGED_TEXT_PROBE'))
        pattern = jena_fulltext_pattern('<' + saved['graph'] + '>', [FTSearchFilter(field, text)], fields, 'score')
        query = 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> SELECT DISTINCT ?res WHERE { ' + pattern + ' }'
        result = json.loads(con.send('FULLTEXT_READ', json.dumps({
            'project': project, 'revision': envelope['revision'], 'query': query})))
        return {row['res']['value'] for row in result['results']['bindings']}

    config = {'graph': 'https://example.org/demo/data', 'fields': {
        'title': ['https://schema.org/name'],
        'representedTitle': ['https://example.org/demo/link', 'https://schema.org/name']}}
    # Exercise the real CLI artifact as input to the service, not a second
    # independent interpretation of ontology YAML in this acceptance test.
    ontology_file = output / 'ontology.yaml'
    ontology_file.write_text(json.dumps({'ontology': {
        'project': {'shortname': 'demo', 'namespace': 'https://example.org/demo/'},
        'fulltext': {'fields': {'title': ['schema:name'],
                                'representedTitle': ['demo:link', 'schema:name']}}}}))
    tools_cli = Path(__file__).resolve().parents[3] / 'oldap-tools/.venv/bin/oldap-tools'
    plan = json.loads(subprocess.check_output([
        str(tools_cli), 'ontology', 'fulltext-plan', '-i', str(ontology_file)], text=True))
    check('Actual oldap-tools YAML plan supplies normalized server configuration',
          {'graph': plan['graph'], 'fields': plan['fields']} == config)
    config = {'graph': plan['graph'], 'fields': plan['fields']}
    expanded = {'graph': config['graph'], 'fields': dict(config['fields'], body=['https://schema.org/description'])}
    log = (output / 'server.log').open('a')
    con = None
    try:
        con = ManagedConnection(java, jar, output / 'dataset', log)
        update('''INSERT DATA {
          GRAPH <https://example.org/demo/data> {
            <urn:item> <https://schema.org/name> "ExistingFox"@en ;
                <https://schema.org/description> "ExistingBody" ; <https://example.org/demo/link> <urn:target> .
            <urn:target> <https://schema.org/name> "LinkedWolf" .
            <urn:fold> <https://schema.org/name> "Zu\u0308rich Straße École Laternen"@de .
          }
          GRAPH <https://example.org/other/data> { <urn:other> <https://schema.org/name> "OtherFox" . }
          GRAPH <http://oldap.org/base#admin> { <urn:private> <https://schema.org/name> "PrivateMarker" . }
        }''')
        check('Absent configuration is explicit', state()['configuration'] is None)
        con.admin = False
        check('User token and transport key do not grant maintenance authority',
              refused(lambda: apply(config), 403))
        con.admin = True
        check('Maintenance key does not replace user token verification',
              refused(lambda: con.send('FULLTEXT_STATE', '{"project":"demo"}', token='invalid'), 401))
        first = apply(config)
        check('Activation returns durable revision and active state', first['revision'] and first['status'] == 'active')
        check('Rebuild indexes RDF written before activation', hits('title', 'ExistingFox') == {'urn:item'})
        check('Activation folds pre-existing Unicode text and wildcard queries',
              hits('title', 'zurich strasse ecole') == {'urn:fold'} and hits('title', 'ZÜR*') == {'urn:fold'})
        check('Activation folding leaves singular and plural distinct',
              hits('title', 'Laternen') == {'urn:fold'} and not hits('title', 'Laterne'))

        check('Persisted paths drive query-time links', hits('representedTitle', 'LinkedWolf') == {'urn:item'})
        check('Admin graph cannot leak into text index', hits('title', 'PrivateMarker') == set())
        check('Other project data excluded before its activation', hits('title', 'OtherFox') == set())
        check('Identical configuration preserves revision without rebuild', apply(config, first['revision']) == first)
        check('Stale revision refuses replacement', refused(lambda: apply(expanded), 409))
        con.transaction_start()
        check('Active transaction refuses rebuild without aborting its owner',
              refused(lambda: apply(expanded, first['revision']), 409) and con.send('QUERY', 'ASK {}'))
        con.transaction_abort()
        invalid = {'graph': 'http://oldap.org/base#admin', 'fields': config['fields']}
        check('Private graph configuration refused', refused(lambda: apply(invalid, first['revision']), 400))
        check('Unknown native connector options refused',
              refused(lambda: apply(dict(config, languages=['en']), first['revision']), 400))
        con.fault = 'before-publish'
        check('Failed candidate publication returns failure', refused(lambda: apply(expanded, first['revision']), 503))
        con.fault = None
        check('Pre-publication failure preserves old state and search', state() == first and hits('title', 'ExistingFox') == {'urn:item'})
        second = apply(expanded, first['revision'])
        check('Search compiled against an old field map is refused', refused(lambda: con.send(
            'FULLTEXT_READ', json.dumps({'project': 'demo', 'revision': first['revision'], 'query': 'ASK {}'})), 409))
        check('New predicate indexes existing literal during replacement', hits('body', 'ExistingBody') == {'urn:item'})
        other = {'graph': 'https://example.org/other/data', 'fields': {'headline': ['https://schema.org/name']}}
        apply(other, project='other')
        check('Another project activates without field code changes', hits('headline', 'OtherFox', 'other') == {'urn:other'})
        check('Rebuilding another project preserves previous project index', hits('title', 'ExistingFox') == {'urn:item'} and state()['revision'] == second['revision'])
        check('Duplicate graph ownership refused', refused(lambda: apply(config, project='duplicate'), 409))
        update('INSERT DATA { GRAPH <https://example.org/demo/data> { <urn:new> <https://schema.org/name> "CommittedOwl" } }')
        check('Writes after activation update current index', hits('title', 'CommittedOwl') == {'urn:new'})
        update('INSERT DATA { GRAPH <https://example.org/demo/data> { <urn:rollback> <https://schema.org/name> "AbortedOwl" } }', False)
        check('Aborted writes leave no index hits', hits('title', 'AbortedOwl') == set())
        update('DELETE DATA { GRAPH <https://example.org/demo/data> { <urn:item> <https://schema.org/name> "ExistingFox"@en } }')
        check('Committed deletion removes index document', hits('title', 'ExistingFox') == set())
        con.close()
        con = ManagedConnection(java, jar, output / 'dataset', log, reopen=True)
        check('Clean restart reloads identical project configuration', state() == second)
        check('Startup rebuild applies folding to authoritative Unicode literals',
              hits('title', 'ZUR*') == {'urn:fold'} and hits('title', 'strass* ecole') == {'urn:fold'})
        literal = json.loads(con.send('READ', 'SELECT ?text WHERE { GRAPH <https://example.org/demo/data> { <urn:fold> <https://schema.org/name> ?text } }'))['results']['bindings'][0]['text']
        check('Rebuild preserves original RDF spelling and language',
              literal['value'] == 'Zu\u0308rich Straße École Laternen' and literal['xml:lang'] == 'de')

        check('Startup rebuild preserves committed changes and excludes rollback',
              hits('title', 'CommittedOwl') == {'urn:new'} and not hits('title', 'AbortedOwl') and not hits('title', 'ExistingFox'))
        con.transaction_start()
        con.transaction_update('INSERT DATA { GRAPH <https://example.org/demo/data> { <urn:crash> <https://schema.org/name> "CrashUncommitted" } }')
        con.process.kill()
        con.process.wait()
        con.process.stdin.close()
        con.process.stdout.close()
        con = ManagedConnection(java, jar, output / 'dataset', log, reopen=True)
        check('SIGKILL recovery rebuilds index from durable RDF and configuration', state() == second and hits('body', 'ExistingBody') == {'urn:item'})
        check('Crash recovery excludes an uncommitted writer', hits('title', 'CrashUncommitted') == set())
        con.fault = 'after-publish'
        check('Post-publication failure is an uncertain activation', refused(lambda: apply(config, second['revision']), 503))
        con.fault = None
        check('Uncertain activation fences queries and new writers',
              refused(lambda: con.send('READ', 'ASK {}'), 503) and refused(lambda: con.send('BEGIN'), 503))
        con.close()
        con = ManagedConnection(java, jar, output / 'dataset', log, reopen=True)
        recovered = state()
        check('Restart resolves uncertain publication to durable desired configuration',
              recovered['configuration'] == config and recovered['revision'] != second['revision'])
        check('Recovery keeps remaining fields and other project searchable',
              hits('title', 'CommittedOwl') == {'urn:new'} and hits('headline', 'OtherFox', 'other') == {'urn:other'})
        # Removed terminal predicate must not survive in a stale Lucene document.
        result = json.loads(con.send('READ', '''SELECT ?s WHERE { GRAPH <https://example.org/demo/data> {
          (?s ?score) <http://jena.apache.org/text#query> (<https://schema.org/description> "ExistingBody") } }'''))
        check('Removed predicate is absent from replacement index', result['results']['bindings'] == [])
        con.close()
        manifest = output / 'dataset/managed-text/configuration.json'
        saved_manifest = manifest.read_bytes()
        manifest.write_text('{broken')
        try:
            try:
                con = ManagedConnection(java, jar, output / 'dataset', log, reopen=True)
            except (ValueError, TimeoutError):
                check('Corrupt durable configuration refuses startup instead of disabling search', True)
            else:
                raise AssertionError('Corrupt manifest accepted')
        finally:
            manifest.write_bytes(saved_manifest)
        con = ManagedConnection(java, jar, output / 'dataset', log, reopen=True)
        check('Restored manifest recovers all active projects', state() == recovered and hits('headline', 'OtherFox', 'other') == {'urn:other'})
        update('''PREFIX oldap: <http://oldap.org/base#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            INSERT DATA { GRAPH oldap:admin {
                <https://example.org/project/demo> a oldap:Project ; oldap:projectShortName "demo"^^xsd:NCName ;
                    oldap:namespaceIri <https://example.org/demo/> ; oldap:projectStart "2024-01-01"^^xsd:date .
                <https://example.org/callback/actor> a oldap:User ; oldap:isActive true ;
                    oldap:inProject <https://example.org/project/demo> .
                <urn:admin-grant> rdf:reifies <<( <https://example.org/callback/actor> oldap:inProject <https://example.org/project/demo> )>> ;
                    oldap:hasAdminPermission oldap:ADMIN_MODEL .
            } }''')
        app = Flask(__name__)
        app.register_blueprint(fulltext_bp)
        api = app.test_client()
        headers = {'Authorization': sessions.TOKENS[0]}
        # Only the backend factory and Redis cache I/O are replaced. The actual
        # Flask route, Project.read and fresh RDF permission query run unchanged.
        with patch('oldap_api.authentication.Connection', return_value=con), \
             patch.object(CacheSingletonRedis, '__init__', return_value=None), \
             patch.object(CacheSingletonRedis, 'get', return_value=None), \
             patch.object(CacheSingletonRedis, 'set', return_value=None):
            check('Public administration rejects missing bearer', api.get('/admin/fulltext/demo').status_code == 401)
            response = api.get('/admin/fulltext/demo', headers=headers)
            check('Public GET resolves real project and current model-admin grant', response.status_code == 200 and response.json == recovered)
            check('Administration responses forbid caching', response.headers.get('Cache-Control') == 'no-store')
            check('Public PUT requires explicit expected revision', api.put('/admin/fulltext/demo', headers=headers,
                  json={'configuration': expanded}).status_code == 400)
            bad_graph = dict(expanded, graph='https://example.org/other/data')
            check('Public PUT rejects another project graph', api.put('/admin/fulltext/demo', headers=headers,
                  json={'configuration': bad_graph, 'expectedRevision': recovered['revision']}).status_code == 400)
            response = api.put('/admin/fulltext/demo', headers=headers,
                               json={'configuration': expanded, 'expectedRevision': recovered['revision']})
            check('Public PUT activates through the bound Jena transport', response.status_code == 200 and hits('body', 'ExistingBody') == {'urn:item'})
            check('Public PUT maps stale revision to conflict', api.put('/admin/fulltext/demo', headers=headers,
                  json={'configuration': config, 'expectedRevision': recovered['revision']}).status_code == 409)
            update('DELETE DATA { GRAPH <http://oldap.org/base#admin> { <https://example.org/callback/actor> <http://oldap.org/base#inProject> <https://example.org/project/demo> } }')
            check('Revoked membership cannot use an orphaned permission reifier', api.get('/admin/fulltext/demo', headers=headers).status_code == 403)
            update('''PREFIX oldap: <http://oldap.org/base#> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                INSERT DATA { GRAPH oldap:admin {
                <https://example.org/callback/actor> oldap:inProject oldap:SystemProject .
                <urn:root-grant> rdf:reifies <<( <https://example.org/callback/actor> oldap:inProject oldap:SystemProject )>> ;
                    oldap:hasAdminPermission oldap:ADMIN_OLDAP . } }''')
            check('Current system administrator can inspect project configuration', api.get('/admin/fulltext/demo', headers=headers).status_code == 200)
            update('DELETE DATA { GRAPH <http://oldap.org/base#admin> { <https://example.org/callback/actor> <http://oldap.org/base#isActive> true } }')
            check('Inactive administrator is refused despite valid token', api.get('/admin/fulltext/demo', headers=headers).status_code == 403)
            con._managed_fulltext = False
            check('GraphDB connection refuses managed endpoint explicitly', api.get('/admin/fulltext/demo', headers=headers).status_code == 503)
            con._managed_fulltext = True
        (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': checks}, indent=2) + '\n')
    finally:
        if con is not None and con.process.poll() is None:
            con.close()
        log.close()
        sessions.TOKENS = original
        peer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', default='java')
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.java, args.jar, args.output.resolve())
