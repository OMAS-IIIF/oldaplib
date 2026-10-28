"""Real list/node loading and hierarchical search on the owned Fuseki fixture."""
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.objectfactory import ResourceInstance, HLSearchFilter, LogicOp, SortBy, SearchFilter, CompOp
from oldaplib.src.xsd.listnode import HListNodeRef, HListNode
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound


def run_hlist_checks(con, project, context, check):
    """Seed two real lists and check subtree/boolean/access/count semantics.

    List writes are fixture SPARQL, not a claim of migrated list mutation APIs.
    All reads use actual OldapList/OldapListNode and ResourceInstance methods.
    """
    keywords = OldapList(con=con, project=project, oldapListId='ProbeKeywords')
    other = OldapList(con=con, project=project, oldapListId='ProbeOther')
    metadata = '''dcterms:creator <https://example.org/callback/actor> ;
        dcterms:contributor <https://example.org/callback/actor> ;
        dcterms:created "2024-01-01T00:00:00Z"^^xsd:dateTime ;
        dcterms:modified "2024-01-01T00:00:00Z"^^xsd:dateTime'''
    triples = [f'{keywords.iri.toRdf} a oldap:OldapList ; skos:prefLabel "Keywords"@en ; {metadata} .',
               f'{other.iri.toRdf} a oldap:OldapList ; skos:prefLabel "Other"@en ; {metadata} .']
    for name, left, right, parent in [('Root', 1, 10, None), ('Parent', 2, 7, 'Root'),
                                     ('Child', 3, 4, 'Parent'), ('Leaf', 5, 6, 'Parent'), ('Sibling', 8, 9, 'Root')]:
        broader = f'; skos:broader L-ProbeKeywords:{parent}' if parent else ''
        triples.append(f'L-ProbeKeywords:{name} a test:ProbeKeywordsNode ; skos:inScheme test:ProbeKeywords ; '
                       f'oldap:leftIndex {left} ; oldap:rightIndex {right} ; skos:prefLabel "{name}"@en ; {metadata} {broader} .')
    triples.append(f'L-ProbeOther:Child a test:ProbeOtherNode ; skos:inScheme test:ProbeOther ; oldap:leftIndex 3 ; oldap:rightIndex 4 ; {metadata} .')
    resources = []
    for name, tags, role, permission in [
        ('hlParent', 'L-ProbeKeywords:Parent', 'Reader', 'DATA_VIEW'),
        ('hlChild', 'L-ProbeKeywords:Child', 'Reader', 'DATA_VIEW'),
        ('hlSibling', 'L-ProbeKeywords:Sibling', 'Reader', 'DATA_VIEW'),
        ('hlMulti', 'L-ProbeKeywords:Child, L-ProbeKeywords:Sibling', 'Reader', 'DATA_VIEW'),
        ('hlForeign', 'L-ProbeOther:Child', 'Reader', 'DATA_VIEW'),
        ('hlDenied', 'L-ProbeKeywords:Child', 'Stranger', 'DATA_VIEW'),
        ('hlRestricted', 'L-ProbeKeywords:Child', 'Reader', 'DATA_RESTRICTED'),
        ('hlOrphan', 'L-ProbeKeywords:Child', None, 'DATA_VIEW'),
        ('hlAlternate', None, 'Reader', 'DATA_VIEW'),
        ('hlOutside', None, 'Reader', 'DATA_VIEW'),
    ]:
        resources.append(f'test:{name} a test:Cat ; test:name "{name}" .')
        if tags:
            resources.append(f'test:{name} test:keyword {tags} .')
        if role:
            resources.append(f'test:{name} oldap:attachedToRole oldap:{role} .')
        resources.append(f'<urn:grant:{name}> rdf:reifies <<( test:{name} oldap:attachedToRole oldap:{role or "Reader"} )>> ; oldap:hasDataPermission oldap:{permission} .')
    resources.append('test:hlAlternate test:alternateKeyword L-ProbeKeywords:Child .')
    con.transaction_start()
    con.transaction_update(context.sparql_context + 'INSERT DATA { GRAPH test:lists {\n' + '\n'.join(triples)
                           + '} GRAPH test:data {\n' + '\n'.join(resources)
                           + '} GRAPH <urn:other-project:data> { test:hlOutside test:keyword L-ProbeKeywords:Child . } }')
    con.transaction_commit()
    loaded = OldapList.read(con, project, 'ProbeKeywords')
    check('Real list loader reconstructs root and child hierarchy',
          len(loaded.nodes) == 1 and str(loaded.nodes[0].oldapListNodeId) == 'Root'
          and {str(node.oldapListNodeId) for node in loaded.nodes[0].nodes} == {'Parent', 'Sibling'})
    parent = OldapListNode.read(con=con, **loaded.info, oldapListNodeId='Parent')
    check('Real node loader reads subtree bounds', int(parent.leftIndex) == 2 and int(parent.rightIndex) == 7)

    def hfilter(node, prop='test:keyword', list_id='ProbeKeywords'):
        return HLSearchFilter(prop, HListNodeRef(list_id, node))

    def search(filters, **kwargs):
        return ResourceInstance.search(con, project, hlfilter=filters, **{'resClass': 'test:Cat', **kwargs})

    def matches(label, expected, filters, **kwargs):
        rows = search(filters, **kwargs)
        check(label, {str(row['iri']) for row in rows} == set(expected)
              and int(search(filters, countOnly=True, **kwargs)) == len(expected))

    descendants = ['test:hlParent', 'test:hlChild', 'test:hlMulti']
    matches('Subtree includes selected node and descendants but excludes sibling and foreign list', descendants, [hfilter('Parent')])
    matches('List-only search needs no explicit class filter', descendants, [hfilter('Parent')], resClass=None)
    matches('Leaf filter matches exact leaf membership', ['test:hlChild', 'test:hlMulti'], [hfilter('Child')])
    matches('Root filter includes all readable tree members exactly once', descendants + ['test:hlSibling'], [hfilter('Root')])
    matches('Separate list with overlapping indices remains isolated', ['test:hlForeign'], [hfilter('Child', list_id='ProbeOther')])
    matches('Legacy list QName input resolves the same subtree', descendants,
            [HLSearchFilter('test:keyword', HListNode('L-ProbeKeywords:Parent'))])
    matches('List OR accepts a match when the other property is absent', descendants + ['test:hlAlternate'],
            [hfilter('Parent'), LogicOp.OR, hfilter('Parent', 'test:alternateKeyword')])
    matches('List AND can match different values of the same property', ['test:hlMulti'],
            [hfilter('Parent'), LogicOp.AND, hfilter('Sibling')])
    matches('List OR across lists keeps their node bindings independent', descendants + ['test:hlForeign'],
            [hfilter('Parent'), LogicOp.OR, hfilter('Child', list_id='ProbeOther')])
    matches('Parenthesized list expressions preserve boolean grouping', ['test:hlMulti'],
            [LogicOp.LEFT_, hfilter('Parent'), LogicOp.OR, hfilter('Parent', 'test:alternateKeyword'), LogicOp._RIGHT,
             LogicOp.AND, hfilter('Sibling')])
    matches('List filter combines with ordinary property filter', ['test:hlChild'], [hfilter('Parent')],
            filter=[SearchFilter('test:name', CompOp.EQ, Xsd_string('hlChild'))])
    check('List pagination selects distinct resources and count ignores the page',
          [str(row['iri']) for row in search([hfilter('Root')], sortBy=[SortBy('test:name')], limit=1, offset=1)] == ['test:hlMulti']
          and int(search([hfilter('Root')], countOnly=True, limit=1, offset=1)) == 4)
    for list_id, node in [('MissingList', 'Parent'), ('ProbeKeywords', 'MissingNode')]:
        try:
            search([hfilter(node, list_id=list_id)])
        except OldapErrorNotFound:
            check('Missing list/node raises NotFound: ' + list_id + '/' + node, True)
        else:
            raise AssertionError('Missing list/node was accepted')
