import json
import uuid
from dataclasses import dataclass
from enum import unique, Enum
from functools import partial
from pprint import pprint

from elementpath.datatypes import AnyURI
from pystrict import strict
from typing import List, Set, Dict, Tuple, Optional, Any, Union, Self
from urllib.parse import quote_plus
from datetime import date, datetime

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, QName, NamespaceIRI, AnyIRI, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasError, OmasErrorValue, OmasErrorAlreadyExists
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.xsd_datatypes import XsdValidator, XsdDatatypes
from connection import Connection, SparqlResultFormat
from model import Model
from rdflib import Graph, ConjunctiveGraph, Namespace, URIRef, Literal

ProjectFieldTypes = AnyIRI | NCName | LangString | NamespaceIRI | date | None

@dataclass
class ProjectFieldChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: ProjectFieldTypes
    action: Action

@unique
class ProjectFields(Enum):
    PROJECT_IRI = 'omas:projectIri'  # virtual property, no equivalent in RDF
    PROJECT_SHORTNAME = 'omas:projectShortName'
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    NAMESPACE_IRI = 'omas:namespaceIri'
    PROJECT_START = 'omas:projectStart'
    PROJECT_END = 'omas:projectEnd'

@strict
class Project(Model):
    __datatypes = {
        ProjectFields.PROJECT_IRI: AnyIRI,
        ProjectFields.PROJECT_SHORTNAME: NCName,
        ProjectFields.LABEL: LangString,
        ProjectFields.COMMENT: LangString,
        ProjectFields.NAMESPACE_IRI: NamespaceIRI,
        ProjectFields.PROJECT_START: date,
        ProjectFields.PROJECT_END: date,
    }

    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None

    __fields: Dict[ProjectFields, ProjectFieldTypes]

    __change_set: Dict[ProjectFields, ProjectFieldChange]

    def __init__(self, *,
                 con: Connection,
                 creator: Optional[AnyIRI] = None,
                 created: Optional[datetime] = None,
                 contributor: Optional[AnyIRI] = None,
                 modified: Optional[datetime] = None,
                 projectIri: Optional[AnyIRI] = None,
                 projectShortName: NCName | str,
                 namespaceIri: NamespaceIRI | QName,
                 label: Optional[LangString | str],
                 comment: Optional[LangString | str],
                 projectStart: Optional[date] = None,
                 projectEnd: Optional[date] = None):
        super().__init__(con)
        self.__creator = creator if creator is not None else con.userIri
        self.__created = created
        self.__contributor = contributor if contributor is not None else con.userIri
        self.__modified = modified
        self.__fields = {}

        if projectIri:
            if isinstance(projectIri, AnyIRI):
                self.__fields[ProjectFields.PROJECT_IRI] = projectIri
            else:
                raise OmasErrorValue(f'projectIri {projectIri} must be an instance of AnyIRI, not {type(projectIri)}')
        else:
            self.__fields[ProjectFields.PROJECT_IRI] = AnyIRI(uuid.uuid4().urn)

        self.__fields[ProjectFields.PROJECT_SHORTNAME] = projectShortName if isinstance(projectShortName, NCName) else NCName(projectShortName)

        if namespaceIri and isinstance(namespaceIri, NamespaceIRI):
            self.__fields[ProjectFields.NAMESPACE_IRI] = namespaceIri
        else:
            raise OmasErrorValue(f'Invalid namespace iri: {namespaceIri}')

        self.__fields[ProjectFields.LABEL] = label if isinstance(label, LangString) else LangString(label)
        self.__fields[ProjectFields.COMMENT] = comment if isinstance(comment, LangString) else LangString(comment)
        self.__fields[ProjectFields.PROJECT_SHORTNAME] = projectShortName if isinstance(projectShortName, NCName) else NCName(projectShortName)
        if projectStart and isinstance(projectStart, date):
            self.__fields[ProjectFields.PROJECT_START] = projectStart
        else:
            self.__fields[ProjectFields.PROJECT_START] = datetime.now().date()
        if projectEnd and isinstance(projectEnd, date):
            self.__fields[ProjectFields.PROJECT_END] = projectEnd

        for field in ProjectFields:
            prefix, name = field.value.split(':')
            setattr(Project, name, property(
                partial(self.__get_value, field=field),
                partial(self.__set_value, field=field),
                partial(self.__del_value, field=field)))
        self.__change_set = {}


    def __get_value(self: Self, self2: Self, field: ProjectFields) -> ProjectFieldTypes | None:
        return self.__fields.get(field)

    def __set_value(self: Self, self2: Self, value: ProjectFieldTypes, field: ProjectFields) -> None:
        if field == ProjectFields.PROJECT_IRI and self.__fields.get(ProjectFields.PROJECT_IRI) is not None:
            OmasErrorAlreadyExists(f'A project IRI already has been assigned: "{repr(self.__fields.get(ProjectFields.PROJECT_IRI))}".')
        self.__change_setter(field, value)

    def __del_value(self: Self, self2: Self, field: ProjectFields) -> None:
        del self.__fields[field]

    #
    # this private method handles the setting of a field. Whenever a field is being
    # set or modified, this method is called. It also puts the original value and the
    # action into the changeset.
    #
    def __change_setter(self, field: ProjectFields, value: ProjectFieldTypes) -> None:
        if self.__fields[field] == value:
            return
        if field == ProjectFields.PROJECT_IRI or field == ProjectFields.NAMESPACE_IRI:
            raise OmasErrorAlreadyExists(f'Field {field.value} is immutable.')
        if self.__fields[field] is None:
            if self.__change_set.get(field) is None:
                self.__change_set[field] = ProjectFieldChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__change_set.get(field) is None:
                    self.__change_set[field] = ProjectFieldChange(self.__fields[field], Action.DELETE)
            else:
                if self.__change_set.get(field) is None:
                    self.__change_set[field] = ProjectFieldChange(self.__fields[field], Action.REPLACE)
        if value is None:
            del self.__fields[field]
        else:
            self.__fields[field] = self.__datatypes[field](value)


    def __str__(self) -> str:
        res = f'Project: {self.__fields[ProjectFields.PROJECT_IRI]}\n'\
              f'  Creation: {self.__created.isoformat()} by {self.__creator}\n'\
              f'  Modified: {self.__modified.isoformat()} by {self.__contributor}\n'\
              f'  Label: {self.__fields[ProjectFields.LABEL]}\n'\
              f'  Comment: {self.__fields[ProjectFields.COMMENT]}\n'\
              f'  Namespace IRI: {self.__fields[ProjectFields.NAMESPACE_IRI]}\n'\
              f'  Project start: {self.__fields[ProjectFields.PROJECT_START].isoformat()}\n'
        if self.__fields.get(ProjectFields.PROJECT_END) is not None:
            res += f'  Project end: {self.__fields[ProjectFields.PROJECT_END].isoformat()}\n'
        return res

    @property
    def creator(self) -> AnyIRI | None:
        return self.__creator

    @property
    def created(self) -> datetime | None:
        return self.__created

    @property
    def contributor(self) -> AnyIRI | None:
        return self.__contributor

    @property
    def modified(self) -> datetime | None:
        return self.__modified

    @property
    def changeset(self) -> Dict[ProjectFields, ProjectFieldChange]:
        """
        Return the changeset, that is dicst with information about all properties that have benn changed.
        :return: A dictionary of all changes
        """
        return self.__change_set

    def clear_changeset(self) -> None:
        """
        Clear the changeset.
        :return: None
        """
        self.__change_set = {}

    @classmethod
    def read(cls, con: Connection, projectIri: AnyIRI | QName) -> Self:
        context = Context(name=con.context_name)
        if isinstance(projectIri, QName):
            projectIri = context.qname2iri(projectIri)
        query = context.sparql_context
        query += f"""
            SELECT ?prop ?val
            FROM omas:admin
            WHERE {{
                {repr(projectIri)} ?prop ?val
            }}
        """
        jsonobj = con.query(query)
        pprint(jsonobj)
        res = QueryProcessor(context, jsonobj)
        creator = None
        created = None
        contributor = None
        modified = None
        projectShortName = None
        namespaceIri = None
        label = LangString()
        comment = LangString()
        projectStart = None
        projectEnd = None
        for r in res:
            match str(r.get('prop')):
                case 'dcterms:creator':
                    creator = r['val']
                case 'dcterms:created':
                    created = r['val']
                case 'dcterms:contributor':
                    contributor = r['val']
                case 'dcterms:modified':
                    modified = r['val']
                case 'omas:namespaceIri':
                    namespaceIri = NamespaceIRI(r['val'])
                case 'omas:projectShortName':
                    projectShortName = r['val']
                case 'rdfs:label':
                    label.add(str(r['val']))
                case 'rdfs:comment':
                    comment.add(str(r['val']))
                case 'omas:projectStart':
                    projectStart = r['val']
                case 'omas:projectEnd':
                    projectEnd = r['val']
        return cls(con=con,
                   creator=creator,
                   created=created,
                   contributor=contributor,
                   modified=modified,
                   projectIri=projectIri,
                   projectShortName=projectShortName,
                   label=label,
                   namespaceIri=namespaceIri,
                   comment=comment,
                   projectStart=projectStart,
                   projectEnd=projectEnd)

    @staticmethod
    def search(*,
               con: Connection,
               label: Optional[str] = None,
               comment: Optional[str] = None) -> List[AnyIRI | QName]:
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?project\n'
        sparql += 'FROM omas:admin\n'
        sparql += 'WHERE {\n'
        sparql += '   ?project a omas:Project .\n'
        if label is not None:
            sparql += '   ?project rdfs:label ?label .\n'
            sparql += f'   FILTER(CONTAINS(STR(?label), "{label}"))\n'
        if comment is not None:
            sparql += '   ?project rdfs:comment ?comment .\n'
            sparql += f'   FILTER(CONTAINS(STR(?comment), "{comment}"))\n'
        sparql += '}\n'
        # sparql += f"""
        # SELECT DISTINCT ?project
        # FROM omas:admin
        # WHERE {{
        #     ?project rdfs:label ?label
        #     FILTER(STRSTARTS(?label, "{label}"))
        # }}
        # """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        projects = []
        for r in res:
            projects.append(r['project'])
        return projects

    def create(self, indent: int = 0, indent_inc: int = 4):
        timestamp = datetime.now()
        indent: int = 0
        indent_inc: int = 4
        if self._con is None:
            raise OmasError("Cannot create: no connection")

        context = Context(name=self._con.context_name)

        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?project
        FROM omas:admin
        WHERE {{
            ?user a omas:Project .
            FILTER(?project = {repr(self.__projectIri)})
        }}
        """

        blank = ''
        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql2 += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'
        sparql2 += f'{blank:{(indent + 2) * indent_inc}}{repr(self.projectIri)} a omas:Project ;\n'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator <{self._con.userIri}>'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor <{self._con.userIri}>'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}omas:projectShortName {self.projectShortName} ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}rdfs:label {repr(self.label)} ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}rdfs:comment {repr(self.comment)} ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}omas:namespaceIri "{str(self.namespaceIri)}"^^xsd:anyURI ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}omas:projectStart "{self.projectStart.isoformat()}"^^xsd:date ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}omas:projectEnd "{self.projectEnd.isoformat()}"^^xsd:date .\n'
        sparql2 += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql2 += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OmasError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OmasErrorAlreadyExists(f'A Project with a projectIri "{self.projectIri}" already exists')

        try:
            self._con.transaction_update(sparql2)
        except OmasError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OmasError:
            self._con.transaction_abort()
            raise


if __name__ == "__main__":
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    project = Project.read(con, QName("omas:SystemProject"))
    print(str(project))

    hyha = Project.read(con, QName("omas:HyperHamlet"))
    print(str(hyha))

    swissbritnet = Project.read(con, AnyIRI('http://www.salsah.org/version/2.0/SwissBritNet'))
    print(swissbritnet)

    p = Project.search(con=con)
    print(p)
    print("=================")
    p = Project.search(con=con, label="Hamlet")
    print(p)
    p = Project.search(con=con, comment="Britain")
    print(p)

