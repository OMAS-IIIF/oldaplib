"""Bounded relationship-search growth checks on the runner's owned Fuseki.

Synthetic records are created in one transaction and always rolled back. This
measures real library queries, not HTTP endpoints or concurrent production load.
Expected ordering and visibility are computed independently in Python.
"""
import json
import statistics
import time

from oldaplib.src.objectfactory import ResourceInstance, SearchFilter, CompOp, LogicOp, SortBy
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def run_relationship_growth(con, project, context, check, output):
    """Check 1,000 children, ties, permissions and complete paged traversal.

    Args:
        con: Owned fixture connection with no transaction currently open.
        project: Fixture project already provisioned by the model-read runner.
        context: Fixture prefixes used for RDF 1.2 updates.
        check: Runner assertion/report callback.
        output: Private output directory for aggregate timings and counts.

    Side effects:
        Temporarily inserts instance/schema triples; always aborts the transaction.
        Writes an aggregate report only after all checks succeed.
    """
    visible = [i for i in range(1000) if i % 4 < 2]
    expected = [f'test:growth{i:04d}' for i in visible]
    relation = SearchFilter('test:growthParent', CompOp.EQ, Iri('test:growthRoot'))
    selected = SearchFilter('test:growthSelection', CompOp.EQ, Iri('test:growthSelected'))
    timings = {}

    def search(label, **kwargs):
        started = time.perf_counter()
        result = ResourceInstance.search(con, project, **{
            'resClass': 'test:Mammal', 'filter': [relation], **kwargs})
        timings.setdefault(label, []).append(round((time.perf_counter() - started) * 1000, 3))
        print('GROWTH', label, timings[label][-1], flush=True)
        return result

    def ids(rows):
        return [str(row['iri']) for row in rows]

    triples = []
    for i in range(1000):
        resource = f'test:growth{i:04d}'
        # Every group has equal names, so IRI ordering must break sort ties.
        predicate = 'test:growthChild' if i % 2 else 'test:growthParent'
        triples.append(f'{resource} a test:Cat ; test:name "Group {i // 4:04d}" ; '
                       f'{predicate} test:growthRoot .')
        if i < 20:
            triples.append(f'{resource} test:growthSelection test:growthSelected .')
        if i % 10 == 0:
            triples.append(f'{resource} test:growthChild test:growthRoot .')
        # One quarter has only an orphan annotation; another is below VIEW.
        if i % 4 != 2:
            triples.append(f'{resource} oldap:attachedToRole oldap:Reader .')
        permission = 'DATA_RESTRICTED' if i % 4 == 3 else 'DATA_VIEW'
        triples.append(f'<urn:growth-grant:{i}> rdf:reifies <<( {resource} '
                       f'oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:{permission} .')

    con.transaction_start()
    try:
        con.transaction_update(context.sparql_context + 'INSERT DATA { GRAPH test:onto { '
            'test:growthChild rdfs:subPropertyOf test:growthParent . } }')
        # Keep each request below the transport limit; all chunks still share
        # the same transaction and are discarded together on failure/rollback.
        for start in range(0, len(triples), 400):
            con.transaction_update(context.sparql_context + 'INSERT DATA { GRAPH test:data { '
                + '\n'.join(triples[start:start + 400]) + ' } }')
        check('Growth class-free count retains exactly 500 readable children',
              int(search('count_without_class', countOnly=True, resClass=None)) == 500)
        for _ in range(3):
            check('Growth count includes exactly 500 readable children',
                  int(search('count', countOnly=True)) == 500)
            check('Growth first page respects tied names and subproperties',
                  ids(search('first_page', sortBy=[SortBy('test:name')], limit=50)) == expected[:50])
        pages = []
        for offset in range(0, 500, 50):
            page = search('page_traversal', sortBy=[SortBy('test:name')],
                          includeProperties={Xsd_QName('test:name')}, limit=50, offset=offset)
            pages.extend(ids(page))
        check('Growth complete traversal has no missing, duplicate or denied children', pages == expected)
        check('Growth page beyond last result is empty',
              search('empty_page', sortBy=[SortBy('test:name')], limit=50, offset=500) == [])
        descending = sorted(visible, key=lambda i: (-(i // 4), i))
        check('Growth descending sort keeps ascending IRI tie-breaks',
              ids(search('descending', sortBy=[SortBy('test:name', 'desc')], limit=50))
              == [f'test:growth{i:04d}' for i in descending[:50]])
        narrow = [f'test:growth{i:04d}' for i in visible if i < 20]
        for label, filters in [('broad_first', [relation, LogicOp.AND, selected]),
                               ('selective_first', [selected, LogicOp.AND, relation])]:
            for _ in range(3):
                rows = search(label, filter=filters, limit=50)
                check('Growth conjunct order preserves the same ten results', ids(rows) == narrow)
        con.transaction_update(context.sparql_context + '''DELETE WHERE {
            GRAPH test:data { test:growth0000 oldap:attachedToRole ?role }
        }''')
        check('Growth count immediately reflects permission revocation',
              int(search('revoked_count', countOnly=True)) == 499)
        check('Growth first page closes the gap after permission revocation',
              ids(search('revoked_page', sortBy=[SortBy('test:name')], limit=50)) == expected[1:51])
    finally:
        con.transaction_abort()
    check('Growth rollback leaves no candidate resources', int(search('after_rollback', countOnly=True)) == 0)
    report = {'status': 'passed', 'children': 1000, 'readable': 500,
              'orphan_grants': 250, 'restricted': 250, 'page_size': 50,
              'timings_ms': {label: {'samples': values, 'median': statistics.median(values)}
                             for label, values in timings.items()},
              'scope': 'Owned synthetic transaction; library transport, not API HTTP; object cache disabled; no concurrency load.'}
    (output / 'relationship-growth.json').write_text(json.dumps(report, indent=2) + '\n')
