"""Journal durability and corruption tests on the existing isolated Redis fixture."""
from dataclasses import replace
import json
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4
from redis.exceptions import ConnectionError as RedisConnectionError

from oldaplib.test import test_mutation_gate as gate_fixture
from oldaplib.test import test_jena_authentication_revocation as revocation_fixture
from oldaplib.src.helpers.revocation_journal import RevocationJournal
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapErrorNotFound
from oldaplib.src.mutation_gate import MutationGateUnavailable


class TestRevocationJournal(unittest.TestCase):
    """Reuse the private Unix-socket/AOF fixture without touching installed Redis."""

    @classmethod
    def setUpClass(cls):
        gate_fixture.MutationGateTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        gate_fixture.MutationGateTest.tearDownClass()

    def setUp(self):
        fixture = revocation_fixture.TestJenaRevocation()
        fixture.setUp()
        self.attempt = fixture.attempt
        self.client = gate_fixture.MutationGateTest.client
        self.journal = RevocationJournal(self.client, 'test-' + str(uuid4()))

    def test_roundtrip_identity_and_no_expiry(self):
        self.journal.save(self.attempt)
        self.assertEqual(self.journal.load(self.attempt.receipt_id), self.attempt)
        self.assertEqual(list(self.journal.retained_ids()), [self.attempt.receipt_id])
        self.assertEqual(self.client.ttl(self.journal._key(self.attempt.receipt_id)), -1)

    def test_conflicting_identity_cannot_overwrite(self):
        self.journal.save(self.attempt)
        changed = replace(self.attempt, command=replace(self.attempt.command, modified='changed'))
        with self.assertRaises(OldapErrorInconsistency):
            self.journal.save(changed)
        self.assertEqual(self.journal.load(self.attempt.receipt_id), self.attempt)

    def test_dataset_scope_isolated(self):
        self.journal.save(self.attempt)
        other = RevocationJournal(self.client, 'another-dataset')
        with self.assertRaises(OldapErrorNotFound):
            other.load(self.attempt.receipt_id)
        self.assertEqual(list(other.retained_ids()), [])

    def test_corrupt_and_incompatible_records_rejected(self):
        key = self.journal._key(self.attempt.receipt_id)
        for field, value in [('schema', 99), ('schema', True), ('dataset', 'other'), ('digest', 'wrong'),
                             ('updateSha256', 'wrong'), ('receiptId', str(uuid4()))]:
            with self.subTest(field=field):
                record = self.journal._record(self.attempt)
                record[field] = value
                self.client.set(key, json.dumps(record))
                with self.assertRaises(OldapErrorInconsistency):
                    self.journal.load(self.attempt.receipt_id)
        self.client.set(key, '{invalid')
        with self.assertRaises(OldapErrorInconsistency):
            self.journal.load(self.attempt.receipt_id)

    def test_no_transport_when_fsync_acknowledgement_is_missing(self):
        update, query = Mock(), Mock()
        with patch('oldaplib.src.helpers.revocation_journal._durable', side_effect=MutationGateUnavailable('no fsync')):
            with self.assertRaises(MutationGateUnavailable):
                self.journal.execute(self.attempt, update=update, query=query)
        update.assert_not_called()
        query.assert_not_called()
        # Redis may have stored the record despite the uncertain durability ack.
        self.assertEqual(self.journal.load(self.attempt.receipt_id), self.attempt)

    def test_unavailable_store_uses_existing_error_family_without_transmission(self):
        update, query = Mock(), Mock()
        with patch.object(self.journal, 'save', side_effect=RedisConnectionError('offline')):
            with self.assertRaises(MutationGateUnavailable):
                self.journal.execute(self.attempt, update=update, query=query)
        update.assert_not_called()
        query.assert_not_called()

    def test_reconnect_between_write_and_durability_never_transmits(self):
        from oldaplib.src.mutation_gate import _durable
        def reconnect(pinned):
            pinned.connection.disconnect()
            _durable(pinned)
        update, query = Mock(), Mock()
        with patch('oldaplib.src.helpers.revocation_journal._durable', side_effect=reconnect):
            with self.assertRaises(MutationGateUnavailable):
                self.journal.execute(self.attempt, update=update, query=query)
        update.assert_not_called()
        query.assert_not_called()

    def test_exact_repeat_rewrites_and_confirms_on_same_pinned_connection(self):
        self.journal.save(self.attempt)
        with patch('oldaplib.src.helpers.revocation_journal._durable') as durable:
            self.journal.save(self.attempt)
        pinned = durable.call_args.args[0]
        self.assertTrue(pinned._single_connection_client)
        self.assertIsNot(pinned, self.client)


if __name__ == '__main__':
    unittest.main()
