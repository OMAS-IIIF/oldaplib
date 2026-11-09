"""Exercise the unchanged public User method through a restricted test connection.

This is not a login or general Fuseki adapter. Its identity is a synthetic trusted
fixture, every unrelated connection operation fails, and Redis is mocked. HTTP
callbacks come only from the owning isolated Fuseki runner.
"""
from unittest.mock import patch

from oldaplib.src.authentication import AuthorizationContext
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_authentication_revocation import RevocationAttempt
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotImplemented, OldapErrorUpdateFailed
from oldaplib.src.iconnection import IConnection
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger


class RevocationProbeConnection(IConnection):
    """Permit only prepared self-revocation against owned probe callbacks."""

    def __init__(self, user, update, query, *, journal=None):
        super().__init__(context_name='JENA_PUBLIC_REVOCATION_PROBE')
        self._userdata = AuthorizationContext(user, Xsd_NCName('probe'), InProjectClass(), ObservableDict())
        self._update = update
        self._query = query
        self.attempt = None
        self.journal = journal

    def _persist_authentication_revocation(self, command, verify_legacy_write):
        if self.in_transaction():
            raise OldapErrorNotImplemented('Cannot join an interactive transaction with a standalone command.')
        self.attempt = RevocationAttempt.prepare(command)
        if self.journal is None:
            self.attempt.execute(update=self._update, query=self._query)
        else:
            self.journal.execute(self.attempt, update=self._update, query=self._query)

    def in_transaction(self):
        return False

    def _unsupported(self, *args, **kwargs):
        raise OldapErrorNotImplemented('Only revocation is supported by this test connection.')

    # Intentionally fail closed for every unrelated abstract interface operation.
    issue_media_token = clear_graph = clear_repo = upload_turtle = _unsupported
    query = update_query = transaction_start = transaction_query = _unsupported
    transaction_update = transaction_commit = transaction_abort = _unsupported


def run_public_revocation_checks(update, query, check):
    """Run actual User.revoke_authentication against Fuseki, without real Redis."""
    before = Xsd_dateTime('2026-10-27T11:00:00Z')
    after = Xsd_dateTime('2026-10-27T11:01:00Z')

    def fixture(name, sender=update):
        iri = Iri(f'https://example.org/jena-public/{name}')
        con = RevocationProbeConnection(iri, sender, query)
        update(Context(name=con.context_name).sparql_context + f'''INSERT DATA {{
            GRAPH oldap:admin {{ {iri.toRdf} a oldap:User ;
            oldap:authVersion "0"^^xsd:nonNegativeInteger ; dcterms:modified {before.toRdf} . }} }}''')
        def model():
            return User(con=con, userIri=iri, userId='probe', familyName='Probe',
                        givenName='Synthetic', email='probe@example.org',
                        credentials='$2b$unused-fixture', modified=before)
        return con, model

    with patch('oldaplib.src.user.CacheSingletonRedis') as cache, \
            patch('oldaplib.src.user.Xsd_dateTime.now', return_value=after):
        con, model = fixture('success')
        user, stale = model(), model()
        result = user.revoke_authentication()
        check('Public User: unchanged return type, object metadata and cache invalidation',
              isinstance(result, Xsd_nonNegativeInteger) and int(result) == 1
              and user.modified == after and user.contributor == user.userIri
              and cache.return_value.delete.call_count == 1 and con.attempt.confirmed(query))
        cache.reset_mock()
        try:
            stale.revoke_authentication()
        except OldapErrorUpdateFailed:
            pass
        else:
            raise AssertionError('Stale User call did not fail')
        check('Public User: stale call raises existing conflict without local/cache mutation',
              int(stale.authVersion) == 0 and stale.modified == before
              and not cache.return_value.delete.called)

        def lost_response(body):
            update(body)
            raise TimeoutError('Simulated loss after completed response')
        con, model = fixture('lost-response', lost_response)
        user = model()
        result = user.revoke_authentication()
        check('Public User: confirmed receipt resolves lost acknowledgement before success',
              int(result) == 1 and user.modified == after and con.attempt.confirmed(query)
              and cache.return_value.delete.call_count == 1)

        cache.reset_mock()
        def no_delivery(body):
            raise TimeoutError('Simulated uncertain transport with no delivery')
        con, model = fixture('unknown', no_delivery)
        user = model()
        try:
            user.revoke_authentication()
        except OldapError as error:
            assert type(error) is OldapError and 'outcome unknown' in str(error)
        else:
            raise AssertionError('Unknown outcome became success')
        check('Public User: unknown result preserves object/cache and recovery identity',
              int(user.authVersion) == 0 and user.modified == before
              and not cache.return_value.delete.called and con.attempt is not None)
        # Reconcile this exact internal attempt; never invoke a fresh public
        # revocation as a retry. Recovery does not silently mutate the stale User.
        con.attempt.execute(update=update, query=query)
        con.attempt.execute(update=update, query=query)
        check('Public User: exact retained attempt recovers once without stale object publication',
              con.attempt.confirmed(query) and int(user.authVersion) == 0
              and not cache.return_value.delete.called)
