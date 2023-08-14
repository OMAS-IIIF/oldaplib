import json
import datetime
import urllib
import requests
from enum import Enum, unique

from pystrict import strict
from typing import List, Set, Dict, Tuple, Optional, Any, Union
from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef, Literal
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from requests import get, post
from pathlib import Path
from urllib.parse import quote_plus

from helpers.omaserror import OmasError
from omaslib.src.helpers.context import Context, DEFAULT_CONTEXT


@unique
class SparqlResultFormat(Enum):
    XML ="application/sparql-results+xml"
    JSON = "application/sparql-results+json"
    TURTLE = "text/turtle"
    N3 = "text/rdf+n3"
    NQUADS = "text/x-nquads"
    JSONLD = "application/ld+json"
    TRIX = "application/trix"
    TRIG = "application/x-trig"
    TEXT = "text/plain"


@strict
class Connection:
    _server: str
    _repo: str
    _context_name: str
    _store: SPARQLUpdateStore
    _query_url: str
    _update_url: str
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

    def __init__(self, server: str, repo: str, context_name: str = DEFAULT_CONTEXT):
        self._server = server
        self._repo = repo
        self._context_name = context_name
        self._query_url = f'{self._server}/repositories/{self._repo}'
        self._update_url = f'{self._server}/repositories/{self._repo}/statements'
        self._store = SPARQLUpdateStore(self._query_url, self._update_url)
        context = Context(name=context_name)
        for prefix, iri in context.items():
            self._store.bind(str(prefix), Namespace(str(iri)))


    @property
    def server(self) -> str:
        return self._server

    @server.setter
    def server(self, value: Any) -> None:
        raise OmasError('Cannot change the server of a connection!')

    @property
    def repo(self) -> str:
        return self._repo

    @repo.setter
    def repo(self, value: Any) -> None:
        raise OmasError('Cannot change the repo of a connection!')

    @property
    def context_name(self) -> str:
        return self._context_name

    @context_name.setter
    def context_name(self, value: Any) -> None:
        raise OmasError('Cannot change the context name of a connection!')

    def clear_repo(self):
        headers = {
            "Accept": "application/json, text/plain, */*",
        }
        data = {"update": "CLEAR ALL"}
        req = requests.post(self._update_url,
                            headers=headers,
                            data=data)
        print(req.text)
        print(req.headers)

    def upload_turtle(self, filename: str, graphname: Optional[str] = None):
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
        print(req.text)
        print(req.headers)


    def query(self, query: str, format: SparqlResultFormat = SparqlResultFormat.JSON) -> Any:
        headers = {
            "Content-Type": "application/sparql-query",
            "Accept": format.value,
        }
        encoded_query = urllib.parse.quote_plus(query)
        url = f"{self._server}/repositories/{self._repo}"  # ?query={encoded_query}&queryLn=sparql"

        res = requests.post(self._query_url, data=query, headers=headers)
        if res.status_code == 200:
            return Connection._switcher[format](res)
        else:
            return res.text

    def update_query(self, query: str) -> Any:
        headers = {
            "Accept": "*/*"
        }
        url = f"{self._server}/repositories/{self._repo}/statements"
        res = requests.post(url, data={"update": query}, headers=headers)
        if res.status_code == 204:
            print("UPDATE SUCCESS")
        else:
            print("UPDATE FAILURE:", res.text)


    def rdflib_query(self, query: str) -> Any:
        return self._store.query(query)


if __name__ == "__main__":
    con_A = Connection(server='http://localhost:7200',
                       repo="omas",
                       context_name="DEFAULT")
    con_A.clear_repo()
    con_A.upload_turtle("../ontologies/omas.ttl", "http://omas.org/base#onto")
    con_A.upload_turtle("../ontologies/omas.shacl.trig")


