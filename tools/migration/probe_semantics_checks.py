"""Step 2 semantics acceptance inside the owned model-read Fuseki fixture.

All extra triples live in a transaction which is aborted before returning.
This exercises actual query builders and permissions, without shared services.
"""
from oldaplib.src.objectfactory import ResourceInstance, SearchFilter, CompOp, SortBy
from oldaplib.src.helpers.jena_entailment import ASSERTED_ONLY, property_pattern
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string


def run_semantics_checks(con, project, context, factory, check):
    """Verify hierarchy filters, modeled hydration, security and rollback."""
    def search(**kwargs):
        return ResourceInstance.search(con, project, **{'resClass': 'test:Cat', **kwargs})

    def matches(label, expected, **kwargs):
        rows = search(**kwargs)
        check(label, {str(row['iri']) for row in rows} == set(expected)
              and int(search(countOnly=True, **kwargs)) == len(expected))

    con.transaction_start()
    try:
        con.transaction_update(context.sparql_context + '''INSERT DATA {
            GRAPH test:onto {
                test:Cat owl:equivalentClass test:EquivalentOnly .
                test:EquivalentOnly owl:equivalentClass test:Cat .
                test:subName rdfs:subPropertyOf test:middleName, test:otherName .
                test:middleName rdfs:subPropertyOf test:name .
                test:otherName rdfs:subPropertyOf test:name .
                test:name rdfs:subPropertyOf test:middleName .
                test:name owl:equivalentProperty test:equivalentName .
                test:equivalentName owl:equivalentProperty test:name .
                test:fakeRole rdfs:subPropertyOf oldap:attachedToRole .
            }
            GRAPH test:data {
                test:denied test:fakeRole oldap:Reader .
                <urn:fake-membership-grant> rdf:reifies <<( test:denied oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
            }
            GRAPH <urn:unselected:onto> { test:name rdfs:subPropertyOf test:foreignName . }
        }''')
        matches('Step2 exact class remains searchable', ['test:cat', 'test:secondCat'])
        matches('Step2 superclass remains searchable', ['test:cat', 'test:secondCat'], resClass='test:Mammal')
        matches('Step2 equivalence-only class does not match', [], resClass='test:EquivalentOnly')
        wanted = [SearchFilter('test:name', CompOp.EQ, Xsd_string('Hauskatze'))]
        matches('Step2 multilevel diamond and cycle match distinct roots', ['test:cat'], filter=wanted)
        matches('Step2 NOT_EXISTS uses effective subproperty values', [],
                filter=[SearchFilter('test:name', CompOp.NOT_EXISTS, Xsd_QName('test:name'))])
        matches('Step2 property equivalence is ignored', [],
                filter=[SearchFilter('test:equivalentName', CompOp.EQ, Xsd_string('Minka'))])
        matches('Step2 foreign schema is ignored', [],
                filter=[SearchFilter('test:foreignName', CompOp.EQ, Xsd_string('Minka'))])
        rows = search(filter=wanted, includeProperties={Xsd_QName('test:name')})
        check('Step2 search projection remains asserted-only',
              {str(v) for row in rows for v in row['test:name']} == {'Minka'})
        check('Step2 hierarchy sorting and paging preserve counts',
              len(search(sortBy=[SortBy('test:name', 'asc')], limit=1)) == 1
              and int(search(countOnly=True)) == 2)
        result = factory.read_data('test:cat')
        check('Step2 single hydration resolves modeled superproperty',
              {str(v) for v in result.data['test:name']} == {'Minka', 'Hauskatze'})
        check('Step2 unmodeled superproperty does not appear in hydration',
              'test:middleName' not in result.data and 'test:otherName' not in result.data)
        check('Step2 single hydration omits equivalence-only types',
              'test:EquivalentOnly' not in {str(v) for v in result.data['rdf:type']})
        summaries = factory.read_summaries(['test:cat', 'test:denied'], include_properties=['test:name'])
        check('Step2 summary resolves modeled field without admitting fake grants',
              set(summaries) == {Iri('test:cat')}
              and {str(v) for v in summaries[Iri('test:cat')].data['test:name']} == {'Minka', 'Hauskatze'})
        # Use the real helper with a variable predicate to exercise guards that
        # cannot be decided in Python at query-build time.
        for index, protected in enumerate(ASSERTED_ONLY):
            con.transaction_update(context.sparql_context + f'''INSERT DATA {{
                GRAPH test:onto {{ test:fake{index} rdfs:subPropertyOf {protected} .
                    {protected} rdfs:subPropertyOf test:leak{index} . }}
                GRAPH test:data {{ test:securityProbe test:fake{index} test:secret . }}
            }}''')
        pattern = property_pattern('test', 'test:securityProbe', '?predicate', '?value',
                                   alias='security', expand_subproperties=True)
        rows = con.transaction_query(context.sparql_context +
            'SELECT DISTINCT ?predicate FROM test:onto FROM NAMED test:data WHERE { ' + pattern + ' }')
        found = {row['predicate']['value'] for row in rows['results']['bindings']}
        check('Step2 all protected endpoints and intermediate bridges are blocked in native Jena',
              found == {f'http://oldap.org/test#fake{i}' for i in range(len(ASSERTED_ONLY))})
    finally:
        con.transaction_abort()
    matches('Step2 abort restores prior property semantics', [],
            filter=[SearchFilter('test:name', CompOp.EQ, Xsd_string('Hauskatze'))])
