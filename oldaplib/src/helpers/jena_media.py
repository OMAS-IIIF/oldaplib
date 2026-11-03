"""Project-scoped RDF 1.2 queries for the existing media lookup API."""
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_entailment import CLASS_PATH, schema_dataset
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency
from oldaplib.src.resource_transaction import resource_query
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI


def media_rows(connection, term: str, *, by_id: bool):
    """Return SPARQL JSON metadata rows for one visible media identity.

    Args:
        connection: Authenticated connection; joins an active transaction.
        term: Already validated and serialized RDF identifier or asset ID.
        by_id: Match the asset ID instead of the resource IRI.

    Returns:
        Bindings including subject, graph, property, value and maximum permission.
        Restricted media retain their numeric permission for derivative tokens.

    Raises:
        OldapErrorInconsistency: Multiple visible resources match the identity.

    Only the registered project's schemas contribute class ancestry. Both an
    asserted role membership and its annotation are required; no admin bypass
    is introduced. Metadata conversion and token issuance remain with the caller.
    """
    prefix = Context(name=connection.context_name).sparql_context
    match = (f'?subject shared:assetId {term} .' if by_id else
             f'VALUES ?subject {{ {term} }} ?subject a ?candidateType .')
    candidates = resource_query(connection, prefix + f'''SELECT DISTINCT ?namespace ?shortName WHERE {{
        GRAPH oldap:admin {{ ?project a oldap:Project ; oldap:namespaceIri ?namespace ; oldap:projectShortName ?shortName . }}
        BIND(IRI(CONCAT(STR(?namespace), "data")) AS ?graph)
        GRAPH ?graph {{ {match} }}
    }}''')['results']['bindings']
    bindings = []
    for candidate in candidates:
        namespace = candidate['namespace']['value']
        data = '<' + str(Xsd_anyURI(namespace + 'data', validate=True)) + '>'
        schemas = schema_dataset(connection, candidate['shortName']['value'])
        # Bind the requested identity inside the subquery: SPARQL subqueries
        # do not inherit bindings from the surrounding query.
        query = prefix + f'''SELECT DISTINCT ?subject ?graph ?prop ?val ?maxPerm
        {schemas}
        FROM NAMED {data} FROM NAMED oldap:admin
        WHERE {{
            {{ SELECT ?subject (MAX(xsd:integer(?pv)) AS ?maxPerm) WHERE {{
                GRAPH {data} {{
                    {match}
                    ?subject a ?directType ; oldap:attachedToRole ?role .
                    ?grant rdf:reifies <<( ?subject oldap:attachedToRole ?role )>> ; oldap:hasDataPermission ?permission .
                }}
                GRAPH oldap:admin {{ {connection.userIri.toRdf} oldap:hasRole ?role .
                    ?permission oldap:permissionValue ?pv . }}
                FILTER (?directType = shared:MediaObject || EXISTS {{ ?directType {CLASS_PATH} shared:MediaObject }})
            }} GROUP BY ?subject }}
            BIND({data} AS ?graph)
            GRAPH {data} {{ ?subject ?prop ?val . }}
        }}'''
        bindings.extend(resource_query(connection, query)['results']['bindings'])
    identities = {(row['subject']['value'], row['graph']['value']) for row in bindings}
    if len(identities) > 1:
        raise OldapErrorInconsistency('Media lookup matches multiple visible resources.')
    return {'head': {'vars': ['subject', 'graph', 'prop', 'val', 'maxPerm']},
            'results': {'bindings': bindings}}
