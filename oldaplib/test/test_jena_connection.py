"""Offline failure semantics for the opt-in transport; no database or Redis I/O."""
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from oldaplib.src.jena_connection import JenaConnection, JenaSettings
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorConfiguration


def connection():
    """Bypass credential bootstrap to test only session state transitions."""
    con = object.__new__(JenaConnection)
    con._jena = JenaSettings('http://localhost:9999/tx', 'service', 'bootstrap', 'admin', 60)
    con._session_id = uuid4()
    con._transaction_url = f'{con._jena.url}/STATUS/{con._session_id}'
    con._uncertain = False
    return con


def test_lost_commit_reply_is_resolved_only_by_receipt():
    con = connection()
    con._send = Mock(side_effect=[OldapErrorConfiguration('lost'), 'committed'])
    con.transaction_commit()
    assert [call.args[0] for call in con._send.call_args_list] == ['COMMIT', 'STATUS']
    assert not con.in_transaction()
    assert not con._uncertain


def test_unknown_commit_retains_session_and_never_replays():
    con = connection()
    con._send = Mock(side_effect=[OldapErrorConfiguration('lost'), 'unknown', 'committed'])
    with pytest.raises(OldapErrorConfiguration):
        con.transaction_commit()
    assert con.in_transaction() and con._uncertain
    with pytest.raises(OldapErrorConfiguration):
        con.transaction_abort()
    with pytest.raises(OldapError):
        con.transaction_start()
    con.transaction_commit()
    assert [call.args[0] for call in con._send.call_args_list] == ['COMMIT', 'STATUS', 'STATUS']
    assert not con.in_transaction()


def test_nested_start_does_not_send_or_abandon_transaction():
    con = connection()
    original = con._transaction_url
    con._send = Mock()
    with pytest.raises(OldapError):
        con.transaction_start()
    assert con._transaction_url == original
    con._send.assert_not_called()


@pytest.mark.parametrize('timeout', ['0', '-1', 'nan', 'inf', '3601', 'invalid'])
def test_invalid_timeout_fails_before_transport(monkeypatch, timeout):
    for key, value in {'URL': 'http://localhost:9999/tx', 'SERVICE_KEY': 'secret',
                       'BOOTSTRAP_KEY': 'secret', 'FULLTEXT_KEY': 'secret', 'TIMEOUT': timeout}.items():
        monkeypatch.setenv('OLDAP_JENA_' + key, value)
    with pytest.raises(OldapErrorConfiguration):
        JenaSettings.from_environment()


def test_bootstrap_does_not_follow_redirect_or_leak_body():
    con = connection()
    with patch('oldaplib.src.jena_connection.requests.post', return_value=Mock(status_code=302, text='secret')) as post:
        with pytest.raises(OldapErrorConfiguration, match='uncertain') as error:
            con._send('BOOTSTRAP', 'ASK {}', bootstrap=True)
    assert 'secret' not in str(error.value)
    assert post.call_count == 1
    assert post.call_args.kwargs['allow_redirects'] is False
    assert post.call_args.kwargs['data'] == b'ASK {}'
    assert 'Authorization' not in post.call_args.kwargs['headers']


def test_lost_abort_reply_preserves_uncertain_ownership():
    con = connection()
    con._send = Mock(side_effect=OldapErrorConfiguration('lost'))
    with pytest.raises(OldapErrorConfiguration):
        con.transaction_abort()
    assert con.in_transaction() and con._uncertain
    with pytest.raises(OldapErrorConfiguration):
        con.transaction_update('INSERT DATA {}')
    assert con._send.call_count == 1


@pytest.mark.parametrize('active', [False, True])
def test_native_export_uses_current_transaction_when_available(active):
    con = connection()
    if not active:
        con._transaction_url = None
    con._send = Mock(return_value='native TriG')
    assert con._project_graph_export('demo', ['data']) == 'native TriG'
    assert con._send.call_args.args[0] == ('EXPORT_GRAPHS' if active else 'READ_GRAPHS')


