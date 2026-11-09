"""Media identity ambiguity and transaction routing without shared services."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from oldaplib.src.helpers.jena_media import media_rows
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency
from oldaplib.src.xsd.iri import Iri


def reply(rows):
    return {'results': {'bindings': rows}}


@pytest.mark.parametrize('active', [False, True])
@pytest.mark.parametrize('by_id', [False, True])
def test_scoped_lookup_joins_existing_transaction(active, by_id):
    rows = [{'subject': {'value': 'urn:media'}, 'graph': {'value': 'https://example.org/data'}}]
    selected = Mock(side_effect=[reply([{'namespace': {'value': 'https://example.org/'}, 'shortName': {'value': 'media'}}]), reply(rows)])
    unused = Mock()
    con = SimpleNamespace(context_name='MEDIA_UNIT', userIri=Iri('urn:actor'),
                          in_transaction=lambda: active,
                          query=unused if active else selected, transaction_query=selected if active else unused)
    term = '"asset"' if by_id else '<urn:media>'
    assert media_rows(con, term, by_id=by_id)['results']['bindings'] == rows
    unused.assert_not_called()
    query = selected.call_args.args[0]
    assert 'FROM media:onto FROM shared:onto FROM oldap:onto' in query
    assert 'rdf:reifies <<(' in query
    # The selector must be bound in the aggregate's scope, not just outside it.
    assert term in query.split('SELECT ?subject (MAX')[1].split('GROUP BY')[0]


def test_duplicate_visible_identity_is_not_merged_into_a_token():
    con = SimpleNamespace(context_name='MEDIA_UNIT', userIri=Iri('urn:actor'), in_transaction=lambda: False,
        query=Mock(side_effect=[reply([{'namespace': {'value': 'https://example.org/'}, 'shortName': {'value': 'media'}}]), reply([
            {'subject': {'value': 'urn:one'}, 'graph': {'value': 'https://example.org/data'}},
            {'subject': {'value': 'urn:two'}, 'graph': {'value': 'https://example.org/data'}}])]))
    with pytest.raises(OldapErrorInconsistency, match='multiple visible'):
        media_rows(con, '"duplicate"', by_id=True)
