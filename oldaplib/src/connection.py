import json
import os
import time

import bcrypt
import jwt
import requests

from jwt import InvalidTokenError
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from pathlib import Path

from requests.auth import HTTPBasicAuth

from oldaplib.src.oldaplogging import get_logger
from oldaplib.src.version import __version__

from oldaplib.src.cachesingleton import CacheSingleton, CacheSingletonRedis
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.userdataclass import UserData
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission
from oldaplib.src.helpers.context import Context, DEFAULT_CONTEXT
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.xsd.xsd_string import Xsd_string

#
# For bootstrapping the whole tripel store, the following SPARQL has to be executed within the GraphDB
# SPARQL-console:
#
"""
"""
#
# Then, executing the __main__ of the file "connection.py" will initialize the triple store with all the data
# needed to run the tests
#
jwt_format = {
    "userId": "https://orcid.org/0000-0003-1681-4036",
    "exp": "2023-11-04T12:00:00+00:00",
    "iat": datetime.now().astimezone().isoformat(),
    "iss": "http://oldap.org"
}
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIkMmIkMTIkaldDSloucWRYRTlNU0NQZFVjMHk0Ljlzd1dZSmNnTFpuMGVQdFJUdS83VThxSC9PWFhrQjIiLCJleHAiOiIyMDI0LTExLTA0VDEyOjAwOjAwKzAwOjAwIiwiaWF0IjoiMjAyNC0wMS0xOVQyMzo0MTozMS45NTI5MTkiLCJpc3MiOiJodHRwOi8vb2xkYXAub3JnIn0.Vsc2qamfyeTW6Xz5l2Wca-mFnA5PcLuOoWPVEo__4Z4"


