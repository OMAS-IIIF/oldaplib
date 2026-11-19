"""Offline transactional round trips for named annotation shape definitions."""
import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from rdflib import Dataset, URIRef

from oldaplib.test.test_datamodel_externalontology_sparql import _RecordingConnection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import (OldapErrorAlreadyExists, OldapErrorInUse, OldapErrorInconsistency,
    OldapErrorNoPermission, OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorValue)
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.reifier_shape import ReifierShape
from oldaplib.src.datamodel import DataModel
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.helpers.reification import validate_property_reifiers, invalidate_model_owners


def parent_names(value):
    """Compare parent sets without depending on RDF/store iteration order."""
    return {str(parent) for parent in (value or [])}


class DatasetConnection(_RecordingConnection):
    """Run real SPARQL on an isolated dataset with rollback snapshots."""
    def __init__(self):
        super().__init__()
        self.dataset = Dataset()

    def query(self, query, format=None):
        # Missing named graphs are empty in this isolated fixture, never URLs
        # to fetch through RDFLib's default FROM graph-loading behaviour.
        with patch('rdflib.plugins.sparql.SPARQL_LOAD_GRAPHS', False):
            result = self.dataset.query(query)
        return result.graph if result.type == 'CONSTRUCT' else json.loads(result.serialize(format='json'))

    def transaction_query(self, query, result_format=None):
        return self.query(query, result_format)

    def transaction_start(self):
        self.before = self.dataset.serialize(format='trig')
        super().transaction_start()

    def transaction_update(self, query):
        self.dataset.update(query)

    def transaction_abort(self):
        self.dataset = Dataset().parse(data=self.before, format='trig')
        super().transaction_abort()


