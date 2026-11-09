"""Resource permission checks retain GraphDB syntax and transaction-local reads."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.objectfactory import ResourceInstance
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.helpers.jena_permission_write import replace_memberships


@pytest.mark.parametrize('rdf12', [False, True])
@pytest.mark.parametrize('active', [False, True])
def test_permission_check_uses_selected_dialect_and_active_transaction(rdf12, active):
    con = SimpleNamespace(context_name='RESOURCE_PERMISSION_UNIT', userIri=Iri('https://example.org/user'),
        _resource_permissions_rdf12=rdf12, in_transaction=lambda: active,
        query=Mock(return_value={'boolean': True}), transaction_query=Mock(return_value={'boolean': True}))
    instance = SimpleNamespace(_con=con, _iri=Iri('https://example.org/resource'), _graph='demo')
    assert ResourceInstance.get_data_permission(instance, DataPermission.DATA_UPDATE)
    selected, unused = (con.transaction_query, con.query) if active else (con.query, con.transaction_query)
    unused.assert_not_called()
    query = selected.call_args.args[0]
    assert 'GRAPH demo:data' in query and 'GRAPH oldap:admin' in query
    assert '<https://example.org/resource> oldap:attachedToRole ?role .' in query
    assert ('rdf:reifies' in query) == rdf12
    assert ('<<( ' in query) == rdf12


def test_empty_resource_grant_replacement_is_scoped_and_removes_membership():
    query = replace_memberships('<https://example.org/resource>', 'oldap:attachedToRole', {}, graph='demo:data')
    assert 'oldap:admin' not in query
    assert 'INSERT DATA' not in query
    assert 'DELETE WHERE { GRAPH demo:data { <https://example.org/resource> oldap:attachedToRole ?target } }' in query
    assert 'oldap:hasDataPermission' in query
