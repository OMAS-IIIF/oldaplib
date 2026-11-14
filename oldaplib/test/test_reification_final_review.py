"""Regression checks found by the complete pre-merge reification audit."""
from contextlib import ExitStack
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from rdflib import URIRef, Namespace, Graph
from rdflib.compare import isomorphic

from oldaplib.test.test_assertion_annotation import native, visits
from oldaplib.test.test_reifier_shape import DatasetConnection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorInUse, OldapErrorInconsistency
from oldaplib.src.helpers.property_validation import validate_value
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.reifier_shape import ReifierShape
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.resource_transaction import resource_transaction
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName as Q
from oldaplib.src.xsd.xsd_integer import Xsd_integer


@pytest.fixture
def model_env():
    con = DatasetConnection()
    project = Project(con=con, projectIri='https://example.org/project', projectShortName='example',
                      namespaceIri=NamespaceIRI('https://example.org/ns/'), projectStart='2026-01-01')
    with patch('oldaplib.src.cachesingleton.CacheSingletonRedis') as cache, patch(
            'oldaplib.src.resource_transaction.archive_coordination_enabled', return_value=False):
        yield SimpleNamespace(con=con, project=project, cache=cache.return_value)


def field(env, **kwargs):
    return PropertyClass(con=env.con, project=env.project, property_class_iri='example:field',
                         datatype=XsdDatatypes.integer, **kwargs)


def test_cached_datamodel_read_has_no_reification_probe(model_env):
    env = model_env
    snapshot = DataModel(con=env.con, project=env.project)
    env.con.query = Mock(side_effect=AssertionError('Cache hit must not query RDF'))
    with patch('oldaplib.src.datamodel.CacheSingletonRedis', return_value=env.cache), patch(
            'oldaplib.src.datamodel.OldapList.ensure_list_node_context'):
        env.cache.get.return_value = snapshot
        assert DataModel.read(env.con, env.project) is snapshot
        env.con.query.assert_not_called()


@pytest.mark.parametrize('abort', [False, True])
def test_shape_cache_eviction_follows_outer_transaction(model_env, abort):
    env = model_env
    shape = ReifierShape(con=env.con, project=env.project, shape_iri='example:Shape', properties=[field(env)])
    try:
        with resource_transaction(env.con):
            shape.create()
            assert env.cache.delete.call_count == 1
            # Simulate a concurrent reader repopulating the old snapshot.
            if abort:
                raise RuntimeError('rollback')
    except RuntimeError:
        pass
    assert env.cache.delete.call_count == 2
    assert all(call.args == (Q('example:shacl'),) for call in env.cache.delete.call_args_list)


def test_shared_shape_blank_nodes_are_not_deleted(model_env):
    env = model_env
    shape = ReifierShape(con=env.con, project=env.project, shape_iri='example:Shape', properties=[field(env)])
    shape.create()
    ns = Namespace('https://example.org/ns/')
    sh = Namespace('http://www.w3.org/ns/shacl#')
    graph = env.con.dataset.graph(ns.shacl)
    node = next(graph.objects(ns.Shape, sh.property))
    graph.add((ns.OtherShape, sh.property, node))
    before = Graph()
    for triple in graph:
        before.add(triple)
    shape['example:field'].name = ['New@en']
    with pytest.raises(OldapErrorInUse, match='blank nodes'):
        shape.update()
    assert isomorphic(env.con.dataset.graph(ns.shacl), before)


def test_property_copy_retains_changes_and_owns_nested_notifications(model_env):
    prop = field(model_env, name=['Before@en'])
    prop.minCount = 1
    clone = deepcopy(prop, {id(model_env.con): model_env.con})
    assert PropClassAttr.MIN_COUNT in clone.changeset
    prop.clear_changeset()
    clone.clear_changeset()
    clone.name['en'] = 'After'
    assert clone.changeset and not prop.changeset
    assert str(prop.name['en']) == 'Before'


def test_resource_assignment_does_not_rebind_callers_notifier(model_env):
    env = model_env
    prop = field(env)
    notify = Mock()
    prop.set_notifier(notify, Q('example:original'))
    with patch.object(ResourceClass, '_sysproject', env.project), patch.object(ResourceClass, '_sharedproject', env.project):
        resource = ResourceClass(con=env.con, project=env.project, owlclass_iri='oldap:Review')
        resource[Q('example:field')] = prop
    prop.minCount = 1
    notify.assert_called_once_with(Q('example:original'))
    assert resource[Q('example:field')].minCount is None


