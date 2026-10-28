"""Offline public-contract regression checks for revocation query extraction."""
import unittest
from unittest.mock import Mock, patch

from oldaplib.src.iconnection import IConnection
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission, OldapErrorUpdateFailed
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger


class TestAuthenticationRevocation(unittest.TestCase):
    """Preserve authorization, rollback and post-commit Python/cache behavior."""

    def setUp(self):
        self.con = Mock(spec=IConnection)
        self.con._persist_authentication_revocation.side_effect = (
            lambda command, verify: IConnection._persist_authentication_revocation(self.con, command, verify)
        )
        self.con.userIri = Iri('https://example.org/alice')
        self.con.userdata = Mock(userIri=self.con.userIri)
        self.con.context_name = 'REVOCATION_UNIT_TEST'
        self.before = Xsd_dateTime('2026-10-27T10:00:00Z')
        self.after = Xsd_dateTime('2026-10-27T10:01:00Z')
        self.user = User(con=self.con, userIri=self.con.userIri, userId='alice', modified=self.before,
                         familyName='Example', givenName='Alice', email='alice@example.org',
                         credentials='$2b$synthetic-unused-test-hash')
        self.cache_patch = patch('oldaplib.src.user.CacheSingletonRedis')
        self.cache = self.cache_patch.start().return_value
        self.addCleanup(self.cache_patch.stop)
        self.clock_patch = patch('oldaplib.src.user.Xsd_dateTime.now', return_value=self.after)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)
        self.con.transaction_query.return_value = {
            'head': {'vars': ['authVersion']},
            'results': {'bindings': [{'authVersion': {'type': 'literal', 'value': '1',
                'datatype': 'http://www.w3.org/2001/XMLSchema#nonNegativeInteger'}}]},
        }

    def test_success_updates_object_and_cache_only_after_commit(self):
        def verify_before_commit():
            self.assertEqual(self.user.authVersion, Xsd_nonNegativeInteger(0))
            self.assertEqual(self.user.modified, self.before)
            self.cache.delete.assert_not_called()
        self.con.transaction_commit.side_effect = verify_before_commit
        with patch.object(User, 'get_modified_by_iri', return_value=self.after):
            result = self.user.revoke_authentication()
        self.assertIsInstance(result, Xsd_nonNegativeInteger)
        self.assertEqual(result, Xsd_nonNegativeInteger(1))
        self.assertEqual(self.user.modified, self.after)
        self.con.transaction_abort.assert_not_called()
        self.cache.delete.assert_called_once_with(self.user.userIri)
        self.assertNotIn('jena-pilot', self.con.transaction_update.call_args.args[0])

    def test_stale_timestamp_aborts_without_local_effects(self):
        with patch.object(User, 'get_modified_by_iri', return_value=self.before):
            with self.assertRaises(OldapErrorUpdateFailed):
                self.user.revoke_authentication()
        self.con.transaction_abort.assert_called_once()
        self.con.transaction_commit.assert_not_called()
        self.assertEqual(self.user.authVersion, Xsd_nonNegativeInteger(0))
        self.assertEqual(self.user.modified, self.before)
        self.cache.delete.assert_not_called()

    def test_denied_actor_never_starts_transaction(self):
        self.con.userdata.userIri = Iri('https://example.org/bob')
        with patch.object(User, 'check_for_permissions', return_value=(False, 'denied')):
            with self.assertRaises(OldapErrorNoPermission):
                self.user.revoke_authentication()
        self.con.transaction_start.assert_not_called()
        self.cache.delete.assert_not_called()

    def test_commit_failure_does_not_publish_local_success(self):
        self.con.transaction_commit.side_effect = TimeoutError('unknown commit outcome')
        with patch.object(User, 'get_modified_by_iri', return_value=self.after):
            with self.assertRaises(TimeoutError):
                self.user.revoke_authentication()
        self.assertEqual(self.user.authVersion, Xsd_nonNegativeInteger(0))
        self.assertEqual(self.user.modified, self.before)
        self.cache.delete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
