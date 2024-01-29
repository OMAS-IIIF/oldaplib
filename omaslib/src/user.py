"""
Ths class User
"""
import json
import uuid
from datetime import datetime
from pprint import pprint
from typing import List, Optional, Self, Dict

import bcrypt

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import AnyIRI, QName, NCName
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.serializer import serializer
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model
from omaslib.user_dataclass import UserDataclass


@serializer
class User(Model, UserDataclass):

    def __init__(self, *,
                 con: Connection | None = None,
                 creator: AnyIRI | None = None,
                 created: datetime | None = None,
                 contributor: AnyIRI | None = None,
                 modified: datetime | None = None,
                 user_iri: AnyIRI | None = None,
                 user_id: NCName | None = None,
                 family_name: str | None = None,
                 given_name: str | None = None,
                 credentials: str | None = None,
                 active: bool | None = None,
                 in_projects: Dict[QName, List[AdminPermission]] | None = None,
                 has_permissions: List[DataPermission] | None = None):
        Model.__init__(self, con)
        UserDataclass.__init__(self,
                               creator=creator,
                               created=created,
                               contributor=contributor,
                               modified=modified,
                               user_iri=user_iri,
                               user_id=user_id,
                               family_name=family_name,
                               given_name=given_name,
                               credentials=credentials,
                               active=active,
                               in_projects=in_projects,
                               has_permissions=has_permissions)

    @property
    def json(self) -> str:
        obj = {
                'userId': self.__userId,
                'userIri': self.__userIri,
                'inProject': self.__inProjects,
                'hasPermissions': self.__hasPermissions
        }
        return json.dumps(obj)

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self._con is None:
            raise OmasError("Cannot create: no connection")
        if self.__userIri is None:
            self.__userIri = AnyIRI(uuid.uuid4().urn)
        context = Context(name=self._con.context_name)
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?user
        FROM omas:admin
        WHERE {{
            ?user a omas:User .
            ?user omas:userId "{self.__userId}"^^NCName
        }}
        """

        salt = bcrypt.gensalt()
        credentials = bcrypt.hashpw(self.credentials.encode('utf-8'), salt)
        timestamp = datetime.now()
        blank = ''
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}<{self.__userIri}> a omas:User ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}dcterms:creator {self._con.user_iri} ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}dcterms:created {timestamp.isoformat()}^^xsd:datetime ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}dcterms:contributor {self._con.user_iri} ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}dcterms:modified {timestamp.isoformat()}^^xsd:datetime ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}omas:userId "{self.user_id}"^^xsd:NCName ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}foaf:familyName "{self.familyName}" ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}foaf:givenName "{self.givenName}" ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}omas:credentials "{credentials}" ;\n'
        if self.in_projects:
            projects = [p.value for p in self.in_projects.values()]
            rdfstr = ", ".join(projects)
            sparql += f'{blank:{(indent + 2) * indent_inc}}omas:inProjects {rdfstr} ;\n'
        if self.has_permissions:
            rdfstr = ", ".join(self.has_permissions)
            sparql += f'{blank:{(indent + 2) * indent_inc}}omas:hasPermissions {rdfstr} ;\n'





        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

    @classmethod
    def read(cls, con: Connection, user_id: NCName | str) -> Self:
        if isinstance(user_id, str):
            user_id = NCName(user_id)

        context = Context(name=con.context_name)
        jsonobj = con.query(cls.sparql_query(context, user_id))
        res = QueryProcessor(context, jsonobj)
        instance = cls(con=con)
        instance.create_from_queryresult(res)
        return instance


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     user_id="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")

    user = User.read(con, 'rosenth')
    print(user)
    jsonstr = json.dumps(user, default=serializer.encoder_default, indent=4)
    print(jsonstr)
    user2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    print(user2)

