"""Behavioral tests for bounded read rules and transaction-local schema selection."""
from unittest.mock import Mock

import pytest
from rdflib import Dataset

from oldaplib.src.helpers.jena_entailment import CLASS_PATH, property_pattern
from oldaplib.src.jena_connection import JenaConnection

PREFIX = '''PREFIX demo: <https://example.org/demo/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX shared: <http://oldap.org/shared#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX oldap: <http://oldap.org/base#>
'''


@pytest.fixture
def data(monkeypatch):
    # Missing FROM NAMED graphs are empty, as in the local Fuseki dataset;
    # RDFLib must not try to dereference test graph IRIs over HTTP.
    monkeypatch.setattr('rdflib.plugins.sparql.SPARQL_LOAD_GRAPHS', False)
    dataset = Dataset()
    dataset.parse(data=PREFIX + '''
      demo:onto {
        demo:parent owl:inverseOf demo:children .
        demo:A owl:equivalentClass demo:B ; rdfs:subClassOf demo:B .
        demo:A owl:equivalentClass demo:EquivalentOnly .
        demo:EquivalentOnly owl:equivalentClass demo:A .
        demo:B owl:equivalentClass demo:A ; rdfs:subClassOf demo:C .
        oldap:attachedToRole owl:inverseOf demo:fakeGrant .
        rdf:type owl:inverseOf demo:fakeType .
        oldap:createdBy owl:inverseOf demo:fakeCreator .
      }
      demo:foreign { demo:parent owl:inverseOf demo:foreignLink . demo:C rdfs:subClassOf demo:Foreign . }
      demo:data {
        demo:child demo:parent demo:item .
        demo:typedA a demo:A . demo:typedB a demo:B . demo:typedC a demo:C . demo:unmodeled a demo:Absent .
        demo:role demo:fakeGrant demo:item .
        demo:FakeClass demo:fakeType demo:item .
        demo:actor demo:fakeCreator demo:item .
      }
    ''', format='trig')
    yield dataset
    dataset.close()


def test_inverse_values_stay_scoped_and_do_not_derive_authorization(data):
    pattern = property_pattern('demo', 'demo:item', '?predicate', '?value', alias='test')
    query = PREFIX + 'SELECT ?predicate ?value FROM demo:onto FROM NAMED demo:data WHERE { ' + pattern + ' }'
    rows = {(str(row.predicate), str(row.value)) for row in data.query(query)}
    assert rows == {('https://example.org/demo/children', 'https://example.org/demo/child')}


def test_only_subclass_ancestry_is_expanded(data):
    def types(start):
        query = PREFIX + f'SELECT DISTINCT ?type FROM demo:onto WHERE {{ demo:{start} {CLASS_PATH} ?type }}'
        return {str(row.type).rsplit('/', 1)[-1] for row in data.query(query)}
    assert types('A') == {'B', 'C'}
    assert types('B') == {'C'}
    assert types('EquivalentOnly') == set()
    assert types('C') == set()  # No inference down to subclasses or into foreign graphs.


@pytest.mark.parametrize('active', [False, True])
def test_schema_registration_reads_join_the_callers_transaction(active):
    con = object.__new__(JenaConnection)
    con._context_name = 'ENTAILMENT_UNIT'
    con._session_id = 'owned-session' if active else None
    con._transaction_url = 'http://owned.invalid/session' if active else None
    result = {'results': {'bindings': [
        {'prefix': {'value': 'schema'}}, {'prefix': {'value': 'schema'}}, {'prefix': {'value': 'example'}}]}}
    con.query = Mock(return_value=result)
    con.transaction_query = Mock(return_value=result)
    assert con._resource_schema_graphs('demo') == ['demo:onto', 'shared:onto', 'oldap:onto',
        '<urn:oldap:vocab:example>', '<urn:oldap:vocab:schema>']
    used, unused = (con.transaction_query, con.query) if active else (con.query, con.transaction_query)
    unused.assert_not_called()
    used.assert_called_once()
    query = used.call_args.args[0]
    assert 'FROM demo:shacl FROM shared:shacl FROM oldap:shacl' in query
    assert 'GRAPH ?' not in query


def test_class_set_includes_exact_types_without_schema_and_excludes_foreign_classes(data):
    from oldaplib.src.helpers.jena_entailment import class_choices
    query = PREFIX + 'SELECT ?type FROM demo:onto FROM NAMED demo:data WHERE { ' + class_choices('?type', 'demo:C', 'demo:data') + ' }'
    assert {str(row.type).rsplit('/', 1)[-1] for row in data.query(query)} == {'A', 'B', 'C'}
    query = PREFIX + 'SELECT ?type FROM demo:onto FROM NAMED demo:data WHERE { ' + class_choices('?type', 'demo:Absent', 'demo:data') + ' }'
    assert {str(row.type).rsplit('/', 1)[-1] for row in data.query(query)} == {'Absent'}


