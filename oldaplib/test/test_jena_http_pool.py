"""Owned loopback HTTP checks for pooling, isolation and connection cleanup.

No database, Redis, real credentials or shared service participates. The peer
speaks HTTP/1.1 so accepted TCP connections measure actual transport reuse.
"""
from contextlib import contextmanager
import gc
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from unittest.mock import Mock, patch
import weakref

import pytest

from oldaplib.src.jena_connection import JenaConnection, JenaSettings
from oldaplib.src.helpers.oldaperror import OldapErrorConfiguration


@contextmanager
def peer():
    """Serve bounded synthetic replies and record accepted sockets and headers."""
    calls = []
    sockets = []

    class Server(ThreadingHTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            sockets.append(address)
            return connection, address

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            calls.append((self.path, self.headers.get('Authorization')))
            self.send_response(503 if '/UPDATE/' in self.path else 200)
            self.send_header('Content-Length', '2')
            self.end_headers()
            self.wfile.write(b'{}')

    server = Server(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/tx', calls, sockets
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def connection(url='http://127.0.0.1:1/tx'):
    """Keep the real transport constructor; omit only library login/bootstrap."""
    settings = JenaSettings(url, 'service', 'bootstrap', 'admin', 5)
    with patch.object(JenaSettings, 'from_environment', return_value=settings), \
            patch('oldaplib.src.connection.Connection.__init__', return_value=None):
        return JenaConnection()


def test_reuses_tcp_connection_without_sharing_identity_or_retrying_writes():
    with peer() as (url, calls, sockets):
        first, second = connection(url), connection(url)
        try:
            for _ in range(20):
                first._send('BOOTSTRAP', 'ASK {}', bootstrap=True)
            assert len(sockets) == 1
            assert all(authorization is None for _, authorization in calls)
            first._token, second._token = 'first-fixture-token', 'second-fixture-token'
            first._send('READ', 'ASK {}')
            second._send('READ', 'ASK {}')
            assert len(sockets) == 2
            assert [value for _, value in calls[-2:]] == [
                'Bearer first-fixture-token', 'Bearer second-fixture-token']
            with pytest.raises(OldapErrorConfiguration):
                first._send('UPDATE', 'INSERT DATA {}')
            assert sum('/UPDATE/' in path for path, _ in calls) == 1
            assert len(sockets) == 2
            assert all(adapter.max_retries.total == 0 for adapter in first._http.adapters.values())
        finally:
            first._http.close()
            second._http.close()


def test_collected_connection_closes_pool_without_database_operations():
    session = Mock()
    with patch('oldaplib.src.jena_connection.requests.Session', return_value=session):
        con = connection()
    reference = weakref.ref(con)
    del con
    gc.collect()
    assert reference() is None
    session.close.assert_called_once_with()
    session.post.assert_not_called()


def test_failed_bootstrap_closes_pool_immediately():
    session = Mock()
    settings = JenaSettings('http://127.0.0.1:1/tx', 'service', 'bootstrap', 'admin', 5)
    with patch('oldaplib.src.jena_connection.requests.Session', return_value=session), \
            patch.object(JenaSettings, 'from_environment', return_value=settings), \
            patch('oldaplib.src.connection.Connection.__init__', side_effect=OldapErrorConfiguration('fixture')):
        with pytest.raises(OldapErrorConfiguration):
            JenaConnection()
    session.close.assert_called_once_with()