def test_less_than_or_equals_uses_its_own_target_and_absence(model_env):
    prop = field(model_env, lessThanOrEquals='example:upper')
    validate_value(Xsd_integer(3), prop, {Q('example:upper'): {Xsd_integer(3)}})
    with pytest.raises(OldapErrorInconsistency):
        validate_value(Xsd_integer(4), prop, {Q('example:upper'): {Xsd_integer(3)}})
    validate_value(Xsd_integer(4), prop, {})
    prop.lessThanOrEquals = None
    prop.lessThan = 'example:upper'
    validate_value(Xsd_integer(4), prop, {})


def test_protected_fields_rejected_at_model_boundary(model_env):
    env = model_env
    prop = PropertyClass(con=env.con, project=env.project, property_class_iri='oldap:hasDataPermission',
                         toClass='oldap:DataPermission')
    with pytest.raises(OldapErrorValue, match='System/permission'):
        ReifierShape(con=env.con, project=env.project, shape_iri='example:Bad', properties=[prop])


def test_foreign_graph_cannot_inject_annotation_policy(native):
    visits(native)
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context + '''INSERT DATA {
          GRAPH <urn:unrelated:shacl> { travel:TripShape sh:property [sh:path travel:label;
            sh:reifierShape <urn:invalid:shape>; sh:reificationRequired true] }
        }''')
    trip = native.factory.read('travel:T')
    trip.update()
    assert len(trip.annotations()) == 2


def test_whole_model_insertion_protects_used_policy(native):
    visits(native)
    resource = ResourceClass(con=native.con, project=native.project, owlclass_iri='travel:Another', properties=[
        PropertyClass(con=native.con, project=native.project, property_class_iri='travel:isAt',
                      toClass='travel:Location', reifierShapes=['travel:VisitShape'])])
    shape = ReifierShape.read(native.con, native.project, 'travel:VisitShape')
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context +
            'CLEAR GRAPH travel:shacl; CLEAR GRAPH travel:onto')
    with pytest.raises(OldapErrorValue, match='asserted values'):
        DataModel(con=native.con, project=native.project, resclasses=[resource], reifier_shapes=[shape]).create()


def test_legacy_plain_write_uses_legacy_quoted_triple_dialect(native):
    from oldaplib.src.assertion_annotation import prepare_write
    Place = native.factory.createObjectInstance('travel:Location')
    native.con._resource_permissions_rdf12 = False
    place = native.factory.read('travel:A')
    native.con.queries.clear()
    with resource_transaction(native.con):
        prepare_write(place, 'update')
    assert place._annotation_write is None
    assert all('<<(' not in query for query in native.con.queries)


def test_annotation_scalar_creation_error_is_client_error(native):
    from flask import Flask
    from oldap_api.views.instance_views import instance_bp
    shape = ReifierShape.read(native.con, native.project, 'travel:VisitShape')
    shape['travel:note'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:note', datatype=XsdDatatypes.string, minLength=3)
    shape.update()
    app=Flask(__name__)
    app.register_blueprint(instance_bp)
    with patch('oldap_api.authentication.Connection',return_value=native.con):
        response=app.test_client().put('/data/travel/travel:Trip',headers={'Authorization':'Bearer native-test'},json={
            'iri':'BadField','travel:isAt':['travel:A'],'@annotations':[{'op':'add','property':'travel:isAt','value':'travel:A',
            'fields':{'travel:dateTime':['2026-01-01T00:00:00Z'],'travel:note':['x']}}]})
    assert response.status_code == 409, response.json


def test_annotation_fetch_rechecks_parent_visibility(native):
    from oldaplib.src.assertion_annotation import read_annotations
    visits(native)
    previous = native.factory.read('travel:T')
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context +
            'DELETE WHERE { GRAPH travel:data { travel:T oldap:attachedToRole ?role } }')
    assert read_annotations(previous) == ()


def test_scalar_comparison_resolves_absolute_sibling_iri(model_env):
    prop = field(model_env, lessThanOrEquals='https://example.org/ns/upper')
    with pytest.raises(OldapErrorInconsistency):
        validate_value(Xsd_integer(4), prop, {Q('example:upper'): {Xsd_integer(3)}})