def test_native_export_refuses_uncertain_session_without_sending():
    con = connection()
    con._uncertain = True
    con._send = Mock()
    with pytest.raises(OldapErrorConfiguration):
        con._project_graph_export('demo', ['data'])
    con._send.assert_not_called()


def idle_connection():
    """Prepare an authenticated transport without bootstrap or real storage."""
    con = connection()
    con._transaction_url = None
    con._session_id = None
    con._token = 'synthetic-access-token'
    return con


def test_refused_begin_retries_fresh_ids_and_balances_ownership():
    con = idle_connection()
    with patch('oldaplib.src.jena_connection.requests.post', side_effect=[
        Mock(status_code=409), Mock(status_code=409), Mock(status_code=200, text='active')
    ]) as post, patch('oldaplib.src.jena_connection.time.sleep') as sleep, \
            patch('oldaplib.src.jena_connection.transaction_opened') as opened, \
            patch('oldaplib.src.jena_connection.transaction_closed') as closed:
        con.transaction_start()
    urls = [call.args[0] for call in post.call_args_list]
    assert len(set(urls)) == 3
    assert all('/BEGIN/' in url for url in urls)
    assert [call.args[0] for call in sleep.call_args_list] == [0.05, 0.1]
    assert closed.call_args_list == opened.call_args_list[:2]
    assert opened.call_args_list[-1].args[0] == con._transaction_url
    assert con.in_transaction() and not con._uncertain


def test_persistent_begin_refusal_is_bounded_and_leaves_no_owner():
    from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists
    con = idle_connection()
    with patch('oldaplib.src.jena_connection.requests.post', return_value=Mock(status_code=409)) as post, \
            patch('oldaplib.src.jena_connection.time.sleep') as sleep, \
            patch('oldaplib.src.jena_connection.transaction_opened') as opened, \
            patch('oldaplib.src.jena_connection.transaction_closed') as closed:
        with pytest.raises(OldapErrorAlreadyExists):
            con.transaction_start()
    assert post.call_count == 5
    assert [call.args[0] for call in sleep.call_args_list] == [0.05, 0.1, 0.2, 0.4]
    assert opened.call_args_list == closed.call_args_list
    assert not con.in_transaction() and not con._uncertain
    assert con._session_id is None


@pytest.mark.parametrize('failure', [401, 403, 500, 503, 'timeout', 'connection'])
@pytest.mark.parametrize('prior_refusal', [False, True])
def test_other_begin_failures_never_retry_and_retain_uncertain_owner(failure, prior_refusal):
    import requests
    con = idle_connection()
    error = (requests.Timeout('private URL') if failure == 'timeout' else
             requests.ConnectionError('private URL') if failure == 'connection' else
             Mock(status_code=failure))
    replies = ([Mock(status_code=409)] if prior_refusal else []) + [error]
    with patch('oldaplib.src.jena_connection.requests.post', side_effect=replies) as post, \
            patch('oldaplib.src.jena_connection.time.sleep') as sleep, \
            patch('oldaplib.src.jena_connection.transaction_opened') as opened, \
            patch('oldaplib.src.jena_connection.transaction_closed') as closed:
        with pytest.raises(OldapError):
            con.transaction_start()
        with pytest.raises(OldapError):
            con.transaction_start()
    assert post.call_count == 1 + int(prior_refusal)
    assert sleep.call_count == int(prior_refusal)
    assert closed.call_args_list == opened.call_args_list[:-1]
    assert con.in_transaction() and con._uncertain
    assert con._transaction_url == opened.call_args_list[-1].args[0]


def test_update_conflict_is_not_retried():
    from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists
    con = connection()
    con._token = 'synthetic-access-token'
    with patch('oldaplib.src.jena_connection.requests.post', return_value=Mock(status_code=409)) as post, \
            patch('oldaplib.src.jena_connection.time.sleep') as sleep:
        with pytest.raises(OldapErrorAlreadyExists):
            con.transaction_update('INSERT DATA {}')
    assert post.call_count == 1
    assert '/UPDATE/' in post.call_args.args[0]
    sleep.assert_not_called()
