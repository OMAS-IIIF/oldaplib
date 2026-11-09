"""Explicit Jena session transport for the migration application.

Keeps Connection's credential/JWT implementation and public query/transaction
surface. The configured endpoint owns one dataset; GraphDB-specific maintenance
operations fail explicitly. No automatic update or callback replay is performed.
"""
from dataclasses import dataclass
import json
import os
import time
import weakref
from urllib.parse import urlsplit
from uuid import uuid4

import requests
from rdflib import Graph

from oldaplib.src.connection import Connection
from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_user_query import jena_user_query
from oldaplib.src.helpers.oldaperror import (
    OldapError, OldapErrorAlreadyExists, OldapErrorConfiguration, OldapErrorValue,
)
from oldaplib.src.mutation_gate import transaction_opened, transaction_closed, track_transaction_end


# At most five admission attempts; 750 ms total backoff, plus HTTP round trips.
_BEGIN_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4)


@dataclass(frozen=True, repr=False)
class JenaSettings:
    """Backend-owned URL and separate service capabilities; never log secrets."""
    url: str
    service_key: str
    bootstrap_key: str
    fulltext_key: str
    timeout: float

    @classmethod
    def from_environment(cls):
        """Validate explicit settings; never default to an existing GraphDB URL."""
        names = ('OLDAP_JENA_URL', 'OLDAP_JENA_SERVICE_KEY', 'OLDAP_JENA_BOOTSTRAP_KEY', 'OLDAP_JENA_FULLTEXT_KEY')
        values = [os.getenv(name, '') for name in names]
        if not all(values):
            raise OldapErrorConfiguration('Jena requires explicit URL, service, bootstrap and fulltext credentials.')
        url = urlsplit(values[0])
        if (url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password
                or url.query or url.fragment or not url.path.rstrip('/').endswith('/tx')):
            raise OldapErrorConfiguration('Jena URL must identify the private /tx service without embedded credentials.')
        try:
            timeout = float(os.getenv('OLDAP_JENA_TIMEOUT', '60'))
            if not 0 < timeout <= 3600:
                raise ValueError()
        except ValueError as error:
            raise OldapErrorConfiguration('Jena timeout must be between 0 and 3600 seconds.') from error
        return cls(values[0].rstrip('/'), *values[1:], timeout)


