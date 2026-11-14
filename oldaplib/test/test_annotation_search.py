"""Native stage-4 search acceptance using the stage-3 disposable Jena fixture."""
from unittest.mock import patch

import pytest
from flask import Flask

from oldaplib.test.test_assertion_annotation import native, visits
from oldaplib.src.annotation_search import AnnotationFilter, AnnotationFieldFilter, parse_annotation_filters
from oldaplib.src.objectfactory import ResourceInstance
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.resource_transaction import resource_transaction
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.reifier_shape import ReifierShape
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.xsd.iri import Iri


def search(native, groups, **kwargs):
    return ResourceInstance.search(native.con, native.project, resClass='travel:Trip', annotationFilter=groups, **kwargs)


def field(op, value=None, prop='travel:dateTime'):
    return AnnotationFieldFilter(prop, op, value)


def test_same_reifier_ranges_and_distinct_count_page(native):
    visits(native)
    # Two visits outside the interval must not satisfy its two halves jointly.
    group = AnnotationFilter('travel:isAt', 'travel:A', (
        field('gt', '2026-01-01T12:00:00Z'), field('lt', '2026-01-02T00:00:00Z')))
    assert search(native, [group]) == []
    matching = AnnotationFilter('travel:isAt', 'travel:A', (field('ge','2026-01-01T00:00:00Z'),))
    assert len(search(native, [matching])) == 1
    assert int(search(native, [matching], countOnly=True)) == 1
    assert len(search(native, [matching], limit=1)) == 1
    assert search(native, [matching], limit=1, offset=1) == []
    # Separate groups can intentionally select different visits.
    assert len(search(native, [AnnotationFilter('travel:isAt', fields=(field('eq','2026-01-01T10:00:00Z'),)),
                               AnnotationFilter('travel:isAt', fields=(field('eq','2026-01-02T10:00:00Z'),))])) == 1


def test_absence_literal_projection_and_orphan_graph_isolation(native):
    trip = native.Trip(iri=Iri('travel:L'), label=['hello'])
    trip.create()
    assert len(search(native, [AnnotationFilter('travel:label', 'hello', exists=False)])) == 1
    assert search(native, [AnnotationFilter('travel:label', 'missing', exists=False)]) == []
    rid = trip.add_annotation('travel:label','hello',{'travel:dateTime':['2026-01-01T00:00:00Z']})
    trip.update()
    rows = search(native, [AnnotationFilter('travel:label', 'hello')], includeAnnotations=True)
    assert len(rows) == 1 and rows[0]['@annotations'][0]['iri'] == str(rid)
    assert '@annotations' not in search(native, [AnnotationFilter('travel:label')])[0]
    assert search(native, [AnnotationFilter('travel:label', exists=False)]) == []
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context + '''INSERT DATA {
          GRAPH travel:data { <urn:orphan> a oldap:AssertionAnnotation ; rdf:reifies <<( travel:L travel:label "missing" )>> ; travel:dateTime "2026-01-02T00:00:00Z"^^xsd:dateTime . }
          GRAPH travel:other { <urn:foreign> a oldap:AssertionAnnotation ; rdf:reifies <<( travel:L travel:label "hello" )>> ; travel:dateTime "2026-01-02T00:00:00Z"^^xsd:dateTime . }
        }''')
    assert search(native, [AnnotationFilter('travel:label','missing')]) == []
    assert search(native, [AnnotationFilter('travel:label','hello',(field('eq','2026-01-02T00:00:00Z'),))]) == []


