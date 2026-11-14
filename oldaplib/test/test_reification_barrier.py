"""Transaction-local annotation barriers including inherited and existing data."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from oldaplib.src.helpers.reification import guard_instance_write
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.resource_transaction import resource_operation
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.test.test_resource_transaction import MemoryConnection


class BarrierConnection(MemoryConnection):
    """Supply scalar query bindings without pretending to evaluate RDF 1.2."""
    def __init__(self, bindings=(), existing=False):
        super().__init__()
        self.bindings = list(bindings)
        self.existing = existing
        self.queries = []

    def transaction_query(self, query, result_format=None):
        assert self.active
        self.queries.append(query)
        if 'SELECT ?parent ?constraint' in query:
            return {'head': {'vars': ['parent', 'constraint']},
                    'results': {'bindings': self.bindings.pop(0) if self.bindings else []}}
        return {'boolean': self.existing}


class TestReificationBarrier(unittest.TestCase):
    def instance(self, con):
        return SimpleNamespace(_con=con, name=Xsd_QName('oldap:Thing'),
            _graph='test', iri=Iri('urn:test:resource'))

    def test_inherited_constraint_aborts_before_mutation(self):
        con = BarrierConnection([
            [{'parent': {'type': 'uri', 'value': 'http://oldap.org/shared#ParentShape'}}],
            [{'constraint': {'type': 'uri', 'value': 'http://www.w3.org/ns/shacl#reifierShape'}}],
        ])
        @resource_operation
        def update(instance):
            instance._con.transaction_update('must not execute')
        with patch('oldaplib.src.resource_transaction.archive_coordination_enabled', return_value=False):
            with self.assertRaisesRegex(OldapErrorValue, 'annotated'):
                update(self.instance(con))
        self.assertEqual(con.events, ['start', 'abort'])
        self.assertEqual(con.durable, [])
        self.assertIn('shared:ParentShape', con.queries[1])

    def test_existing_annotations_are_checked_in_project_graph(self):
        con = BarrierConnection(existing=True)
        con.transaction_start()
        with self.assertRaisesRegex(OldapErrorValue, 'Existing business reifiers'):
            guard_instance_write(self.instance(con), 'delete', (), {})
        self.assertIn('GRAPH test:data', con.queries[-1])
        self.assertIn('oldap:attachedToRole', con.queries[-1])

    def test_target_class_checked_and_plain_instance_passes(self):
        con = BarrierConnection()
        con.transaction_start()
        guard_instance_write(self.instance(con), 'transform_class', ('shared:Target',), {})
        self.assertIn('shared:TargetShape', con.queries[0])
        self.assertEqual(len(con.queries), 2)

    def test_transform_link_source_is_also_guarded(self):
        con = BarrierConnection([[], [
            {'constraint': {'type': 'uri', 'value': 'http://www.w3.org/ns/shacl#reifierShape'}}
        ]])
        con.transaction_start()
        instance = self.instance(con)
        source = self.instance(con)
        source.name = Xsd_QName('shared:Source')
        instance.factory = SimpleNamespace(read=lambda iri: source)
        with self.assertRaisesRegex(OldapErrorValue, 'annotated'):
            guard_instance_write(instance, 'transform_class', ('shared:Target',),
                                 {'link_from_iri': 'urn:test:source'})
        self.assertIn('shared:SourceShape', con.queries[-1])
