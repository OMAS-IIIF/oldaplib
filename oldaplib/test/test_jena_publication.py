"""Run publication policy decisions with the RDF 1.2 backend enabled."""
from contextlib import nullcontext
from unittest.mock import Mock, patch

from oldaplib.test import test_archive_publication as legacy
from oldaplib.src.archive_publication import PublicationConflict
from oldaplib.src.enums.datapermissions import DataPermission as DP
from oldaplib.src.helpers.jena_permission_write import clear_membership_annotations


class JenaPublicationTests(legacy.PublicationServiceTests):
    def setUp(self):
        super().setUp()
        self.con._resource_permissions_rdf12 = True
        self.con.transaction_query = Mock(return_value={'boolean': False})

    def test_apply_replaces_only_public_grants_and_writes_receipt_last(self):
        self.service._review = Mock(return_value=(self.records,
            {iri: DP.DATA_VIEW for iri in self.records}, 'a' * 64))
        with patch('oldaplib.src.archive_publication.resource_transaction', return_value=nullcontext()):
            self.service.apply({'resourceIri': 'urn:test:root', 'permission': 'DATA_VIEW', 'revision': 'a' * 64},
                               '00000000-0000-4000-8000-000000000001')
        queries = [call.args[0] for call in self.con.transaction_update.call_args_list]
        assert len(queries) == 3
        for query in queries[:2]:
            assert 'rdf:reifies <<(' in query
            assert 'oldap:attachedToRole <http://oldap.org/base#Unknown>' in query
            assert '?target' not in query
            assert 'FILTER NOT EXISTS' in query
        assert 'urn:oldap:archive-operations' in queries[-1]

    def test_shared_reifier_uses_publication_conflict(self):
        self.con.transaction_query.return_value = {'boolean': True}
        self.service._review = Mock(return_value=(self.records,
            {iri: DP.DATA_VIEW for iri in self.records}, 'a' * 64))
        with patch('oldaplib.src.archive_publication.resource_transaction', return_value=nullcontext()):
            with self.assertRaises(PublicationConflict):
                self.service.apply({'resourceIri': 'urn:test:root', 'permission': 'DATA_VIEW', 'revision': 'a' * 64},
                                   '00000000-0000-4000-8000-000000000001')
        self.con.transaction_update.assert_not_called()


def test_targeted_cleanup_does_not_change_existing_whole_map_default():
    whole = clear_membership_annotations('demo:resource', 'oldap:attachedToRole', graph='demo:data')
    public = clear_membership_annotations('demo:resource', 'oldap:attachedToRole', graph='demo:data', target='demo:Public')
    assert '?target' in whole
    assert public == whole.replace('?target', 'demo:Public')
