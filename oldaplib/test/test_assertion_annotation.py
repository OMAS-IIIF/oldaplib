"""Native RDF 1.2 lifecycle acceptance on disposable Jena storage.

Set OLDAP_TEST_FUSEKI_JAR; this module never connects to a running service.
Library CRUD, actual permission queries and history execute unmocked SPARQL.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rdflib import URIRef

from tools.reification.probe_model import NativeConnection, ROOT
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorInUse, OldapErrorNotFound, OldapErrorNoPermission, OldapErrorUpdateFailed
from oldaplib.src.jena_connection import JenaConnection
from oldaplib.src.objectfactory import ResourceInstanceFactory, ResourceInstance
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.reifier_shape import ReifierShape
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.resource_history import ResourceHistory
from oldaplib.src.resource_transaction import resource_transaction
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName as Q
from oldaplib.src.xsd.xsd_date import Xsd_date


class AnnotationConnection(NativeConnection):
    _resource_permissions_rdf12 = True
    _resource_search_rdf12 = True
    _resource_read_query = JenaConnection._resource_read_query
    def __init__(self, process):
        super().__init__(process)
        self.queries = []
    def query(self, query, format=None):
        self.queries.append(query)
        return super().query(query, format)


@pytest.fixture
def native(tmp_path):
    jar = os.environ.get('OLDAP_TEST_FUSEKI_JAR')
    if not jar:
        pytest.skip('Set OLDAP_TEST_FUSEKI_JAR for native annotation lifecycle acceptance.')
    assert hashlib.sha256(Path(jar).read_bytes()).hexdigest() == '2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee'
    java = Path('/opt/homebrew/opt/openjdk@25/bin')
    subprocess.run([str(java/'javac'), '-cp', jar, '-d', str(tmp_path), str(ROOT/'tools/reification/JenaModelProbe.java')], check=True)
    process = subprocess.Popen([str(java/'java'), '-cp', str(tmp_path)+':'+jar, 'JenaModelProbe', str(tmp_path/'tdb')],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    con = AnnotationConnection(process)
    try:
        projects = {name: Project(con=con, projectIri=f'https://annotation.test/projects/{name}', projectShortName=name,
            namespaceIri=NamespaceIRI(ns), projectStart=Xsd_date('2026-01-01')) for name, ns in (
            ('travel','https://annotation.test/'), ('oldap','http://oldap.org/base#'), ('shared','http://oldap.org/shared#'))}
        context = Context(name=con.context_name)
        for name, project in projects.items():
            context[name] = project.namespaceIri
        def project_read(con=None, projectIri_SName=None, **kwargs):
            if isinstance(projectIri_SName, Project):
                return projectIri_SName
            return projects['shared' if str(projectIri_SName) == 'oldap:SharedProject' else str(projectIri_SName)]
        cache = MagicMock()
        cache.get.return_value = None
        with ExitStack() as stack:
            stack.enter_context(patch.object(Project, 'read', side_effect=project_read))
            stack.enter_context(patch.object(ResourceClass, '_sysproject', projects['oldap']))
            stack.enter_context(patch.object(ResourceClass, '_sharedproject', projects['shared']))
            for module in ('datamodel','resourceclass','propertyclass','cachesingleton'):
                stack.enter_context(patch(f'oldaplib.src.{module}.CacheSingletonRedis', return_value=cache))
            stack.enter_context(patch('oldaplib.src.datamodel.OldapList.ensure_list_node_context'))
            stack.enter_context(patch('oldaplib.src.datamodel.ExternalOntology.search', return_value=[]))
            stack.enter_context(patch('oldaplib.src.resource_transaction.archive_coordination_enabled', return_value=False))
            con._userdata.hasRole = {Q('travel:Reader'): Iri('oldap:DATA_UPDATE')}
            con.transaction_start()
            con.send('load', path=str(ROOT/'oldaplib/ontologies/oldap.trig'))
            con.transaction_update(Context(name=con.context_name).sparql_context + f'''INSERT DATA {{ GRAPH oldap:admin {{
                {con.userIri.toRdf} oldap:hasRole travel:Reader .
                oldap:DATA_UPDATE oldap:permissionValue {DataPermission.DATA_UPDATE.numeric.toRdf} . }} }}''')
            con.transaction_commit()
            project = projects['travel']
            field = PropertyClass(con=con, project=project, property_class_iri='travel:dateTime',
                                  datatype=XsdDatatypes.dateTime, minCount=1, maxCount=1)
            shape = ReifierShape(con=con, project=project, shape_iri='travel:VisitShape', properties=[field])
            location = ResourceClass(con=con, project=project, owlclass_iri='travel:Location')
            trip = ResourceClass(con=con, project=project, owlclass_iri='travel:Trip', properties=[
                PropertyClass(con=con, project=project, property_class_iri='travel:isAt', toClass='travel:Location',
                              reifierShapes=['travel:VisitShape'], reificationRequired=True),
                PropertyClass(con=con, project=project, property_class_iri='travel:label', datatype=XsdDatatypes.string,
                              reifierShapes=['travel:VisitShape'], reificationRequired=False)])
            DataModel(con=con, project=project, resclasses=[location,trip], reifier_shapes=[shape]).create()
            DataModel(con=con, project=projects['shared']).create()
            factory = ResourceInstanceFactory(con, project)
            Place = factory.createObjectInstance('travel:Location')
            place = Place(iri=Iri('travel:A'))
            place.create()
            yield SimpleNamespace(con=con, project=project, factory=factory, Trip=factory.createObjectInstance('travel:Trip'),
                                  history=ResourceHistory(con, project), root=tmp_path)
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()


def visits(env):
    trip = env.Trip(iri=Iri('travel:T'), isAt=['travel:A'])
    first = trip.add_annotation('travel:isAt', 'travel:A', {'travel:dateTime': ['2026-01-01T10:00:00Z']})
    second = trip.add_annotation('travel:isAt', 'travel:A', {'travel:dateTime': ['2026-01-02T10:00:00Z']})
    trip.create()
    return first, second


def test_independent_visits_history_restore_and_cleanup(native):
    first, second = visits(native)
    trip = native.factory.read('travel:T')
    assert len(trip.annotations()) == 2
    trip.replace_annotation(first, {'travel:dateTime': ['2026-01-03T10:00:00Z']})
    trip.update()
    records = {str(record.iri): record for record in trip.annotations()}
    assert str(records[str(second)].fields[URIRef('https://annotation.test/dateTime')][0]).startswith('2026-01-02')
    entries = native.history.list('travel:T')
    assert len(entries) == 1 and len(entries[0].annotations) == 2
    native.history.restore('travel:T', entries[0].iri)
    restored = native.factory.read('travel:T')
    assert len(restored.annotations()) == 2
    restored.remove_annotation(str(restored.annotations()[0].iri))
    restored.update()
    assert len(restored.annotations()) == 1
    # Dropping the base triple cleans up its remaining owned annotation.
    restored[Q('travel:isAt')] = []
    restored.update()
    assert not restored.annotations()
    restored.delete()


def test_required_and_invalid_annotations_rollback(native):
    trip = native.Trip(iri=Iri('travel:Bad'), isAt=['travel:A'])
    with pytest.raises(OldapErrorValue, match='Required'):
        trip.create()
    trip.add_annotation('travel:isAt','travel:A',{})
    with pytest.raises(OldapErrorValue, match='cardinality'):
        trip.create()
    trip = native.Trip(iri=Iri('travel:Bad'), isAt=['travel:A'])
    trip.add_annotation('travel:isAt','travel:A',{'travel:dateTime':['not-a-timestamp']})
    with pytest.raises(OldapErrorValue):
        trip.create()
    assert not native.con.query(Context(name=native.con.context_name).sparql_context + 'ASK { GRAPH travel:data { travel:Bad ?p ?o }}')['boolean']


def test_literal_base_and_annotation_noop(native):
    trip = native.Trip(iri=Iri('travel:L'), label=['hello'])
    rid = trip.add_annotation('travel:label','hello',{'travel:dateTime':['2026-01-01T00:00:00Z']})
    trip.create()
    trip = native.factory.read('travel:L')
    before = str(trip.lastModificationDate)
    trip.replace_annotation(rid, {'travel:dateTime':['2026-01-01T00:00:00Z']})
    trip.update()
    assert str(native.factory.read('travel:L').lastModificationDate) == before
    assert not native.history.list('travel:L')


def test_last_required_deletion_stale_writer_and_callback_rollback(native):
    first, second = visits(native)
    stale = native.factory.read('travel:T')
    trip = native.factory.read('travel:T')
    trip.remove_annotation(first)
    trip.update()
    stale.remove_annotation(second)
    with pytest.raises(OldapErrorUpdateFailed):
        stale.update()
    trip.remove_annotation(second)
    with pytest.raises(OldapErrorValue, match='Required'):
        trip.update()
    trip = native.factory.read('travel:T')
    trip.replace_annotation(second, {'travel:dateTime':['2026-01-04T00:00:00Z']})
    def reject(con):
        raise RuntimeError('reject')
    with pytest.raises(RuntimeError, match='reject'):
        trip.update(before_commit=reject)
    assert str(native.factory.read('travel:T').annotations()[0].fields[URIRef('https://annotation.test/dateTime')][0]).startswith('2026-01-02')


def test_plain_reads_and_search_do_not_expand_annotations(native):
    visits(native)
    native.con.queries.clear()
    native.factory.read('travel:T')
    queries = list(native.con.queries)
    assert len(queries) == 1
    assert '?reifier ?predicate ?value ?field' not in queries[0]
    native.con.queries.clear()
    ResourceInstance.search(native.con, native.project, resClass='travel:Trip')
    assert all('?reifier ?predicate ?value ?field' not in query for query in native.con.queries)


def test_permissions_cross_instance_ids_and_external_references(native):
    first, _ = visits(native)
    other = native.Trip(iri=Iri('travel:Other'))
    other.create()
    other = native.factory.read('travel:Other')
    other.remove_annotation(first)
    with pytest.raises(OldapErrorNotFound):
        other.update()
    context = Context(name=native.con.context_name)
    trip = native.factory.read('travel:T')
    with resource_transaction(native.con):
        native.con.transaction_update(context.sparql_context + f'INSERT DATA {{ GRAPH travel:data {{ travel:External travel:ref {first.toRdf} }} }}')
    trip.replace_annotation(first, {'travel:dateTime':['2026-01-05T00:00:00Z']})
    with pytest.raises(OldapErrorInUse):
        trip.update()
    with resource_transaction(native.con):
        native.con.transaction_update(context.sparql_context + f'DELETE DATA {{ GRAPH travel:data {{ travel:External travel:ref {first.toRdf} }} }}')
    native.con._userdata.inProject = {}
    native.con._userdata.userIri = Iri('urn:test:intruder')
    with pytest.raises(OldapErrorNoPermission):
        trip.update()
    with pytest.raises(OldapErrorNotFound):
        trip.annotations()


def test_blank_or_external_reifiers_are_visible_but_read_only(native):
    visits(native)
    context = Context(name=native.con.context_name)
    with resource_transaction(native.con):
        native.con.transaction_update(context.sparql_context + '''INSERT DATA { GRAPH travel:data {
            _:external rdf:reifies <<( travel:T travel:isAt travel:A )>> ; travel:dateTime "2026-01-01T00:00:00Z"^^xsd:dateTime . }}''')
    trip = native.factory.read('travel:T')
    records = trip.annotations()
    assert len(records) == 3 and any(not record.managed for record in records)
    with pytest.raises(OldapErrorValue, match='read-only'):
        trip.delete()


def test_multiple_fields_and_link_validation(native):
    shape = ReifierShape.read(native.con, native.project, 'travel:VisitShape')
    shape['travel:observer'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:observer', toClass='travel:Location', maxCount=1)
    shape['travel:note'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:note', datatype=XsdDatatypes.string, minLength=2, maxLength=5)
    shape.update()
    trip = native.Trip(iri=Iri('travel:Multi'), isAt=['travel:A'])
    rid = trip.add_annotation('travel:isAt','travel:A', {'travel:dateTime':['2026-01-01T00:00:00Z'],
                            'travel:observer':['travel:A'], 'travel:note':['good']})
    trip.create()
    assert len(trip.annotations()[0].fields) == 3
    trip = native.factory.read('travel:Multi')
    trip.replace_annotation(rid, {'travel:dateTime':['2026-01-01T00:00:00Z'], 'travel:note':['x']})
    with pytest.raises(Exception, match='length'):
        trip.update()


def test_api_create_read_update_history_and_delete(native):
    pytest.importorskip('oldap_api')
    from flask import Flask
    from oldap_api.views.instance_views import instance_bp
    app = Flask(__name__)
    app.register_blueprint(instance_bp)
    headers = {'Authorization':'Bearer native-test'}
    with patch('oldap_api.authentication.Connection', return_value=native.con):
        client = app.test_client()
        result = client.put('/data/travel/travel:Trip', json={'iri':'ApiTrip', 'travel:isAt':['travel:A'],
            '@annotations':[{'op':'add', 'property':'travel:isAt', 'value':{'type':'uri','value':'travel:A'},
                'fields':{'travel:dateTime':[{'type':'literal','datatype':'xsd:dateTime','value':'2026-01-01T00:00:00Z'}]}}]}, headers=headers)
        assert result.status_code == 200, result.json
        rid = result.json['annotationIris'][0]
        read = client.get('/data/annotations/travel/travel:ApiTrip', headers=headers)
        assert read.status_code == 200 and len(read.json['items']) == 1, read.json
        plain = client.get('/data/travel/travel:ApiTrip', headers=headers)
        assert plain.status_code == 200 and '@annotations' not in plain.json
        result = client.post('/data/travel/travel:ApiTrip', json={'@annotations':[
            {'op':'replace','iri':rid,'fields':{'travel:dateTime':['2026-01-02T00:00:00Z']}}]}, headers=headers)
        assert result.status_code == 200, result.json
        history = client.get('/data/history/travel/travel:ApiTrip', headers=headers)
        assert history.status_code == 200 and history.json['items'][0]['annotations'], history.json
        result = client.post('/data/history/travel/travel:ApiTrip/restore', json={
            'historyIri':history.json['items'][0]['iri']}, headers=headers)
        assert result.status_code == 200, result.json
        result = client.delete('/data/travel/travel:ApiTrip', headers=headers)
        assert result.status_code == 200, result.json


@pytest.mark.skipif(not os.environ.get('OLDAP_ANNOTATION_BENCHMARK'), reason='Explicit repeated native performance acceptance')
def test_ordinary_read_search_performance_against_pre_stage3(native):
    """Compare exact query text/counts and interleaved timings with git HEAD."""
    import importlib.util
    import random
    import statistics
    import sys
    import time
    baseline_path = os.environ.get('OLDAP_ANNOTATION_BASELINE_SOURCE')
    baseline_source = (Path(baseline_path).read_bytes() if baseline_path else
                       subprocess.check_output(['git','show','HEAD:oldaplib/src/objectfactory.py'], cwd=ROOT))
    path = native.root / 'baseline_objectfactory.py'
    path.write_bytes(baseline_source)
    spec = importlib.util.spec_from_file_location('oldap_stage3_baseline', path)
    baseline = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = baseline
    spec.loader.exec_module(baseline)
    first, second = visits(native)
    # Populate a page-sized workload with extra annotation rows. Ordinary
    # searches must retain the same result cardinality and query execution.
    context = Context(name=native.con.context_name)
    triples = []
    for index in range(100):
        subject = f'travel:bench{index}'
        triples.append(f'''{subject} a travel:Trip ; travel:label "trip{index}" ;
            oldap:createdBy {native.con.userIri.toRdf} ; oldap:lastModifiedBy {native.con.userIri.toRdf} ;
            oldap:creationDate "2026-01-01T00:00:00Z"^^xsd:dateTimeStamp ;
            oldap:lastModificationDate "2026-01-01T00:00:00Z"^^xsd:dateTimeStamp ; oldap:attachedToRole travel:Reader .
            <urn:benchmark:grant{index}> rdf:reifies <<( {subject} oldap:attachedToRole travel:Reader )>> ; oldap:hasDataPermission oldap:DATA_UPDATE .''')
        for visit in range(5):
            triples.append(f'''<urn:benchmark:annotation{index}-{visit}> a oldap:AssertionAnnotation ;
                rdf:reifies <<( {subject} travel:label "trip{index}" )>> ; travel:dateTime "2026-01-01T00:00:00Z"^^xsd:dateTime .''')
    with resource_transaction(native.con):
        native.con.transaction_update(context.sparql_context + 'INSERT DATA { GRAPH travel:data { '+'\n'.join(triples)+' } }')
    old_factory = baseline.ResourceInstanceFactory(native.con, native.project)
    calls = {
        'read': (lambda: old_factory.read('travel:T').toJsonObject(), lambda: native.factory.read('travel:T').toJsonObject()),
        'read_data': (lambda: old_factory.read_data('travel:T').data, lambda: native.factory.read_data('travel:T').data),
        'search_page': (lambda: baseline.ResourceInstance.search(native.con, native.project, resClass='travel:Trip',
                              includeProperties={Q('travel:label')}, limit=25),
                        lambda: ResourceInstance.search(native.con, native.project, resClass='travel:Trip',
                              includeProperties={Q('travel:label')}, limit=25)),
    }
    report = {'baselineCommit':None if baseline_path else subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'baselineSource':baseline_path or 'HEAD:oldaplib/src/objectfactory.py',
              'baselineSourceSha256':hashlib.sha256(baseline_source).hexdigest(),
              'currentSourceSha256':hashlib.sha256((ROOT/'oldaplib/src/objectfactory.py').read_bytes()).hexdigest(),
              'supportingSourceSha256':{str(path):hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in (
                  'oldaplib/src/helpers/property_validation.py', 'oldaplib/src/assertion_annotation.py',
                  'oldaplib/src/annotation_search.py',
                  'tools/reification/JenaModelProbe.java')},
              'scope':'Same isolated Jena dataset; 100 extra resources with 500 annotations; warm interleaved runs', 'measurements':{}}
    regressions = []
    for name, (old, new) in calls.items():
        native.con.queries.clear()
        expected = old()
        old_queries = list(native.con.queries)
        native.con.queries.clear()
        assert new() == expected
        assert native.con.queries == old_queries
        for _ in range(30):
            old(); new()
        samples = [[], []]
        for repeat in range(30):
            for which in ((0,1) if repeat % 2 == 0 else (1,0)):
                started = time.perf_counter_ns()
                for _ in range(10):
                    (old, new)[which]()
                samples[which].append((time.perf_counter_ns()-started)/10/1e6)
        differences = [after-before for before,after in zip(*samples)]
        randomizer = random.Random(34)
        bootstrap = sorted(statistics.mean(randomizer.choices(differences,k=len(differences))) for _ in range(2000))
        interval = [bootstrap[50],bootstrap[1949]]
        report['measurements'][name] = {'queriesPerCall':len(old_queries), 'queryTextIdentical':True,
            'baselineMedianMs':statistics.median(samples[0]), 'currentMedianMs':statistics.median(samples[1]),
            'pairedMeanDeltaMs':statistics.mean(differences), 'pairedDelta95PercentIntervalMs':interval,
            'samplesPerVersion':300}
        if interval[0] > 0:
            regressions.append(name)
    Path(os.environ['OLDAP_ANNOTATION_BENCHMARK']).write_text(json.dumps(report,indent=2)+'\n')
    assert not regressions, f'Measurable regression: {regressions}; inspect performance receipt.'


def test_native_data_and_history_transfer_preserve_reifier_identity(native):
    first, _ = visits(native)
    trip = native.factory.read('travel:T')
    trip.replace_annotation(first, {'travel:dateTime':['2026-01-07T00:00:00Z']})
    trip.update()
    before = [record.to_json() for record in trip.annotations()]
    history_before = native.history.list('travel:T')
    files = []
    for graph in ('data','history'):
        path = native.root / f'{graph}.trig'
        native.con.send('export', path=str(path), graph=f'https://annotation.test/{graph}')
        files.append(path)
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context + 'CLEAR GRAPH travel:data; CLEAR GRAPH travel:history')
        for path in files:
            native.con.send('load', path=str(path))
    assert [record.to_json() for record in native.factory.read('travel:T').annotations()] == before
    assert native.history.list('travel:T') == history_before


def test_annotated_transform_is_explicitly_rejected(native):
    visits(native)
    trip = native.factory.read('travel:T')
    with pytest.raises(OldapErrorValue, match='annotated'):
        trip.transform_class('travel:Location', preserve_class='oldap:Thing')
    assert len(trip.annotations()) == 2


def test_conjunctive_shapes_and_inherited_required_flag(native):
    extra = ReifierShape(con=native.con, project=native.project, shape_iri='travel:NoteShape', properties=[
        PropertyClass(con=native.con, project=native.project, property_class_iri='travel:note',
                      datatype=XsdDatatypes.string, minCount=1, minLength=2)])
    extra.create()
    parent = ResourceClass.read(native.con, native.project, 'travel:Trip', ignore_cache=True)
    parent[Q('travel:isAt')].reifierShapes = ['travel:VisitShape','travel:NoteShape']
    parent.update()
    child = ResourceClass(con=native.con, project=native.project, owlclass_iri='travel:Child',
        superclass=['travel:Trip'], properties=[PropertyClass(con=native.con, project=native.project,
            property_class_iri='travel:isAt', toClass='travel:Location', reificationRequired=False)])
    child.create()
    factory = ResourceInstanceFactory(native.con, native.project)
    Child = factory.createObjectInstance('travel:Child')
    trip = Child(iri=Iri('travel:Inherited'), isAt=['travel:A'])
    with pytest.raises(OldapErrorValue, match='Required'):
        trip.create()
    trip.add_annotation('travel:isAt','travel:A',{'travel:dateTime':['2026-01-01T00:00:00Z']})
    with pytest.raises(OldapErrorValue, match='cardinality'):
        trip.create()
    trip = Child(iri=Iri('travel:Inherited'), isAt=['travel:A'])
    trip.add_annotation('travel:isAt','travel:A',{'travel:dateTime':['2026-01-01T00:00:00Z'],'travel:note':['ok']})
    trip.create()
    assert len(trip.annotations()) == 1


def test_history_restore_replay_is_noop(native):
    first, _ = visits(native)
    trip = native.factory.read('travel:T')
    trip.replace_annotation(first, {'travel:dateTime':['2026-02-01T00:00:00Z']})
    trip.update()
    entry = native.history.list('travel:T')[0]
    native.history.restore('travel:T',entry.iri)
    restored = native.factory.read('travel:T')
    before = str(restored.lastModificationDate)
    identifiers = {str(record.iri) for record in restored.annotations()}
    native.history.restore('travel:T',entry.iri)
    assert str(native.factory.read('travel:T').lastModificationDate) == before
    assert {str(record.iri) for record in restored.annotations()} == identifiers
    assert len(native.history.list('travel:T')) == 2


def test_language_constraints_and_controlled_iri_fields(native):
    shape = ReifierShape.read(native.con, native.project, 'travel:VisitShape')
    shape['travel:note'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:note', datatype=XsdDatatypes.langString,
        languageIn=['en','de'], uniqueLang=True, minLength=2, maxLength=5)
    shape['travel:choice'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:choice', toClass='travel:Location', inSet=['travel:A'])
    shape.update()
    trip = native.Trip(iri=Iri('travel:Languages'), isAt=['travel:A'])
    rid = trip.add_annotation('travel:isAt','travel:A',{'travel:dateTime':['2026-01-01T00:00:00Z'],
        'travel:note':['good@en','gut@de'], 'travel:choice':['travel:A']})
    trip.create()
    assert len(trip.annotations()[0].fields) == 3
    trip = native.factory.read('travel:Languages')
    trip.replace_annotation(rid, {'travel:dateTime':['2026-01-01T00:00:00Z'],'travel:note':['good@en','other@en']})
    with pytest.raises(OldapErrorValue, match='Duplicate annotation language'):
        trip.update()


def test_deletion_removes_owned_self_links(native):
    shape = ReifierShape.read(native.con, native.project, 'travel:VisitShape')
    shape['travel:owner'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:owner', toClass='travel:Trip')
    shape.update()
    first, _ = visits(native)
    trip = native.factory.read('travel:T')
    trip.replace_annotation(first, {'travel:dateTime':['2026-01-01T00:00:00Z'], 'travel:owner':['travel:T']})
    trip.update()
    trip.delete()
    with pytest.raises(OldapErrorNotFound):
        native.factory.read('travel:T')


@pytest.mark.parametrize('extra', [
    'GRAPH travel:other { <RID> travel:note "foreign" }',
    'GRAPH travel:data { <RID> rdf:reifies <<( travel:A travel:label "shared" )>> }',
])
def test_cross_graph_and_shared_reifier_rejected(native, extra):
    first, _ = visits(native)
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context +
            'INSERT DATA { '+extra.replace('RID',str(first))+' }')
    trip = native.factory.read('travel:T')
    trip.remove_annotation(first)
    with pytest.raises(OldapErrorInUse):
        trip.update()