class Connection(IConnection):
    """
    Class that implements the connection to an external triple store for oldap.

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
        - Any setting of the _server_, _repo_ or _context_name_ - variables raises an OldapError-exception
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
    _dbuser: str
    _dbpassword: str
    _userdata: Optional[UserData]
    _token: Optional[str]
    _context_name: str = DEFAULT_CONTEXT
    _store: SPARQLUpdateStore
    _query_url: str
    _update_url: str
    _transaction_url: Optional[str]
    __jwtkey: str
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
                 server: Optional[str] = None,
                 repo: Optional[str] = None,
                 userId: Optional[str | Xsd_NCName] = None,
                 credentials: Optional[str | Xsd_string] = None,
                 token: Optional[str] = None,
                 dbuser: Optional[str] = None,
                 dbpassword: Optional[str] = None,
                 context_name: Optional[str] = DEFAULT_CONTEXT) -> None:
        """
        Constructor that establishes the connection parameters.

        :param server: URL of the server (including port information if necessary)
        :type server: str
        :param repo: Name of the triple store repository on the server
        :type repo: str
        :param userId: User identifier for authentication. If not specified, a default "unknown" value
                       is used. Can optionally be validated against `Xsd_NCName`.
        :type userId: Optional[str | Xsd_NCName]
        :param credentials: User credentials for authentication. If not specified, defaults to None.
        :type credentials: Optional[str]
        :param token: JWT token string for authentication. If provided, it bypasses userId and credentials.
        :type token: Optional[str]
        :param context_name: A name of the Context to be used (see ~Context). If no such context exists,
                             a new context with this name is created.
        :type context_name: Optional[str]
        :raises OldapError: Raised when invalid credentials or token are provided, or if there is
                            an issue during the authentication process. Also raised on login failure
                            in specific scenarios.
        """
        super().__init__(context_name=context_name)
        self.__jwtkey = os.getenv("OLDAP_JWT_SECRET", "You have to change this!!! +D&RWG+")
        self._server = server or os.getenv("OLDAP_TS_SERVER", "http://localhost:7200")
        self._repo = repo or os.getenv("OLDAP_TS_REPO", "oldap")
        self._dbuser = dbuser or os.getenv("OLDAP_TS_USER", "")
        self._dbpassword = dbpassword or os.getenv("OLDAP_TS_PASSWORD", "")
        self._query_url = f'{self._server}/repositories/{self._repo}'
        self._update_url = f'{self._server}/repositories/{self._repo}/statements'
        self._store = SPARQLUpdateStore(self._query_url, self._update_url)

        logger = get_logger()

        context = Context(name=context_name)
        if token is not None:
            try:
                payload = jwt.decode(jwt=token, key=self.__jwtkey, algorithms="HS256")
            except InvalidTokenError:
                logger.error("Connection with invalid token")
                raise OldapError("Wrong credentials")
            self._userdata = json.loads(payload['userdata'], object_hook=serializer.decoder_hook)
            self._token = token
            return
        if userId is None and credentials is None:
            userId = Xsd_NCName("unknown", validate=False)
        if not isinstance(userId, Xsd_NCName):
            userId = Xsd_NCName(userId)
        if userId is None:
            logger.error("Connection with wrong credentials")
            raise OldapError("Wrong credentials")
        sparql = UserData.sparql_query(context=context, userId=userId)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8",
        }
        data = {
            'query': sparql,
        }
        #
        # if we have protected the triplestore by a user/password, add it to the request
        #
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        res = requests.post(url=self._query_url, headers=headers, data=data, auth=auth)
        if res.status_code == 200:
            jsonobj = res.json()
        else:
            logger.error(f"Could not connect to triplestore: {res.text}")
            raise OldapError(res.status_code, res.text)
        res = QueryProcessor(context=context, query_result=jsonobj)

        self._userdata = UserData.from_query(res)
        if not self._userdata.isActive:
            logger.error("Connection with wrong credentials")
            raise OldapError("Wrong credentials")  # On purpose, we are not providing too much information why the login failed
        if userId != "unknown":
            hashed = str(self._userdata.credentials).encode('utf-8')
            if not bcrypt.checkpw(credentials.encode('utf-8'), hashed):
                logger.error("Connection with wrong credentials")
                raise OldapError("Wrong credentials")  # On purpose, we are not providing too much information why the login failed

        expiration = datetime.now().astimezone() + timedelta(days=1)
        payload = {
            "userdata": json.dumps(self._userdata, default=serializer.encoder_default),
            "exp": expiration.timestamp(),
            "iat": int(datetime.now().astimezone().timestamp()),
            "iss": "http://oldap.org"
        }
        self._token = jwt.encode(
            payload=payload,
            key=self.__jwtkey,
            algorithm="HS256")
        #
        # Get projects and add to Context
        #
        sparql = context.sparql_context
        sparql += """
        SELECT ?sname ?ns
        FROM oldap:onto
        FROM shared:onto
        FROM NAMED oldap:admin
        WHERE {
            GRAPH oldap:admin {
                ?proj a oldap:Project .
                ?proj oldap:projectShortName ?sname .
                ?proj oldap:namespaceIri ?ns .
            }
        }
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8",
        }
        data = {
            'query': sparql,
        }
        res = requests.post(url=self._query_url, headers=headers, data=data, auth=auth)
        if res.status_code == 200:
            jsonobj = res.json()
        else:
            logger.error(f"Could not connect to triplestore: {res.text}")
            raise OldapError(res.status_code, res.text)
        res = QueryProcessor(context=context, query_result=jsonobj)
        for r in res:
            context[r['sname']] = r['ns']
        logger.info(f'Connection established. User "{str(self._userdata.userId)}".')

    @staticmethod
    def version(self) -> str:
        return __version__

    @property
    def jwtkey(self) -> str:
        """Getter for the JWT token"""
        return self.__jwtkey

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
        Clears (deletes) the given RDF graph from the system.

        This method uses the SPARQL Update protocol to clear the specified graph.
        Permission checks are performed to ensure that the actor has sufficient
        privileges. If the user does not have the required permissions or
        the graph clearing operation fails, appropriate exceptions are raised.

        :param graph_iri: RDF graph name as QName. The prefix must be defined
                          in the context.
        :type graph_iri: Xsd_QName
        :return: None
        :rtype: None
        :raises OldapErrorNoPermission: If the user lacks the required
                                        permission to clear the graph.
        :raises OldapError: If the SPARQL update operation fails.
        """
        logger = get_logger()
        if not self._userdata:
            logger.error("Connection with no permission to clear graph.")
            raise OldapErrorNoPermission("No permission")
        actor = self._userdata
        sysperms = actor.inProject.get(Xsd_QName('oldap:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            raise OldapErrorNoPermission("No permission")

        context = Context(name=self._context_name)
        headers = {
            "Content-Type": "application/sparql-update",
            "Accept": "application/json, text/plain, */*",
        }
        data = f"CLEAR GRAPH <{context.qname2iri(graph_iri)}>"
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        req = requests.post(self._update_url,
                            headers=headers,
                            data=data,
                            auth=auth)
        if not req.ok:
            logger.error(f'Clearing of graph "{graph_iri}" failed: {req.text}')
            raise OldapError(req.text)
        logger.info(f'Graph "{graph_iri}" cleared.')

    def clear_repo(self) -> None:
        """
        Deletes the complete repository. This operation is destructive and should
        be used with extreme caution. Removes all data from the repository and executes
        a "CLEAR ALL" update operation.

        :return: None
        """
        # if not self._userdata:
        #     raise OldapErrorNoPermission("No permission")
        # actor = self._userdata
        # sysperms = actor.inProject.get(QName('oldap:SystemProject'))
        # is_root: bool = False
        # if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
        #     is_root = True
        # if not is_root:
        #     raise OldapErrorNoPermission("No permission")
        headers = {
            "Accept": "application/json, text/plain, */*",
        }
        data = {"update": "CLEAR ALL"}
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        req = requests.post(self._update_url,
                            headers=headers,
                            data=data,
                            auth=auth)
        if not req.ok:
            raise OldapError(req.text)



    def upload_turtle(self, filename: str, graphname: Optional[str] = None) -> None:
        """
        Upload a TTL/TRiG file to GraphDB using the RDF4J /statements endpoint.

        This call is synchronous: when it returns without error, the data is loaded.
        """
        logger = get_logger()

        ext = Path(filename).suffix.lower()
        if ext == ".ttl":
            mime = "text/turtle"
        elif ext == ".trig":
            # use the standard MIME type for TriG
            mime = "application/trig"
        else:
            raise OldapError(f"Unsupported RDF extension: {ext}")

        with open(filename, "rb") as f:
            data = f.read()

        # RDF4J / GraphDB statements endpoint
        url = f"{self._server.rstrip('/')}/repositories/{self._repo}/statements"

        # Optional context: only use this if you really want to force
        # all triples into a single named graph. For TriG you usually
        # leave this empty so the quads' graph IRIs are respected.
        params = {}
        if graphname:
            # GraphDB expects the context IRI wrapped in < > and URL-encoded
            params["context"] = f"<{graphname}>"

        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        headers = {
            "Content-Type": mime,
            "Accept": "text/plain"  # or */*, result body is usually empty
        }

        resp = requests.post(url, params=params, headers=headers, data=data, auth=auth)

        if not resp.ok:
            logger.error(f'Upload of file "{filename}" failed: {resp.status_code} {resp.text}')
            raise OldapError(resp.text)

        logger.info(f'File "{filename}" uploaded synchronously via /statements.')

    def query(self, query: str, format: SparqlResultFormat = SparqlResultFormat.JSON) -> Any:
        """
        Send a SPARQL-query and return the result. The result may be nested dict (in case of JSON) or a text.

        :param query: SPARQL query as string
        :type query: str
        :param format: The format desired (see ~SparqlResultFormat)
        :type format: SparqlResultFormat
        :return: Query results or an error message (as text)
        :rtype: Any
        :raises OldapError: Raised if not logged in or if there is an issue with the query execution.
        """
        logger = get_logger()
        if not self._userdata:
            logger.error("Not a valid user session.")
            raise OldapError("No login")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": format.value,
        }
        data = {
            'query': query,
        }
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        res = requests.post(url=self._query_url,
                            headers=headers,
                            data=data,
                            auth=auth)
        if res.status_code == 200:
            return Connection._switcher[format](res)
        else:
            logger.error(f"SPARQL query failed: {res.text}")
            raise OldapError(res.text)

    def update_query(self, query: str) -> Dict[str,str]:
        """
        Sends an SPARQL UPDATE query to the triple store.

        This method constructs, performs, and handles the response of an SPARQL UPDATE query
        sent to an RDF triple store. If no user session is active, an error will be raised.

        :param query: The SPARQL UPDATE query as a string to be executed on the triple store.
        :type query: str
        :return: A dictionary containing the response information from the triple store.
        :rtype: Dict[str, str
        :raises OldapError: If user authentication is missing or the SPARQL UPDATE execution fails.
        """
        logger = get_logger()
        if not self._userdata:
            logger.error("Not a valid user session.")
            raise OldapError("No login")
        headers = {
            "Accept": "*/*"
        }
        url = f"{self._server}/repositories/{self._repo}/statements"
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        res = requests.post(url, data={"update": query}, headers=headers, auth=auth)
        if not res.ok:
            logger.error(f"SPARQL update query failed: {res.text}")
            raise OldapError(f'Update query failed. Reason: "{res.text}"')

    def transaction_start(self) -> None:
        """
        Initiates a new transaction for the current repository on the server.

        This method starts a transaction by sending a POST request to the server's
        transaction endpoint. If the `location` header is missing in the response,
        it indicates that the transaction initiation failed.

        :raises OldapError: If the user is not logged in or if the transaction cannot
                            be started on the server.
        :return: None
        """
        if not self._userdata:
            raise OldapError("No login")
        headers = {
            "Accept": "*/*"
        }
        url = f"{self._server}/repositories/{self._repo}/transactions"
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        res = requests.post(url, headers=headers, auth=auth)
        if res.headers.get('location') is None:
            raise OldapError('GraphDB start of transaction failed')
        self._transaction_url = res.headers['location']

    def transaction_query(self, query: str, result_format: SparqlResultFormat = SparqlResultFormat.JSON) -> Any:
        """
        Executes a SPARQL query against the currently ongoing transaction in GraphDB.

        This method sends a SPARQL query using HTTP POST to the active transaction URL
        and handles the response based on the provided result format. It ensures that
        the user is authenticated and that a transaction is already started. In case
        of errors, appropriate exceptions are raised.

        :param query: The SPARQL query as a string to execute.
        :type query: str
        :param result_format: The expected format of the SPARQL query result. Defaults
                              to JSON.
        :type result_format: SparqlResultFormat
        :return: The query result in the specified format.
        :rtype: Any
        :raises OldapError: If no user is logged in, no transaction is started, or the
                            query execution fails.
        """
        if not self._userdata:
            raise OldapError("No login")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": result_format.value
        }
        if self._transaction_url is None:
            raise OldapError("No GraphDB transaction started")
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        res = requests.post(self._transaction_url,
                            data={'action': 'QUERY', 'query': query},
                            headers=headers,
                            auth=auth)
        if not res.ok:
            raise OldapError(f'GraphDB Transaction query failed. Reason: "{res.text}"')
        return Connection._switcher[result_format](res)

    def transaction_update(self, query: str) -> None:
        """
        Updates the current GraphDB transaction with a specified SPARQL update query.

        This method sends a POST request to the specified transaction URL with the
        provided SPARQL `query`. It throws an error if the user is not logged in or
        if no GraphDB transaction URL is available. If the request fails, an exception
        is raised containing the reason for the failure.

        :param query: The SPARQL update query to execute as part of the current GraphDB
                      transaction.
        :type query: str
        :raises OldapError: If the user is not logged in or no transaction URL is defined.
        :raises OldapError: If the GraphDB transaction update fails.
        :return: None
        """
        if not self._userdata:
            raise OldapError("No login")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "*/*"
        }
        if self._transaction_url is None:
            raise OldapError("No GraphDB transaction started")
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        res = requests.post(self._transaction_url,
                            data={'action': 'UPDATE', 'update': query},
                            headers=headers,
                            auth=auth)
        if not res.ok:
            raise OldapError(f'GraphDB Transaction update failed. Reason: "{res.text}"')

    def transaction_commit(self) -> None:
        """
        Commits the current transaction for the GraphDB session. This method ensures that
        the transaction completes and is finalized successfully. In the case of an error
        in committing the transaction, it raises an exception to notify the caller.

        :raises OldapError: If the user is not logged in, no transaction is started,
            or the commit operation fails.
        :rtype: None
        :return: None
        """
        if not self._userdata:
            raise OldapError("No login")
        headers = {
            "Accept": "*/*"
        }
        if self._transaction_url is None:
            raise OldapError("No GraphDB transaction started")
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        res = requests.put(f'{self._transaction_url}?action=COMMIT', headers=headers, auth=auth)
        if not res.ok:
            raise OldapError(f'GraphDB transaction commit failed. Reason: "{res.text}"')
        self._transaction_url = None

    def transaction_abort(self) -> None:
        """
        Aborts an ongoing GraphDB transaction if it exists. This method ensures that
        a started transaction is properly terminated to prevent stale or lingering
        transactions.

        :raises OldapError: If the user is not logged in or there is no transaction
            to abort, or if the abort request to the server fails.
        :return: None
        """
        if not self._userdata:
            raise OldapError("No login")
        headers = {
            "Accept": "*/*"
        }
        if self._transaction_url is None:
            raise OldapError("No GraphDB transaction started")
        auth = HTTPBasicAuth(self._dbuser, self._dbpassword) if self._dbuser and self._dbpassword else None
        res = requests.delete(self._transaction_url, headers=headers, auth=auth)
        if not res.ok:
            raise OldapError(f'GraphDB transaction abort failed. Reason: "{res.text}"')
        self._transaction_url = None

    def in_transaction(self) -> bool:
        """
        Determines if the current instance is in a transaction.

        This method checks if there is a transaction URL indicating that a transaction
        is currently active. If `_transaction_url` is not None, it means a transaction
        is in progress. Otherwise, no transaction is active.

        :return: True if in a transaction, False otherwise
        :rtype: bool
        """
        return self._transaction_url is not None


if __name__ == "__main__":
    con = Connection(server='http://localhost:7200',
                     userId="rosenth",
                     credentials="RioGrande",
                     repo="oldap",
                     context_name="DEFAULT")
    cache = CacheSingletonRedis()
    cache.clear()
    con.clear_repo()
    con.upload_turtle("../ontologies/oldap.trig")
    con.upload_turtle("../ontologies/shared.trig")
    con.upload_turtle("../ontologies/admin.trig")

    # Eingabeaufforderung für das Laden der Testinstanzen
    load_test_instances = input("Testinstanzen laden [Y/N] ?(Y): ").strip().lower()
    if not load_test_instances or load_test_instances in ['y', 'yes', 'ja']:
        print("Lade Testinstanzen...")
        con.upload_turtle("../ontologies/admin-testing.trig")
        print("Testinstanzen erfolgreich geladen.")
    else:
        print("Testinstanzen übersprungen.")
