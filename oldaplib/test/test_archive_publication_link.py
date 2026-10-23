"""Additive publication links preserve permissions and review exact state."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch
from oldaplib.src.archive_publication import ArchivePublication, PublicationConflict
from oldaplib.src.enums.datapermissions import DataPermission as DP
from oldaplib.test.test_archive_publication import PublicationTests, DEFINITION


class LinkTests(TestCase):
    def setUp(self):
        fixture = PublicationTests(); fixture.setUp()
        self.policy = fixture.policy
        self.service = object.__new__(ArchivePublication)
        self.service._con = MagicMock(userIri=fixture.con.userIri)
        self.service.project = fixture.project
        self.request = {'mediaIri': 'urn:media:test', 'parentIri': 'urn:parent:test'}
        self.service._read = MagicMock(side_effect=lambda iri, policy: MagicMock(iri=iri))
        self.patches = [
            patch('oldaplib.src.archive_publication._kind', side_effect=lambda r,d: 'media' if r.iri == 'urn:media:test' else 'root'),
            patch('oldaplib.src.archive_publication.single', return_value=DEFINITION['publishedStatusIri']),
            patch('oldaplib.src.archive_publication.values', return_value=[]),
            patch('oldaplib.src.archive_publication._public_permission', return_value=DP.DATA_VIEW),
            patch.object(type(self.policy),'require_data'),
            patch('oldaplib.src.archive_publication.resource_query',return_value={'results':{'bindings':[]}}),
        ]
        self.mocks = [p.start() for p in self.patches]
        for p in self.patches:self.addCleanup(p.stop)

    def test_review_checks_update_on_both_and_binds_request(self):
        revision, exists = self.service._link_review(self.request,self.policy,DEFINITION)
        self.assertFalse(exists)
        self.assertEqual(self.mocks[4].call_count,2)
        other = {**self.request,'parentIri':'urn:parent:other'}
        self.assertNotEqual(revision,self.service._link_review(other,self.policy,DEFINITION)[0])

    def test_private_parent_and_unequal_grants_rejected(self):
        self.mocks[1].return_value = None
        with self.assertRaises(PublicationConflict):self.service._link_review(self.request,self.policy,DEFINITION)
        self.mocks[1].return_value = DEFINITION['publishedStatusIri']
        self.mocks[3].side_effect = [DP.DATA_VIEW,DP.DATA_VIEW,DP.DATA_RESTRICTED,DP.DATA_VIEW]
        with self.assertRaises(PublicationConflict):self.service._link_review(self.request,self.policy,DEFINITION)

    def test_stale_review_and_receipt_conflict_write_nothing(self):
        self.service._configured = MagicMock(return_value=(self.policy,DEFINITION))
        self.service._authorize = MagicMock()
        self.service._link_review = MagicMock(return_value=('b'*64,False))
        self.service._receipt = MagicMock(return_value=None)
        request={**self.request,'revision':'a'*64}
        with patch('oldaplib.src.archive_publication.resource_transaction',return_value=nullcontext()):
            with self.assertRaises(PublicationConflict):self.service.apply_link(request,'6c49ea1c-ce68-46c4-bd14-983bdce55954')
            self.service._receipt.return_value={'requestDigest':'other'}
            with self.assertRaises(PublicationConflict):self.service.apply_link(request,'6c49ea1c-ce68-46c4-bd14-983bdce55954')
        self.service._con.transaction_update.assert_not_called()
