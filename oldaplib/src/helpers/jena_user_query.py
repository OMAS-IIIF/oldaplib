"""Build an opt-in RDF 1.2 user read with the existing UserData result columns.

GraphDB's public query builder remains unchanged. Reifiers carry membership
annotations in Jena; query results contain only ordinary RDF terms, so the
existing QueryProcessor and UserData parser can continue to be used.
"""
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def jena_user_query(context: Context, user_id: IriOrNCName | Iri | Xsd_NCName | Xsd_QName | str,
                    *, validate: bool = False) -> str:
    """Read a user by ID or IRI, including RDF 1.2 project/role annotations.

    Args:
        context: Prefix context, including project namespaces.
        user_id: An existing OLDAP identifier accepted by IriOrNCName.
        validate: Validate the identifier using existing OLDAP value classes.

    Returns:
        A SELECT query with the same columns as UserData.sparql_query.

    Membership must be asserted as well as annotated: a reifier describing an
    absent membership must not grant permissions. Empty memberships still appear
    through the ordinary-property branch. No assumption about result order is made.
    """
    identifier = user_id if isinstance(user_id, IriOrNCName) else IriOrNCName(user_id, validate=validate)
    name, iri = identifier.value()
    selection = (f'?user oldap:userId {name.toRdf} .' if name is not None
                 else f'VALUES ?user {{ {iri.toRdf} }}')
    return context.sparql_context + f'''
SELECT ?user ?prop ?val ?proj ?rval ?role ?defdp
FROM oldap:admin
WHERE {{
    {selection}
    ?user a oldap:User .
    {{ ?user ?prop ?val }}
    UNION {{
        ?user oldap:inProject ?proj .
        ?grant rdf:reifies <<( ?user oldap:inProject ?proj )>> ;
               oldap:hasAdminPermission ?rval .
    }}
    UNION {{
        ?user oldap:hasRole ?role .
        ?default rdf:reifies <<( ?user oldap:hasRole ?role )>> ;
                 oldap:hasDefaultDataPermission ?defdp .
    }}
}}
'''
