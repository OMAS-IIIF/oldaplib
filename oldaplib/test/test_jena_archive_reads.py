"""Archive query dialect and schema-scope regressions without shared services."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from oldaplib.src.archive_adoption import ArchiveAdoption
from oldaplib.src.archive_inventory import ArchiveInventory
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri


@pytest.mark.parametrize('rdf12', [False, True])
@pytest.mark.parametrize('active', [False, True])
def test_inventory_and_adoption_queries_select_backend_and_transaction(rdf12, active):
    context = Context(name='ARCHIVE_READ_UNIT')
    context['demo'] = NamespaceIRI('https://example.org/demo/')
    reply = {'head': {'vars': []}, 'results': {'bindings': []}}
    con = SimpleNamespace(context_name='ARCHIVE_READ_UNIT', userIri=Iri('https://example.org/user'),
        _resource_permissions_rdf12=rdf12, in_transaction=lambda: active,
        query=Mock(return_value=reply), transaction_query=Mock(return_value=reply))
    repo = object.__new__(ArchiveAdoption)
    repo._con = con
    repo.project = SimpleNamespace(projectShortName='demo')
    policy = SimpleNamespace(context=context, media_classes=['https://example.org/demo/Catalogue'])
    folder = SimpleNamespace(iri=Iri('demo:folder'), get=lambda prop: {Iri('demo:area')})
    inventory = object.__new__(ArchiveInventory)
    inventory._con = con
    inventory.repository = repo
    inventory._rows(policy, folder, 3, None)
    repo._direct_media_counts([{'iri': 'https://example.org/demo/folder'}], 'https://example.org/demo/area', policy)
    selected, unused = (con.transaction_query, con.query) if active else (con.query, con.transaction_query)
    unused.assert_not_called()
    for call in selected.call_args_list:
        query = call.args[0]
        assert ('rdf:reifies <<(' in query) == rdf12
        assert ('FROM demo:onto FROM shared:onto FROM oldap:onto' in query) == rdf12
        assert ('FROM NAMED demo:data FROM NAMED oldap:admin' in query) == rdf12
        assert ('?class = ' in query) == rdf12
        assert 'GRAPH demo:data' in query and 'GRAPH oldap:admin' in query
        assert 'oldap:createdBy' in query
        assert 'oldap:attachedToRole' in query

    assert repo._visibility('?media').startswith('{') == rdf12
    selected.reset_mock()
    repo._states(['https://example.org/demo/folder'], policy)
    repo.folder_revision(folder, policy)
    for call in selected.call_args_list:
        query = call.args[0]
        assert ('rdf:reifies <<(' in query) == rdf12
        assert 'GRAPH demo:data' in query
        # Snapshots preserve annotation state, but not reifier identifiers.
        assert '?archiveGrant' not in query.split('WHERE')[0]


@pytest.mark.parametrize('rdf12', [False, True])
def test_archive_level_validation_selects_the_same_schemas_for_preflight_and_writes(rdf12):
    from oldaplib.src.archive_domain import _archive_level_query
    context = Context(name='ARCHIVE_READ_UNIT')
    policy = SimpleNamespace(context=context, project=SimpleNamespace(projectShortName='demo'),
                             connection=SimpleNamespace(_resource_permissions_rdf12=rdf12))
    query = _archive_level_query(policy, 'shared:Series')
    assert ('FROM demo:onto FROM shared:onto FROM oldap:onto' in query) == rdf12
    assert '<http://oldap.org/shared#Series> a shared:ArchiveLevel' in query
