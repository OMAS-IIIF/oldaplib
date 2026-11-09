"""Probe native Fuseki sessions using actual OLDAP access-token validation.

The private introspection peer is a local test host for the unchanged TokenCodec,
not a production API route. All identities, signing keys and service secrets are
fresh fixtures; no actual user token, password, Redis or GraphDB is involved.
"""
import argparse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
from urllib.error import HTTPError
from urllib.parse import parse_qs
from urllib.request import Request, urlopen

import jwt
import probe_http_sessions as session_probe
from oldaplib.src.authentication import AuthorizationContext, TokenCodec, TokenSettings
from oldaplib.src.helpers.oldaperror import OldapErrorToken


class IdentityPeer:
    """Owned introspection host; fail closed and never log bearer credentials."""
    def __init__(self):
        self.secret = secrets.token_urlsafe(32)
        self.transport_secret = secrets.token_urlsafe(32)
        self.codec = TokenCodec(TokenSettings(access_secret=secrets.token_urlsafe(32)))
        self.mode = 'normal'
        peer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                """Validate with the same codec used by the existing Connection."""
                if self.path != '/introspect':
                    self.send_error(404)
                    return
                if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + peer.secret):
                    self.send_error(401)
                    return
                if peer.mode == 'unavailable':
                    self.send_error(503)
                    return
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16384:
                    self.send_error(413)
                    return
                fields = parse_qs(self.rfile.read(size).decode())
                tokens = fields.get('token', [])
                result = {'active': False}
                if len(tokens) == 1:
                    try:
                        context = peer.codec.decode_access_token(tokens[0])
                        result = {'active': True, 'sub': str(context.userIri)}
                    except OldapErrorToken:
                        pass
                if peer.mode == 'malformed':
                    result = {'active': True, 'sub': 'not-an-absolute-iri'}
                data = json.dumps(result).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_port}/introspect'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def token(self, name):
        context = AuthorizationContext.from_claims(user_id=name,
            user_iri='https://example.org/callback/' + name,
            claims={'inProject': {}, 'hasRole': {}})
        return self.codec.issue_access_token(context)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def run(java, jar, output):
    """Run the shared suite on Fuseki and verify invalid identity failure paths."""
    output.mkdir(parents=True, exist_ok=False)
    peer = IdentityPeer()
    original_tokens = session_probe.TOKENS
    access = peer.token('actor')
    session_probe.TOKENS = ('Bearer ' + access, 'Bearer ' + peer.token('other'))

    class FusekiConnection(session_probe.HttpProbeConnection):
        server_source = 'FusekiSessionProbe.java'
        route_prefix = '/tx'

        def server_environment(self):
            # No OLDAP JWT signing key is sent to Java. It cannot mint user tokens.
            environment = {key: value for key, value in os.environ.items()
                           if not (key.startswith('OLDAP_') and key.endswith('JWT_SECRET'))}
            return dict(environment, PROBE_IDENTITY_URL=peer.url,
                        PROBE_IDENTITY_SECRET=peer.secret, PROBE_TRANSPORT_SECRET=peer.transport_secret)

        def request_headers(self):
            return {'X-Oldap-Service-Key': peer.transport_secret}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._userdata = peer.codec.decode_access_token(access)

    con = None
    log = None
    checks = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print('PASS', name, flush=True)

    def status(operation='STATUS', token=None, headers=None, path=None, method='POST'):
        request = Request(path or f'{con.base}/{operation}/{con.session}', data=b'',
            headers=headers if headers is not None else dict(con.request_headers(), Authorization=token or session_probe.TOKENS[0]),
            method=method)
        try:
            with urlopen(request, timeout=10) as response:
                return response.status
        except HTTPError as error:
            return error.code

    try:
        session_probe.run(java, jar, output / 'sessions', connection_factory=FusekiConnection)
        log = (output / 'identity.log').open('a')
        con = FusekiConnection(java, jar, output / 'identity-dataset', log)
        check('Real OLDAP TokenCodec identity is accepted by Fuseki servlet', status() == 200)
        check('Private servlet rejects GET and TRACE', status(method='GET') == 405 and status(method='TRACE') == 405)
        check('Access token alone cannot access internal transaction endpoint',
              status(headers={'Authorization': session_probe.TOKENS[0]}) == 401)
        check('Service credential alone is not an OLDAP identity', status(headers=con.request_headers()) == 401)
        check('Invalid service credential is rejected',
              status(headers={'Authorization': session_probe.TOKENS[0], 'X-Oldap-Service-Key': 'wrong'}) == 401)
        check('Unsigned actor header cannot substitute for a verified token',
              status(headers=dict(con.request_headers(), **{'X-Oldap-Actor': str(con.userIri)})) == 401)

        payload = jwt.decode(access, options={'verify_signature': False}) # Fixture mutation only.
        key = peer.codec.settings.require_access_secret()
        for name, changes in [
            ('expired', {'exp': int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())}),
            ('wrong audience', {'aud': 'unrelated-service'}),
            ('wrong issuer', {'iss': 'https://wrong.example'}),
            ('wrong purpose', {'typ': 'media'}),
            ('malformed authorization context', {'auth': {'inProject': [], 'hasRole': {}}}),
        ]:
            invalid = jwt.encode(dict(payload, **changes), key, algorithm='HS256')
            check('Existing codec rejects ' + name, status(token='Bearer ' + invalid) == 401)
        forged = jwt.encode(payload, secrets.token_urlsafe(32), algorithm='HS256')
        check('Existing codec rejects forged signature', status(token='Bearer ' + forged) == 401)
        check('Service secret is not accepted as access token', status(token='Bearer ' + peer.secret) == 401)

        con.transaction_start()
        con.transaction_update('INSERT DATA { GRAPH <urn:identity:test> { <urn:item> <urn:value> 1 } }')
        expired = jwt.encode(dict(payload, exp=int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())),
                             key, algorithm='HS256')
        check('Expired access token cannot commit an existing session', status('COMMIT', token='Bearer ' + expired) == 401)
        renewed = peer.token('actor')
        check('New valid token for the same actor retains session ownership',
              json.loads(con.send('QUERY', 'ASK { GRAPH <urn:identity:test> { ?s ?p ?o } }',
                                  token='Bearer ' + renewed))['boolean'])
        peer.mode = 'unavailable'
        check('Verifier outage blocks commit without claiming success', status('COMMIT') == 503)
        peer.mode = 'malformed'
        check('Malformed verified identity blocks commit', status('COMMIT') == 503)
        peer.mode = 'normal'
        con.transaction_abort()
        check('Rejected identity checks leave no committed application writes',
              not con.query('ASK { GRAPH <urn:identity:test> { ?s ?p ?o } }')['boolean'])
        check('Raw Fuseki dataset endpoint is not mounted', status(path=con.base.removesuffix('/tx') + '/application/query') == 404)
        # A caller knowing the peer address cannot introspect without service auth.
        try:
            urlopen(Request(peer.url, data=b'token=invalid'), timeout=3)
        except HTTPError as error:
            check('Identity peer itself requires separate service credentials', error.code == 401)
        else:
            raise AssertionError('Unauthenticated introspection accepted')
        (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': checks}, indent=2) + '\n')
    finally:
        if con is not None and con.process.poll() is None:
            con.close()
        if log is not None:
            log.close()
        session_probe.TOKENS = original_tokens
        peer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', default='java')
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.java, args.jar, args.output.resolve())
