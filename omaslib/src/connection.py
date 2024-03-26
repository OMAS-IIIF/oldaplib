import json
from time import sleep

import bcrypt
import jwt
import requests

from jwt import InvalidTokenError
from pystrict import strict
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from pathlib import Path

from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNoPermission
from omaslib.src.helpers.context import Context, DEFAULT_CONTEXT
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.serializer import serializer
from omaslib.src.iconnection import IConnection
from omaslib.src.enums.sparql_result_format import SparqlResultFormat
from omaslib.src.user_dataclass import UserDataclass
from omaslib.src.xsd.xsd_string import Xsd_string

#
# For bootstrapping the whole tripel store, the following SPARQL has to be executed within the GraphDB
# SPARQL-console:
#
# PREFIX omas: <http://omas.org/base#>
#
# INSERT DATA {
# 	GRAPH omas:admin {
# 		<https://orcid.org/0000-0003-1681-4036> a omas:User ;
#         	omas:personLastName "Rosenthaler" ;
#         	omas:personFirstName "Lukas" ;
#         	omas:userId "rosenth" ;
#         	omas:userCredentials "$2b$12$jWCJZ.qdXE9MSCPdUc0y4.9swWYJcgLZn0ePtRTu/7U8qH/OXXkB2" ;
#         	omas:userIsActive true .
# 	}
# }
#
# Then, executing the __main__ of the file "connection.py" will initialize the triple store with all the data
# needed to run the tests
#
jwt_format = {
    "userId": "https://orcid.org/0000-0003-1681-4036",
    "exp": "2023-11-04T12:00:00+00:00",
    "iat": datetime.now().isoformat(),
    "iss": "http://oldap.org"
}
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIkMmIkMTIkaldDSloucWRYRTlNU0NQZFVjMHk0Ljlzd1dZSmNnTFpuMGVQdFJUdS83VThxSC9PWFhrQjIiLCJleHAiOiIyMDI0LTExLTA0VDEyOjAwOjAwKzAwOjAwIiwiaWF0IjoiMjAyNC0wMS0xOVQyMzo0MTozMS45NTI5MTkiLCJpc3MiOiJodHRwOi8vb2xkYXAub3JnIn0.Vsc2qamfyeTW6Xz5l2Wca-mFnA5PcLuOoWPVEo__4Z4"


