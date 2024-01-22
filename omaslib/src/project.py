import json
from pprint import pprint

from elementpath.datatypes import AnyURI
from pystrict import strict
from typing import List, Set, Dict, Tuple, Optional, Any, Union, Self
from urllib.parse import quote_plus
from datetime import date, datetime

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, QName, NamespaceIRI, AnyIRI
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasError, OmasValueError
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.xsd_datatypes import XsdValidator, XsdDatatypes
from connection import Connection, SparqlResultFormat
from model import Model
from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef, Literal



@strict
class Project(Model):
    __creator: Optional[AnyIRI]
    __created: Optional[datetime]
    __contributor: Optional[AnyIRI]
    __modified: Optional[datetime]
    _projectIri: QName | None
    _namespaceIri: NamespaceIRI | None
    _projectShortName: NCName
    _projectName: LangString
    _projectDescription: LangString | None
    _projectStart: date
    _projectEnd: date | None

    def __init__(self,
                 con: Connection,
                 short_name: NCName,
                 namespace_iri: NamespaceIRI,
                 name: Optional[LangString |str] = None,
                 description: Optional[LangString | str] = None,
                 start: Optional[date] = None,
                 end: Optional[date] = None):
        super().__init__(con)
        self.__creator = con.user_iri
        self.__created = None
        self.__contributor = con.user_iri
        self.__modified = None
        self._namespaceIri = namespace_iri
        if not isinstance(short_name, NCName):
            raise OmasValueError(f'Project ID {short_name} is not a NCName')
        self._project = short_name
        if name is not None:
            self._projectName = name if isinstance(name, LangString) else LangString(name)
        else:
            self._projectName = LangString()
        if description is not None:
            self._projectDescription = description if description is isinstance(description, LangString) else LangString(description)
        else:
            self._projectDescription = LangString()
        if start and isinstance(start, date):
            self._projectStart = start
        else:
            start = datetime.now().date()
        if end and isinstance(end, date):
            self._projectStart = end

    @property
    def projectIri(self) -> QName:
        return self._projectIri

    @projectIri.setter
    def projectIri(self, qName: QName):
        if self._projectIri is None:
            self._projectIri = qName
        else:
            raise OmasValueError(f'')

    def __str__(self) -> str:
        return (f'Project "{self._projectName}":\n  iri: {self._projectIri}\n'
                f'  namespace: {self._namespaceIri}\n  name: {self._projectName}\n'
                f'  description: {self._projectDescription}\n  start: {self._projectStart.isoformat()}\n')

    @classmethod
    def read(cls, con: Connection, id: NCName) -> Self:
        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
            SELECT omas:{id} ?prop ?val
            FROM omas:admin
            WHERE {{
                 ?project ?prop ?val
            }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        project_iri = None
        project_id = None
        namespace_iri = None
        project_name = LangString()
        project_description = LangString()
        project_start = None
        project_end = None
        for r in res:
            if r['prop'] == QName('omas:projectId'):
                project_id = r['val']
            if r['prop'] == QName('omas:namespaceIri'):
                namespace_iri = NamespaceIRI(r['val'])
            elif r['prop'] == QName('omas:projectName'):
                project_name.add(str(r['val']))
            elif r['prop'] == QName('omas:projectDescription'):
                project_description.add(str(r['val']))
            elif r['prop'] == QName('omas:projectStart'):
                project_start = r['val']
            elif r['prop'] == QName('omas:projectEnd'):
                project_end = r['val']

        return cls(con=con,
                   short_name=project_id,
                   namespace_iri=namespace_iri,
                   name=project_name,
                   description=project_description,
                   start=project_start,
                   end=project_end)

    def create(self, indent: int = 0, indent_inc: int = 4):
        timestamp = datetime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

if __name__ == "__main__":
    con = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userid="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
    project = Project.read(con, NCName("system"))
    print(str(project))

    hyha = Project.read(con, NCName("hyha"))
    print(str(hyha))