def test_field_existence_visibility_and_root_acl(native):
    shape = ReifierShape.read(native.con, native.project, 'travel:VisitShape')
    shape['travel:link'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:link', toClass='travel:Location')
    shape.update()
    Place = native.factory.createObjectInstance('travel:Location')
    Place(iri=Iri('travel:B')).create()
    choice = ReifierShape(con=native.con, project=native.project, shape_iri='travel:LinkChoice', properties=[
        PropertyClass(con=native.con, project=native.project, property_class_iri='travel:link',
                      toClass='travel:Location', inSet=['travel:B'])])
    choice.create()
    model = ResourceClass.read(native.con, native.project, 'travel:Trip', ignore_cache=True)
    model[Xsd_QName('travel:isAt')].reifierShapes = ['travel:VisitShape','travel:LinkChoice']
    model.update()
    first, _ = visits(native)
    trip = native.factory.read('travel:T')
    trip.replace_annotation(first, {'travel:dateTime':['2026-01-01T00:00:00Z'], 'travel:link':['travel:B']})
    trip.update()
    has_link = AnnotationFilter('travel:isAt',fields=(field('exists',prop='travel:link'),))
    no_link = AnnotationFilter('travel:isAt',fields=(field('not_exists',prop='travel:link'),))
    assert len(search(native,[has_link])) == len(search(native,[no_link])) == 1
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context +
            'DELETE WHERE { GRAPH travel:data { travel:B oldap:attachedToRole ?role } }')
    assert search(native,[has_link]) == []
    assert len(search(native,[no_link])) == 1
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context +
            'DELETE WHERE { GRAPH travel:data { travel:A oldap:attachedToRole ?role } }')
    # The base object itself must be visible even for an absence query.
    assert search(native,[no_link]) == []
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context +
            'INSERT DATA { GRAPH travel:data { travel:A oldap:attachedToRole travel:Reader } }')
    assert len(search(native,[AnnotationFilter('travel:isAt')])) == 1
    with resource_transaction(native.con):
        native.con.transaction_update(Context(name=native.con.context_name).sparql_context +
            'DELETE WHERE { GRAPH travel:data { travel:T oldap:attachedToRole ?role } }')
    assert search(native,[AnnotationFilter('travel:isAt')],countOnly=True) == 0


def test_model_validation_and_api(native):
    visits(native)
    with pytest.raises(OldapErrorValue):
        search(native,[AnnotationFilter('travel:unknown')])
    with pytest.raises(OldapErrorValue):
        search(native,[AnnotationFilter('travel:isAt',fields=(field('eq','bad-date'),))])
    with pytest.raises(OldapErrorValue):
        search(native,[AnnotationFilter('travel:isAt',fields=(field('exists',prop='travel:unknown'),))])
    from oldap_api.views.instance_views import instance_bp
    app = Flask(__name__)
    app.register_blueprint(instance_bp)
    payload = {'resClass':'travel:Trip','annotationFilter':[{'property':'travel:isAt','fields':[
        {'property':'travel:dateTime','op':'ge','value':'2026-01-01T00:00:00Z'}]}]}
    with patch('oldap_api.authentication.Connection',return_value=native.con):
        client = app.test_client()
        headers = {'Authorization':'Bearer native-test'}
        result = client.post('/data/search/travel',json={**payload,'includeAnnotations':True},headers=headers)
        assert result.status_code == 200, result.json
        assert len(result.json) == 1 and len(result.json[0]['@annotations']) == 2
        result = client.post('/data/search/travel',json={**payload,'countOnly':True},headers=headers)
        assert result.status_code == 200 and result.json['count'] == 1
        result = client.post('/data/search/travel',json={**payload,'includeAnnotations':'true'},headers=headers)
        assert result.status_code == 400
        result = client.post('/data/search/travel',json={'resClass':'travel:Trip','annotationFilter':None},headers=headers)
        assert result.status_code == 400
        result = client.get('/data/search/travel',query_string={'resClass':'travel:Trip','includeAnnotations':'true'},headers=headers)
        assert result.status_code == 400


@pytest.mark.parametrize('value', [None, {}, [{'property':'travel:isAt','fields':{}}],
    [{'property':'travel:isAt','exists':'false'}], [{'property':'travel:isAt','fields':[{'property':'travel:x','op':'bad'}]}]])
def test_strict_parser(value):
    with pytest.raises(OldapErrorValue):
        parse_annotation_filters(value)