def test_outer_bound_archive_target_is_correlated_instead_of_invalid_values(data):
    from oldaplib.src.helpers.jena_entailment import class_choices
    query = PREFIX + 'SELECT ?type FROM demo:onto FROM NAMED demo:data WHERE { VALUES (?type ?target) { (demo:A demo:C) (demo:C demo:A) } '
    query += class_choices('?type', '?target', 'demo:data') + ' }'
    assert {str(row.type).rsplit('/', 1)[-1] for row in data.query(query)} == {'A'}


def property_rows(data, predicate='?predicate', *, modeled=False):
    """Execute the real property builder without RDF 1.2-only grant syntax."""
    pattern = property_pattern('demo', 'demo:item', predicate, '?value', alias='test',
                               expand_subproperties=True, modeled_only=modeled)
    query = PREFIX + '''SELECT DISTINCT * FROM demo:onto
        FROM NAMED demo:data FROM NAMED demo:shacl
        FROM NAMED shared:shacl FROM NAMED oldap:shacl WHERE { ''' + pattern + ' }'
    return list(data.query(query))


@pytest.fixture
def hierarchy(data):
    data.parse(data=PREFIX + '''
        demo:onto {
            demo:specific rdfs:subPropertyOf demo:left, demo:right .
            demo:left rdfs:subPropertyOf demo:general .
            demo:right rdfs:subPropertyOf demo:general .
            demo:general rdfs:subPropertyOf demo:left ; owl:equivalentProperty demo:equivalent .
            demo:equivalent owl:equivalentProperty demo:general .
        }
        demo:data { demo:item a demo:A ; demo:specific "Text"@en ; demo:plain "Direct" . }
        demo:shacl {
            demo:BShape sh:targetClass demo:B ; sh:property [ sh:path demo:general ] .
            demo:OtherShape sh:targetClass demo:Unrelated ; sh:property [ sh:path demo:right ] .
        }
        demo:foreign { demo:specific rdfs:subPropertyOf demo:foreignProperty . }
    ''', format='trig')
    return data


def test_subproperties_follow_hierarchies_and_preserve_literal_identity(hierarchy):
    from rdflib import Literal
    for predicate in ('specific', 'left', 'right', 'general'):
        assert {row.value for row in property_rows(hierarchy, 'demo:' + predicate)} == {Literal('Text', lang='en')}
    assert not property_rows(hierarchy, 'demo:equivalent')
    assert not property_rows(hierarchy, 'demo:foreignProperty')
    assert {str(row.value) for row in property_rows(hierarchy, 'demo:plain')} == {'Direct'}
    assert not property_rows(hierarchy, 'demo:missing')
    # A general assertion must not create a narrower assertion.
    hierarchy.update(PREFIX + 'DELETE WHERE { GRAPH demo:data { demo:item demo:specific ?v } }; INSERT DATA { GRAPH demo:data { demo:item demo:general "Other" } }')
    assert not property_rows(hierarchy, 'demo:specific')


def test_hydration_only_adds_modeled_superproperty_keys(hierarchy):
    predicates = {str(row.predicate).rsplit('/', 1)[-1] for row in property_rows(hierarchy, modeled=True)}
    assert 'general' in predicates  # Modeled on an ancestor, not the asserted class.
    assert 'specific' in predicates and 'plain' in predicates  # Asserted fields survive.
    assert not {'left', 'right', 'equivalent', 'foreignProperty'} & predicates
    hierarchy.update(PREFIX + 'DELETE WHERE { GRAPH demo:shacl { ?s ?p ?o } }')
    assert 'general' not in {str(row.predicate).rsplit('/', 1)[-1] for row in property_rows(hierarchy, modeled=True)}


@pytest.mark.parametrize('protected', [
    'rdf:type', 'rdf:reifies', 'oldap:attachedToRole', 'oldap:hasRole',
    'oldap:inProject', 'oldap:hasAdminPermission', 'oldap:hasDataPermission',
    'oldap:hasDefaultDataPermission', 'oldap:permissionValue', 'oldap:createdBy',
    'oldap:creationDate', 'oldap:lastModifiedBy', 'oldap:lastModificationDate',
])
def test_protected_properties_cannot_be_hierarchy_endpoints_or_bridges(data, protected):
    data.parse(data=PREFIX + f'''
        demo:onto {{ demo:fake rdfs:subPropertyOf {protected} .
            {protected} rdfs:subPropertyOf demo:leaked . }}
        demo:data {{ demo:item demo:fake demo:target ; {protected} demo:explicit . }}
    ''', format='trig')
    assert not property_rows(data, 'demo:leaked')
    assert {str(row.value) for row in property_rows(data, protected)} == {'https://example.org/demo/explicit'}
    assert not any(str(row.predicate).endswith('/leaked') for row in property_rows(data))


def test_class_selection_keeps_direct_equivalent_named_types_but_not_equivalence(data):
    from oldaplib.src.helpers.jena_entailment import class_choices
    data.update(PREFIX + 'INSERT DATA { GRAPH demo:data { demo:explicit a demo:EquivalentOnly } }')
    query = PREFIX + 'SELECT ?type FROM demo:onto FROM NAMED demo:data WHERE { ' + class_choices('?type', 'demo:EquivalentOnly', 'demo:data') + ' }'
    assert {str(row.type).rsplit('/', 1)[-1] for row in data.query(query)} == {'EquivalentOnly'}
