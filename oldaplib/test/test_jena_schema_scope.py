"""Schema discovery reuse must remain bounded to one explicit read operation."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from oldaplib.src.jena_connection import JenaConnection


def connection():
    """Build a transport-free connection with changeable registration results."""
    con = object.__new__(JenaConnection)
    con._context_name = "SCHEMA_SCOPE_TEST"
    con._transaction_url = None
    con._session_id = None
    con._token = "owned-test-token"
    con.query = Mock(return_value={"results": {"bindings": []}})
    con.transaction_query = con.query
    con._jena = SimpleNamespace(
        service_key="owned-test-key", url="http://owned.invalid", timeout=1
    )
    con._http = Mock()
    con._http.post.return_value = SimpleNamespace(status_code=200, text="")
    return con


def test_scope_reuses_per_project_and_does_not_leak_or_expose_mutable_cache():
    con = connection()
    with con._resource_schema_scope():
        first = con._resource_schema_graphs("demo")
        first.append("foreign:onto")
        with con._resource_schema_scope():
            assert "foreign:onto" not in con._resource_schema_graphs("demo")
        assert con._resource_schema_graphs("other")[0] == "other:onto"
        assert con.query.call_count == 2
    con.query.return_value = {"results": {"bindings": [{"prefix": {"value": "new"}}]}}
    with con._resource_schema_scope():
        assert "<urn:oldap:vocab:new>" in con._resource_schema_graphs("demo")
    assert con.query.call_count == 3


def test_scope_discards_on_failure_and_unscoped_calls_remain_live():
    con = connection()
    with pytest.raises(RuntimeError):
        with con._resource_schema_scope():
            con._resource_schema_graphs("demo")
            raise RuntimeError("owned failure")
    con._resource_schema_graphs("demo")
    con._resource_schema_graphs("demo")
    assert con.query.call_count == 3
    assert con._scoped_schema_graphs is None


def test_active_transaction_always_reads_its_own_current_registrations():
    con = connection()
    con._transaction_url = "http://owned.invalid/tx"
    with con._resource_schema_scope():
        con._resource_schema_graphs("demo")
        con.query.return_value = {
            "results": {"bindings": [{"prefix": {"value": "uncommitted"}}]}
        }
        assert "<urn:oldap:vocab:uncommitted>" in con._resource_schema_graphs("demo")
    assert con.transaction_query.call_count == 2


@pytest.mark.parametrize(
    "operation", ["BEGIN", "UPDATE", "COMMIT", "ABORT", "IMPORT_GRAPHS"]
)
def test_non_read_send_invalidates_before_the_transport(operation):
    con = connection()
    with con._resource_schema_scope():
        con._resource_schema_graphs("demo")
        con._send(operation)
        con._resource_schema_graphs("demo")
        assert con.query.call_count == 2