def test_different_fields_must_match_same_visit_and_value(native):
    shape = ReifierShape.read(native.con, native.project, 'travel:VisitShape')
    shape['travel:note'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:note', datatype=XsdDatatypes.string)
    shape['travel:score'] = PropertyClass(con=native.con, project=native.project,
        property_class_iri='travel:score', datatype=XsdDatatypes.integer)
    shape.update()
    first, second = visits(native)
    trip = native.factory.read('travel:T')
    trip.replace_annotation(first, {'travel:dateTime':['2026-01-01T10:00:00Z'], 'travel:note':['first'], 'travel:score':[1,10]})
    trip.replace_annotation(second, {'travel:dateTime':['2026-01-02T10:00:00Z'], 'travel:note':['second']})
    trip.update()
    assert search(native,[AnnotationFilter('travel:isAt',fields=(
        field('eq','2026-01-01T10:00:00Z'), field('eq','second','travel:note')))]) == []
    assert search(native,[AnnotationFilter('travel:isAt',fields=(
        field('gt',3,'travel:score'), field('lt',7,'travel:score')))]) == []
    assert len(search(native,[AnnotationFilter('travel:isAt',fields=(
        field('eq','2026-01-01T10:00:00Z'), field('eq','first','travel:note')))])) == 1


def test_bounded_annotated_search_receipt(native):
    """Record opt-in planning/query timings and native algebra on a modest page."""
    import hashlib
    import json
    import os
    from pathlib import Path
    import statistics
    import time
    destination = os.environ.get('OLDAP_ANNOTATION_SEARCH_RECEIPT')
    if not destination:
        pytest.skip('Set OLDAP_ANNOTATION_SEARCH_RECEIPT for bounded search evidence.')
    context = Context(name=native.con.context_name)
    triples = []
    for index in range(100):
        subject = f'travel:bench{index}'
        triples.append(f'''{subject} a travel:Trip ; travel:label "trip{index}" ;
          oldap:attachedToRole travel:Reader .
          <urn:search:grant{index}> rdf:reifies <<( {subject} oldap:attachedToRole travel:Reader )>> ; oldap:hasDataPermission oldap:DATA_UPDATE .''')
        for visit in range(5):
            triples.append(f'''<urn:search:annotation{index}-{visit}> a oldap:AssertionAnnotation ;
              rdf:reifies <<( {subject} travel:label "trip{index}" )>> ; travel:dateTime "2026-01-0{visit+1}T00:00:00Z"^^xsd:dateTime .''')
    with resource_transaction(native.con):
        native.con.transaction_update(context.sparql_context + 'INSERT DATA { GRAPH travel:data { '+' '.join(triples)+' } }')
    filters = [AnnotationFilter('travel:label',fields=(field('ge','2026-01-02T00:00:00Z'),field('le','2026-01-04T00:00:00Z')))]
    report = {'resources':100,'annotationsPerResource':5,'runsPerCase':20,'cases':{}}
    for name, groups, count in [('plain_page',None,False),('annotated_page',filters,False),('annotated_count',filters,True)]:
        call = lambda: search(native,groups,countOnly=count,limit=25)
        native.con.queries.clear()
        result = call()
        assert int(result) == 100 if count else len(result) == 25
        queries = list(native.con.queries)
        query = queries[-1]
        plan = native.con.send('explain',query=query)['result']
        assert 'LIMIT 25' not in query if count else 'LIMIT 25' in query
        if groups:
            assert 'exists' in plan and 'annotation0Reifier' in plan
        for _ in range(5):
            call()
        samples=[]
        for _ in range(20):
            start=time.perf_counter_ns()
            call()
            samples.append((time.perf_counter_ns()-start)/1e6)
        report['cases'][name]={'queriesIncludingModelResolution':len(queries),
            'medianMs':statistics.median(samples),'maximumMs':max(samples),
            'querySha256':hashlib.sha256(query.encode()).hexdigest(), 'optimizedAlgebra':plan}
    Path(destination).write_text(json.dumps(report,indent=2)+'\n')
