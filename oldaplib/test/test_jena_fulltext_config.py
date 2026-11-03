"""Offline checks for the portable fulltext configuration boundary."""
import pytest

from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_fulltext import jena_fulltext_fields, jena_fulltext_pattern
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.objectfactory import FTSearchFilter


def test_config_resolves_project_qnames_and_aliases_without_mutating_input():
    context = Context(name='TEXT_CONFIG_UNIT')
    context['demo'] = NamespaceIRI('https://example.org/demo#')
    source = {'fields': {'title': ['demo:title'], 'linkedTitle': ['demo:link', 'demo:title'],
                         'alias': ['https://example.org/demo#title']}}
    fields = jena_fulltext_fields(source, context)
    assert tuple(map(str, fields['linkedTitle'])) == ('https://example.org/demo#link', 'https://example.org/demo#title')
    assert fields['title'] == fields['alias']
    assert source['fields']['linkedTitle'] == ['demo:link', 'demo:title']
    query = jena_fulltext_pattern('<https://example.org/demo#data>', [FTSearchFilter('linkedTitle', 'fox')], fields, 'score')
    assert '?res <https://example.org/demo#link> ?ft_0_target' in query
    assert '(?ft_0_target ?ft_0_score)' in query


@pytest.mark.parametrize('config', [
    None, {}, {'fields': {}}, {'fields': []},
    {'fields': {'name': []}}, {'fields': {'name': 'schema:name'}},
    {'fields': {'name': ['']}}, {'fields': {'name': ['relative']}},
    {'fields': {'name': [42]}}, {'fields': {42: ['schema:name']}},
    {'fields': {'bad:field': ['schema:name']}},
    {'fields': {'name': ['missingPrefix:predicate']}},
    {'fields': {'name': ['schema:name']}, 'analyzer': 'unknown'},
    {'fields': {'name': ['schema:name']}, 'types': ['schema:Book']},
    {'fields': {'name': ['schema:name']}, 'languages': ['de']},
])
def test_invalid_or_unsupported_configuration_is_not_silently_accepted(config):
    with pytest.raises(OldapErrorValue):
        jena_fulltext_fields(config, Context(name='TEXT_CONFIG_INVALID'))


@pytest.mark.parametrize('text', ['Laterne Stamm', 'Stamm Laterne', 'Later* Stamm', '  Laterne   Stamm  '])
def test_plain_words_require_every_word_without_requiring_a_phrase(text):
    """User words become explicit conjunctions; quotes retain phrase semantics."""
    context = Context(name='TEXT_WORDS')
    fields = jena_fulltext_fields({'fields': {'title': ['schema:name']}}, context)
    query = jena_fulltext_pattern('<urn:data>', [FTSearchFilter('title', text)], fields, 'score')
    assert query.count('<http://jena.apache.org/text#query>') == 2
    assert '?ft_0_0_score' in query and '?ft_0_1_score' in query
    phrase = jena_fulltext_pattern('<urn:data>', [FTSearchFilter('title', '"Laterne Stamm"')], fields, 'score')
    assert phrase.count('<http://jena.apache.org/text#query>') == 1


@pytest.mark.parametrize('text', ['Laterne OR Stamm', 'AND', '*Stamm', 'name:Stamm', '(Laterne)', 'Laterne +Stamm'])
def test_plain_words_do_not_enable_arbitrary_lucene_syntax(text):
    """Only the documented word/wildcard/phrase subset crosses the boundary."""
    fields = jena_fulltext_fields({'fields': {'title': ['schema:name']}}, Context(name='TEXT_WORDS_INVALID'))
    with pytest.raises(OldapErrorValue):
        jena_fulltext_pattern('<urn:data>', [FTSearchFilter('title', text)], fields, 'score')


def test_referenced_search_checks_each_hop_with_asserted_membership():
    """Private intermediates and orphan annotations cannot authorize text paths."""
    fields = jena_fulltext_fields({'fields': {'linked': ['schema:about', 'schema:about', 'schema:name']}}, Context(name='TEXT_PATH_ACCESS'))
    query = jena_fulltext_pattern('<urn:data>', [FTSearchFilter('linked', 'hidden')], fields, 'score', user_iri='<urn:user>')
    assert query.count('FILTER EXISTS') == 2
    assert query.count('<urn:user> oldap:hasRole') == 2
    assert '?ft_0_hop_0 oldap:attachedToRole' in query
    assert '?ft_0_target oldap:attachedToRole' in query
    assert query.count('rdf:reifies') == 2


@pytest.mark.parametrize('text', ['BMG-Stamm', 'BMG‐Stamm', 'BMG‑Stamm'])
def test_hyphenated_words_use_the_existing_and_join(text):
    """Ordinary hyphens must not be interpreted as Lucene negation."""
    fields = jena_fulltext_fields({'fields': {'title': ['schema:name']}}, Context(name='TEXT_HYPHENS'))
    query = jena_fulltext_pattern('<urn:data>', [FTSearchFilter('title', text)], fields, 'score')
    assert query.count('<http://jena.apache.org/text#query>') == 2


@pytest.mark.parametrize('text', ["L'art", "L’art", '"BMG-Stamm"', '"L’art français"'])
def test_apostrophes_and_quoted_hyphens_remain_one_index_lookup(text):
    fields = jena_fulltext_fields({'fields': {'title': ['schema:name']}}, Context(name='TEXT_PUNCTUATION'))
    query = jena_fulltext_pattern('<urn:data>', [FTSearchFilter('title', text)], fields, 'score')
    assert query.count('<http://jena.apache.org/text#query>') == 1


@pytest.mark.parametrize('text', ['-Stamm', '+Stamm', 'BMG-', "'art", 'BMG--Stamm', 'BMG-OR-Stamm'])
def test_ordinary_punctuation_does_not_enable_query_operators(text):
    fields = jena_fulltext_fields({'fields': {'title': ['schema:name']}}, Context(name='TEXT_PUNCTUATION_INVALID'))
    with pytest.raises(OldapErrorValue):
        jena_fulltext_pattern('<urn:data>', [FTSearchFilter('title', text)], fields, 'score')


def test_canonical_unicode_input_uses_identical_query_terms():
    fields = jena_fulltext_fields({'fields': {'title': ['schema:name']}}, Context(name='TEXT_CANONICAL'))
    def query(text):
        return jena_fulltext_pattern('<urn:data>', [FTSearchFilter('title', text)], fields, 'score')
    assert query('Zürich') == query('Zu\u0308rich')
    assert query('Zür*') == query('Zu\u0308r*')
