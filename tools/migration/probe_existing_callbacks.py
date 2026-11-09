"""Run real Python audit/mobile callbacks against an owned interactive Jena bridge.

Use the sibling API virtualenv: imports execute existing application functions,
not copied query strings. Resource instances/permission setup remain synthetic;
no Flask application, GraphDB, Redis cache or full CRUD factory is started.
"""
import argparse
import base64
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import selectors
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD
from oldap_api.mobile_media import repository as vocabulary
from oldap_api.mobile_media.lifecycle import GraphDbMobileMediaLifecycleOutbox, MobileMediaLifecycleError
from oldap_api.views.instance_views import _mobile_lifecycle_hook
from oldaplib.src.archive_domain import audit_resource_operation, audit_command
from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.iconnection import IConnection
from oldaplib.src.resource_transaction import resource_transaction, resource_operation, resource_query, ResourceTransactionError
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class BridgeConnection(IConnection):
    """Minimal test connection; preserve existing transaction method signatures."""

    def __init__(self, java, jar, directory, log, *, reopen=False):
        super().__init__(context_name='JENA_CALLBACK_PROBE')
        self._userdata = SimpleNamespace(userIri=Iri('https://example.org/callback/actor'))
        self.active = False
        self.operations = []
        self.process = subprocess.Popen([java, '-Xmx512m', '--class-path', str(jar),
            str(Path(__file__).with_name('JenaCallbackBridge.java')), str(directory),
            'reopen' if reopen else 'new'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log)

    def _request(self, operation, body=''):
        self.operations.append(operation)
        self.process.stdin.write(operation.encode() + b'\t' + base64.b64encode(body.encode()) + b'\n')
        self.process.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=30):
                raise TimeoutError('Owned Java callback bridge did not answer')
        line = self.process.stdout.readline()
        if not line:
            raise OldapError('Owned Java callback bridge exited; inspect its log')
        status, payload = line.rstrip(b'\n').split(b'\t', 1)
        text = base64.b64decode(payload).decode()
        if status != b'OK':
            raise OldapError(text)
        return text

    def transaction_start(self):
        self._request('BEGIN')
        self.active = True

    def transaction_update(self, query):
        self._request('UPDATE', query)

    def transaction_query(self, query, result_format=SparqlResultFormat.JSON):
        if result_format != SparqlResultFormat.JSON:
            raise ValueError('Probe supports JSON only')
        return json.loads(self._request('QUERY', query))

    def transaction_commit(self):
        self._request('COMMIT')
        self.active = False

    def transaction_abort(self):
        self._request('ABORT')
        self.active = False

    def query(self, query, format=SparqlResultFormat.JSON):
        if format != SparqlResultFormat.JSON:
            raise ValueError('Probe supports JSON only')
        return json.loads(self._request('READ', query))

    def in_transaction(self):
        return self.active

    def close(self):
        """Close the pipe without an explicit abort to exercise server EOF cleanup."""
        self.process.stdin.close()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
            raise
        finally:
            self.process.stdout.close()
        if self.process.returncode:
            raise OldapError('Owned bridge did not close cleanly')

    def _unsupported(self, *args, **kwargs):
        raise NotImplementedError('Not implemented by this restricted probe connection')

    issue_media_token = clear_graph = clear_repo = upload_turtle = update_query = _unsupported


class Folder:
    """Synthetic structural model consumed by the real audit implementation."""
    name = Xsd_QName('shared:StagingFolder')
    superclass = {}
    attachedToRoleAnnotation = {}
    iri = Iri('https://example.org/callback/folder')

    def __init__(self, parent):
        self.parent = Iri(parent)

    def get(self, field):
        return self.parent if str(field) == 'shared:inStagingFolder' else None


class Medium:
    """Only the model/write body is a fixture; decorator and hook are real."""
    name = Xsd_QName('shared:StagingMediaObject')
    iri = Iri('https://example.org/callback/media')

    def __init__(self, connection):
        self._con = connection

    def get(self, field):
        return 'a' * 64 if str(field) == 'shared:checksum' else None

    @resource_operation
    def move(self, parent, *, before_commit=None):
        """Stage a fixture move; the real decorator invokes before_commit."""
        self._con.transaction_update(f'''DELETE {{ GRAPH <urn:callback:data> {{
            <{self.iri}> <urn:callback:parent> ?old }} }}
            INSERT {{ GRAPH <urn:callback:data> {{ <{self.iri}> <urn:callback:parent> <{parent}> }} }}
            WHERE {{ OPTIONAL {{ GRAPH <urn:callback:data> {{ <{self.iri}> <urn:callback:parent> ?old }} }} }}''')


