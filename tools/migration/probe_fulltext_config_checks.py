"""Verify YAML-driven fields, project separation and live property-chain joins."""
from oldaplib.src.objectfactory import ResourceInstance, FTSearchFilter
from oldaplib.src.project import Project
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.oldaperror import OldapErrorValue


def run_fulltext_config_checks(con, project, context, check):
    """Use configurations from fulltext-fixture.yaml without code field mapping."""
    context['other'] = NamespaceIRI('http://example.org/other#')
    con.transaction_start()
    con.transaction_update(context.sparql_context + '''INSERT DATA {
GRAPH oldap:admin {
 other:Project a oldap:Project ; oldap:projectShortName "other"^^xsd:NCName ;
 oldap:namespaceIri <http://example.org/other#> ; oldap:projectStart "2024-01-01"^^xsd:date .
}
GRAPH test:data {
 test:chainA a test:Cat ; test:friend test:target1, test:target2 ; oldap:attachedToRole oldap:Reader .
 test:chainB a test:Cat ; test:friend test:target1 ; oldap:attachedToRole oldap:Reader .
 test:chainDenied a test:Cat ; test:friend test:target1 ; oldap:attachedToRole oldap:Stranger .
 test:chainCross a test:Cat ; oldap:attachedToRole oldap:Reader .
 test:target1 test:name "Chainword red" ; test:subName "Forest chain" ; test:friend test:target2 .
 test:target2 test:name "Chainword blue" ; test:subName "River chain" .
 <urn:chainA> rdf:reifies <<( test:chainA oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
 <urn:chainB> rdf:reifies <<( test:chainB oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
 <urn:chainCross> rdf:reifies <<( test:chainCross oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
 <urn:chainDenied> rdf:reifies <<( test:chainDenied oldap:attachedToRole oldap:Stranger )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
}
GRAPH other:data {
 other:item a test:Cat ; other:headline "Otherprojectword" ; oldap:attachedToRole oldap:Reader .
 test:chainCross test:friend test:target1 .
 test:target1 test:name "Forbiddenotherword" .
 <urn:other-grant> rdf:reifies <<( other:item oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
}
}''')
    con.transaction_commit()
    other = Project.read(con, 'other')

    def matches(label, expected, filters, selected=project):
        rows = ResourceInstance.search(con, selected, resClass='test:Cat', ftfilter=filters)
        total = ResourceInstance.search(con, selected, resClass='test:Cat', ftfilter=filters, countOnly=True)
        check(label, {str(row['iri']) for row in rows} == set(expected) and int(total) == len(expected))

    chain = [FTSearchFilter('representedName', 'chainword')]
    matches('Configured chain returns source resources and counts distinct roots', ['test:chainA', 'test:chainB'], chain)
    matches('Configured chain AND can use different target values', ['test:chainA'],
            [FTSearchFilter('representedName', 'red'), 'AND', FTSearchFilter('representedName', 'blue')])
    matches('Different configured chain fields remain independent', ['test:chainA', 'test:chainB'],
            [FTSearchFilter('representedName', 'red'), 'AND', FTSearchFilter('representedDescription', 'forest')])
    matches('Configured two-link path reaches terminal indexed text', ['test:chainA', 'test:chainB'],
            [FTSearchFilter('twoHopName', 'blue')])
    matches('Another project gets its own configured field without code mapping', ['other:item'],
            [FTSearchFilter('headline', 'otherprojectword')], other)
    matches('Same field name resolves differently in each project', ['other:item'],
            [FTSearchFilter('name', 'otherprojectword')], other)
    matches('First project cannot search second project text', [], [FTSearchFilter('name', 'otherprojectword')])
    matches('Configured chain cannot read terminal text from another graph', [],
            [FTSearchFilter('representedName', 'forbiddenotherword')])
    try:
        ResourceInstance.search(con, project, ftfilter=[FTSearchFilter('headline', 'otherprojectword')])
    except OldapErrorValue:
        check('Project rejects field configured only in another project', True)
    else:
        raise AssertionError('Cross-project field accepted')

    # Link changes need no copied search text or custom invalidation registry:
    # the path join reads current RDF, and the terminal text is already indexed.
    con.transaction_start()
    con.transaction_update(context.sparql_context + 'DELETE DATA { GRAPH test:data { test:chainB test:friend test:target1 } }')
    con.transaction_abort()
    matches('Aborted chain unlink preserves both results', ['test:chainA', 'test:chainB'], chain)
    con.transaction_start()
    con.transaction_update(context.sparql_context + 'DELETE DATA { GRAPH test:data { test:chainB test:friend test:target1 } }')
    con.transaction_commit()
    matches('Committed chain unlink immediately removes source hit', ['test:chainA'], chain)
    con.transaction_start()
    con.transaction_update(context.sparql_context + '''DELETE DATA { GRAPH test:data { test:target1 test:name "Chainword red" } };
INSERT DATA { GRAPH test:data { test:target1 test:name "Changedtargetword" } }''')
    con.transaction_commit()
    matches('Changed terminal text is reflected through configured chain', ['test:chainA'],
            [FTSearchFilter('representedName', 'changedtargetword')])
    matches('Removed terminal text no longer matches chain', [], [FTSearchFilter('representedName', 'red')])
