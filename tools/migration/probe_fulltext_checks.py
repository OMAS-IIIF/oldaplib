"""Exercise public OLDAP search through authenticated Fuseki and Jena Text."""
from oldaplib.src.objectfactory import ResourceInstance, FTSearchFilter, SearchFilter, CompOp
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.oldaperror import OldapErrorValue


def run_fulltext_checks(con, project, context, check):
    """Validate real filter adaptation, ACL/count/page, and transactional indexing."""
    private_lookup = con.query(context.sparql_context + """
SELECT ?s WHERE { (?s ?score) <http://jena.apache.org/text#query> (test:name 'ReceiptTextMarker') }
""")
    check('Raw text lookup cannot expose private receipt canary', private_lookup['results']['bindings'] == [])
    con.transaction_start()
    con.transaction_update(context.sparql_context + '''INSERT DATA {
GRAPH test:data {
 test:ftA a test:Cat ; test:keyword L-ProbeKeywords:Child ; test:name "Red fox", "Fox photo" ; test:subName "Forest animal" ; oldap:attachedToRole oldap:Reader .
 test:ftB a test:Cat ; test:name "Blue fox" ; test:subName "River animal" ; oldap:attachedToRole oldap:Reader .
 test:ftPrivate a test:Cat ; test:name "Fox fox fox" ; oldap:attachedToRole oldap:Stranger .
 test:ftOrphan a test:Cat ; test:name "Fox" .
 test:ftRestricted a test:Cat ; test:name "Fox" ; oldap:attachedToRole oldap:Reader .
 <urn:ftA> rdf:reifies <<( test:ftA oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
 <urn:ftB> rdf:reifies <<( test:ftB oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
 <urn:ftPrivate> rdf:reifies <<( test:ftPrivate oldap:attachedToRole oldap:Stranger )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
 <urn:ftOrphan> rdf:reifies <<( test:ftOrphan oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
 <urn:ftRestricted> rdf:reifies <<( test:ftRestricted oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_RESTRICTED .
}
GRAPH <urn:other-project:data> { test:ftA test:name "OtherGraphMarker" . }
}''')
    con.transaction_commit()

    def search(filters, **kwargs):
        return ResourceInstance.search(con, project, ftfilter=filters, **{'resClass': 'test:Cat', **kwargs})

    def matches(label, expected, filters, **kwargs):
        rows = search(filters, **kwargs)
        check(label, {str(row['iri']) for row in rows} == set(expected)
              and int(search(filters, countOnly=True, **kwargs)) == len(expected))

    fox = [FTSearchFilter('name', 'fox')]
    matches('Public full-text search and count enforce current RDF 1.2 ACL', ['test:ftA', 'test:ftB'], fox)
    matches('Full-text-only search works without a class filter', ['test:ftA', 'test:ftB'], fox, resClass=None)
    matches('Full-text search combines with superclass filtering', ['test:ftA', 'test:ftB'], fox, resClass='test:Mammal')
    matches('Full-text phrase is safely serialized', ['test:ftA'], [FTSearchFilter('name', '"red fox"')])
    matches('Full-text wildcard matches expected resource', ['test:ftB'], [FTSearchFilter('name', 'blu*')])
    # Ordinary words now use AND, including across literal values. These native
    # checks protect the agreed semantics when changing the query join order.
    matches('Full-text ordinary words ignore order', ['test:ftA'], [FTSearchFilter('name', 'fox red')])
    matches('Full-text ordinary words join separate values', ['test:ftA'], [FTSearchFilter('name', 'red photo')])
    matches('Full-text ordinary words require every word', [], [FTSearchFilter('name', 'red absentmarker')])
    matches('Full-text phrase cannot span separate values', [], [FTSearchFilter('name', '"red photo"')])
    matches('Full-text AND joins different fields on the resource', ['test:ftA'],
            [FTSearchFilter('name', 'fox'), 'AND', FTSearchFilter('description', 'forest')])
    matches('Full-text AND joins different values of one field', ['test:ftA'],
            [FTSearchFilter('name', 'red'), 'AND', FTSearchFilter('name', 'photo')])
    matches('Full-text OR does not require both fields', ['test:ftA', 'test:ftB'],
            [FTSearchFilter('name', 'red'), 'OR', FTSearchFilter('description', 'river')])
    matches('Full-text AND binds more tightly than OR', ['test:ftA', 'test:ftB'],
            [FTSearchFilter('name', 'red'), 'OR', FTSearchFilter('name', 'blue'), 'AND', FTSearchFilter('description', 'river')])
    matches('Full-text repeated OR branch does not inflate count', ['test:ftA'],
            [FTSearchFilter('name', 'red'), 'OR', FTSearchFilter('name', 'red')])
    matches('Full-text combines with ordinary property filter', ['test:ftA'], fox,
            filter=[SearchFilter('test:subName', CompOp.EQ, Xsd_string('Forest animal'))])
    from oldaplib.src.objectfactory import HLSearchFilter
    from oldaplib.src.xsd.listnode import HListNodeRef
    matches('Full-text combines with real hierarchical-list filter', ['test:ftA'], fox,
            hlfilter=[HLSearchFilter('test:keyword', HListNodeRef('ProbeKeywords', 'Parent'))])
    matches('Full-text cannot match text from another project', [], [FTSearchFilter('name', 'OtherGraphMarker')])
    rows = search(fox, includeProperties={Xsd_QName('test:name')})
    check('Full-text returns numeric scores and complete multivalue projection',
          all(float(row['score']) >= 0 for row in rows)
          and {str(v) for row in rows if str(row['iri']) == 'test:ftA' for v in row['test:name']} == {'Red fox', 'Fox photo'})
    check('Full-text paging preserves score order after permission filtering',
          [row['iri'] for row in rows] == [search(fox, limit=1, offset=i)[0]['iri'] for i in range(2)]
          and int(search(fox, countOnly=True, limit=1, offset=1)) == 2)
    for filters in ([FTSearchFilter('missing', 'fox')], [FTSearchFilter('name', 'red AND photo')],
                    [FTSearchFilter('name', '*fox')],
                    [FTSearchFilter('name', 'fox'), 'NOT', FTSearchFilter('name', 'blue')],
                    [FTSearchFilter('name', 'fox'), 'OR']):
        from unittest.mock import patch
        with patch.object(con, 'query', wraps=con.query) as query:
            try:
                search(filters)
            except OldapErrorValue:
                check('Unsupported full-text input rejected before HTTP: ' + str(filters), query.call_count == 0)
            else:
                raise AssertionError('Unsupported full-text silently accepted')
    con.transaction_start()
    con.transaction_update(context.sparql_context + 'INSERT DATA { GRAPH test:data { test:ftA test:name "AbortedIndexMarker" } }')
    con.transaction_abort()
    matches('Full-text HTTP rollback leaves no index hit', [], [FTSearchFilter('name', 'AbortedIndexMarker')])
    con.transaction_start()
    con.transaction_update(context.sparql_context + '''DELETE DATA { GRAPH test:data { test:ftA test:name "Red fox" } };
INSERT DATA { GRAPH test:data { test:ftA test:name "Golden hare" } }''')
    con.transaction_commit()
    matches('Full-text HTTP commit removes replaced text', [], [FTSearchFilter('name', 'red')])
    matches('Full-text HTTP commit indexes replacement text', ['test:ftA'], [FTSearchFilter('name', 'golden')])
    con.transaction_start()
    con.transaction_update(context.sparql_context + 'DELETE DATA { GRAPH test:data { test:ftB test:name "Blue fox" } }')
    con.transaction_commit()
    matches('Full-text HTTP deletion removes index hit', [], [FTSearchFilter('name', 'blue')])
