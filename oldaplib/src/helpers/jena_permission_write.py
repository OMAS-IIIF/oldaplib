"""RDF 1.2 permission writes shared by users and resources.

Callers provide validated OLDAP RDF terms and run updates inside the existing
domain transaction. Only the declared permission predicates are owned
here; unrelated annotations on a reifier are preserved.
"""
from uuid import uuid4


MEMBERSHIPS = {
    'oldap:inProject': 'oldap:hasAdminPermission',
    'oldap:hasRole': 'oldap:hasDefaultDataPermission',
    'oldap:attachedToRole': 'oldap:hasDataPermission',
}


def permission_annotation(subject: str, predicate: str, target: str, permission: str) -> str:
    """Return one explicit reifier statement for INSERT DATA or TriG export.

    Inputs are serialized RDF terms, not untrusted text. The asserted membership
    is emitted separately by the caller; a reifier alone grants no membership.
    """
    annotation = MEMBERSHIPS[predicate]
    return (f'<urn:uuid:{uuid4()}> rdf:reifies <<( {subject} {predicate} {target} )>> ; '
            f'{annotation} {permission} .\n')


def clear_membership_annotations(subject: str, predicate: str, *, graph: str = 'oldap:admin', target: str = '?target') -> str:
    """Remove all matching permission values, including duplicate legacy reifiers.

    Remove the reification link only when no other annotations remain. This
    preserves metadata outside this helper's ownership without retaining grants.
    """
    annotation = MEMBERSHIPS[predicate]
    # A fixed target limits publication edits to the public role. The default
    # variable retains whole-map cleanup for existing user/resource callers.
    triple = f'<<( {subject} {predicate} {target} )>>'
    return f'''WITH {graph}
DELETE {{ ?grant {annotation} ?permission . }}
WHERE {{ ?grant rdf:reifies {triple} ; {annotation} ?permission . }} ;
WITH {graph}
DELETE {{ ?grant rdf:reifies {triple} . }}
WHERE {{
    ?grant rdf:reifies {triple} .
    FILTER NOT EXISTS {{ ?grant ?other ?value . FILTER (?other != rdf:reifies) }}
}}'''


def replace_memberships(subject: str, predicate: str, memberships: dict, *, graph: str = 'oldap:admin') -> str:
    """Replace one changed membership map after the caller's timestamp check.

    Args:
        subject: Serialized subject IRI.
        predicate: One of the supported membership predicates.
        memberships: Target RDF term to iterable of permission RDF terms.
        graph: Serialized graph IRI or QName, selected by the domain caller.

    Returns:
        Update operations without prefixes. Empty permissions retain membership;
        an empty map removes it. Other membership predicates are untouched.
    """
    statements = [clear_membership_annotations(subject, predicate, graph=graph),
                  f'DELETE WHERE {{ GRAPH {graph} {{ {subject} {predicate} ?target }} }}']
    triples = []
    for target, permissions in memberships.items():
        triples.append(f'{subject} {predicate} {target} .')
        triples.extend(permission_annotation(subject, predicate, target, value) for value in permissions)
    if triples:
        statements.append('INSERT DATA { GRAPH ' + graph + ' {\n' + '\n'.join(triples) + '\n} }')
    return ' ;\n'.join(statements)


def delete_user(subject: str) -> str:
    """Delete subject triples and owned permissions only in the administration graph."""
    statements = [clear_membership_annotations(subject, predicate) for predicate in ('oldap:inProject', 'oldap:hasRole')]
    statements.append(f'DELETE WHERE {{ GRAPH oldap:admin {{ {subject} ?predicate ?value }} }}')
    return ' ;\n'.join(statements)


def require_exclusive_reifiers(con, subject: str, predicates, *, graph: str = 'oldap:admin') -> None:
    """Reject shared reifiers before changing permissions in an active transaction.

    RDF 1.2 permits a reifier to describe multiple triples. OLDAP grants describe
    one membership: changing a shared annotation could change another subject's
    rights. Such imported data must be separated explicitly before editing.
    """
    from oldaplib.src.helpers.context import Context
    from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency
    predicates = tuple(predicates)
    if not predicates:
        return
    query = Context(name=con.context_name).sparql_context + f'''
ASK {{ GRAPH {graph} {{
    VALUES ?membership {{ {' '.join(predicates)} }}
    ?grant rdf:reifies <<( {subject} ?membership ?target )>> ; rdf:reifies ?other .
    FILTER (?other != <<( {subject} ?membership ?target )>>)
}} }}'''
    if con.transaction_query(query)['boolean']:
        raise OldapErrorInconsistency('A subject permission reifier describes multiple memberships; separate it before editing.')
