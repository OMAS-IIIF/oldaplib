"""Run the actual Connection login against fresh RDF 1.2 user data in Fuseki.

Only two internal bootstrap hooks select the HTTP transport and query dialect.
Password checking, UserData parsing, AuthorizationContext and JWT issuance execute
in the real library. This restricted subclass is not a general Jena Connection.
"""
import argparse
import inspect
import json
import os
from pathlib import Path
import secrets
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import bcrypt
import probe_http_sessions as sessions
from probe_fuseki_identity import IdentityPeer
from oldaplib.src.authentication import TokenCodec, TokenSettings
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_user_query import jena_user_query
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.userdataclass import UserData
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_string import Xsd_string


def run(java, jar, output):
    """Own all services/data, seed fixtures, exercise login and close cleanly."""
    output.mkdir(parents=True, exist_ok=False)
    peer = IdentityPeer()
    bootstrap_secret = secrets.token_urlsafe(32)
    original_tokens = sessions.TOKENS
    sessions.TOKENS = ('Bearer ' + peer.token('actor'), 'Bearer ' + peer.token('other'))
    checks = []
    requests_seen = []
    log = (output / 'server.log').open('a')
    con = None

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print('PASS', name, flush=True)

    class Server(sessions.HttpProbeConnection):
        server_source = 'FusekiSessionProbe.java'
        route_prefix = '/tx'

        def server_environment(self):
            environment = {key: value for key, value in os.environ.items()
                           if not (key.startswith('OLDAP_') and key.endswith('JWT_SECRET'))}
            return dict(environment, PROBE_IDENTITY_URL=peer.url, PROBE_IDENTITY_SECRET=peer.secret,
                        PROBE_TRANSPORT_SECRET=peer.transport_secret, PROBE_BOOTSTRAP_SECRET=bootstrap_secret)

        def request_headers(self):
            return {'X-Oldap-Service-Key': peer.transport_secret}

    def bootstrap(query, *, with_key=True):
        headers = dict(con.request_headers())
        if with_key:
            headers['X-Oldap-Bootstrap-Key'] = bootstrap_secret
        request = Request(con.base + '/bootstrap', data=query.encode(), headers=headers)
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read())

    class LoginConnection(Connection):
        """Test-only bootstrap overrides; the public constructor is inherited."""
        def _bootstrap_query(self, sparql):
            requests_seen.append(sparql)
            return bootstrap(sparql)

        def _bootstrap_user_query(self, context, user_id):
            return jena_user_query(context, user_id)

        def query(self, *args, **kwargs):
            raise NotImplementedError('This proof supports initialization only')

    def login(**kwargs):
        return LoginConnection(server=con.base, repo='probe', context_name='JENA_LOGIN_PROBE',
                               token_codec=kwargs.pop('token_codec', peer.codec), **kwargs)

    try:
        con = Server(java, jar, output / 'dataset', log)
        context = Context(name='JENA_LOGIN_PROBE')
        prefixes = context.sparql_context + 'PREFIX demo: <https://example.org/demo#>\n'
        password = 'synthetic-password-for-owned-probe'
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
        # Model data is minimal and explicit; this does not claim inference parity.
        triples = '''
<https://example.org/project> a oldap:Project ; oldap:projectShortName "demo"^^xsd:NCName ;
    oldap:namespaceIri "https://example.org/demo#"^^xsd:anyURI .
'''
        for name, active in [('actor', 'true'), ('inactive', 'false'), ('unknown', 'true')]:
            triples += f'''
<https://example.org/callback/{name}> a oldap:User ;
    dcterms:creator <https://example.org/callback/actor> ;
    oldap:userId {Xsd_NCName(name).toRdf} ; schema:familyName "Example" ;
    schema:givenName "Probe" ; schema:email "probe@example.org" ;
    oldap:credentials {Xsd_string(password_hash).toRdf} ; oldap:isActive {active} .
'''
        triples += '''
<https://example.org/callback/actor> a demo:Curator ; oldap:authVersion 7 ;
    oldap:inProject <https://example.org/project>, <https://example.org/member-only> ;
    oldap:hasRole oldap:Editor, oldap:Observer ; demo:note "profile fixture" .
<urn:grant:one> rdf:reifies <<( <https://example.org/callback/actor> oldap:inProject <https://example.org/project> )>> ;
    oldap:hasAdminPermission oldap:ADMIN_USERS .
<urn:grant:two> rdf:reifies <<( <https://example.org/callback/actor> oldap:inProject <https://example.org/project> )>> ;
    oldap:hasAdminPermission oldap:ADMIN_RESOURCES .
<urn:grant:duplicate> rdf:reifies <<( <https://example.org/callback/actor> oldap:inProject <https://example.org/project> )>> ;
    oldap:hasAdminPermission oldap:ADMIN_USERS .
<urn:default:editor> rdf:reifies <<( <https://example.org/callback/actor> oldap:hasRole oldap:Editor )>> ;
    oldap:hasDefaultDataPermission oldap:DATA_UPDATE .
<urn:orphan:project> rdf:reifies <<( <https://example.org/callback/actor> oldap:inProject <https://example.org/not-a-member> )>> ;
    oldap:hasAdminPermission oldap:ADMIN_OLDAP .
<urn:orphan:role> rdf:reifies <<( <https://example.org/callback/actor> oldap:hasRole oldap:NotAssigned )>> ;
    oldap:hasDefaultDataPermission oldap:DATA_PERMISSIONS .
'''
        con.transaction_start()
        con.transaction_update(prefixes + 'INSERT DATA { GRAPH oldap:admin { ' + triples + ' } }')
        con.transaction_commit()
        authenticated = login(userId='actor', credentials=password)
        check('Real Connection constructor authenticates bcrypt credentials from Jena', str(authenticated.userIri) == 'https://example.org/callback/actor')
        check('Public constructor signature is unchanged in the probe', inspect.signature(LoginConnection) == inspect.signature(Connection))
        check('Project namespaces are loaded before user properties', 'https://example.org/demo#' in context.sparql_context)
        claims = authenticated.userdata.to_claims()
        check('Multiple and duplicate RDF 1.2 project grants parse correctly',
              claims['inProject']['https://example.org/project'] == ['oldap:ADMIN_RESOURCES', 'oldap:ADMIN_USERS'])
        check('Membership without annotations and role without default remain present',
              claims['inProject']['https://example.org/member-only'] == [] and claims['hasRole']['oldap:Observer'] is None)
        check('Role default and authVersion survive initialization',
              claims['hasRole']['oldap:Editor'] == 'oldap:DATA_UPDATE' and authenticated.auth_version == 7)
        check('Unasserted reified memberships do not confer grants',
              'https://example.org/not-a-member' not in claims['inProject'] and 'oldap:NotAssigned' not in claims['hasRole'])
        decoded = peer.codec.decode_access_token(authenticated.token)
        check('Issued access token preserves identity and permissions', decoded.userIri == authenticated.userIri and decoded.to_claims() == claims)
        check('Issued login token is accepted by native Fuseki session endpoint',
              con.send('STATUS', token='Bearer ' + authenticated.token) == 'committed')

        raw = bootstrap(jena_user_query(context, Iri('https://example.org/callback/actor')))
        data = UserData.from_query(QueryProcessor(context=context, query_result=raw))
        check('IRI lookup preserves custom user class and additional profile properties',
              str(data.userclass) == 'demo:Curator' and str(next(iter(data.additionalProperties.values()))) == 'profile fixture')
        reversed_result = dict(raw, results={'bindings': list(reversed(raw['results']['bindings']))})
        reversed_data = UserData.from_query(QueryProcessor(context=context, query_result=reversed_result))
        check('Actual Jena result order does not change permissions', data.inProject == reversed_data.inProject and data.hasRole == reversed_data.hasRole)

        for name, supplied in [('actor', 'wrong-password'), ('inactive', password)]:
            try:
                login(userId=name, credentials=supplied)
            except OldapError as error:
                check('Existing login rejects ' + ('wrong password' if name == 'actor' else 'inactive user'), str(error) == 'Wrong credentials')
            else:
                raise AssertionError('Rejected login unexpectedly succeeded')
        try:
            login(userId='missing', credentials=password)
        except OldapErrorNotFound:
            check('Missing user preserves existing not-found behavior', True)
        else:
            raise AssertionError('Missing user accepted')
        anonymous = login()
        check('Anonymous initialization uses the existing unknown user and default version', str(anonymous.userid) == 'unknown' and anonymous.auth_version == 0)
        no_token = login(userId='actor', credentials=password, issue_access_token=False,
                         token_codec=TokenCodec(TokenSettings()))
        check('Credential authentication without token issuance needs no signing key', no_token.token is None and no_token.userdata.to_claims() == claims)
        before = len(requests_seen)
        restored = login(token=authenticated.token)
        check('Access-token reconstruction preserves existing no-bootstrap behavior',
              len(requests_seen) == before and restored.userdata.to_claims() == claims and restored.auth_version is None)
        for query, with_key, expected in [('ASK {}', False, 401), ('INSERT DATA { <urn:bad> <urn:p> 1 }', True, 400)]:
            try:
                bootstrap(query, with_key=with_key)
            except HTTPError as error:
                check('Bootstrap rejects ' + ('missing separate credential' if not with_key else 'mutation'), error.code == expected)
            else:
                raise AssertionError('Bootstrap boundary accepted invalid request')
        check('Bootstrap view cannot read commit receipts', not bootstrap('ASK { GRAPH <urn:probe:http-commits> { ?s ?p ?o } }')['boolean'])
        (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': checks}, indent=2) + '\n')
    finally:
        if con is not None and con.process.poll() is None:
            con.close()
        log.close()
        sessions.TOKENS = original_tokens
        peer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', default='java')
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.java, args.jar, args.output.resolve())