@strict
class Connection(IConnection):
    """
    Class that implements the connection to an external triple store for omaslib.

    The connection to a SPARQL endpoint requires the following information:

    * _server_: URL of the server (inlcuding port number)
    * _repo_: Name of the repository to connect to
    * _context_name_: Name of the context (see ~helper.Context)

    The class implements the following methods:

    * Getter-methods:
        - _server_: returns the server string
        - _repo_: returns the repository name
        - _context_name_: returns the context name
    * Setter methods:
        - Any setting of the _server_, _repo_ or _context_name_ - variables raises an OmasError-exception
    * Further methods
        - _Constructor(server,repo,contextname)_: requires _server_ and _repo_string, _context_name defaults to "DEFAULT"
        - _clear_graph_(graph_name: QName)_: Deletes the given graph (must be given as QName)
        - _clear_repo()_ Deletes all data in the repository given by the Connection instance
        - _upload_turtle(filename: str, graphname:str)_: Loads the data in the given file (must be turtle or trig
          format) into the given repo and graph. If graphname is not given, the data will either be loaded into the
          default graph of the repository or into the graph given in the trig file.
          _Note_: The method returns before the triple store has digested all the data! It may not immediately
          available after this method returns!
        - _query(query: str, format: SparqlResultFormat)_: Sends a SPARQL query to the triple store and returns the
          result in the given format. If no format is given, JSON will be used as default format.
        - _update_query(query: str)_: Send a SPARQL update query to the SPARQL endpoint. The method return either
          {'status': 'OK'} or {'status': 'ERROR', 'message': 'error-text'}
        - _rdflib_query(query: str, bindings: Optional[Mapping[str, Identifier]])_: Send a SPAQRL query using rdflib
          to the SPARQL endpoint. The variable _bindings_ allows to set query parameters to given values.

    """
    _server: str
    _repo: str
    _userId: str
    #_userdata: UserDataclass  ## IConnection
    #_context_name: str  ## IConnection
    _store: SPARQLUpdateStore
    _query_url: str
    _update_url: str
    _transaction_url: Optional[str]
    #_token: str | None
    jwtkey: str = "You have to change this!!! +D&RWG+"
    _switcher = {
        SparqlResultFormat.XML: lambda a: a.text,
        SparqlResultFormat.JSON: lambda a: a.json(),
        SparqlResultFormat.TURTLE: lambda a: a.text,
        SparqlResultFormat.N3: lambda a: a.text,
        SparqlResultFormat.NQUADS: lambda a: a.text,
        SparqlResultFormat.JSONLD: lambda a: a.json(),
        SparqlResultFormat.TRIX: lambda a: a.text,
        SparqlResultFormat.TRIG: lambda a: a.text,
        SparqlResultFormat.TEXT: lambda a: a.text
    }

    def __init__(self, *,
                 server: str,
                 repo: str,
                 userId: Optional[str | Xsd_NCName] = None,
                 credentials: Optional[str | Xsd_string] = None,
                 token: Optional[str] = None,
                 context_name: Optional[str] = DEFAULT_CONTEXT) -> None:
        """
        Constructor that establishes the connection parameters.

        :param server: URL of the server (including port information if necessary)
        :param repo: Name of the triple store repository on the server
        :param context_name: A name of the Context to be used (see ~Context). If no such context exists,
            a new context of this name is created
        """
        super().__init__(context_name=context_name)
        self._server = server
        self._repo = repo
        self._query_url = f'{self._server}/repositories/{self._repo}'
        self._update_url = f'{self._server}/repositories/{self._repo}/statements'
        self._store = SPARQLUpdateStore(self._query_url, self._update_url)
        context = Context(name=context_name)
        if token is not None:
            try:
                payload = jwt.decode(jwt=token, key=Connection.jwtkey, algorithms="HS256")
            except InvalidTokenError:
                raise OmasError("Wrong credentials")
            self._userdata = json.loads(payload['userdata'], object_hook=serializer.decoder_hook)
            self._token = token
            return
        if not isinstance(userId, Xsd_NCName):
            userId = Xsd_NCName(userId)
        if userId is None or credentials is None:
            raise OmasError("Wrong credentials")
        sparql = UserDataclass.sparql_query(context=context, userId=userId)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8",
        }
        data = {
            'query': sparql,
        }
        res = requests.post(url=self._query_url, headers=headers, data=data)
        if res.status_code == 200:
            jsonobj = res.json()
        else:
            raise OmasError(res.status_code, res.text)
        res = QueryProcessor(context=context, query_result=jsonobj)

        self._userdata = UserDataclass()
        self._userdata._create_from_queryresult(queryresult=res)
        if not self._userdata.isActive:
            raise OmasError("Wrong credentials")  # On purpose, we are not providing too much information why the login failed
        hashed = str(self._userdata.credentials).encode('utf-8')
        if not bcrypt.checkpw(credentials.encode('utf-8'), hashed):
            raise OmasError("Wrong credentials")  # On purpose, we are not providing too much information why the login failed

        expiration = datetime.now() + timedelta(days=1)
        payload = {
            "userdata": json.dumps(self._userdata, default=serializer.encoder_default),
            "exp": expiration.timestamp(),
            "iat": int(datetime.now().timestamp()),
            "iss": "http://oldap.org"
        }
        self._token = jwt.encode(
            payload=payload,
            key=Connection.jwtkey,
            algorithm="HS256")

    @property
    def server(self) -> str:
        """Getter for server string"""
        return self._server

    @property
    def repo(self) -> str:
        """Getter for repository name"""
        return self._repo

    def clear_graph(self, graph_iri: Xsd_QName) -> None:
        """
        This method clears (deletes) the given RDF graph. May raise an OmasError.

        :param graph_iri: RDF graph name as QName. The prefix must be defined in the context!
        :return: None
        """
        if not self._userdata:
            raise OmasErrorNoPermission("No permission")
        actor = self._userdata
        sysperms = actor.inProject.get(Xsd_QName('omas:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            raise OmasErrorNoPermission("No permission")

        context = Context(name=self._context_name)
        headers = {
            "Content-Type": "application/sparql-update",
            "Accept": "application/json, text/plain, */*",
        }
        data = f"CLEAR GRAPH <{context.qname2iri(graph_iri)}>"
        req = requests.post(self._update_url,
                            headers=headers,
                            data=data)
        if not req.ok:
            raise OmasError(req.text)

    def clear_repo(self) -> None:
        """
        This method deletes the complete repository. Use with caution!!!

        :return: None
        """
        # if not self._userdata:
        #     raise OmasErrorNoPermission("No permission")
        # actor = self._userdata
        # sysperms = actor.inProject.get(QName('omas:SystemProject'))
        # is_root: bool = False
        # if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
        #     is_root = True
        # if not is_root:
        #     raise OmasErrorNoPermission("No permission")
        headers = {
            "Accept": "application/json, text/plain, */*",
        }
        data = {"update": "CLEAR ALL"}
        req = requests.post(self._update_url,
                            headers=headers,
                            data=data)
        if not req.ok:
            raise OmasError(req.text)

    def upload_turtle(self, filename: str, graphname: Optional[str] = None) -> None:
        """
        Upload a turtle- or trig-file to the given repository. This method returns immediately after sending the
        command to upload the given file to the triplestore. The import process may take a while!

        :param filename: Name of the file to upload
        :param graphname: Optional name of the RDF-graph where the data should be imported in.
        :return: None
        """
        # if not self._userdata:
        #     raise OmasErrorNoPermission("No permission")
        # actor = self._userdata
        # sysperms = actor.inProject.get(QName('omas:SystemProject'))
        # is_root: bool = False
        # if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
        #     is_root = True
        # if not is_root:
        #     raise OmasErrorNoPermission("No permission")

        with open(filename, encoding="utf-8") as f:
            content = f.read()
            ext = Path(filename).suffix
            mime = ""
            if ext == ".ttl":
                mime = "text/turtle"
            elif ext == ".trig":
                mime = "application/x-trig"

            ct = datetime.now()
            ts = ct.timestamp()
            data = {
                "name": f'Data from "{filename}"',
                "status": None,
                "message": "",
                "context": graphname,
                "replaceGraphs": [],
                "baseURI": None,
                "forceSerial": False,
                "type": "text",
                "format": mime,
                "data": content,
                "timestamp": ts,
                "parserSettings": {
                    "preserveBNodeIds": False,
                    "failOnUnknownDataTypes": False,
                    "verifyDataTypeValues": False,
                    "normalizeDataTypeValues": False,
                    "failOnUnknownLanguageTags": False,
                    "verifyLanguageTags": True,
                    "normalizeLanguageTags": True,
                    "stopOnError": True
                }
            }
            jsondata = json.dumps(data)
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json; charset=utf-8"
            }
            url = f"{self._server}/rest/repositories/{self._repo}/import/upload/text"
            req = requests.post(url,
                                headers=headers,
                                data=jsondata)
        if not req.ok:
            raise OmasError(req.text)

    def query(self, query: str, format: SparqlResultFormat = SparqlResultFormat.JSON) -> Any:
        """
        Send a SPARQL-query and return the result. The result may be nested dict (in case of JSON) or a text.

        :param query: SPARQL query as string
        :param format: The format desired (see ~SparqlResultFormat)
        :return: Query results or an error message (as text)
        """
        if not self._userdata:
            raise OmasError("No login")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": format.value,
        }
        data = {
            'query': query,
        }
        res = requests.post(url=self._query_url,
                            headers=headers,
                            data=data)
        if res.status_code == 200:
            return Connection._switcher[format](res)
        else:
            return res.text

    def update_query(self, query: str) -> Dict[str,str]:
        """
        Send an SPARQL UPDATE query to the triple store
        :param query: SPARQL UPDATE query as string
        :return:
        """
        if not self._userdata:
            raise OmasError("No login")
        headers = {
            "Accept": "*/*"
        }
        url = f"{self._server}/repositories/{self._repo}/statements"
        res = requests.post(url, data={"update": query}, headers=headers)
        if not res.ok:
            raise OmasError(f'Update query failed. Reason: "{res.text}"')

    def transaction_start(self) -> None:
        if not self._userdata:
            raise OmasError("No login")
        headers = {
            "Accept": "*/*"
        }
        url = f"{self._server}/repositories/{self._repo}/transactions"
        res = requests.post(url, headers=headers)
        if res.headers.get('location') is None:
            raise OmasError('GraphDB start of transaction failed')
        self._transaction_url = res.headers['location']

    def transaction_query(self, query: str, result_format: SparqlResultFormat = SparqlResultFormat.JSON) -> Any:
        if not self._userdata:
            raise OmasError("No login")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": result_format.value
        }
        if self._transaction_url is None:
            raise OmasError("No GraphDB transaction started")
        res = requests.post(self._transaction_url, data={'action': 'QUERY', 'query': query}, headers=headers)
        if not res.ok:
            raise OmasError(f'GraphDB Transaction query failed. Reason: "{res.text}"')
        return Connection._switcher[result_format](res)

    def transaction_update(self, query: str) -> None:
        if not self._userdata:
            raise OmasError("No login")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "*/*"
        }
        if self._transaction_url is None:
            raise OmasError("No GraphDB transaction started")
        res = requests.post(self._transaction_url, data={'action': 'UPDATE', 'update': query}, headers=headers)
        if not res.ok:
            raise OmasError(f'GraphDB Transaction update failed. Reason: "{res.text}"')

    def transaction_commit(self) -> None:
        if not self._userdata:
            raise OmasError("No login")
        headers = {
            "Accept": "*/*"
        }
        if self._transaction_url is None:
            raise OmasError("No GraphDB transaction started")
        res = requests.put(f'{self._transaction_url}?action=COMMIT', headers=headers)
        if not res.ok:
            raise OmasError(f'GraphDB transaction commit failed. Reason: "{res.text}"')
        self._transaction_url = None

    def transaction_abort(self) -> None:
        if not self._userdata:
            raise OmasError("No login")
        headers = {
            "Accept": "*/*"
        }
        if self._transaction_url is None:
            raise OmasError("No GraphDB transaction started")
        res = requests.delete(self._transaction_url, headers=headers)
        if not res.ok:
            raise OmasError(f'GraphDB transaction abort failed. Reason: "{res.text}"')
        self._transaction_url = None

    def in_transaction(self) -> bool:
        return self._transaction_url is not None



    # def rdflib_query(self, query: str,
    #                  bindings: Optional[Mapping[str, Identifier]] = None) -> Result:
    #     """
    #     Send a SPARQL query to a triple store using the Python rdflib interface.
    #
    #     :param query: SPARQL query string
    #     :param bindings: Bindings to variables
    #     :return: a RDFLib Result instance
    #     """
    #     if not self._userdata:
    #         raise OmasError("No login")
    #     return self._store.query(query, initBindings=bindings)


if __name__ == "__main__":
    con = Connection(server='http://localhost:7200',
                     userId="rosenth",
                     credentials="RioGrande",
                     repo="omas",
                     context_name="DEFAULT")
    con.clear_repo()
    con.upload_turtle("../ontologies/omas.ttl", "http://omas.org/base#onto")
    con.upload_turtle("../ontologies/omas.shacl.trig")
    con.upload_turtle("../ontologies/admin.trig")

