"""Exercise real history SPARQL and resource updates on an isolated RDF dataset."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from rdflib import Dataset, Graph, Literal, Namespace, RDF, URIRef, XSD

from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission, OldapErrorUpdateFailed, OldapErrorValue
from oldaplib.src.objectfactory import ResourceInstance, _alias_requested_subjects, _resource_from_construct
from oldaplib.src.helpers.construct_processor import ConstructProcessor
from oldaplib.src.resource_history import ResourceHistory, H, history_properties
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName as Q
from oldaplib.src.xsd.dating import Dating, OldapCalendar

P = Namespace('https://history.test/')
S = Namespace('https://schema.org/')


class DatasetConnection:
    """Run generated SPARQL against a transactional in-memory dataset."""
    context_name = 'property-history-tests'
    userIri = Iri('urn:test:editor')

    def __init__(self):
        self.dataset = Dataset()
        self.active = False
        self.before = None
        self.can_read = True
        self.permission = DataPermission.DATA_UPDATE
        self.writes = []
        ctx = Context(name=self.context_name)
        ctx['hist'] = NamespaceIRI(str(P))
        self.dataset.graph(P.data).parse(data=ctx.turtle_context + '''
          hist:one a hist:Item ; schema:name "Before"@en, "Vorher"@de ;
          oldap:createdBy <urn:test:editor> ;
          oldap:creationDate "2026-01-01T00:00:00+00:00"^^xsd:dateTimeStamp ;
          oldap:lastModificationDate "2026-01-01T00:00:00+00:00"^^xsd:dateTimeStamp ;
          oldap:lastModifiedBy <urn:test:editor> .''', format='turtle')

    def in_transaction(self):
        return self.active

    def transaction_start(self):
        self.before = self.dataset.serialize(format='trig')
        self.active = True

    def transaction_commit(self):
        self.active = False

    def transaction_abort(self):
        self.dataset = Dataset().parse(data=self.before, format='trig')
        self.active = False

    def query(self, query, format=SparqlResultFormat.JSON):
        result = self.dataset.query(query)
        return result.graph if result.type == 'CONSTRUCT' else json.loads(result.serialize(format='json'))

    def transaction_query(self, query, result_format=SparqlResultFormat.JSON):
        assert self.active
        return self.query(query, result_format)

    def transaction_update(self, query):
        assert self.active
        self.writes.append(query)
        self.dataset.update(query)


def prop(datatype=None, toClass=None, minCount=None, maxCount=None):
    """Minimal model metadata; use actual setters and cardinality validation."""
    return SimpleNamespace(datatype=datatype, toClass=toClass, inversePath=None,
                           minCount=minCount, maxCount=maxCount, get=lambda key: None)


@pytest.fixture
def setup():
    con = DatasetConnection()
    props = {
        Q('schema:name'): prop(XsdDatatypes.langString),
        Q('hist:number'): prop(XsdDatatypes.integer),
        Q('hist:link'): prop(toClass=Iri('oldap:Thing')),
        Q('hist:date'): prop(toClass=Iri('oldap:Dating')),
        Q('oldap:createdBy'): prop(toClass=Iri('oldap:User')),
        Q('oldap:creationDate'): prop(XsdDatatypes.dateTimeStamp),
        Q('oldap:lastModifiedBy'): prop(toClass=Iri('oldap:User')),
        Q('oldap:lastModificationDate'): prop(XsdDatatypes.dateTimeStamp),
    }
    cls = type('HistoryItem', (ResourceInstance,), {
        '_con': con, 'project': SimpleNamespace(projectShortName='hist'),
        'name': Q('hist:Item'), 'properties': props,
        'superclass': {Q('oldap:Thing'): None}, 'user_default_roles': {},
        'check_for_permissions': lambda self, permission: (False, ''),
        'get_data_permission': lambda self, permission: con.permission >= permission,
    })

    def read(iri):
        if not con.can_read:
            raise OldapErrorNoPermission('Not readable')
        ctx = Context(name=con.context_name)
        data = _alias_requested_subjects(ctx, ConstructProcessor.process(ctx, con.dataset.graph(P.data)), [Iri(str(iri))])
        _, kwargs = _resource_from_construct(Iri(str(iri)), data, props)
        return cls(iri=Iri(str(iri)), **kwargs)

    history = ResourceHistory.__new__(ResourceHistory)
    history.con = con
    history.factory = SimpleNamespace(read=read)
    return con, read, history


def test_first_change_complete_language_set_and_undo(setup):
    con, read, history = setup
    assert history.list('hist:one') == []
    instance = read('hist:one')
    instance[Q('schema:name')] = ['After@en', 'Vorher@de']
    instance.update()
    entries = history.list('hist:one')
    assert len(entries) == 1
    assert {str(v) for v in entries[0].values} == {'Before@en', 'Vorher@de'}
    history.restore('hist:one', entries[0].iri)
    assert {str(v) for v in read('hist:one')[Q('schema:name')]} == {'Before@en', 'Vorher@de'}
    assert len(history.list('hist:one')) == 2
    history.restore('hist:one', entries[0].iri)
    assert len(history.list('hist:one')) == 2


def test_empty_multivalue_zero_and_delete_roundtrip(setup):
    con, read, history = setup
    instance = read('hist:one')
    instance[Q('hist:number')] = [0, 2]
    instance.update()
    first = history.list('hist:one')[0]
    assert first.values == ()
    instance[Q('hist:number')].discard(2)
    instance.update()
    assert {int(v) for v in history.list('hist:one')[0].values} == {0, 2}
    history.restore('hist:one', first.iri)
    assert read('hist:one').get(Q('hist:number')) is None
    assert len(history.list('hist:one')) == 3


def test_rollback_and_stale_writer_leave_no_history(setup):
    con, read, history = setup
    stale = read('hist:one')
    current = read('hist:one')
    current[Q('schema:name')] = ['New@en']
    with pytest.raises(RuntimeError):
        current.update(before_commit=lambda con: (_ for _ in ()).throw(RuntimeError('late failure')))
    assert history.list('hist:one') == []
    current = read('hist:one')
    current[Q('schema:name')] = ['New@en']
    current.update()
    stale[Q('schema:name')] = ['Stale@en']
    with pytest.raises(OldapErrorUpdateFailed):
        stale.update()
    assert len(history.list('hist:one')) == 1


def test_permissions_and_current_constraints(setup):
    con, read, history = setup
    instance = read('hist:one')
    instance[Q('hist:number')] = [1, 2]
    instance.update()
    empty = history.list('hist:one')[0]
    con.permission = DataPermission.DATA_VIEW
    with pytest.raises(OldapErrorNoPermission):
        history.restore('hist:one', empty.iri)
    con.can_read = False
    with pytest.raises(OldapErrorNoPermission):
        history.list('hist:one')
    con.can_read = True
    con.permission = DataPermission.DATA_EXTEND
    instance = read('hist:one')
    instance[Q('hist:number')].discard(2)
    with pytest.raises(OldapErrorNoPermission):
        instance.update()
    con.permission = DataPermission.DATA_UPDATE
    instance.properties[Q('hist:number')].minCount = 1
    with pytest.raises(OldapErrorValue):
        history.restore('hist:one', empty.iri)
    assert len(history.list('hist:one')) == 1


def test_system_and_inverse_properties_are_excluded(setup):
    con, read, history = setup
    instance = read('hist:one')
    assert Q('oldap:lastModifiedBy') not in history_properties(instance)
    instance.properties[Q('hist:link')].inversePath = Q('hist:backlink')
    assert Q('hist:link') not in history_properties(instance)
    with pytest.raises(OldapErrorValue):
        history.list('hist:one', property_iri='oldap:lastModifiedBy')
    assert Q('schema:name') in history_properties(instance)


def test_paging_counts_entries_and_scopes_entry_to_resource(setup):
    con, read, history = setup
    for value in range(4):
        instance = read('hist:one')
        instance[Q('hist:number')] = [value, value + 10]
        instance.update()
    assert len(history.list('hist:one', limit=2)) == 2
    assert len(history.list('hist:one', limit=2, offset=2)) == 2
    assert history.list('hist:one', offset=4) == []
    assert history.list('hist:one', property_iri='schema:name') == []
    for limit in (0, 1001, True):
        with pytest.raises(OldapErrorValue):
            history.list('hist:one', limit=limit)


def test_dating_snapshot_survives_live_mutation(setup):
    con, read, history = setup
    instance = read('hist:one')
    instance[Q('hist:date')] = Dating((1930,), inCalendar=OldapCalendar.JULIAN,
                                    verbatimDate='[around 1930]')
    instance.update()
    instance = read('hist:one')
    instance[Q('hist:date')] = Dating((1940,))
    instance.update()
    old = history.list('hist:one')[0]
    assert isinstance(old.values[0], Dating)
    assert old.values[0]._as_dict()['verbatimDate'] == '[around 1930]'
    history.restore('hist:one', old.iri)
    restored = read('hist:one')[Q('hist:date')]
    assert restored._as_dict()['verbatimDate'] == '[around 1930]'
    assert restored._as_dict()['inCalendar'] == OldapCalendar.JULIAN
    assert len(history.list('hist:one')) == 3


def test_iri_values_full_iri_subject_and_noop(setup):
    con, read, history = setup
    instance = read(str(P.one))
    instance[Q('hist:link')] = [Iri('urn:test:target')]
    instance.update()
    instance = read(str(P.one))
    instance[Q('hist:link')] = [Iri('urn:test:other')]
    instance.update()
    entry = history.list(str(P.one))[0]
    assert str(entry.values[0]) == 'urn:test:target'
    history.restore(str(P.one), entry.iri)
    history.restore(str(P.one), entry.iri)
    assert len(history.list(str(P.one))) == 3


def test_history_cannot_restore_a_system_property_even_if_forged(setup):
    con, read, history = setup
    con.dataset.graph(P.history).add((P.forged, RDF.type, H.PropertyHistory))
    for predicate, value in [(H.historyProperty, H.createdBy), (H.historyResource, P.one),
                             (H.historyTimestamp, Literal('2026-01-01T00:00:00Z', datatype=XSD.dateTimeStamp))]:
        con.dataset.graph(P.history).add((P.forged, predicate, value))
    assert history.list('hist:one') == []
    from oldaplib.src.helpers.oldaperror import OldapErrorNotFound
    with pytest.raises(OldapErrorNotFound):
        history.restore('hist:one', str(P.forged))


def test_noop_empty_restore_and_nested_dating(setup):
    con, read, history = setup
    instance = read('hist:one')
    instance[Q('hist:date')] = Dating((1930,), before={Dating((1940,))})
    instance.update()
    empty = history.list('hist:one')[0]
    instance = read('hist:one')
    instance[Q('hist:date')] = Dating((1950,))
    instance.update()
    previous = history.list('hist:one')[0]
    history.restore('hist:one', previous.iri)
    assert len(history.list('hist:one')) == 3
    history.restore('hist:one', previous.iri)
    assert len(history.list('hist:one')) == 3
    history.restore('hist:one', empty.iri)
    count = len(history.list('hist:one'))
    history.restore('hist:one', empty.iri)
    assert len(history.list('hist:one')) == count


def test_history_does_not_block_resource_deletion(setup, monkeypatch):
    con, read, history = setup
    instance = read('hist:one')
    instance[Q('schema:name')] = ['After@en']
    instance.update()
    con.permission = DataPermission.DATA_DELETE
    # RDFLib cannot parse the existing RDF-star deletion; execute the actual
    # reference query and verify that the operation reaches the deletion write.
    write = Mock()
    monkeypatch.setattr(con, 'transaction_update', write)
    instance.delete()
    write.assert_called_once()


def test_history_retained_after_property_removed_from_model(setup):
    con, read, history = setup
    instance = read('hist:one')
    instance[Q('hist:number')] = [1]
    instance.update()
    entry = history.list('hist:one')[0]
    del instance.properties[Q('hist:number')]
    assert len(history.list('hist:one')) == 1
    with pytest.raises(OldapErrorValue):
        history.restore('hist:one', entry.iri)


def test_transform_versions_removed_and_added_business_properties(setup):
    con, read, history = setup
    source = read('hist:one')
    base = SimpleNamespace(name=Q('oldap:Thing'), superclass={}, properties={
        key: value for key, value in source.properties.items() if str(key).startswith('oldap:')})
    target_cls = type('TransformedItem', (type(source),), {'name': Q('hist:Other')})
    source.factory = SimpleNamespace(createObjectInstance=lambda name: base if name == Q('oldap:Thing') else target_cls)
    con.permission = DataPermission.DATA_DELETE
    source.transform_class('hist:Other', preserve_class='oldap:Thing', properties={'hist:number': [9]})
    entries = history.list('hist:one')
    assert {str(entry.property_iri) for entry in entries} == {'schema:name', 'hist:number'}
    assert next(entry for entry in entries if str(entry.property_iri) == 'hist:number').values == ()
    assert {str(value) for value in next(entry for entry in entries if str(entry.property_iri) == 'schema:name').values} == {'Before@en', 'Vorher@de'}


def test_history_write_failure_rolls_back_live_change(setup, monkeypatch):
    con, read, history = setup
    write = con.transaction_update

    def fail_history(query):
        if 'GRAPH hist:history' in query:
            raise RuntimeError('history storage failure')
        write(query)

    monkeypatch.setattr(con, 'transaction_update', fail_history)
    instance = read('hist:one')
    instance[Q('schema:name')] = ['After@en']
    with pytest.raises(RuntimeError):
        instance.update()
    assert history.list('hist:one') == []
    assert {str(value) for value in read('hist:one')[Q('schema:name')]} == {'Before@en', 'Vorher@de'}


def test_foreign_entry_cannot_be_read_or_restored(setup):
    from oldaplib.src.helpers.oldaperror import OldapErrorNotFound
    con, read, history = setup
    instance = read('hist:one')
    instance[Q('schema:name')] = ['After@en']
    instance.update()
    entry = history.list('hist:one')[0]
    for _, predicate, value in list(con.dataset.graph(P.data).triples((P.one, None, None))):
        con.dataset.graph(P.data).add((P.other, predicate, value))
    with pytest.raises(OldapErrorNotFound):
        history.get('hist:other', entry.iri)
    with pytest.raises(OldapErrorNotFound):
        history.restore('hist:other', entry.iri)


def test_creation_has_no_initial_history(setup):
    con, read, history = setup
    source = read('hist:one')
    cls = type('NewHistoryItem', (type(source),), {'check_for_permissions': lambda *args: (True, '')})
    new = cls(iri=Iri('hist:new'), **{str(prop): list(values) for prop, values in source._values.items()})
    new.create()
    assert history.list('hist:new') == []
    new[Q('schema:name')] = ['Edited@en']
    new.update()
    assert len(history.list('hist:new')) == 1


def test_update_rejects_multiple_modification_dates_before_commit(setup):
    """A second stored timestamp must roll back the edit and its history."""
    con, read, history = setup
    instance = read('hist:one')
    before = set(con.dataset.graph(P.data))
    original_query = con.transaction_query

    def duplicate_result(query, *args, **kwargs):
        result = original_query(query, *args, **kwargs)
        if 'SELECT ?modified' in query:
            result['results']['bindings'] *= 2
        return result

    con.transaction_query = duplicate_result
    instance[Q('schema:name')] = ['Rejected@en']
    with pytest.raises(OldapErrorUpdateFailed, match='exactly one lastModificationDate'):
        instance.update()
    assert set(con.dataset.graph(P.data)) == before
    assert history.list('hist:one') == []


def test_modification_update_deletes_the_bound_stored_literal(setup):
    """Keep timestamp concurrency comparison separate from the DELETE RDF term."""
    con, read, _ = setup
    instance = read('hist:one')
    instance[Q('schema:name')] = ['Changed@en']
    instance.update()
    update = next(query for query in con.writes if 'FILTER(?oldModified =' in query)
    assert '?res oldap:lastModificationDate ?oldModified .' in update.split('INSERT')[0]
    assert len(list(con.dataset.graph(P.data).objects(P.one, H.lastModificationDate))) == 1
