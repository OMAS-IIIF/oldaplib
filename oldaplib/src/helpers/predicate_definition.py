"""Shared, set-valued superproperty persistence for property and shape editors.

A superproperty belongs to the predicate IRI, not to an individual SHACL use.
Every explicitly declared parent is retained, including imported RDF hierarchies.
"""
from oldaplib.src.iconnection import IConnection
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapErrorNoPermission, OldapErrorUpdateFailed
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def _query(con, body):
    context = Context(name=con.context_name)
    execute = con.transaction_query if con.in_transaction() else con.query
    return QueryProcessor(context, execute(context.sparql_context + body))


def superproperty_set(value) -> set[Iri]:
    """Normalize legacy scalar inputs and iterable parents without sharing mutable state."""
    if value is None:
        return set()
    if isinstance(value, (str, Iri, Xsd_QName)):
        value = [value]
    return {Iri(parent) for parent in value}


def read_superproperty(con: IConnection, predicate: Xsd_QName) -> set[Iri]:
    """Read all distinct shared parents from named ontology graphs (possibly empty)."""
    rows = _query(con, f'''SELECT DISTINCT ?parent WHERE {{
        GRAPH ?graph {{ {predicate.toRdf} rdfs:subPropertyOf ?parent }} }}''')
    return {Iri(row['parent']) for row in rows}


def superproperty_update(con: IConnection, project: Xsd_NCName | str, predicate: Xsd_QName,
                         previous, desired) -> str:
    """Build a guarded replacement in the owner's ontology graph.

    Call inside the write transaction, then execute the returned SPARQL in that
    transaction. Foreign declarations are readable but cannot be changed here.
    The caller remains responsible for project permissions and cache eviction.
    """
    previous = superproperty_set(previous)
    desired = superproperty_set(desired)
    current = read_superproperty(con, predicate)
    if current != previous:
        raise OldapErrorUpdateFailed(f'Superproperty of {predicate} changed; reload its definition.')
    if current == desired:
        return ''
    graph = Xsd_QName(str(project), 'onto')
    if str(predicate.prefix) != str(project):
        raise OldapErrorNoPermission('Change a predicate superproperty in its owning project.')
    foreign = list(_query(con, f'''SELECT ?graph WHERE {{ GRAPH ?graph {{
        {predicate.toRdf} rdfs:subPropertyOf ?parent }} FILTER(?graph != {graph.toRdf}) }}'''))
    if foreign:
        raise OldapErrorInconsistency('A foreign graph declares this superproperty; reconcile it before editing.')
    insert = '\n'.join(f'{predicate.toRdf} rdfs:subPropertyOf {parent.toRdf} .'
                       for parent in sorted(desired, key=str))
    return f'''WITH {graph.toRdf}
        DELETE {{ {predicate.toRdf} rdfs:subPropertyOf ?old }}
        INSERT {{ {insert} }}
        WHERE {{ OPTIONAL {{ {predicate.toRdf} rdfs:subPropertyOf ?old }} }}'''


def invalidate_predicate_models(con: IConnection, predicate: Xsd_QName, *, owned_transaction: bool = False) -> None:
    """Evict predicate, using model graphs and resource snapshots (including children)."""
    from oldaplib.src.cachesingleton import CacheSingletonRedis
    from oldaplib.src.resource_transaction import invalidate_model_cache_on_completion, ResourceTransactionError
    keys = {predicate}
    rows = list(_query(con, f'''SELECT DISTINCT ?graph ?owner ?class WHERE {{
        GRAPH ?graph {{ ?owner sh:property ?field .
            ?field (sh:path|oldap:field) {predicate.toRdf} .
            OPTIONAL {{ ?owner sh:targetClass ?class }} }} }}'''))
    pending, seen = set(), set()
    while rows:
        for row in rows:
            keys.add(row['graph'])
            if row.get('class') is not None:
                keys.add(row['class'])
            pending.add(row['owner'])
        current = pending - seen
        if not current:
            break
        seen.update(current)
        terms = ' '.join(owner.toRdf for owner in current)
        rows = list(_query(con, f'''SELECT DISTINCT ?graph ?owner ?class WHERE {{
            VALUES ?parent {{ {terms} }} GRAPH ?graph {{
                {{ ?owner sh:node ?parent }} UNION
                {{ ?owner sh:property ?field . ?field sh:reifierShape ?parent }}
                OPTIONAL {{ ?owner sh:targetClass ?class }} }} }}'''))
    for key in keys:
        if owned_transaction:
            invalidate_model_cache_on_completion(con, key)
        else:
            try:
                invalidate_model_cache_on_completion(con, key)
            except ResourceTransactionError:
                # Legacy standalone PropertyClass transactions are not wrapped
                # in resource_transaction; their caller also evicts after commit.
                CacheSingletonRedis().delete(key)
