from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, AnyIRI, QName
from omaslib.src.helpers.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.query_processor import QueryProcessor


@dataclass
class UserDataclass:
    creator: AnyIRI | None
    created: datetime | None
    contributor: AnyIRI | None
    modified: datetime | None
    userId: NCName
    userIri: AnyIRI
    familyName: str
    givenName: str
    credentials: str
    inProjects: Dict[QName, List[AdminPermission]] | None
    hasPermissions: List[DataPermission] | None
    active: bool

    def sparql_query(self, context: Context, user_id: NCName) -> str:
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?user ?prop ?val ?proj ?rval
        FROM omas:admin
        WHERE {{
            {{
                ?user a omas:User .
                ?user omas:userId "{user_id}"^^xsd:NCName .
                ?user ?prop ?val .
            }} UNION {{
                <<?user omas:userInProject ?proj>> omas:hasPermission ?rval .
            }}
        }}
        """
        return sparql

    @classmethod
    def create_from_queryresult(cls, queryresult: QueryProcessor):
        creator: AnyIRI | None = None
        created: datetime | None = None
        contributor: AnyIRI | None = None
        modified: datetime | None = None
        user_id: NCName | None = None
        user_iri: AnyIRI | None = None
        family_name: str | None = None
        given_name: str | None = None
        credentials: str | None = None
        active: bool | None = None
        in_project: Dict[QName, List[AdminPermission]] = {}
        has_permissions: List[DataPermission] = []
        for r in queryresult:
            match str(r.get('prop')):
                case 'dcterms:creator':
                    creator = r['val']
                    user_iri = r['user']
                case 'dcterms:created':
                    created = r['val']
                case 'dcterms:contributor':
                    contributor = r['val']
                case 'dcterms:modified':
                    modified = r['val']
                case 'omas:userId':
                    user_id = r['val']
                case 'foaf:familyName':
                    family_name = r['val']
                case 'foaf:givenName':
                    given_name = r['val']
                case 'omas:credentials':
                    credentials = r['val']
                case 'omas:isActive':
                    active = r['val']
                case 'omas:inProject':
                    in_project = {r['val']: []}
                case _:
                    if r.get('proj') is not None:
                        if in_project.get(r['proj']) is None:
                            in_project[r['proj']] = []
                        in_project[r['proj']].append(AdminPermission(r['rval']))
        return cls(creator=creator,
                   created=created,
                   contributor=contributor,
                   modified=modified,
                   userIri=user_iri,
                   userId=user_id,
                   familyName=family_name,
                   givenName=given_name,
                   credentials=credentials,
                   active=active,
                   inProjects=in_project,
                   hasPermissions=has_permissions)

