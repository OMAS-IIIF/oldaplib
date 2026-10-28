"""Structured-search acceptance checks for the owned model-read Fuseki fixture.

Invoked by probe_model_reads while its private dataset and real model are open.
No shared services are used. Fixture additions happen only after batch checks.
"""
from oldaplib.src.objectfactory import (
    ResourceInstance, SearchFilter, LinkedResourceSearchFilter, CompOp, LogicOp,
    SortBy, FTSearchFilter,
)
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.dating import Dating
from oldaplib.src.xsd.xsd_integer import Xsd_integer


def run_search_checks(con, project, context, check):
    """Check result/count agreement, graph scope, joins, ordering and pagination."""
    def search(**kwargs):
        return ResourceInstance.search(con, project, **{'resClass': 'test:Cat', **kwargs})

    def ids(rows):
        return [str(row['iri']) for row in rows]

    def matches(label, expected, **kwargs):
        check(label, set(ids(search(**kwargs))) == set(expected)
              and int(search(countOnly=True, **kwargs)) == len(expected))

    matches('Search and count omit denied/orphan/restricted/creator-only resources', ['test:cat', 'test:secondCat'])
    matches('Superclass search follows project ontology while keeping asserted classes',
            ['test:cat', 'test:secondCat'], resClass='test:Mammal')
    check('Superclass search returns concrete asserted result classes',
          all(str(row['resclass']) == 'test:Cat' for row in search(resClass='test:Mammal')))
    matches('Equality filter matches only a bound property', ['test:cat'],
            filter=[SearchFilter('test:subName', CompOp.EQ, Xsd_string('Hauskatze'))])
    matches('OR retains matches when another property is missing', ['test:cat', 'test:secondCat'],
            filter=[SearchFilter('test:subName', CompOp.EQ, Xsd_string('Hauskatze')), LogicOp.OR,
                    SearchFilter('test:name', CompOp.EQ, Xsd_string('Zora'))])
    matches('NOT_EXISTS checks absence in project data', ['test:secondCat'],
            filter=[SearchFilter('test:subName', CompOp.NOT_EXISTS, Xsd_QName('test:subName'))])
    matches('Other-project values cannot match a filter', [],
            filter=[SearchFilter('test:name', CompOp.EQ, Xsd_string('must-not-leak'))])
    matches('A property-only search retains access control', ['test:cat'], resClass=None,
            filter=[SearchFilter('test:name', CompOp.CONTAINS, Xsd_string('INK'))])
    for op, value in ((CompOp.STRSTARTS, 'Min'), (CompOp.STRENDS, 'ka'), (CompOp.REGEXP, '^m.*a$')):
        matches('Text operator ' + op.value + ' preserves result/count agreement', ['test:cat'],
                filter=[SearchFilter('test:name', op, Xsd_string(value))])
    matches('AND combines direct-property constraints', ['test:cat'],
            filter=[SearchFilter('test:name', CompOp.EQ, Xsd_string('Minka')), LogicOp.AND,
                    SearchFilter('test:subName', CompOp.EQ, Xsd_string('Hauskatze'))])
    check('Default pagination has a stable outer IRI order',
          ids(search(limit=1)) == ['test:cat'] and ids(search(limit=1, offset=1)) == ['test:secondCat'])
    check('Sorted pagination preserves order and total count',
          ids(search(sortBy=[SortBy('test:name', 'desc')], limit=1)) == ['test:secondCat']
          and ids(search(sortBy=[SortBy('test:name', 'desc')], limit=1, offset=1)) == ['test:cat']
          and int(search(countOnly=True, limit=1, offset=1)) == 2)
    projected = search(includeProperties={Xsd_QName('test:name')})
    check('Projected fields exclude other-project values',
          {str(value) for row in projected for value in row['test:name']} == {'Minka', 'Zora'})

    con.transaction_start()
    con.transaction_update(context.sparql_context + '''INSERT DATA {
GRAPH test:data {
    test:cat test:friend test:secondCat ; test:privateFriend test:denied ; test:writtenAt <urn:search-date> .
    test:secondCat test:name "Zora alias" ; test:age 7 .
    test:cat test:age 3 .
    <urn:duplicate-search-grant> rdf:reifies <<( test:cat oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
    <urn:search-date> oldap:normalizedStart "1200-01-01"^^xsd:date ; oldap:normalizedEnd "1299-12-31"^^xsd:date .
}
GRAPH test:onto { test:Cat rdfs:subClassOf shared:ProbeParent . }
GRAPH shared:onto { shared:ProbeParent rdfs:subClassOf shared:ProbeAncestor . }
GRAPH <urn:other-project:data> { test:secondCat test:subName "Outside" . }
}''')
    con.transaction_commit()
    matches('Superclass paths cross project and shared schema graphs', ['test:cat', 'test:secondCat'],
            resClass='shared:ProbeAncestor')
    for op, expected in ((CompOp.EQ, ['test:cat']), (CompOp.NE, ['test:secondCat']),
                         (CompOp.GT, ['test:secondCat']), (CompOp.GE, ['test:cat', 'test:secondCat']),
                         (CompOp.LT, []), (CompOp.LE, ['test:cat'])):
        matches('Numeric operator ' + op.value + ' preserves result/count agreement', expected,
                filter=[SearchFilter('test:age', op, Xsd_integer(3))])
    matches('Duplicate grants and multiple values do not inflate counts', ['test:cat', 'test:secondCat'])
    check('Pagination selects resources before expanding multivalued properties',
          len(search(sortBy=[SortBy('test:name', 'desc')], limit=1)) == 1
          and {str(v) for v in search(sortBy=[SortBy('test:name', 'desc')], limit=1)[0]['test:name']} == {'Zora', 'Zora alias'})
    matches('Linked permission and superclass filters match a readable target', ['test:cat'],
            filter=[LinkedResourceSearchFilter('test:friend', 'test:name', CompOp.EQ, Xsd_string('Zora'),
                                              linkedClass='test:Mammal', checkLinkedPermissions=True)])
    matches('Linked permission filter rejects a denied target', [],
            filter=[LinkedResourceSearchFilter('test:privateFriend', 'test:name', CompOp.EQ, Xsd_string('Private'),
                                              checkLinkedPermissions=True)])
    matches('Explicitly unchecked linked permissions preserve existing caller policy', ['test:cat'],
            filter=[LinkedResourceSearchFilter('test:privateFriend', 'test:name', CompOp.EQ, Xsd_string('Private'))])
    matches('Linked NOT_EXISTS requires an existing readable target', ['test:cat'],
            filter=[LinkedResourceSearchFilter('test:friend', 'test:subName', CompOp.NOT_EXISTS, Xsd_string(''),
                                              checkLinkedPermissions=True)])
    matches('Linked NOT_EXISTS cannot treat denied targets as readable missing properties', [],
            filter=[LinkedResourceSearchFilter('test:privateFriend', 'test:subName', CompOp.NOT_EXISTS, Xsd_string(''),
                                              checkLinkedPermissions=True)])
    matches('Denied linked absence cannot contaminate an OR branch', ['test:secondCat'],
            filter=[LinkedResourceSearchFilter('test:privateFriend', 'test:subName', CompOp.NOT_EXISTS,
                                              Xsd_string(''), checkLinkedPermissions=True), LogicOp.OR,
                    SearchFilter('test:name', CompOp.EQ, Xsd_string('Zora'))])
    matches('Dating overlap uses scoped normalized dates', ['test:cat'],
            filter=[SearchFilter('test:writtenAt', CompOp.OVERLAPS, Dating('1250'))])
    check('Dating sort puts missing dates last',
          ids(search(sortBy=[SortBy('test:writtenAt', kind='dating')])) == ['test:cat', 'test:secondCat'])
    try:
        search(ftfilter=[FTSearchFilter('name', 'Minka')])
    except OldapErrorValue as error:
        check('Unimplemented Jena full-text reports a clear error', 'not implemented' in str(error))
    else:
        raise AssertionError('Unsupported full-text silently accepted')
