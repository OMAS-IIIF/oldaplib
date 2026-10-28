"""Offline failure/reconciliation tests for the internal Fuseki revocation path."""
import unittest
from dataclasses import replace
from unittest.mock import Mock

from oldaplib.src.helpers.authentication_revocation import AuthenticationRevocation
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_authentication_revocation import RevocationAttempt
from oldaplib.src.helpers.oldaperror import (
    OldapError, OldapErrorInconsistency, OldapErrorNoPermission, OldapErrorUpdateFailed,
)
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger


class TestJenaRevocation(unittest.TestCase):
    """A transport acknowledgement is not proof that a guarded mutation applied."""

    def setUp(self):
        self.command = AuthenticationRevocation.prepare(
            context=Context(name='JENA_REVOCATION_UNIT'), user=Iri('https://example.org/alice'),
            actor=Iri('https://example.org/alice'), expected=Xsd_nonNegativeInteger(0),
            previous_modified=Xsd_dateTime('2026-10-27T10:00:00Z'),
            modified=Xsd_dateTime('2026-10-27T10:01:00Z'))
        self.attempt = RevocationAttempt.prepare(self.command)
        self.update = Mock()
        self.query = Mock(return_value=self.receipt())

    def receipt(self):
        return {'results': {'bindings': [
            {'predicate': {'type': 'uri', 'value': 'urn:oldap:jena-pilot:digest'},
             'value': {'type': 'literal', 'value': self.command.digest}},
            {'predicate': {'type': 'uri', 'value': 'urn:oldap:jena-pilot:version'},
             'value': {'type': 'literal', 'value': '1',
                       'datatype': 'http://www.w3.org/2001/XMLSchema#nonNegativeInteger'}},
            {'predicate': {'type': 'uri', 'value': 'urn:oldap:jena-pilot:status'},
             'value': {'type': 'literal', 'value': 'committed'}},
        ]}}

    def execute(self):
        self.attempt.execute(update=self.update, query=self.query)

    def test_acknowledged_update_needs_matching_receipt(self):
        self.execute()
        self.update.assert_called_once()
        self.query.assert_called_once()

    def test_acknowledged_noop_is_conflict(self):
        self.query.return_value = {'results': {'bindings': []}}
        with self.assertRaises(OldapErrorUpdateFailed):
            self.execute()

    def test_lost_acknowledgement_with_receipt_is_success(self):
        self.update.side_effect = TimeoutError('lost')
        self.execute()
        self.update.assert_called_once()

    def test_uncertain_delivery_without_receipt_is_not_conflict(self):
        self.update.side_effect = TimeoutError('lost')
        self.query.return_value = {'results': {'bindings': []}}
        with self.assertRaises(OldapError) as caught:
            self.execute()
        self.assertIs(type(caught.exception), OldapError)
        self.assertIn('outcome unknown', str(caught.exception))
        self.assertIn(str(self.attempt.receipt_id), str(caught.exception))
        self.update.assert_called_once()

    def test_receipt_read_failure_is_unknown(self):
        self.query.side_effect = TimeoutError('cannot observe')
        with self.assertRaisesRegex(OldapError, 'outcome unknown'):
            self.execute()

    def test_changed_digest_wrong_result_duplicate_or_partial_receipt_fail_closed(self):
        variants = []
        wrong_digest = self.receipt()
        wrong_digest['results']['bindings'][0]['value']['value'] = 'other'
        variants.append(wrong_digest)
        wrong_result = self.receipt()
        wrong_result['results']['bindings'][1]['value']['value'] = '2'
        variants.append(wrong_result)
        duplicate = self.receipt()
        duplicate['results']['bindings'].append(duplicate['results']['bindings'][0])
        variants.append(duplicate)
        partial = self.receipt()
        partial['results']['bindings'].pop()
        variants.append(partial)
        for result in variants:
            with self.subTest(receipt=result):
                self.query.return_value = result
                with self.assertRaises(OldapErrorInconsistency):
                    self.execute()

    def test_receipt_uri_or_language_literal_cannot_impersonate_digest(self):
        for value in ({'type': 'uri', 'value': self.command.digest},
                      {'type': 'literal', 'value': self.command.digest, 'xml:lang': 'en'}):
            with self.subTest(value=value):
                self.query.return_value = self.receipt()
                self.query.return_value['results']['bindings'][0]['value'] = value
                with self.assertRaises(OldapErrorInconsistency):
                    self.execute()

    def test_atomic_denial_uses_existing_permission_error(self):
        rows = self.receipt()['results']['bindings']
        rows.pop(1)
        rows[-1]['value']['value'] = 'denied'
        self.query.return_value = {'results': {'bindings': rows}}
        with self.assertRaises(OldapErrorNoPermission):
            self.execute()

    def test_atomic_denial_after_lost_response_is_not_unknown(self):
        self.update.side_effect = TimeoutError('lost')
        rows = self.receipt()['results']['bindings']
        rows.pop(1)
        rows[-1]['value']['value'] = 'denied'
        self.query.return_value = {'results': {'bindings': rows}}
        with self.assertRaises(OldapErrorNoPermission):
            self.execute()

    def test_denial_receipt_cannot_claim_a_persisted_version(self):
        self.query.return_value['results']['bindings'][-1]['value']['value'] = 'denied'
        with self.assertRaises(OldapErrorInconsistency):
            self.execute()

    def test_exact_retry_retains_uuid_timestamp_and_full_payload(self):
        self.execute()
        self.execute()
        self.assertEqual(self.update.call_args_list[0], self.update.call_args_list[1])


if __name__ == '__main__':
    unittest.main()
