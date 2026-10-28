"""Read repository SHACL/OWL models and permission-filtered resources via Fuseki.

Only Redis cache I/O is replaced with cache misses; model parsing, factory,
class inheritance, permission query and resource hydration are real library code.
All datasets, bearer identities and fixture resource grants belong to this probe.
"""
import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

from rdflib import Graph
import probe_http_sessions as sessions
from probe_fuseki_identity import IdentityPeer
from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorValue
from oldaplib.src.objectfactory import (ResourceInstanceFactory, _build_resource_read_query,
                                       _build_resource_summaries_query,
                                       MAX_RESOURCE_SUMMARY_BATCH, MAX_RESOURCE_SUMMARY_PROPERTIES)
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def run(java, jar, output):
    """Seed fresh TDB2 with real model files and check one complete read path."""
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    peer = IdentityPeer()
    original = sessions.TOKENS
    sessions.TOKENS = ('Bearer ' + peer.token('actor'), 'Bearer ' + peer.token('other'))
    checks = []
    count = 0

    class ReadConnection(sessions.HttpProbeConnection):
        _resource_search_rdf12 = True
        server_source = 'FusekiSessionProbe.java'
        route_prefix = '/tx'

        def server_environment(self):
            environment = {key: value for key, value in os.environ.items()
                           if not (key.startswith('OLDAP_') and key.endswith('JWT_SECRET'))}
            return dict(environment, PROBE_IDENTITY_URL=peer.url, PROBE_IDENTITY_SECRET=peer.secret,
                        PROBE_TRANSPORT_SECRET=peer.transport_secret,
                        PROBE_SEED_FILES='\n'.join(str(root / path) for path in (
                            'oldaplib/ontologies/oldap.trig', 'oldaplib/ontologies/shared.trig',
                            'oldaplib/testdata/objectfactory_test.trig')))

        def request_headers(self):
            return {'X-Oldap-Service-Key': peer.transport_secret}

        def query(self, query, format=SparqlResultFormat.JSON):
            nonlocal count
            count += 1
            result = self.send('READ', query)
            if format == SparqlResultFormat.JSONLD:
                return Graph().parse(data=result, format='json-ld')
            if format != SparqlResultFormat.JSON:
                raise NotImplementedError('Probe supports JSON and JSON-LD')
            return json.loads(result)

        def _resource_read_query(self, graph, iri, user_iri, *, include_creator):
            return _build_resource_read_query(self, graph, iri, user_iri,
                                             include_creator=include_creator, rdf12=True)

        def _resource_summaries_query(self, graph, iris, include_properties):
            return _build_resource_summaries_query(self, graph, iris, include_properties, rdf12=True)

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print('PASS', name, flush=True)

    log = (output / 'server.log').open('a')
    con = None
    try:
        con = ReadConnection(java, jar, output / 'dataset', log)
        con._userdata = peer.codec.decode_access_token(sessions.TOKENS[0].removeprefix('Bearer '))
        context = Context(name=con.context_name)
        context['test'] = NamespaceIRI('http://oldap.org/test#')
        seed = context.sparql_context + '''INSERT DATA {
GRAPH oldap:admin {
    oldap:SystemProject a oldap:Project ; oldap:projectShortName "oldap"^^xsd:NCName ;
        oldap:namespaceIri <http://oldap.org/base#> ; oldap:projectStart "2024-01-01"^^xsd:date .
    oldap:SharedProject a oldap:Project ; oldap:projectShortName "shared"^^xsd:NCName ;
        oldap:namespaceIri <http://oldap.org/shared#> ; oldap:projectStart "2024-01-01"^^xsd:date .
    <https://example.org/callback/actor> oldap:hasRole oldap:Reader .
    oldap:DATA_VIEW oldap:permissionValue 2 .
    oldap:DATA_RESTRICTED oldap:permissionValue 1 .
    oldap:DATA_UPDATE oldap:permissionValue 4 .
}
GRAPH test:data {
    test:cat a test:Cat ; test:name "Minka" ; test:subName "Hauskatze" ;
        oldap:createdBy <https://example.org/callback/other> ;
        oldap:creationDate "2024-01-01T00:00:00Z"^^xsd:dateTimeStamp ;
        oldap:lastModifiedBy <https://example.org/callback/other> ;
        oldap:lastModificationDate "2024-01-01T00:00:00Z"^^xsd:dateTimeStamp ;
        oldap:attachedToRole oldap:Reader, oldap:Stranger .
    <urn:cat-grant> rdf:reifies <<( test:cat oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
    <urn:cat-second-grant> rdf:reifies <<( test:cat oldap:attachedToRole oldap:Stranger )>> ; oldap:hasDataPermission oldap:DATA_UPDATE .
    test:restricted a test:Cat ; test:name "Restricted" ; oldap:attachedToRole oldap:Reader .
    <urn:restricted-grant> rdf:reifies <<( test:restricted oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_RESTRICTED .
    test:denied a test:Cat ; test:name "Private" ; oldap:attachedToRole oldap:Stranger .
    <urn:denied-grant> rdf:reifies <<( test:denied oldap:attachedToRole oldap:Stranger )>> ; oldap:hasDataPermission oldap:DATA_UPDATE .
    test:orphan a test:Cat ; test:name "Orphan" .
    <urn:orphan-grant> rdf:reifies <<( test:orphan oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
}
GRAPH test:data {
    test:secondCat a test:Cat ; test:name "Zora" ; oldap:attachedToRole oldap:Reader, oldap:Stranger .
    <urn:second-cat-grant> rdf:reifies <<( test:secondCat oldap:attachedToRole oldap:Reader )>> ; oldap:hasDataPermission oldap:DATA_UPDATE .
    <urn:second-cat-stranger-grant> rdf:reifies <<( test:secondCat oldap:attachedToRole oldap:Stranger )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
    test:unrequested a test:Cat ; test:name "Unrequested" ; oldap:createdBy <https://example.org/callback/actor> .
}
GRAPH <urn:other-project:data> { test:cat test:name "must-not-leak" . }
}'''
        con.transaction_start()
        con.transaction_update(seed)
        con.transaction_update(context.sparql_context + '''
INSERT { GRAPH test:data { test:creatorOnly ?p ?o ; oldap:createdBy <https://example.org/callback/actor> } }
WHERE { GRAPH test:data { test:cat ?p ?o . FILTER(?p NOT IN (oldap:attachedToRole, oldap:createdBy)) } }
''')
        con.transaction_commit()
        # Replace cache I/O, not model/factory behavior. No shared Redis touched.
        with patch.object(CacheSingletonRedis, '__init__', return_value=None), \
             patch.object(CacheSingletonRedis, 'get', return_value=None), \
             patch.object(CacheSingletonRedis, 'set', return_value=None):
            project = Project.read(con, 'test', ignore_cache=True)
            check('Real Project.read resolves fixture namespace', str(project.namespaceIri) == 'http://oldap.org/test#')
            model = DataModel.read(con, project, ignore_cache=True)
            check('Real DataModel.read loads repository SHACL and OWL',
                  Xsd_QName('test:Cat') in model.get_resclasses() and Xsd_QName('test:Mammal') in model.get_resclasses())
            factory = ResourceInstanceFactory(con, project)
            Cat = factory.createObjectInstance('test:Cat')
            check('Factory resolves inherited properties from model metadata', Xsd_QName('test:name') in Cat.resolved_properties())
            cat = factory.read(Iri('test:cat'))
            check('Factory reads a permitted RDF 1.2 resource with inherited field', {str(value) for value in cat.get(Xsd_QName('test:name'))} == {'Minka'})
            check('Factory retains concrete type and direct property', str(cat.name) == 'test:Cat' and {str(value) for value in cat.get(Xsd_QName('test:subName'))} == {'Hauskatze'})
            check('Multiple resource grants retain the correct role-permission association',
                  dict(cat.attachedToRoleAnnotation) == {Xsd_QName('oldap:Reader'): DataPermission.DATA_VIEW,
                                                       Xsd_QName('oldap:Stranger'): DataPermission.DATA_UPDATE})
            check('Other project data does not enter the resource read', 'must-not-leak' not in str(cat.get(Xsd_QName('test:name'))))
            result = factory.read_data('http://oldap.org/test#cat')
            check('Generic read_data keeps asserted type distinct from inferred ancestors',
                  {str(value) for value in result.asserted_types} == {'test:Cat'}
                  and str(result.resource_class) == 'test:Cat')
            raw = con.query(con._resource_read_query(project.projectShortName, Iri('test:cat'), con.userIri,
                                                    include_creator=False), format=SparqlResultFormat.JSONLD)
            from rdflib import URIRef
            from rdflib.namespace import RDF
            check('Scoped resource read explicitly entails superclass type',
                  (URIRef('http://oldap.org/test#cat'), RDF.type, URIRef('http://oldap.org/test#Mammal')) in raw)
            for name in ('denied', 'orphan', 'missing', 'restricted', 'creatorOnly'):
                try:
                    factory.read(Iri('test:' + name))
                except OldapErrorNotFound:
                    check('Factory denies ' + name + ' resource', True)
                else:
                    raise AssertionError('Unauthorized or missing resource was returned')
            check('Class read preserves the explicit creator exception',
                  Cat.read(con, Iri('test:creatorOnly')).iri == Iri('test:creatorOnly'))
            check('Generic read_data preserves its creator exception',
                  str(factory.read_data('test:creatorOnly').resource_class) == 'test:Cat')
            # The real factory has already initialized model/list context. The
            # batch itself must use one READ, independently of the input size.
            before_batch = count
            summaries = factory.read_summaries(
                ['test:secondCat', 'test:denied', 'http://oldap.org/test#cat',
                 'test:orphan', 'test:missing', 'test:restricted', 'test:creatorOnly', 'test:secondCat'],
                include_properties=['test:name'])
            check('Summary batch uses one HTTP READ after model initialization', count == before_batch + 1)
            check('Summary order, full IRI alias and duplicate collapse are preserved',
                  list(summaries) == [Iri('test:secondCat'), Iri('http://oldap.org/test#cat'), Iri('test:creatorOnly')])
            check('Summary omits denied, orphan, missing and restricted resources',
                  all(Iri('test:' + name) not in summaries for name in ('denied', 'orphan', 'missing', 'restricted')))
            check('Creator access cannot escape requested summary VALUES', Iri('test:unrequested') not in summaries)
            cat_summary = summaries[Iri('http://oldap.org/test#cat')]
            check('Summary returns only the requested property from the project',
                  {str(value) for value in cat_summary.data['test:name']} == {'Minka'}
                  and 'test:subName' not in cat_summary.data)
            check('Summary preserves concrete and asserted types alongside inferred ancestors',
                  str(cat_summary.resource_class) == 'test:Cat'
                  and {str(value) for value in cat_summary.asserted_types} == {'test:Cat'}
                  and 'test:Mammal' in {str(value) for value in cat_summary.data['rdf:type']})
            check('Summary keeps multi-resource grant pairs separate',
                  cat_summary.data[Xsd_QName('oldap:attachedToRole')] == {
                      Xsd_QName('oldap:Reader'): DataPermission.DATA_VIEW,
                      Xsd_QName('oldap:Stranger'): DataPermission.DATA_UPDATE}
                  and summaries[Iri('test:secondCat')].data[Xsd_QName('oldap:attachedToRole')] == {
                      Xsd_QName('oldap:Reader'): DataPermission.DATA_UPDATE,
                      Xsd_QName('oldap:Stranger'): DataPermission.DATA_VIEW})
            check('Summary retains explicit creator access without a role grant',
                  summaries[Iri('test:creatorOnly')].data[Xsd_QName('oldap:attachedToRole')] == {})
            check('Summary with no properties still returns types and role metadata',
                  set(factory.read_summaries(['test:cat'])[Iri('test:cat')].data) == {
                      'rdf:type', Xsd_QName('oldap:attachedToRole')})
            check('Entirely unreadable summary batch is empty',
                  factory.read_summaries(['test:denied', 'test:missing', 'test:orphan', 'test:restricted']) == {})
            before_empty = count
            check('Empty summary batch is empty without a request', factory.read_summaries([]) == {} and count == before_empty)
            for label, iris, properties in (
                ('scalar input', 'test:cat', []),
                ('resource limit', [f'test:batch{i}' for i in range(MAX_RESOURCE_SUMMARY_BATCH + 1)], []),
                ('property limit', ['test:cat'], [f'test:property{i}' for i in range(MAX_RESOURCE_SUMMARY_PROPERTIES + 1)]),
            ):
                before_invalid = count
                try:
                    factory.read_summaries(iris, include_properties=properties)
                except OldapErrorValue:
                    check('Summary rejects ' + label + ' before any request', count == before_invalid)
                else:
                    raise AssertionError('Invalid summary input was accepted: ' + label)
            # Include the maximum distinct input count; absent resources still
            # must not cause per-resource requests or appear in the response.
            before_maximum = count
            maximum = factory.read_summaries(['test:cat'] + [f'test:absent{i}' for i in range(MAX_RESOURCE_SUMMARY_BATCH - 1)])
            check('Maximum-size summary batch remains one query with no phantom resources',
                  list(maximum) == [Iri('test:cat')] and count == before_maximum + 1)
            from probe_search_checks import run_search_checks
            run_search_checks(con, project, context, check)
            from probe_hlist_checks import run_hlist_checks
            run_hlist_checks(con, project, context, check)
            con.transaction_start()
            con.transaction_update(context.sparql_context + 'DELETE DATA { GRAPH oldap:admin { <https://example.org/callback/actor> oldap:hasRole oldap:Reader } }')
            con.transaction_commit()
            try:
                factory.read(Iri('test:cat'))
            except OldapErrorNotFound:
                check('Read checks current role membership after revocation', True)
            else:
                raise AssertionError('Revoked membership still allowed the read')
            check('Summary applies current role removal while preserving creator access',
                  list(factory.read_summaries(['test:cat', 'test:secondCat', 'test:creatorOnly'])) == [Iri('test:creatorOnly')])
            from oldaplib.src.objectfactory import ResourceInstance
            check('Search and count apply current role removal',
                  ResourceInstance.search(con, project, resClass='test:Cat') == []
                  and int(ResourceInstance.search(con, project, resClass='test:Cat', countOnly=True)) == 0)
            from oldaplib.src.objectfactory import HLSearchFilter
            from oldaplib.src.xsd.listnode import HListNodeRef
            subtree = [HLSearchFilter('test:keyword', HListNodeRef('ProbeKeywords', 'Parent'))]
            check('List-filter results and counts honor current role removal',
                  ResourceInstance.search(con, project, hlfilter=subtree) == []
                  and int(ResourceInstance.search(con, project, hlfilter=subtree, countOnly=True)) == 0)
            check('Plain Jena does not silently infer superclass rdf:type',
                  not con.query(context.sparql_context + 'ASK { GRAPH test:data { test:cat a test:Mammal } }')['boolean'])
            check('Explicit subclass path derives membership from model graph',
                  con.query(context.sparql_context + 'ASK { GRAPH test:data { test:cat a ?type } GRAPH test:onto { ?type rdfs:subClassOf+ test:Mammal } }')['boolean'])
        (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': checks, 'read_queries': count}, indent=2) + '\n')
    finally:
        if con is not None and con.process.poll() is None:
            con.close()
        log.close()
        sessions.TOKENS = original
        peer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', default='java')
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.java, args.jar, args.output.resolve())
