"""Per-graph namespace resolution must preserve CONSTRUCT value semantics."""
from unittest.mock import patch

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, XSD

from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.construct_processor import ConstructProcessor
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def test_repeated_known_and_unknown_iris_are_resolved_once_per_graph():
    context = Context(name='CONSTRUCT_LOCAL_RESOLUTION')
    context['sample'] = NamespaceIRI('https://example.org/sample/')
    first, second = (URIRef('https://example.org/sample/' + name) for name in ('first', 'second'))
    unknown = URIRef('https://unknown.example/resource')
    unknown_predicate = URIRef('https://unknown.example/predicate')
    graph = Graph()
    for subject in (first, second):
        graph.add((subject, RDF.type, URIRef('https://example.org/sample/Record')))
        graph.add((subject, unknown_predicate, unknown))
    with patch.object(context, 'iri2qname', wraps=context.iri2qname) as resolve:
        result = ConstructProcessor.process(context, graph)
    iris = {term for triple in graph for term in triple if isinstance(term, URIRef)}
    assert resolve.call_count == len(iris)
    for name in ('first', 'second'):
        data = result[Xsd_QName('sample:' + name)]
        assert data[Xsd_QName('rdf:type')] == Xsd_QName('sample:Record')
        # Unknown predicates stay RDFLib URIs; unknown object values stay IRIs.
        assert data[unknown_predicate] == Iri(str(unknown))
    first_type = result[Xsd_QName('sample:first')][Xsd_QName('rdf:type')]
    second_type = result[Xsd_QName('sample:second')][Xsd_QName('rdf:type')]
    assert first_type is not second_type
    first_type += 'Changed'
    assert second_type == Xsd_QName('sample:Record')


def test_context_changes_are_observed_on_the_next_graph():
    context = Context(name='CONSTRUCT_CHANGED_CONTEXT')
    subject = URIRef('https://new.example/record')
    graph = Graph()
    graph.add((subject, RDF.value, Literal('1911-01-01', datatype=XSD.date)))
    before = ConstructProcessor.process(context, graph)
    assert Iri(str(subject)) in before
    context['fresh'] = NamespaceIRI('https://new.example/')
    after = ConstructProcessor.process(context, graph)
    assert Xsd_QName('fresh:record') in after
    assert str(after[Xsd_QName('fresh:record')][Xsd_QName('rdf:value')]) == '1911-01-01'
    assert Iri(str(subject)) in before
