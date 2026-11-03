"""Bulk-read dialect, result-shape and transaction-routing regressions."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.objectfactory import ResourceInstance
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@pytest.mark.parametrize('rdf12', [False, True])
@pytest.mark.parametrize('active', [False, True])
def test_bulk_reads_keep_projection_and_route_to_current_transaction(rdf12, active):
    reply = {'head': {'vars': ['s', 'o0']}, 'results': {'bindings': [
        {'s': {'type': 'uri', 'value': 'https://example.org/resource'},
         'o0': {'type': 'literal', 'value': 'first'}},
        {'s': {'type': 'uri', 'value': 'https://example.org/resource'},
         'o0': {'type': 'literal', 'value': 'second'}}]}}
    con = SimpleNamespace(context_name='BULK_READ_UNIT', userIri=Iri('https://example.org/user'),
        _resource_permissions_rdf12=rdf12, in_transaction=lambda: active,
        query=Mock(return_value=reply), transaction_query=Mock(return_value=reply))
    with patch('oldaplib.src.objectfactory.Project.read', return_value=SimpleNamespace(projectShortName='demo')):
        result = ResourceInstance.all_resources(con, 'demo', 'demo:Record',
            includeProperties=[Xsd_QName('demo:body'), Xsd_QName('demo:missing')])
    selected, unused = (con.transaction_query, con.query) if active else (con.query, con.transaction_query)
    unused.assert_not_called()
    query = selected.call_args.args[0]
    assert ('rdf:reifies <<(' in query) == rdf12
    assert ('<< ?s oldap:attachedToRole ?role >>' in query) == (not rdf12)
    assert 'GRAPH demo:data' in query and 'GRAPH oldap:admin' in query
    assert '?s oldap:attachedToRole ?role .' in query
    assert len(result) == 1
    assert [str(value) for value in result[0][Xsd_QName('demo:body')]] == ['first', 'second']
    assert result[0][Xsd_QName('demo:missing')] == []
    assert str(result[0]['iri'][0]) == 'https://example.org/resource'


def test_bulk_query_error_is_not_masked_by_logging():
    con = SimpleNamespace(context_name='BULK_READ_UNIT', userIri=Iri('https://example.org/user'),
        in_transaction=lambda: False, query=Mock(side_effect=OldapError('query failed')))
    with patch('oldaplib.src.objectfactory.Project.read', return_value=SimpleNamespace(projectShortName='demo')):
        with pytest.raises(OldapError, match='query failed'):
            ResourceInstance.all_resources(con, 'demo', 'demo:Record')
