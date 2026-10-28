"""GraphDB login retains its wire format across the internal bootstrap seam."""
import unittest
from unittest.mock import Mock, patch

import bcrypt

from oldaplib.src.authentication import TokenCodec, TokenSettings
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.userdataclass import UserData
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_string import Xsd_string


class TestConnectionBootstrap(unittest.TestCase):
    def test_graphdb_password_login_preserves_requests_and_legacy_query(self):
        password = 'synthetic-bootstrap-test'
        user = UserData(userIri=Iri('https://example.org/test-user'), userId=Xsd_NCName('probe'),
                        familyName=Xsd_string('Example'), givenName=Xsd_string('Probe'),
                        email=Xsd_string('probe@example.org'), isActive=Xsd_boolean(True),
                        credentials=Xsd_string(bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()),
                        authVersion=4)
        empty = {'head': {'vars': []}, 'results': {'bindings': []}}
        response = Mock(status_code=200)
        response.json.return_value = empty
        codec = TokenCodec(TokenSettings(access_secret='synthetic-bootstrap-key-with-at-least-32-bytes'))
        with patch('oldaplib.src.connection.requests.post', return_value=response) as post, \
             patch.object(UserData, 'from_query', return_value=user):
            connection = Connection(server='http://example.invalid', repo='legacy', userId='probe',
                                    credentials=password, dbuser='service', dbpassword='service-fixture',
                                    token_codec=codec, context_name='BOOTSTRAP_UNIT')
        self.assertEqual(connection.auth_version, 4)
        self.assertEqual(codec.decode_access_token(connection.token).userIri, user.userIri)
        self.assertEqual(post.call_count, 2)
        for call in post.call_args_list:
            args = call.kwargs
            self.assertEqual(args['url'], 'http://example.invalid/repositories/legacy')
            self.assertEqual(args['auth'].username, 'service')
            self.assertEqual(args['auth'].password, 'service-fixture')
            self.assertEqual(args['headers'], {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8',
            })
        self.assertIn('SELECT ?sname ?ns', post.call_args_list[0].kwargs['data']['query'])
        self.assertEqual(post.call_args_list[1].kwargs['data']['query'],
                         UserData.sparql_query(Context(name='BOOTSTRAP_UNIT'), Xsd_NCName('probe')))

    def test_bootstrap_http_error_stops_initialization(self):
        response = Mock(status_code=503, text='synthetic unavailable')
        with patch('oldaplib.src.connection.requests.post', return_value=response) as post:
            with self.assertRaises(OldapError):
                Connection(server='http://example.invalid', repo='legacy', userId='probe',
                           credentials='fixture', token_codec=TokenCodec(TokenSettings()))
        self.assertEqual(post.call_count, 1)
        response.json.assert_not_called()


if __name__ == '__main__':
    unittest.main()