class JenaConnection(Connection):
    """Use existing Python model logic over authenticated Jena HTTP sessions.

    Constructor keywords are those of Connection. Server/repository overrides
    may not redirect this backend-bound connection. The service currently runs
    the migration protocol; this class does not make unported RDF-star writers
    or broader inference semantics compatible automatically.
    """
    _resource_permissions_rdf12 = True
    _user_permissions_rdf12 = True
    _resource_search_rdf12 = True
    _managed_fulltext = True

    def __init__(self, **kwargs):
        self._jena = JenaSettings.from_environment()
        if kwargs.get('server') not in (None, self._jena.url) or kwargs.get('repo') not in (None, 'jena'):
            raise OldapErrorConfiguration('Jena connections cannot override the configured dataset endpoint.')
        if kwargs.get('issue_access_token') is False:
            raise OldapErrorConfiguration('Jena transport requires an access token for authenticated operations.')
        self._session_id = None
        self._uncertain = False
        self._text_revision = None
        kwargs.update(server=self._jena.url, repo='jena')
        # One task-local pool serves bootstrap, reads and transaction operations.
        # Opening a TCP connection for every model query can exhaust ephemeral
        # ports during bulk work. Credentials remain explicit per-request headers;
        # Requests' default adapters do not retry failed requests.
        self._http = requests.Session()
        # Release idle sockets when the owning connection is collected, including cycles.
        cleanup = weakref.finalize(self, self._http.close)
        try:
            super().__init__(**kwargs)
        except BaseException:
            cleanup()
            raise

    def _send(self, operation, body='', *, bootstrap=False, admin=False, timeout=None):
        """Reuse the transport, send once, and keep errors free of credentials.

        Closing the HTTP pool only releases sockets; transaction ownership and
        uncertain outcomes still follow the explicit commit/abort protocol.
        """
        headers = {'X-Oldap-Service-Key': self._jena.service_key, 'Content-Type': 'text/plain; charset=utf-8'}
        if bootstrap:
            headers['X-Oldap-Bootstrap-Key'] = self._jena.bootstrap_key
            path = '/bootstrap'
        else:
            if not self.token:
                raise OldapErrorConfiguration('Jena requires an authenticated access token.')
            headers['Authorization'] = 'Bearer ' + self.token
            path = f'/{operation}/{self._session_id or uuid4()}'
        if admin:
            headers['X-Oldap-Fulltext-Admin-Key'] = self._jena.fulltext_key
        try:
            response = self._http.post(self._jena.url + path, data=body.encode('utf-8'), headers=headers,
                                     timeout=timeout or self._jena.timeout, allow_redirects=False)
        except requests.RequestException as error:
            raise OldapErrorConfiguration(f'Jena {operation} response unavailable; no automatic retry.') from error
        if response.status_code == 409:
            raise OldapErrorAlreadyExists(f'Jena {operation} refused: conflict or writer busy.')
        if response.status_code >= 500 or 300 <= response.status_code < 400:
            raise OldapErrorConfiguration(f'Jena {operation} unavailable or outcome uncertain.')
        if response.status_code != 200:
            raise OldapError(f'Jena {operation} refused (HTTP {response.status_code}).')
        return response.text

    def _bootstrap_query(self, sparql):
        return json.loads(self._send('BOOTSTRAP', sparql, bootstrap=True))

    def _bootstrap_user_query(self, context, user_id):
        return jena_user_query(context, user_id)

    def _user_read_query(self, context, user_id):
        return jena_user_query(context, user_id)

    @staticmethod
    def _decode(raw, format):
        """Decode native JSON SELECT/ASK or JSON-LD CONSTRUCT without RDF-star rewriting."""
        if format == SparqlResultFormat.JSON:
            return json.loads(raw)
        graph = Graph().parse(data=raw, format='json-ld')
        if format == SparqlResultFormat.JSONLD:
            return graph
        formats = {SparqlResultFormat.TURTLE: 'turtle', SparqlResultFormat.N3: 'n3',
                   SparqlResultFormat.XML: 'xml'}
        if format not in formats:
            raise OldapErrorValue('Unsupported Jena query result format.')
        return graph.serialize(format=formats[format])

    def query(self, query, format=SparqlResultFormat.JSON, *, timeout=None):
        """Read outside a write session, preserving any compiled field-map revision."""
        if self._text_revision is not None:
            project, revision = self._text_revision
            raw = self._send('FULLTEXT_READ', json.dumps({'project': project, 'revision': revision, 'query': query}), timeout=timeout)
        else:
            raw = self._send('READ', query, timeout=timeout)
        return self._decode(raw, format)

    def transaction_start(self):
        """Open a session, briefly retrying only explicitly refused admission.

        HTTP 409 at BEGIN proves that this attempt did not open a transaction.
        Retry with a fresh identifier after bounded backoff. Lost replies and
        other errors retain uncertain ownership and are never retried here;
        UPDATE and COMMIT retain their existing no-replay semantics.
        """
        if self.in_transaction():
            raise OldapError('A Jena transaction is already active or uncertain.')
        for attempt in range(len(_BEGIN_RETRY_DELAYS) + 1):
            self._session_id = uuid4()
            # Track every admission before sending: a lost reply may conceal
            # an active writer and must remain visible to recovery tooling.
            self._transaction_url = f'{self._jena.url}/STATUS/{self._session_id}'
            transaction_opened(self._transaction_url)
            try:
                self._send('BEGIN')
                return
            except OldapErrorAlreadyExists:
                # Only an explicit refusal permits releasing this ownership.
                transaction_closed(self._transaction_url)
                self._transaction_url = None
                self._session_id = None
                if attempt == len(_BEGIN_RETRY_DELAYS):
                    raise
                time.sleep(_BEGIN_RETRY_DELAYS[attempt])
            except OldapError:
                self._uncertain = True
                raise

    def transaction_query(self, query, result_format=SparqlResultFormat.JSON):
        """Read the active session, including its uncommitted changes."""
        self._require_transaction()
        return self._decode(self._send('QUERY', query), result_format)

    def transaction_update(self, query):
        """Send one update inside the active session without replay."""
        self._require_transaction()
        self._send('UPDATE', query)

    def _require_transaction(self):
        if not self.in_transaction() or self._uncertain:
            raise OldapErrorConfiguration('No usable Jena transaction; inspect any uncertain receipt.')

    @track_transaction_end
    def transaction_commit(self):
        """Commit once; resolve lost replies using the durable receipt only."""
        if not self.in_transaction():
            raise OldapError('No Jena transaction started.')
        if not self._uncertain:
            try:
                if self._send('COMMIT') == 'committed':
                    self._transaction_url = None
                    return
            except OldapError:
                pass
        self._uncertain = True
        # Only a durable actor-bound receipt proves success after a lost reply.
        if self._send('STATUS') == 'committed':
            self._uncertain = False
            self._transaction_url = None
            return
        raise OldapErrorConfiguration(f'Jena commit outcome unknown for {self._session_id}; do not replay.')

    @track_transaction_end
    def transaction_abort(self):
        """Abort a known active session; never claim rollback after uncertain commit."""
        if self._uncertain:
            raise OldapErrorConfiguration('Cannot claim rollback of an uncertain Jena transaction.')
        if self.in_transaction():
            try:
                self._send('ABORT')
            except OldapError:
                self._uncertain = True
                raise
            self._transaction_url = None

    def update_query(self, query):
        """Run one standalone update atomically; never join a caller-owned transaction."""
        self.transaction_start()
        try:
            self.transaction_update(query)
            self.transaction_commit()
        except Exception:
            if self.in_transaction() and not self._uncertain:
                self.transaction_abort()
            raise

    def _fulltext_admin(self, operation, payload):
        state = json.loads(self._send(operation, json.dumps(payload), admin=True))
        if operation == 'FULLTEXT_APPLY':
            self._text_revision = None
        return state

    def _resource_fulltext_pattern(self, graph, filters, score_var):
        from oldaplib.src.helpers.jena_fulltext import jena_fulltext_fields, jena_fulltext_pattern
        context = Context(name=self.context_name)
        project = str(graph)
        state = self._fulltext_admin('FULLTEXT_STATE', {'project': project})
        config = state.get('configuration')
        if config is None or config['graph'] != str(context[project]) + 'data':
            raise OldapErrorValue('No matching managed fulltext configuration for this project.')
        fields = jena_fulltext_fields({'fields': config['fields']}, context)
        self._text_revision = (project, state['revision'])
        return jena_fulltext_pattern('<' + config['graph'] + '>', filters, fields, score_var,
                                     user_iri=self.userIri.toRdf)

    def _resource_schema_graphs(self, graph):
        """Resolve explicit project/shared/base external vocabulary registrations.

        Read on every query build so ontology edits, including an active caller
        transaction, are visible without a new persistent cache/invalidation rule.
        Vocabulary graph names follow the existing urn:oldap:vocab:<prefix>
        provisioning convention; unregistered graphs cannot affect these reads.
        """
        from oldaplib.src.resource_transaction import resource_query
        from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
        graph = Xsd_NCName(str(graph), validate=True)
        context = Context(name=self.context_name)
        result = resource_query(self, context.sparql_context + f"""
            SELECT DISTINCT ?prefix
            FROM {graph}:shacl FROM shared:shacl FROM oldap:shacl
            WHERE {{ ?ontology a oldap:ExternalOntology ; oldap:prefix ?prefix . }}
        """)
        prefixes = sorted({str(Xsd_NCName(row['prefix']['value'], validate=True))
                           for row in result['results']['bindings']})
        return [f'{graph}:onto', 'shared:onto', 'oldap:onto',
                *[f'<urn:oldap:vocab:{prefix}>' for prefix in prefixes]]

    def _resource_read_query(self, graph, iri, user_iri, *, include_creator):
        from oldaplib.src.objectfactory import _build_resource_read_query
        return _build_resource_read_query(self, graph, iri, user_iri, include_creator=include_creator, rdf12=True)

    def _resource_summaries_query(self, graph, iris, include_properties):
        from oldaplib.src.objectfactory import _build_resource_summaries_query
        return _build_resource_summaries_query(self, graph, iris, include_properties, rdf12=True)

    def _project_graph_export(self, project: str, parts: list[str]) -> str:
        """Export scoped graphs as native RDF 1.2 TriG; server requires root rights.

        Preserve blank-node identity across graphs and join an active session.
        No administrative graphs, index configuration or binary files are included.
        """
        if self.in_transaction():
            self._require_transaction()
        operation = 'EXPORT_GRAPHS' if self.in_transaction() else 'READ_GRAPHS'
        return self._send(operation, json.dumps({'project': project, 'parts': parts}))

    def _project_graph_import(self, project: str, parts: list[str], trig: str) -> None:
        """Atomically append scoped native TriG; join a managed resource transaction.

        The server validates every graph before writing. No replacement or retry
        occurs; blank nodes are fresh for each import. The existing project and
        its roles/users must already be provisioned. Malformed input aborts the
        whole transaction, including earlier writes in a joined scope.
        """
        from oldaplib.src.resource_transaction import resource_transaction
        with resource_transaction(self):
            self._require_transaction()
            self._send('IMPORT_GRAPHS', json.dumps({'project': project, 'parts': parts, 'trig': trig}))

    def _unsupported_maintenance(self, *args, **kwargs):
        raise OldapErrorConfiguration('This GraphDB maintenance operation is not implemented for Jena.')

    clear_graph = _unsupported_maintenance
    move_graph = _unsupported_maintenance
    clear_repo = _unsupported_maintenance
    recompute_inference = _unsupported_maintenance
    upload_turtle = _unsupported_maintenance
