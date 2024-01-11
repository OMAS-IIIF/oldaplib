import json
import datetime
#import urllib

import bcrypt
import requests
from enum import Enum, unique

from pystrict import strict
from typing import List, Set, Dict, Tuple, Optional, Any, Union, Mapping
#from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef, Literal
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from rdflib.query import Result
from rdflib.term import Identifier
#from requests import get, post
from pathlib import Path
#from urllib.parse import quote_plus, urlencode

from omaslib.src.helpers.datatypes import QName, AnyIRI
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.context import Context, DEFAULT_CONTEXT
from omaslib.src.helpers.query_processor import QueryProcessor


#
# For bootstrapping the whole tripel store, the following SPARQL has to be executed within the GraphDB
# SPARQL-console:
#
# PREFIX omas: <http://omas.org/base#>
#
# INSERT DATA {
# 	GRAPH omas:admin {
# 		<https://orcid.org/ORCID-0000-0003-1681-4036> a omas:User ;
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

@unique
class SparqlResultFormat(Enum):
    """
    Enumeration of formats that may be returned by the triple store (if the specific store supports these)
    """
    XML ="application/sparql-results+xml"
    JSON = "application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8" # Accept: application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8
    TURTLE = "text/turtle"
    N3 = "text/rdf+n3"
    NQUADS = "text/x-nquads"
    JSONLD = "application/ld+json"
    TRIX = "application/trix"
    TRIG = "application/x-trig"
    TEXT = "text/plain"


@strict
class Connection:
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
    _userid: str
    _user_iri: QName
    _context_name: str
    _store: SPARQLUpdateStore
    _query_url: str
    _update_url: str
    _transaction_url: Optional[str]
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

    def __init__(self, server: str,
                 repo: str,
                 userid: str,
                 credentials: str,
                 context_name: str = DEFAULT_CONTEXT) -> None:
        """
        Constructor that establishes the connection parameters.

        :param server: URL of the server (including port information if necessary)
        :param repo: Name of the repository on the server
        :param context_name: A name of the Context to be used (see ~Context). If no such context exists,
            a new context of this name is created
        """
        self._server = server
        self._repo = repo
        self._userid = userid
        self._context_name = context_name
        self._query_url = f'{self._server}/repositories/{self._repo}'
        self._update_url = f'{self._server}/repositories/{self._repo}/statements'
        self._store = SPARQLUpdateStore(self._query_url, self._update_url)
        self._transaction_url = None
        context = Context(name=context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?s ?p ?o
        FROM omas:admin
        WHERE {{
            ?s a omas:User ;
                omas:userId "{self._userid}" ;
                ?p ?o .
        }}
        """
        success = False
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
        # TODO: Add more user information / permissions
        for r in res:
            if str(r['p']) == 'omas:userCredentials':
                hashed = str(r['o']).encode('utf-8')
                if bcrypt.checkpw(credentials.encode('utf-8'), hashed):
                    success = True
                    self._user_iri = r['s']
        if not success:
            raise OmasError("Wrong credentials")

    @property
    def server(self) -> str:
        """Getter for server string"""
        return self._server

    @property
    def repo(self) -> str:
        """Getter for repository name"""
        return self._repo

    @property
    def userid(self) -> str:
        return self._userid

    @property
    def user_iri(self) -> QName:
        return self._user_iri

    @property
    def login(self) -> bool:
        return self._user_iri is not None

    @property
    def context_name(self) -> str:
        """Getter for the context name"""
        return self._context_name

    def clear_graph(self, graph_iri: QName) -> None:
        """
        This method clears (deletes) the given RDF graph. May raise an ~herlper.OmasError.

        :param graph_iri: RDF graph name as QName. The prefix must be defined in the context!
        :return: None
        """
        if not self._user_iri:
            raise OmasError("No login")
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
        if not self._user_iri:
            raise OmasError("No login")
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
        if not self._user_iri:
            raise OmasError("No login")
        with open(filename, encoding="utf-8") as f:
            content = f.read()
            ext = Path(filename).suffix
            mime = ""
            if ext == ".ttl":
                mime = "text/turtle"
            elif ext == ".trig":
                mime = "application/x-trig"

            ct = datetime.datetime.now()
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
        if not self._user_iri:
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
        if not self._user_iri:
            raise OmasError("No login")
        headers = {
            "Accept": "*/*"
        }
        url = f"{self._server}/repositories/{self._repo}/statements"
        res = requests.post(url, data={"update": query}, headers=headers)
        if not res.ok:
            raise OmasError(f'Update query failed. Reason: "{res.text}"')

    def transaction_start(self):
        if not self._user_iri:
            raise OmasError("No login")
        headers = {
            "Accept": "*/*"
        }
        url = f"{self._server}/repositories/{self._repo}/transactions"
        res = requests.post(url, headers=headers)
        if res.headers.get('location') is None:
            raise OmasError('GraphDB start of transaction failed')
        self._transaction_url = res.headers['location']

    def transaction_query(self, query: str, result_format: SparqlResultFormat = SparqlResultFormat.JSON):
        if not self._user_iri:
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
        if not self._user_iri:
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
        if not self._user_iri:
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
        if not self._user_iri:
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



    def rdflib_query(self, query: str,
                     bindings: Optional[Mapping[str, Identifier]] = None) -> Result:
        """
        Send a SPARQL query to a triple store using the Python rdflib interface.

        :param query: SPARQL query string
        :param bindings: Bindings to variables
        :return: a RDFLib Result instance
        """
        if not self._user_iri:
            raise OmasError("No login")
        return self._store.query(query, initBindings=bindings)


if __name__ == "__main__":
    con = Connection(server='http://localhost:7200',
                     userid="rosenth",
                     credentials="RioGrande",
                     repo="omas",
                     context_name="DEFAULT")
    con.clear_repo()
    con.upload_turtle("../ontologies/omas.ttl", "http://omas.org/base#onto")
    con.upload_turtle("../ontologies/omas.shacl.trig")
    con.upload_turtle("../ontologies/admin.trig")