def run(java, jar, output, *, connection_factory=BridgeConnection):
    """Exercise existing callbacks in a fresh dataset and close the owned bridge."""
    output.mkdir(parents=True, exist_ok=False)
    results = []
    def check(name, condition=True):
        assert condition, name
        results.append(name)
        print('PASS', name, flush=True)
    log = (output / 'bridge.log').open('a')
    con = connection_factory(java, jar, output / 'dataset', log)
    context = Context(name=con.context_name)
    policy = SimpleNamespace(enabled=True, context=context, connection=con,
                             project=SimpleNamespace(projectShortName='probe'))
    now = datetime.now(UTC)
    medium = Medium(con)
    before, after = Folder('https://example.org/callback/old'), Folder('https://example.org/callback/new')
    audit_graph = 'urn:oldap:archive-operations'
    def event_count():
        return int(con.query(f'''SELECT (COUNT(?event) AS ?n) WHERE {{ GRAPH <{vocabulary.RECEIPT_GRAPH}> {{
            ?event a <urn:oldap:mobile-media:LifecycleEvent> }} }}''')['results']['bindings'][0]['n']['value'])
    def snapshot():
        return con.query('SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?s ?p ?o } } ORDER BY ?g ?s ?p ?o')
    def add_mobile_receipt():
        facts = [(RDF.type, vocabulary.RECEIPT_CLASS),
                 (vocabulary.UPLOAD_ID, Literal(str(uuid4()))),
                 (vocabulary.CLIENT_ASSET_ID, Literal(str(uuid4()))),
                 (vocabulary.OWNER, URIRef(str(con.userIri))),
                 (vocabulary.STAGING_AREA, URIRef('https://example.org/callback/area')),
                 (vocabulary.RESOURCE, Literal(str(medium.iri), datatype=XSD.anyURI))]
        triples = ' '.join(f'<urn:callback:upload> {p.n3()} {o.n3()} .' for p, o in facts)
        con.transaction_update(f'INSERT DATA {{ GRAPH <{vocabulary.RECEIPT_GRAPH}> {{ {triples} }} }}')
    def audit():
        audit_resource_operation(after, before, 'move', policy)
    try:
        # The coordination gate is deliberately disabled in this isolated probe;
        # real Python ownership/decorators still run, but no Redis store is used.
        with patch('oldaplib.src.resource_transaction.archive_coordination_enabled', return_value=False):
            initial = snapshot()
            with resource_transaction(con):
                add_mobile_receipt()
                with audit_command('probe-composed-operation'):
                    audit()
                hook = _mobile_lifecycle_hook(medium, 'moved')
                assert hook is not None
                medium.move(str(after.iri), before_commit=hook)
                check('Real callback sees newly inserted mobile receipt inside outer transaction',
                      resource_query(con, f'ASK {{ GRAPH <{vocabulary.RECEIPT_GRAPH}> {{ ?event a <urn:oldap:mobile-media:LifecycleEvent> }} }}')['boolean'])
                check('Separate reader cannot see resource/audit/outbox before commit', snapshot() == initial)
                hook(con) # Same closure retains event_id: its query must be idempotent.
            check('Nested real decorator and callback commit exactly once', con.operations.count('BEGIN') == 1 and con.operations.count('COMMIT') == 1 and event_count() == 1)
            rows = con.query(f'SELECT ?record WHERE {{ GRAPH <{audit_graph}> {{ ?event <urn:oldap:archive:record> ?record }} }}')['results']['bindings']
            record = json.loads(rows[0]['record']['value'])
            check('Real structural audit preserves before/after and operation ID',
                  len(rows) == 1 and record['operationId'] == 'probe-composed-operation'
                  and record['before']['shared:inStagingFolder'] != record['after']['shared:inStagingFolder'])
            baseline = snapshot()
            try:
                with resource_transaction(con):
                    audit()
                    def late_failure(connection):
                        _mobile_lifecycle_hook(medium, 'archived')(connection)
                        raise ValueError('after-outbox')
                    medium.move('https://example.org/callback/rollback', before_commit=late_failure)
            except ValueError:
                pass
            else:
                raise AssertionError('Late callback failure was ignored')
            check('Real late callback failure rolls back resource, audit and outbox', snapshot() == baseline)
            try:
                with resource_transaction(con):
                    audit()
                    try:
                        medium.move('https://example.org/callback/caught', before_commit=late_failure)
                    except ValueError:
                        pass
            except ResourceTransactionError:
                pass
            else:
                raise AssertionError('Caught inner failure allowed commit')
            check('Caught nested callback failure still poisons outer transaction', snapshot() == baseline)
            def reject_commit():
                """Model a final application precondition that rejects the move."""
                raise ValueError('owner veto')

            try:
                with resource_transaction(con, before_commit=reject_commit):
                    audit()
                    medium.move('https://example.org/callback/veto', before_commit=_mobile_lifecycle_hook(medium, 'moved'))
            except ValueError:
                pass
            else:
                raise AssertionError('Owner precondition was ignored')
            check('Owner final precondition rolls back successful inner callbacks', snapshot() == baseline)

            # Exercise the actual API worker's read/check/write methods as well.
            outbox = GraphDbMobileMediaLifecycleOutbox(con)
            claim = outbox.claim_next('probe-worker', now=now + timedelta(seconds=2))
            check('Real worker claim reads and updates the committed event', claim is not None and claim.resource_iri == str(medium.iri))
            try:
                outbox.complete(claim.event_id, str(uuid4()), 'probe-worker', completed_at=now + timedelta(seconds=3))
            except MobileMediaLifecycleError:
                pass
            else:
                raise AssertionError('Wrong completion claim accepted')
            outbox.complete(claim.event_id, claim.claim_id, 'probe-worker', completed_at=now + timedelta(seconds=3))
            outbox.complete(claim.event_id, claim.claim_id, 'probe-worker', completed_at=now + timedelta(seconds=4))
            check('Real completion rejects stale claim and accepts exact duplicate', outbox.claim_next('probe-worker', now=now + timedelta(seconds=5)) is None)
            # New media with no mobile receipt must not create lifecycle work.
            legacy = Medium(con)
            legacy.iri = Iri('https://example.org/callback/legacy')
            with resource_transaction(con):
                legacy.move(str(after.iri), before_commit=_mobile_lifecycle_hook(legacy, 'moved'))
            check('Real callback emits no event for non-mobile media', event_count() == 1)

            stable = snapshot()
            con.transaction_start()
            audit()
            _mobile_lifecycle_hook(medium, 'staging_deleted')(con)
            con.close() # EOF with open transaction, deliberately no abort request.
            con = connection_factory(java, jar, output / 'dataset', log, reopen=True)
            check('Client disconnect aborts uncommitted callback work before dataset reopen', snapshot() == stable)
        (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': results}, indent=2) + '\n')
    finally:
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