def test_cached_model_json_round_trip_preserves_reifier_definitions(native):
    """Use the real cache serializer and reconstruct an independent factory."""
    import json
    from oldaplib.src.helpers.serializer import serializer
    from oldaplib.src.objectfactory import ResourceInstanceFactory
    snapshots = {}
    for project in (native.project, 'shared'):
        model = DataModel.read(native.con, project, ignore_cache=True)
        snapshots[str(model._project.projectShortName) + ':shacl'] = json.dumps(model, default=serializer.encoder_default)
    cache = Mock()
    cache.get.side_effect = lambda key, connection=None: json.loads(
        snapshots[str(key)], object_hook=serializer.make_decoder_hook(connection=connection)) if str(key) in snapshots else None
    cache.set.side_effect = lambda key, value: snapshots.__setitem__(str(key), json.dumps(value, default=serializer.encoder_default))
    with ExitStack() as stack:
        for module in ('datamodel', 'resourceclass', 'propertyclass'):
            stack.enter_context(patch(f'oldaplib.src.{module}.CacheSingletonRedis', return_value=cache))
        ResourceInstanceFactory(native.con, native.project)
        native.con.queries.clear()
        factory = ResourceInstanceFactory(native.con, native.project)
        assert factory._datamodel.reifier_shapes
        assert not native.con.queries


def test_cached_factory_performance_against_baseline(native):
    """Opt-in timing includes model reconstruction; Redis transport is excluded."""
    import hashlib
    import json
    import os
    import random
    import statistics
    import subprocess
    import time
    from pathlib import Path
    from types import ModuleType
    from oldaplib.src.helpers.serializer import serializer
    from oldaplib.src.objectfactory import ResourceInstanceFactory
    import oldaplib.src.objectfactory as current_factory
    receipt = os.environ.get('OLDAP_FACTORY_BENCHMARK')
    if not receipt:
        pytest.skip('Explicit cached-factory timing acceptance')
    baseline_source = subprocess.check_output(['git', 'show', 'HEAD:oldaplib/src/datamodel.py'])
    baseline = ModuleType('final_review_baseline_datamodel')
    # Preserve the live serializer registry when loading the historical class.
    with patch('oldaplib.src.helpers.serializer.serializer', new=lambda cls: cls):
        exec(compile(baseline_source, '<baseline datamodel>', 'exec'), baseline.__dict__)
    snapshots = {}
    for project in (native.project, 'shared'):
        model = DataModel.read(native.con, project, ignore_cache=True)
        snapshots[str(model._project.projectShortName) + ':shacl'] = json.dumps(model, default=serializer.encoder_default)
    cache = Mock()
    cache.get.side_effect = lambda key, connection=None: json.loads(
        snapshots[str(key)], object_hook=serializer.make_decoder_hook(connection=connection)) if str(key) in snapshots else None
    cache.set.side_effect = lambda key, value: snapshots.__setitem__(str(key), json.dumps(value, default=serializer.encoder_default))
    def construct(model_class):
        with patch.object(current_factory, 'DataModel', model_class):
            return ResourceInstanceFactory(native.con, native.project)
    with ExitStack() as stack:
        for module in ('datamodel', 'resourceclass', 'propertyclass'):
            stack.enter_context(patch(f'oldaplib.src.{module}.CacheSingletonRedis', return_value=cache))
        stack.enter_context(patch.object(baseline, 'CacheSingletonRedis', return_value=cache))
        construct(DataModel)
        native.con.queries.clear()
        for cls in (baseline.DataModel, DataModel):
            for _ in range(30):
                construct(cls)
        samples = [[], []]
        for repeat in range(30):
            for index in ((0, 1) if repeat % 2 == 0 else (1, 0)):
                start = time.perf_counter_ns()
                for _ in range(10):
                    construct((baseline.DataModel, DataModel)[index])
                samples[index].append((time.perf_counter_ns() - start) / 1e7)
        assert not native.con.queries
    differences = [new - old for old, new in zip(*samples)]
    rng = random.Random(34)
    bootstrap = sorted(statistics.mean(rng.choices(differences, k=30)) for _ in range(2000))
    interval = [bootstrap[50], bootstrap[1949]]
    Path(receipt).write_text(json.dumps({
        'scope': 'Fresh factory, cached annotated model JSON reconstruction; same current factory and serializers; baseline DataModel.read from HEAD; Redis transport excluded',
        'baselineCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'baselineDataModelSha256': hashlib.sha256(baseline_source).hexdigest(),
        'currentDataModelSha256': hashlib.sha256(Path('oldaplib/src/datamodel.py').read_bytes()).hexdigest(),
        'queriesPerFactory': 0, 'samplesPerVersion': 300,
        'baselineMedianMs': statistics.median(samples[0]), 'currentMedianMs': statistics.median(samples[1]),
        'pairedDelta95PercentIntervalMs': interval}, indent=2) + '\n')
    assert interval[0] <= 0, f'Measurable factory regression: {interval}'
