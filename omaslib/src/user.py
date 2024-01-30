"""
Ths class User
"""
import json
import uuid
from datetime import datetime
from typing import List, Self, Dict

import bcrypt

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import AnyIRI, QName, NCName
from omaslib.src.helpers.omaserror import OmasError, OmasErrorAlreadyExists, OmasErrorNotFound
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.serializer import serializer
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model
from omaslib.src.user_dataclass import UserDataclass


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
                 in_project: Dict[QName, List[AdminPermission]] | None = None,
                 has_permissions: List[QName] | None = None):
        if user_iri is None:
            user_iri = AnyIRI(uuid.uuid4().urn)
        Model.__init__(self, connection=con)
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
                               in_project=in_project,
                               has_permissions=has_permissions)

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self._con is None:
            raise OmasError("Cannot create: no connection")
        if self.user_iri is None:
            self.user_iri = AnyIRI(uuid.uuid4().urn)
        context = Context(name=self._con.context_name)
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?user
        FROM omas:admin
        WHERE {{
            ?user a omas:User .
            ?user omas:userId "{self.user_id}"^^xsd:NCName .         
        }}
        """

        sparql2 = context.sparql_context
        sparql2 += f"""
        SELECT ?user
        FROM omas:admin
        WHERE {{
            ?user a omas:User .
            FILTER(?user = <{self.user_iri}>)
        }}
        """

        salt = bcrypt.gensalt()
        credentials = bcrypt.hashpw(str(self.credentials).encode('utf-8'), salt).decode('utf-8')
        timestamp = datetime.now()
        blank = ''
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}<{self.user_iri}> a omas:User'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator <{self._con.user_iri}>'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:datetime'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor <{self._con.user_iri}>'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:datetime'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:userId "{self.user_id}"^^xsd:NCName'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}foaf:familyName "{self.familyName}"'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}foaf:givenName "{self.givenName}"'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:credentials "{credentials}"'
        star = ''
        if self.in_project:
            project = [str(p) for p in self.in_project.keys()]
            rdfstr = ", ".join(project)
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:inProject {rdfstr}'
            for p in project:
                for admin_p in self.in_project[p]:
                    star += f'{blank:{(indent + 2) * indent_inc}}<<<{self.user_iri}> omas:inProject {p}>> omas:hasAdminPermission {admin_p.value} .\n'
        if self.has_permissions:
            rdfstr = ", ".join([ str(x) for x in self.has_permissions])
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:hasPermissions {rdfstr}'
        sparql += " .\n\n"
        sparql += star
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OmasError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OmasErrorAlreadyExists(f'A user with a user ID "{self.user_id}" already exists')
        try:
            jsonobj = self._con.transaction_query(sparql2)
        except OmasError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OmasErrorAlreadyExists(f'A user with a user IRI "{self.user_iri}" already exists')
        try:
            self._con.transaction_update(sparql)
        except OmasError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OmasError:
            self._con.transaction_abort()
            raise


    @classmethod
    def read(cls, con: Connection, user_id: NCName | str) -> Self:
        if isinstance(user_id, str):
            user_id = NCName(user_id)

        context = Context(name=con.context_name)
        jsonobj = con.query(cls.sparql_query(context, user_id))
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OmasErrorNotFound(f'User "{user_id}" not found.')
        instance = cls(con=con)
        instance.create_from_queryresult(res)
        return instance

    def delete(self) -> None:
        context = Context(name=self._con.context_name)
        blank = ''
        sparql = context.sparql_context
        sparql += f"""
        DELETE {{
            <<?user omas:inProject ?proj>> omas:hasAdminPermission ?rval .    
        }}
        WHERE {{
            ?user a omas:User .
            ?user omas:userId "{self.user_id}"^^xsd:NCName .
        }} ;
        DELETE WHERE {{
            ?user a omas:User .
            ?user omas:userId "{self.user_id}"^^xsd:NCName .
            ?user ?prop ?val .
        }} 
        """
        self._con.update_query(sparql)


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     user_id="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")

    user = User.read(con, 'rosenth')
    print(user)
    user2 = User(con=con,
                 user_id=NCName("testuser"),
                 family_name="Test",
                 given_name="Test",
                 credentials="Ein@geheimes&Passw0rt",
                 in_project={QName('omas:HyperHamlet'): [AdminPermission.ADMIN_USERS,
                                                         AdminPermission.ADMIN_RESOURCES,
                                                         AdminPermission.ADMIN_CREATE]},
                 has_permissions=[QName('omas:GenericView')])
    print(user2)
    user2.create()
    user3 = User.read(con, 'testuser')
    print(user3)
    #jsonstr = json.dumps(user2, default=serializer.encoder_default, indent=4)
    #print(jsonstr)
    #user3 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    #print(user3)