class TestReifierShape(unittest.TestCase):
    def setUp(self):
        cache = patch("oldaplib.src.cachesingleton.CacheSingletonRedis")
        cache.start()
        self.addCleanup(cache.stop)
        resource_cache = patch("oldaplib.src.resourceclass.CacheSingletonRedis")
        resource_cache.start().return_value.get.return_value = None
        self.addCleanup(resource_cache.stop)
        self.con = DatasetConnection()
        self.project = Project(con=self.con, projectIri='https://example.org/project',
            projectShortName='example', namespaceIri=NamespaceIRI('https://example.org/ns/'),
            projectStart=Xsd_date('2026-01-01'))
        self.field = PropertyClass(con=self.con, project=self.project,
            property_class_iri='example:dateTime', datatype=XsdDatatypes.dateTime,
            minCount=1, maxCount=1)
        self.shape = ReifierShape(con=self.con, project=self.project,
            shape_iri='example:VisitShape', properties=[self.field])
        self.gate = patch('oldaplib.src.resource_transaction.archive_coordination_enabled', return_value=False)
        self.gate.start()
        self.addCleanup(self.gate.stop)

    def test_create_read_update_delete_round_trip(self):
        self.shape.create()
        loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        self.assertEqual(loaded['example:dateTime'].minCount, 1)
        loaded['example:dateTime'].maxCount = 2
        self.assertTrue(loaded.changeset)
        loaded.update()
        self.assertEqual(ReifierShape.read(self.con, self.project, loaded.shape_iri)['example:dateTime'].maxCount, 2)
        loaded.delete()
        with self.assertRaises(OldapErrorNotFound):
            ReifierShape.read(self.con, self.project, loaded.shape_iri)
        self.assertEqual(len(self.con.dataset.graph(URIRef('https://example.org/ns/shacl'))), 0)

    def test_superproperty_roundtrip_replace_clear_and_field_removal(self):
        from oldaplib.src.helpers.predicate_definition import read_superproperty
        self.shape['example:dateTime'].subPropertyOf = Iri('dcterms:date')
        self.shape.create()
        loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        self.assertEqual(parent_names(loaded['example:dateTime'].subPropertyOf), {'dcterms:date'})
        loaded['example:dateTime'].subPropertyOf = Iri('dcterms:created')
        loaded.update()
        loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        self.assertEqual(parent_names(loaded['example:dateTime'].subPropertyOf), {'dcterms:created'})
        loaded['example:dateTime'].subPropertyOf = None
        loaded.update()
        self.assertIsNone(ReifierShape.read(self.con, self.project, loaded.shape_iri)['example:dateTime'].subPropertyOf)
        loaded['example:dateTime'].subPropertyOf = Iri('dcterms:date')
        loaded.update()
        del loaded['example:dateTime']
        loaded.update()
        self.assertEqual(parent_names(read_superproperty(self.con, self.field.property_class_iri)), {'dcterms:date'})
        loaded.delete()
        self.assertEqual(parent_names(read_superproperty(self.con, self.field.property_class_iri)), {'dcterms:date'})

    def test_shared_parent_and_normal_property_update_use_one_definition(self):
        self.shape['example:dateTime'].subPropertyOf = Iri('dcterms:date')
        self.shape.create()
        other = ReifierShape(con=self.con, project=self.project, shape_iri='example:Other',
            properties=[self.shape['example:dateTime']])
        other.create()
        stale = ReifierShape.read(self.con, self.project, other.shape_iri)
        # Exercise ordinary PropertyClass persistence without a live service.
        ordinary = deepcopy(self.field, {id(self.con): self.con})
        ordinary.read_owl()
        ordinary.clear_changeset()
        ordinary.subPropertyOf = Iri('dcterms:created')
        self.con.transaction_start()
        self.con.transaction_update(Context(name=self.con.context_name).sparql_context + ordinary.update_owl())
        self.con.transaction_commit()
        for shape in (self.shape, other):
            self.assertEqual(parent_names(ReifierShape.read(self.con, self.project, shape.shape_iri)['example:dateTime'].subPropertyOf), {'dcterms:created'})
        with self.assertRaises(OldapErrorUpdateFailed):
            stale.update()
        fresh = ReifierShape.read(self.con, self.project, other.shape_iri)
        fresh['example:dateTime'].subPropertyOf = Iri('dcterms:date')
        fresh.update()
        ordinary.read_owl()
        self.assertEqual(parent_names(ordinary.subPropertyOf), {'dcterms:date'})

    def test_foreign_predicate_parent_is_readonly_and_not_copied(self):
        context = Context(name=self.con.context_name)
        self.con.dataset.update(context.sparql_context + '''INSERT DATA {
            GRAPH shared:onto { shared:date rdfs:subPropertyOf dcterms:date }
        }''')
        field = PropertyClass(con=self.con, project=self.project, property_class_iri='shared:date',
            datatype=XsdDatatypes.dateTime, subPropertyOf='dcterms:date')
        shape = ReifierShape(con=self.con, project=self.project, shape_iri='example:Foreign', properties=[field])
        shape.create()
        self.assertFalse(self.con.query(context.sparql_context + 'ASK { GRAPH example:onto { shared:date rdfs:subPropertyOf ?p }}')['boolean'])
        shape['shared:date'].subPropertyOf = Iri('dcterms:created')
        with self.assertRaises(OldapErrorNoPermission):
            shape.update()
        self.assertEqual(parent_names(ReifierShape.read(self.con, self.project, shape.shape_iri)['shared:date'].subPropertyOf), {'dcterms:date'})

    def test_imported_multiple_parents_are_not_silently_collapsed(self):
        self.shape.create()
        self.con.dataset.update(Context(name=self.con.context_name).sparql_context + '''INSERT DATA {
            GRAPH example:onto { example:dateTime rdfs:subPropertyOf dcterms:date, dcterms:created }
        }''')
        loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        self.assertEqual(parent_names(loaded['example:dateTime'].subPropertyOf),
                         {'dcterms:date', 'dcterms:created'})
        loaded['example:dateTime'].maxCount = 3
        loaded.update()
        loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        self.assertEqual(parent_names(loaded['example:dateTime'].subPropertyOf),
                         {'dcterms:date', 'dcterms:created'})

    def test_named_attribute_setter_accepts_multiple_and_scalar_parents(self):
        self.field.oldapSetAttr('subPropertyOf', ['dcterms:date', 'dcterms:created'])
        self.assertEqual(parent_names(self.field.subPropertyOf), {'dcterms:date', 'dcterms:created'})
        self.field.oldapSetAttr('subPropertyOf', 'dcterms:modified')
        self.assertEqual(parent_names(self.field.subPropertyOf), {'dcterms:modified'})
        self.field.oldapSetAttr('subPropertyOf', None)
        self.assertIsNone(self.field.subPropertyOf)

    def test_cached_scalar_parent_is_upgraded_before_read_and_edit(self):
        """Cloudpickle snapshots created before set support retain scalar attributes."""
        from oldaplib.src.enums.propertyclassattr import PropClassAttr
        self.field._attributes[PropClassAttr.SUBPROPERTY_OF] = Iri('dcterms:date')
        self.assertEqual(parent_names(self.field.subPropertyOf), {'dcterms:date'})
        self.field.clear_changeset()
        self.field.subPropertyOf.add('dcterms:created')
        self.assertEqual(parent_names(self.field.changeset[PropClassAttr.SUBPROPERTY_OF].old_value),
                         {'dcterms:date'})
        self.field.subPropertyOf = None
        self.assertIsNone(self.field.subPropertyOf)

    def test_imported_dcterms_parents_survive_inherited_model_read(self):
        """Bundled shared:ArchiveUnit resolves temporal's two real DCTERMS parents."""
        from pathlib import Path
        root = Path(__file__).parents[1] / 'ontologies'
        for name in ('oldap.trig', 'shared.trig'):
            self.con.dataset.parse(root / name, format='trig')
        self.con.dataset.graph(URIRef('http://purl.org/dc/terms/onto')).parse(
            root / 'standard' / 'dcterms.ttl', format='turtle')
        system = Project(con=self.con, projectIri='http://oldap.org/base#SystemProject',
            projectShortName='oldap', namespaceIri=NamespaceIRI('http://oldap.org/base#'),
            projectStart=Xsd_date('2026-01-01'))
        shared = Project(con=self.con, projectIri='http://oldap.org/shared#SharedProject',
            projectShortName='shared', namespaceIri=NamespaceIRI('http://oldap.org/shared#'),
            projectStart=Xsd_date('2026-01-01'))
        with patch.object(ResourceClass, '_sysproject', system), patch.object(
                ResourceClass, '_sharedproject', shared), patch(
                'oldaplib.src.propertyclass.CacheSingletonRedis') as cache, patch(
                'oldaplib.src.datamodel.CacheSingletonRedis'), patch(
                'oldaplib.src.datamodel.OldapList.ensure_list_node_context'), patch(
                'oldaplib.src.datamodel.ExternalOntology.search', return_value=[]):
            cache.return_value.get.return_value = None
            resource = ResourceClass(con=self.con, project=self.project,
                owlclass_iri='example:Archive', superclass=['shared:ArchiveUnit'])
            model = DataModel(con=self.con, project=self.project, resclasses=[resource])
            model.create()
            loaded = DataModel.read(self.con, self.project, ignore_cache=True)
            parent = loaded[Xsd_QName('example:Archive')].superclass[Xsd_QName('shared:ArchiveUnit')]
            temporal = parent.properties[Xsd_QName('dcterms:temporal')]
            self.assertEqual(parent_names(temporal.subPropertyOf), {'dc:coverage', 'dcterms:coverage'})
            field = PropertyClass(con=self.con, project=self.project,
                property_class_iri='dcterms:temporal', toClass='dcterms:PeriodOfTime', maxCount=1)
            shape = ReifierShape(con=self.con, project=self.project,
                shape_iri='example:Imported', properties=[field])
            shape.create()
            shape['dcterms:temporal'].maxCount = 2
            shape.update()
            fresh = ReifierShape.read(self.con, self.project, shape.shape_iri)
            self.assertEqual(parent_names(fresh['dcterms:temporal'].subPropertyOf),
                             {'dc:coverage', 'dcterms:coverage'})
            fresh['dcterms:temporal'].subPropertyOf = ['dcterms:coverage']
            with self.assertRaises(OldapErrorNoPermission):
                fresh.update()

    def test_multiple_parent_set_edits_clear_and_stale_snapshots(self):
        """In-place edits keep independent snapshots and persist the complete parent set."""
        self.shape['example:dateTime'].subPropertyOf = ['dcterms:date', 'dcterms:created']
        self.shape.create()
        stale = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        loaded['example:dateTime'].subPropertyOf.add('dcterms:modified')
        loaded.update()
        with self.assertRaises(OldapErrorUpdateFailed):
            stale.update()
        ordinary = deepcopy(self.field, {id(self.con): self.con})
        ordinary.read_owl()
        ordinary.clear_changeset()
        ordinary.subPropertyOf.discard(Iri('dcterms:date'))
        self.con.transaction_start()
        self.con.transaction_update(Context(name=self.con.context_name).sparql_context + ordinary.update_owl())
        self.con.transaction_commit()
        actual = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        self.assertEqual(parent_names(actual['example:dateTime'].subPropertyOf),
                         {'dcterms:created', 'dcterms:modified'})
        actual['example:dateTime'].subPropertyOf = []
        actual.update()
        self.assertIsNone(ReifierShape.read(self.con, self.project,
            self.shape.shape_iri)['example:dateTime'].subPropertyOf)

    def test_standalone_property_lifecycle_preserves_annotation_use(self):
        # RDFLib resolves property paths in multi-operation updates using the
        # dataset namespace manager as well as the explicit SPARQL prologue.
        for prefix, namespace in Context(name=self.con.context_name).items():
            self.con.dataset.bind(str(prefix), str(namespace))
        with patch('oldaplib.src.propertyclass.CacheSingletonRedis'):
            ordinary = PropertyClass(con=self.con, project=self.project,
                property_class_iri='example:dateTime', appliesToProperty='example:event',
                datatype=XsdDatatypes.dateTime, subPropertyOf='dcterms:date')
            ordinary.create()
            self.shape.create()
            self.assertEqual(parent_names(self.shape['example:dateTime'].subPropertyOf), {'dcterms:date'})
            ordinary.subPropertyOf = Iri('dcterms:created')
            ordinary.update()
            loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
            self.assertEqual(parent_names(loaded['example:dateTime'].subPropertyOf), {'dcterms:created'})
            ordinary.delete()
            loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
            self.assertEqual(parent_names(loaded['example:dateTime'].subPropertyOf), {'dcterms:created'})

    def test_normal_property_creation_cannot_add_a_conflicting_parent(self):
        self.shape['example:dateTime'].subPropertyOf = Iri('dcterms:date')
        self.shape.create()
        ordinary = PropertyClass(con=self.con, project=self.project,
            property_class_iri='example:dateTime', appliesToProperty='example:event',
            datatype=XsdDatatypes.dateTime, subPropertyOf='dcterms:created')
        with self.assertRaises(OldapErrorInconsistency):
            ordinary.create()
        self.assertFalse(self.con.in_transaction())
        loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        self.assertEqual(parent_names(loaded['example:dateTime'].subPropertyOf), {'dcterms:date'})

    def test_aggregate_rejects_conflicting_parents_before_writing(self):
        self.shape['example:dateTime'].subPropertyOf = Iri('dcterms:date')
        other = ReifierShape(con=self.con, project=self.project, shape_iri='example:Other',
            properties=[self.field])
        other['example:dateTime'].subPropertyOf = Iri('dcterms:created')
        model = DataModel(con=self.con, project=self.project, reifier_shapes=[self.shape, other])
        with self.assertRaises(OldapErrorValue):
            model.create()
        self.assertEqual(len(self.con.dataset), 0)

    def test_shared_parent_evicts_dependent_models_after_outer_commit(self):
        from oldaplib.src.resource_transaction import resource_transaction
        self.shape.create()
        self.con.dataset.update(Context(name=self.con.context_name).sparql_context + '''INSERT DATA {
            GRAPH shared:shacl { shared:ParentShape sh:targetClass shared:Parent ;
                sh:property [ sh:path example:event ; sh:reifierShape example:VisitShape ] }
            GRAPH oldap:shacl { oldap:ChildShape sh:targetClass oldap:Child ; sh:node shared:ParentShape }
        }''')
        self.shape['example:dateTime'].subPropertyOf = Iri('dcterms:date')
        with patch('oldaplib.src.cachesingleton.CacheSingletonRedis') as cache:
            with resource_transaction(self.con):
                self.shape.update()
                cache.return_value.delete.reset_mock()
            evicted = {str(call.args[0]) for call in cache.return_value.delete.call_args_list}
            self.assertTrue({'example:shacl', 'shared:shacl', 'oldap:shacl',
                'example:dateTime', 'shared:Parent', 'oldap:Child'} <= evicted)

    def test_resource_property_editor_and_annotation_share_parent(self):
        from pathlib import Path
        self.con.dataset.parse(Path(__file__).parents[1] / 'ontologies' / 'oldap.trig', format='trig')
        for prefix, namespace in Context(name=self.con.context_name).items():
            self.con.dataset.bind(str(prefix), str(namespace))
        system = Project(con=self.con, projectIri='http://oldap.org/base#SystemProject',
            projectShortName='oldap', namespaceIri=NamespaceIRI('http://oldap.org/base#'),
            projectStart=Xsd_date('2026-01-01'))
        with patch.object(ResourceClass, '_sysproject', system), patch.object(
                ResourceClass, '_sharedproject', self.project), patch(
                'oldaplib.src.datamodel.CacheSingletonRedis'), patch(
                'oldaplib.src.propertyclass.CacheSingletonRedis') as cache:
            cache.return_value.get.return_value = None
            prop = deepcopy(self.field, {id(self.con): self.con})
            prop.subPropertyOf = Iri('dcterms:date')
            resource = ResourceClass(con=self.con, project=self.project,
                owlclass_iri='example:Event', properties=[prop])
            resource.create()
            self.shape.create()
            model = DataModel(con=self.con, project=self.project, resclasses=[resource], reifier_shapes=[self.shape])
            resource.update_notifier(model.notifier, resource.owl_class_iri)
            resource[Xsd_QName('example:dateTime')].subPropertyOf = Iri('dcterms:created')
            model.update()
            shape = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
            self.assertEqual(parent_names(shape['example:dateTime'].subPropertyOf), {'dcterms:created'})
            shape['example:dateTime'].subPropertyOf = Iri('dcterms:date')
            shape.update()
            resource = ResourceClass.read(self.con, self.project, 'example:Event', ignore_cache=True)
            self.assertEqual(parent_names(resource[Xsd_QName('example:dateTime')].subPropertyOf), {'dcterms:date'})
            del resource[Xsd_QName('example:dateTime')]
            resource.update()
            self.assertEqual(parent_names(ReifierShape.read(self.con, self.project,
                shape.shape_iri)['example:dateTime'].subPropertyOf), {'dcterms:date'})

    def test_zero_constraints_survive_constructor_and_rdf_roundtrip(self):
        field = PropertyClass(con=self.con, project=self.project,
            property_class_iri='example:zero', datatype=XsdDatatypes.integer,
            minCount=0, maxCount=0, minInclusive=0, maxInclusive=0, order=0)
        shape = ReifierShape(con=self.con, project=self.project,
            shape_iri='example:ZeroShape', properties=[field])
        shape.create()
        actual = ReifierShape.read(self.con, self.project, shape.shape_iri)['example:zero']
        for name in ('minCount', 'maxCount', 'minInclusive', 'maxInclusive', 'order'):
            self.assertIsNotNone(getattr(actual, name), name)
            self.assertEqual(getattr(actual, name), 0, name)

    def test_owned_fields_and_copies_are_independent(self):
        self.shape['example:dateTime'].minCount = 0
        self.assertEqual(self.field.minCount, 1)
        other = deepcopy(self.shape)
        other['example:dateTime'].maxCount = 5
        self.assertEqual(self.shape['example:dateTime'].maxCount, 1)

    def test_stale_update_and_collision(self):
        self.shape.create()
        stale = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        with self.assertRaises(OldapErrorAlreadyExists):
            self.shape.create()
        self.shape['example:dateTime'].maxCount = 2
        self.shape.update()
        with self.assertRaises(OldapErrorUpdateFailed):
            stale.update()

    def test_references_and_existing_data_protect_structure(self):
        self.shape.create()
        self.con.dataset.update(Context(name=self.con.context_name).sparql_context + '''INSERT DATA {
            GRAPH example:shacl { example:TravelShape sh:property [
                sh:path example:isAt ; sh:reifierShape example:VisitShape ] }
            GRAPH example:data { example:trip example:isAt example:place }
        }''')
        with self.assertRaises(OldapErrorInUse):
            self.shape.delete()
        self.shape['example:dateTime'].maxCount = 2
        with self.assertRaises(OldapErrorInUse):
            self.shape.update()
        self.assertEqual(ReifierShape.read(self.con, self.project, self.shape.shape_iri)['example:dateTime'].maxCount, 1)
        loaded = ReifierShape.read(self.con, self.project, self.shape.shape_iri)
        loaded['example:dateTime'].name = ['Visit time@en']
        loaded.update()
        self.assertIsNotNone(ReifierShape.read(self.con, self.project, self.shape.shape_iri)['example:dateTime'].name)
        loaded['example:dateTime'].subPropertyOf = Iri('dcterms:date')
        loaded.update()
        self.assertEqual(parent_names(ReifierShape.read(self.con, self.project, loaded.shape_iri)['example:dateTime'].subPropertyOf), {'dcterms:date'})

    def test_invalid_ownership_duplicate_and_permissions(self):
        with self.assertRaises(OldapErrorValue):
            ReifierShape(con=self.con, project=self.project, shape_iri='shared:Other')
        with self.assertRaises(OldapErrorValue):
            ReifierShape(con=self.con, project=self.project, shape_iri='example:Other',
                properties=[self.field, self.field])
        self.con.userdata.inProject.clear()
        with self.assertRaises(OldapErrorNoPermission):
            self.shape.create()

    def test_unsupported_definition_rejected(self):
        with self.assertRaises(OldapErrorValue):
            ReifierShape.from_definition(self.con, self.project, self.shape.shape_iri,
                {Xsd_QName('rdf:type'): Xsd_QName('sh:NodeShape'),
                 Xsd_QName('sh:targetClass'): Xsd_QName('example:Travel')})

    def test_datamodel_round_trip_and_false_reference_policy(self):
        """Shape definitions stay separate from classes and preserve explicit false."""
        prop = PropertyClass(con=self.con, project=self.project,
            property_class_iri='example:isAt', toClass='schema:Place',
            reifierShapes=['example:VisitShape'], reificationRequired=False)
        from pathlib import Path
        self.con.dataset.parse(Path(__file__).parents[1] / 'ontologies' / 'oldap.trig', format='trig')
        system_project = Project(con=self.con, projectIri='http://oldap.org/base#SystemProject',
            projectShortName='oldap', namespaceIri=NamespaceIRI('http://oldap.org/base#'),
            projectStart=Xsd_date('2026-01-01'))
        with patch.object(ResourceClass, '_sysproject', system_project), patch.object(
            ResourceClass, '_sharedproject', self.project), patch(
            'oldaplib.src.propertyclass.CacheSingletonRedis') as property_cache, patch(
            'oldaplib.src.datamodel.CacheSingletonRedis'), patch(
            'oldaplib.src.datamodel.OldapList.ensure_list_node_context'), patch(
            'oldaplib.src.datamodel.ExternalOntology.search', return_value=[]):
            property_cache.return_value.get.return_value = None
            resource = ResourceClass(con=self.con, project=self.project,
                owlclass_iri='example:TestTravel', properties=[prop])
            model = DataModel(con=self.con, project=self.project, resclasses=[resource],
                              reifier_shapes=[self.shape])
            model.create()
            # Generated list shapes belong to OldapList, not editable resource classes.
            self.con.dataset.update(Context(name=self.con.context_name).sparql_context + """INSERT DATA {
                GRAPH example:shacl {
                    example:TopicsNodeShape a sh:NodeShape, example:TopicsNode ;
                        sh:targetClass example:TopicsNode ; sh:node oldap:OldapListNodeShape ;
                        sh:property [ sh:path rdf:type ] ;
                        sh:property [ sh:path skos:inScheme ; sh:class oldap:OldapList ;
                            sh:hasValue example:Topics ] .
                }
                GRAPH example:onto {
                    example:TopicsNode a owl:Class ; rdfs:subClassOf oldap:OldapListNode .
                }
            }""")
            loaded = DataModel.read(self.con, self.project, ignore_cache=True)
            self.assertNotIn(Xsd_QName('example:TopicsNode'), loaded.get_resclasses())
            self.assertEqual(loaded.get_reifier_shapes(), [self.shape.shape_iri])
            actual = loaded[Xsd_QName('example:TestTravel')].properties[Xsd_QName('example:isAt')]
            self.assertEqual({str(x) for x in actual.reifierShapes}, {'example:VisitShape'})
            self.assertIsNotNone(actual.reificationRequired)
            self.assertFalse(bool(actual.reificationRequired))
            exported = Dataset().parse(data=loaded.write_as_str(), format='trig')
            self.assertTrue(exported.query('''ASK { GRAPH <https://example.org/ns/shacl> {
                <https://example.org/ns/VisitShape> a <http://oldap.org/base#ReifierShape> }}''').askAnswer)

    def test_serializer_preserves_field_ownership_and_rejects_direct_update(self):
        data = json.dumps(self.shape, default=serializer.encoder_default)
        with patch.object(Project, 'read', return_value=self.project), patch.object(
            Project, '_read_identity', return_value=(self.project.projectShortName,
            self.project.projectIri, self.project.namespaceIri)):
            decoded = json.loads(data, object_hook=serializer.make_decoder_hook(connection=self.con))
        self.assertEqual(decoded.shape_iri, self.shape.shape_iri)
        self.assertEqual(decoded['example:dateTime']._ownerShape, self.shape.shape_iri)
        with self.assertRaisesRegex(OldapErrorValue, 'owning ReifierShape'):
            decoded['example:dateTime'].update()

    def test_referenced_unmarked_shape_can_be_adopted_without_audit_metadata(self):
        self.con.dataset.update(Context(name=self.con.context_name).sparql_context + '''INSERT DATA {
            GRAPH example:shacl {
                example:ImportedShape a sh:NodeShape ; sh:property [ sh:path example:note ; sh:datatype xsd:string ] .
                example:TravelShape sh:property [ sh:path example:isAt ; sh:reifierShape example:ImportedShape ] .
            }}''')
        imported = ReifierShape.read(self.con, self.project, 'example:ImportedShape')
        self.assertIsNone(imported.modified)
        imported['example:note'].maxCount = 1
        imported.update()
        self.assertIsNotNone(ReifierShape.read(self.con, self.project, imported.shape_iri).modified)

    def test_reusing_predicate_definition_does_not_transfer_class_ownership(self):
        with patch.object(ResourceClass, '_sysproject', self.project), patch.object(
            ResourceClass, '_sharedproject', self.project):
            one = ResourceClass(con=self.con, project=self.project, owlclass_iri='oldap:One', properties=[self.field])
            two = ResourceClass(con=self.con, project=self.project, owlclass_iri='oldap:Two', properties=[self.field])
        one.properties[self.field.property_class_iri].maxCount = 5
        self.assertEqual(two.properties[self.field.property_class_iri].maxCount, 1)
        self.assertIsNone(self.field.inResourceClass)

    def test_empty_and_invalid_shape_fields(self):
        empty = ReifierShape(con=self.con, project=self.project, shape_iri='example:Empty')
        empty.create()
        self.assertFalse(ReifierShape.read(self.con, self.project, empty.shape_iri).properties)
        self.field.minCount = -1
        with self.assertRaises(OldapErrorValue):
            self.shape[self.field.property_class_iri] = self.field

    def test_reference_set_updates_are_scoped_and_preserve_false(self):
        prefix = Context(name=self.con.context_name).sparql_context
        self.con.dataset.update(prefix + '''INSERT DATA { GRAPH example:shacl {
            example:OneShape sh:property [ sh:path example:isAt ;
                sh:reifierShape example:First ; sh:reificationRequired true ] .
            example:TwoShape sh:property [ sh:path example:isAt ; sh:reifierShape example:Other ] .
        }}''')
        prop = PropertyClass(con=self.con, project=self.project, property_class_iri='example:isAt',
            toClass='schema:Place', reifierShapes=['example:First'], reificationRequired=True,
            _inResourceClass=Xsd_QName('example:One'))
        prop.reifierShapes.add(Iri('example:Second'))
        prop.reificationRequired = False
        self.con.dataset.update(prefix + prop.update_shacl(owlclass_iri=Xsd_QName('example:One'), timestamp=Xsd_dateTime.now()))
        self.assertTrue(self.con.query(prefix + '''ASK { GRAPH example:shacl {
            example:OneShape sh:property [ sh:reifierShape example:First, example:Second ; sh:reificationRequired false ] .
            example:TwoShape sh:property [ sh:reifierShape example:Other ] . }}''')['boolean'])
        prop.clear_changeset()
        prop.reifierShapes = []
        prop.reificationRequired = None
        self.con.dataset.update(prefix + prop.update_shacl(owlclass_iri=Xsd_QName('example:One'), timestamp=Xsd_dateTime.now()))
        self.assertFalse(self.con.query(prefix + 'ASK { GRAPH example:shacl { example:OneShape sh:property [ sh:reifierShape ?shape ] }}')['boolean'])

    def test_shared_reference_is_resolved_without_copying_definition(self):
        shared = Project(con=self.con, projectIri='http://oldap.org/shared', projectShortName='shared',
            namespaceIri=NamespaceIRI('http://oldap.org/shared#'), projectStart=Xsd_date('2026-01-01'))
        shape = ReifierShape(con=self.con, project=shared, shape_iri='shared:VisitShape', properties=[self.field])
        shape.create()
        prop = PropertyClass(con=self.con, project=self.project, property_class_iri='example:isAt',
            toClass='schema:Place', reifierShapes=['shared:VisitShape'])
        with patch.object(Project, 'read', return_value=shared):
            validate_property_reifiers(prop, self.con, self.project)
        self.assertEqual(len(self.con.dataset.graph(URIRef('https://example.org/ns/shacl'))), 0)
        prop.reifierShapes = ['example:Missing']
        with self.assertRaises(OldapErrorNotFound):
            validate_property_reifiers(prop, self.con, self.project)

    def test_cache_eviction_follows_inheritance_across_graphs(self):
        self.con.dataset.update(Context(name=self.con.context_name).sparql_context + '''INSERT DATA {
            GRAPH shared:shacl { shared:ChildShape sh:node example:ParentShape ; sh:targetClass shared:Child }
            GRAPH example:shacl { example:GrandchildShape sh:node shared:ChildShape ; sh:targetClass example:Grandchild }
        }''')
        with patch('oldaplib.src.cachesingleton.CacheSingletonRedis') as cache:
            invalidate_model_owners(self.con, 'example', Xsd_QName('example:Parent'))
        deleted = {str(call.args[0]) for call in cache.return_value.delete.call_args_list}
        self.assertTrue({'example:Parent', 'shared:Child', 'example:Grandchild', 'example:shacl', 'shared:shacl'} <= deleted)

    def test_conflicting_owl_predicate_kind_is_rejected_before_update(self):
        self.shape.create()
        replacement = PropertyClass(con=self.con, project=self.project,
            property_class_iri='example:dateTime', toClass='schema:Place')
        self.shape['example:dateTime'] = replacement
        with self.assertRaises(OldapErrorInconsistency):
            self.shape.update()
        self.assertEqual(ReifierShape.read(self.con, self.project, self.shape.shape_iri)['example:dateTime'].datatype,
                         XsdDatatypes.dateTime)
