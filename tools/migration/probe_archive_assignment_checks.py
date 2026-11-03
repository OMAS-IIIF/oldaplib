"""Verify the archive-assignment model correction in an owned Jena transaction.

The fixture uses the actual Fasnacht property declaration from the sibling YAML,
real resource query builders and existing fixture grants. It deliberately seeds
both orientations of the obsolete axiom; target cleanup must remove both. All
fixture data and schema changes are aborted, including on assertion failures.
"""
from pathlib import Path

import yaml
from rdflib import URIRef

from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.objectfactory import (
    ResourceInstance, SearchFilter, CompOp, _build_resource_read_query,
    _build_resource_summaries_query,
)
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def run_archive_assignment_checks(con, project, context, check):
    """Check direct assignment, subject independence, filtering and rollback.

    Args:
        con: Owned native probe connection with transactional JSON-LD support.
        project: The probe's test project, never a live Fasnacht project.
        context: Prefix context shared with the resource query builders.
        check: Acceptance recorder that raises on a false condition.
    """
    model_path = Path(__file__).resolve().parents[3] / 'oldap-tools/fasnacht/fasnacht-onto.yaml'
    model = yaml.safe_load(model_path.read_text())['ontology']
    declaration = next(prop for prop in model['classes']['fasnacht:ArchiveObject']['properties']
                       if prop['iri'] == 'fasnacht:archiveUnit')
    check('Archive assignment YAML explicitly clears the legacy inverse',
          'inverse_of' in declaration and declaration['inverse_of'] is None
          and declaration['to_class'] == 'shared:ArchiveUnit' and declaration['max_count'] == 1)
    context['fasnacht'] = NamespaceIRI('http://fasnacht.digital/ns/')
    field = URIRef('http://fasnacht.digital/ns/archiveUnit')
    about = URIRef('https://schema.org/about')
    cat = URIRef('http://oldap.org/test#cat')
    second = URIRef('http://oldap.org/test#secondCat')
    unit = URIRef('http://oldap.org/test#assignmentUnit')

    def read(iri):
        query = _build_resource_read_query(con, 'test', Iri(iri), con.userIri,
                                          include_creator=True, rdf12=True)
        return con.transaction_query(query, SparqlResultFormat.JSONLD)

    def search(iri, count=False):
        return ResourceInstance.search(con, project, resClass='test:Cat',
            filter=[SearchFilter('fasnacht:archiveUnit', CompOp.EQ, Iri(iri))], countOnly=count)

    # Exercise the exact reviewed target data update, using this probe's graph.
    # Schema import is separate: the target model must use only isPartOf.
    queries = Path(__file__).with_name('sparql')
    conversion = (queries / 'fasnacht-parts.ru').read_text().replace(
        'http://fasnacht.digital/ns/', 'http://oldap.org/test#')
    preflight = (queries / 'fasnacht-parts-preflight.rq').read_text().replace(
        'http://fasnacht.digital/ns/', 'http://oldap.org/test#')
    con.transaction_start()
    try:
        con.transaction_update(context.sparql_context + '''INSERT DATA {
          GRAPH test:data {
            test:whole dcterms:hasPart test:part, test:otherPart .
            test:part dcterms:isPartOf test:whole .
            test:part a test:Place .
          }
          GRAPH <urn:foreign:data> { test:whole dcterms:hasPart test:part }
        }''')
        check('Parts preflight accepts consistent duplicate directions',
              not con.transaction_query(preflight)['results']['bindings'])
        con.transaction_update(context.sparql_context + '''INSERT DATA {
          GRAPH test:data { test:part dcterms:isPartOf test:conflictingParent }
        }''')
        check('Parts preflight detects multiple place parents',
              bool(con.transaction_query(preflight)['results']['bindings']))
        con.transaction_update(context.sparql_context + '''DELETE DATA {
          GRAPH test:data { test:part dcterms:isPartOf test:conflictingParent }
        }''')
        con.transaction_update(conversion)
        con.transaction_update(conversion)
        rows = con.transaction_query(context.sparql_context + '''SELECT ?part WHERE {
          GRAPH test:data { ?part dcterms:isPartOf test:whole }
        }''')['results']['bindings']
        check('Parts conversion reverses both edges and replay creates no duplicates', len(rows) == 2)
        check('Parts conversion removes legacy edges only in the selected graph',
              not con.transaction_query(context.sparql_context +
                  'ASK { GRAPH test:data { test:whole dcterms:hasPart ?part } }')['boolean']
              and con.transaction_query(context.sparql_context +
                  'ASK { GRAPH <urn:foreign:data> { test:whole dcterms:hasPart test:part } }')['boolean'])
    finally:
        con.transaction_abort()

    con.transaction_start()
    try:
        con.transaction_update(context.sparql_context + '''INSERT DATA {
          GRAPH test:onto {
            fasnacht:archiveUnit a owl:ObjectProperty ; owl:inverseOf schema:about .
            schema:about owl:inverseOf fasnacht:archiveUnit .
          }
          GRAPH test:shacl {
            test:CatShape sh:property [ sh:path fasnacht:archiveUnit ;
              sh:class shared:ArchiveUnit ; sh:maxCount 1 ] .
          }
          GRAPH test:data {
            test:cat fasnacht:archiveUnit test:assignmentUnit .
            test:assignmentUnit a shared:ArchiveUnit .
            test:subjectUnit a shared:ArchiveUnit ; schema:about test:secondCat .
            test:story schema:about test:secondCat .
            test:cat schema:about test:organisation .
          }
        }''')
        check('Archive fixture reproduces the obsolete inverse inference',
              bool(list(read('test:secondCat').objects(second, field))))
        # This is explicit target ontology cleanup, not instance conversion.
        # Append-only project transfer cannot remove an existing schema axiom.
        con.transaction_update(context.sparql_context + '''DELETE DATA { GRAPH test:onto {
          fasnacht:archiveUnit owl:inverseOf schema:about .
          schema:about owl:inverseOf fasnacht:archiveUnit .
        } }''')
        result = con.transaction_query(context.sparql_context + '''ASK { GRAPH test:onto {
          { fasnacht:archiveUnit owl:inverseOf schema:about }
          UNION { schema:about owl:inverseOf fasnacht:archiveUnit }
        } }''')
        check('Archive cleanup removes both legacy axiom orientations', not result['boolean'])
        data = read('test:cat')
        check('Archive single read retains the directly assigned unit', set(data.objects(cat, field)) == {unit})
        check('Archive single read preserves independent subject data',
              set(data.objects(cat, about)) == {URIRef('http://oldap.org/test#organisation')})
        check('Archive subject links no longer manufacture assignments',
              not list(read('test:secondCat').objects(second, field)))
        query = _build_resource_summaries_query(con, 'test', [Iri('test:cat'), Iri('test:secondCat')],
                                               [Xsd_QName('fasnacht:archiveUnit')], rdf12=True)
        summary = con.transaction_query(query, SparqlResultFormat.JSONLD)
        check('Archive summaries retain only asserted assignments',
              set(summary.objects(cat, field)) == {unit} and not list(summary.objects(second, field)))
        check('Archive assignment filter and count agree',
              {str(row['iri']) for row in search('test:assignmentUnit')} == {'test:cat'}
              and int(search('test:assignmentUnit', True)) == 1)
        check('Archive subject-only unit does not match placement search',
              search('test:subjectUnit') == [] and int(search('test:subjectUnit', True)) == 0)
        con.transaction_update(context.sparql_context + '''DELETE DATA { GRAPH test:data {
          test:cat fasnacht:archiveUnit test:assignmentUnit .
        } }''')
        check('Archive removing assignment preserves the subject relation',
              not list(read('test:cat').objects(cat, field))
              and bool(list(read('test:cat').objects(cat, about))))
    finally:
        con.transaction_abort()
    check('Archive acceptance abort removes its fixture data',
          int(search('test:assignmentUnit', True)) == 0)
