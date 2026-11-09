"""Characterize language behavior through the real Jena text/search boundary.

All text is synthetic and belongs to the disposable native rehearsal. This is
an executable description of current behavior, not a choice of future stemming,
accent folding or language policy. Stored RDF and production indexes are untouched.
"""
import json
from oldaplib.src.objectfactory import ResourceInstance, FTSearchFilter
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.xsd.xsd_string import Xsd_string


def run_fulltext_language(con, project, context, check, output):
    """Insert owned text, compare language cases, and remove the fixture.

    Args:
        con: Native rehearsal connection with no active transaction.
        project: Existing test project with the configured name text field.
        context: Prefix context for the disposable dataset.
        check: Runner assertion callback.
        output: Private directory for the language result matrix.

    Side effects:
        Commits fixture text to exercise the actual index, then deletes exactly
        those triples in a finally block. Writes observations before assertions.
    """
    texts = {
        'title': ('Laterne BMG Stamm', 'de'),
        'plural': ('Laternen', 'de'),
        'umlaut': ('Zürich München Straße', 'de'),
        'ascii': ('Zurich Munchen Strasse', 'de'),
        'compound': ('Fasnachtslaterne', 'de'),
        'hyphen': ('BMG-Stamm', 'de'),
        'phrase': ('Basler Fasnacht', 'de'),
        'reverse': ('Fasnacht Basler', 'de'),
        'french': ('École française', 'fr'),
        'apostrophe': ("L'art", 'fr'),
        'decomposed': ('Zu\u0308rich', 'de'),
        'stopword': ('Die Laterne', 'de'),
        'private': ('Sprachprivat', 'de'),
    }
    triples = []
    for name, (text, language) in texts.items():
        subject = f'test:language_{name}'
        role = 'oldap:Stranger' if name == 'private' else 'oldap:Reader'
        triples.append(f'{subject} a test:Cat ; test:name {Xsd_string(text, language).toRdf} ; oldap:attachedToRole {role} .')
        triples.append(f'<urn:language-grant:{name}> rdf:reifies <<( {subject} oldap:attachedToRole {role} )>> ; oldap:hasDataPermission oldap:DATA_VIEW .')
    data = 'GRAPH test:data { ' + '\n'.join(triples) + ' }'

    def update(operation):
        con.transaction_start()
        try:
            con.transaction_update(context.sparql_context + operation + ' DATA { ' + data + ' }')
            con.transaction_commit()
        except Exception:
            if con.in_transaction():
                con.transaction_abort()
            raise

    cases = [
        ('lowercase', 'laterne'), ('uppercase', 'LATERNE'),
        ('word_order', 'Stamm Laterne'), ('singular', 'Laterne'),
        ('plural', 'Laternen'), ('prefix', 'Latern*'),
        ('compound_exact', 'Fasnachtslaterne'), ('compound_part', 'Fasnachts'),
        ('umlaut', 'Zürich'), ('ascii', 'Zurich'), ('transliteration', 'Zuerich'),
        ('eszett', 'Straße'), ('double_s', 'Strasse'),
        ('accent', 'école'), ('accentless', 'ecole'),
        ('french_uppercase', 'ÉCOLE'), ('french_and', 'française école'),
        ('hyphen_input', 'BMG-Stamm'), ('hyphen_as_words', 'BMG Stamm'),
        ('apostrophe_input', "L'art"), ('apostrophe_suffix', 'art'),
        ('phrase', '"Basler Fasnacht"'), ('phrase_reverse', '"Fasnacht Basler"'),
        ('phrase_over_hyphen', '"BMG Stamm"'),
        ('stopword', 'die'), ('canonical_decomposed_input', 'Zu\u0308rich'),
        ('umlaut_prefix', 'Zür*'), ('ascii_prefix', 'Zur*'),
        ('eszett_prefix', 'Straß*'), ('ascii_eszett_prefix', 'Strass*'),
        ('accent_prefix', 'éco*'), ('ascii_accent_prefix', 'eco*'),
        ('folded_phrase', '"zurich munchen strasse"'),
        ('private', 'Sprachprivat'),
    ]
    observations = []
    update('INSERT')
    try:
        for name, query in cases:
            try:
                rows = ResourceInstance.search(con, project, resClass='test:Cat',
                    ftfilter=[FTSearchFilter('name', query)], limit=1000)
                hits = sorted(str(row['iri']).split('language_', 1)[1]
                    for row in rows if 'language_' in str(row['iri']))
                observations.append({'case': name, 'query': query, 'status': 'accepted', 'matches': hits})
            except OldapErrorValue:
                observations.append({'case': name, 'query': query, 'status': 'rejected', 'matches': []})
        (output / 'fulltext-language.json').write_text(json.dumps({
            'fixture': texts, 'observations': observations}, ensure_ascii=False, indent=2) + '\n')
        by_name = {row['case']: row for row in observations}
        check('Language search ignores letter case', by_name['lowercase']['matches'] == by_name['uppercase']['matches'] == ['stopword', 'title'])
        check('Language words retain order-independent AND', by_name['word_order']['matches'] == ['title'])
        check('Language phrases retain their word order', by_name['phrase']['matches'] == ['phrase'] and by_name['phrase_reverse']['matches'] == ['reverse'])
        check('Language fixture does not bypass private resource grants', by_name['private']['matches'] == [])
        check('Language hyphens follow the same AND semantics as spaces', by_name['hyphen_input']['matches'] == by_name['hyphen_as_words']['matches'] == ['hyphen', 'title'])
        check('Language apostrophes can be searched literally', by_name['apostrophe_input']['matches'] == ['apostrophe'])
        equivalent = ['ascii', 'decomposed', 'umlaut']
        check('Language umlaut and canonical Unicode variants share hits', all(
            by_name[name]['matches'] == equivalent for name in
            ['umlaut', 'ascii', 'canonical_decomposed_input', 'umlaut_prefix', 'ascii_prefix']))
        check('Language sharp s and ss share exact and prefix hits', all(
            by_name[name]['matches'] == ['ascii', 'umlaut'] for name in
            ['eszett', 'double_s', 'eszett_prefix', 'ascii_eszett_prefix']))
        check('Language accents share exact and prefix hits', all(
            by_name[name]['matches'] == ['french'] for name in
            ['accent', 'accentless', 'french_uppercase', 'accent_prefix', 'ascii_accent_prefix']))
        check('Language folded phrases preserve token positions', by_name['folded_phrase']['matches'] == ['ascii', 'umlaut'])
        check('Language folding does not introduce stemming or compound splitting',
            by_name['singular']['matches'] == ['stopword', 'title'] and
            by_name['plural']['matches'] == ['plural'] and by_name['compound_part']['matches'] == [])
        check('Language folding does not imply German ue transliteration', by_name['transliteration']['matches'] == [])

    finally:
        update('DELETE')
