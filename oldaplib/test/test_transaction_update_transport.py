"""Offline regression checks for raw SPARQL transaction update transport."""
import unittest
from unittest.mock import Mock, patch
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError


class TransactionUpdateTransportTests(unittest.TestCase):
    def setUp(self):
        self.connection = object.__new__(Connection)
        self.connection._userdata = True
        self.connection._transaction_url = 'http://localhost:7200/repositories/test/transactions/id'
        self.connection._dbuser = None
        self.connection._dbpassword = None

    def test_large_unicode_update_uses_raw_body(self):
        query = 'INSERT DATA { <urn:s> <urn:p> "' + 'ſä𐀀' * 300000 + '" }'
        with patch('oldaplib.src.connection.requests.put', return_value=Mock(ok=True)) as put:
            self.connection.transaction_update(query)
        self.assertEqual(put.call_args.kwargs['data'], query.encode('utf-8'))
        self.assertEqual(put.call_args.kwargs['params'], {'action': 'UPDATE'})
        self.assertEqual(put.call_args.kwargs['headers']['Content-Type'],
                         'application/sparql-update; charset=UTF-8')

    def test_failure_and_transaction_guards(self):
        with patch('oldaplib.src.connection.requests.put', return_value=Mock(ok=False, text='rejected')):
            with self.assertRaises(OldapError):
                self.connection.transaction_update('INSERT DATA {}')
        self.connection._transaction_url = None
        with patch('oldaplib.src.connection.requests.put') as put:
            with self.assertRaises(OldapError):
                self.connection.transaction_update('INSERT DATA {}')
            put.assert_not_called()
