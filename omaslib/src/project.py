import json
import uuid
from dataclasses import dataclass
from enum import unique, Enum
from functools import partial
from pprint import pprint

from pystrict import strict
from typing import List, Set, Dict, Tuple, Optional, Any, Union, Self
from datetime import date, datetime

from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, QName, NamespaceIRI, AnyIRI, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasError, OmasErrorValue, OmasErrorAlreadyExists, OmasErrorNoPermission, OmasErrorUpdateFailed, OmasErrorImmutable
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.tools import lprint
from omaslib.src.iconnection import IConnection
from omaslib.src.model import Model

ProjectFieldTypes = AnyIRI | QName | NCName | LangString | NamespaceIRI | date | None

@dataclass
class ProjectFieldChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: ProjectFieldTypes
    action: Action

@unique
class ProjectFields(Enum):
    """
    This enum class represents the fields used in the project model
    """
    PROJECT_IRI = 'omas:projectIri'  # virtual property, represents the RDF subject
    PROJECT_SHORTNAME = 'omas:projectShortName'
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    NAMESPACE_IRI = 'omas:namespaceIri'
    PROJECT_START = 'omas:projectStart'
    PROJECT_END = 'omas:projectEnd'

@strict
class Project(Model):
    """
    # Project

    This class implements the Project model. A Project is a distinct research space within Oldap
    framework that offers dedicated space for data, its own data modeling and access control. A project
    needs the following metadata:

    - `projectIri`: The IRI that uniquely identifies this project. This can be an
      [AnyIRI](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.AnyIRI) or
      [QName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.QName).
    - `projectShortName`: The short name of the project that must be a NCName
    - `label`: A multilingual string with a human-readable label for the project (`rdfs:label`)
    - `comment`: A multilingual description of the project (`rdfs:comment`)
    - `namespaceIri`: The namespace that the project uses for its data and data model. Must be
       a [NamespaceIRI](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.NamespaceIRI).
    - `projectStart`: The start date of the project.  Must be a Python `date` type.
    - `projectEnd`: The optional end date of the project.Must be a Python `date` type.

    The class provides the following methods:

    - [Project(...)](/python_docstrings/project#omaslib.src.project.Project.__init__)): Constructor
    - [read(...)](/python_docstrings/project#omaslib.src.project.Project.read):
      Read project form triplestore and return a Project-instance
    - [search(...)](/python_docstrings/project#omaslib.src.project.Project.search):
      Search a Project in the triplestore
    - [create(...)](/python_docstrings/project#omaslib.src.project.Project.create): Create a new project in the triplestore
    - [update(...)](/python_docstrings/project#omaslib.src.project.Project.update):
      Write changes to triplestore
    - [delete(...)](/python_docstrings/project#omaslib.src.project.Project.update):
      Delete a project in the triplestore

    The class provides the following properties:

    - `projectIri`: The project IRI [read only]
    - `projectShortName`: The project short name. Must be a NCName [read/write]
    - `projectLabel`: The projects label as multilingual LangString [read/write]
    - `projectComment`: The projects comment/description as multilingual
      [LangString](/python_docstrings/langstring) [read/write]
    - `namespaceIri`: The namespace that the project uses for its data and data model. Must be
      a [NamespaceIRI](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.NamespaceIRI). [read only]
    - `projectStart`: The start date of the project. Must be a Python `date` type [read/write]
    - `projectEnd`: The end date of the project. Must be a Python `date` type [read/write]
    - `creator`: The creator of the project. Must be a
      [AnyIRI](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.AnyIRI) or
      [QName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.AnyIRI) [read only]
    - `created`: The creation date of the project. Must be a Python `date` type [read only]
    - `contributor`: The person which made the last changes to the project data. Must be a
      [AnyIRI](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.AnyIRI) or
      [QName](/python_docstrings/datatypes#omaslib.src.helpers.datatypes.AnyIRI) [read only]
    - `modified`: The modification date of the project. Must be a Python `date` type [read only]

    """
    __datatypes = {
        ProjectFields.PROJECT_IRI: {AnyIRI, QName},
        ProjectFields.PROJECT_SHORTNAME: NCName,
        ProjectFields.LABEL: LangString,
        ProjectFields.COMMENT: LangString,
        ProjectFields.NAMESPACE_IRI: NamespaceIRI,
        ProjectFields.PROJECT_START: date,
        ProjectFields.PROJECT_END: date,
    }
    __repr = {
        ProjectFields.PROJECT_IRI: lambda x: repr(x),
        ProjectFields.PROJECT_SHORTNAME: lambda x: repr(x),
        ProjectFields.LABEL: lambda x: repr(x),
        ProjectFields.COMMENT: lambda x: repr(x),
        ProjectFields.NAMESPACE_IRI: lambda x: repr(x),
        ProjectFields.PROJECT_START: lambda x: f'"{x.isoformat()}"^^xsd:date',
        ProjectFields.PROJECT_END: lambda x: f'"{x.isoformat()}"^^xsd:date',
    }

    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None

    __fields: Dict[ProjectFields, ProjectFieldTypes]

    __change_set: Dict[ProjectFields, ProjectFieldChange]

    def __init__(self, *,
                 con: IConnection,
                 creator: Optional[AnyIRI | QName] = None,
                 created: Optional[datetime] = None,
                 contributor: Optional[AnyIRI | QName] = None,
                 modified: Optional[datetime] = None,
                 projectIri: Optional[AnyIRI | QName] = None,
                 projectShortName: NCName | str,
                 namespaceIri: NamespaceIRI,
                 label: Optional[LangString | str],
                 comment: Optional[LangString | str],
                 projectStart: Optional[date] = None,
                 projectEnd: Optional[date] = None):
        """
        Constructs a new Project
        :param con: [Connection](/python_docstrings/iconnection) instance
        :param creator: Creator of the project  [Optional, usually not set!]
        :type creator: AnyIRI | None
        :param created: Date the project was created  [Optional, usually not set!]
        :type created: datetime | None
        :param contributor: person that made the last change  [Optional, usually not set!]
        :type contributor: AnyIRI
        :param modified: Last date the project was modified  [Optional, usually not set!]
        :type modified: date | None
        :param projectIri: IRI to be used for the project. If no projectIRI is provied, the constrctor
         will create an arbitrary IRI based on thr URN scheme and a UUID. [Optional].
        :type projectIri: AnyIRI | QName
        :param projectShortName: A short name for the project. Is used as prefix for named graphs that
           are being used for the project.
        :type projectShortName: NCname (strings are accepted only if conform to NCName syntax)
        :param namespaceIri: The namespace for the project
        :type namespaceIri: NamespaceIRI
        :param label: Human-readable name for the project (multi-language) (`rdfs:label`)
        :type label: LangString
        :param comment: Description of the project (multi-language) (`rdfs:comment`)
        :type comment: LangString
        :param projectStart: Start date of the project
        :type projectStart: Python date
        :param projectEnd: End date of the project [Optional]
        :type projectEnd: Python date
        """
        super().__init__(con)
        self.__creator = creator if creator is not None else con.userIri
        self.__created = created
        self.__contributor = contributor if contributor is not None else con.userIri
        self.__modified = modified
        self.__fields = {}

        if projectIri:
            if isinstance(projectIri, AnyIRI):
                self.__fields[ProjectFields.PROJECT_IRI] = projectIri
            elif isinstance(projectIri, QName):
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
        self.__fields[ProjectFields.LABEL].set_notifier(self.notifier, QName(ProjectFields.LABEL.value))
        self.__fields[ProjectFields.COMMENT] = comment if isinstance(comment, LangString) else LangString(comment)
        self.__fields[ProjectFields.COMMENT].set_notifier(self.notifier, QName(ProjectFields.COMMENT.value))
        self.__fields[ProjectFields.PROJECT_SHORTNAME] = projectShortName if isinstance(projectShortName, NCName) else NCName(projectShortName)
        if projectStart and isinstance(projectStart, date):
            self.__fields[ProjectFields.PROJECT_START] = projectStart
        else:
            self.__fields[ProjectFields.PROJECT_START] = datetime.now().date()
        if projectEnd and isinstance(projectEnd, date):
            self.__fields[ProjectFields.PROJECT_END] = projectEnd

        #
        # create all the attributes of the class according to the ProjectFields dfinition
        #
        for field in ProjectFields:
            prefix, name = field.value.split(':')
            setattr(Project, name, property(
                partial(Project.__get_value, field=field),
                partial(Project.__set_value, field=field),
                partial(Project.__del_value, field=field)))
        self.__change_set = {}

    def __get_value(self: Self, field: ProjectFields) -> ProjectFieldTypes | None:
        return self.__fields.get(field)

    def __set_value(self: Self, value: ProjectFieldTypes, field: ProjectFields) -> None:
        self.__change_setter(field, value)

    def __del_value(self: Self, field: ProjectFields) -> None:
        del self.__fields[field]

    #
    # this private method handles the setting of a field. Whenever a field is being
    # set or modified, this method is called. It also puts the original value and the
    # action into the changeset.
    #
    def __change_setter(self, field: ProjectFields, value: ProjectFieldTypes) -> None:
        if self.__fields[field] == value:
            return
        if field == ProjectFields.PROJECT_IRI or field == ProjectFields.NAMESPACE_IRI or field == ProjectFields.PROJECT_SHORTNAME:
            raise OmasErrorImmutable(f'Field {field.value} is immutable.')
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
            if not isinstance(value, self.__datatypes[field]):
                self.__fields[field] = self.__datatypes[field](value)
            else:
                self.__fields[field] = value
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

    def notifier(self, fieldname: QName):
        field = ProjectFields(fieldname)
        self.__change_set[field] = ProjectFieldChange(self.__fields[field], Action.MODIFY)
        pass

    @classmethod
    def read(cls, con: IConnection, projectIri: AnyIRI | QName) -> Self:
        """
        Read the project from the triplestore and return an instance of the project
        :param con: A valid Connection object
        :type con: IConnection
        :param projectIri: The IRI/QName of the project to be read
        :type projectIri: AnyIRI | QName
        :return: Project instance
        """
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
        label.changeset_clear()
        label.set_notifier(cls.notifier, QName(ProjectFields.LABEL.value))
        comment.changeset_clear()
        comment.set_notifier(cls.notifier, QName(ProjectFields.COMMENT.value))
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
    def search(con: IConnection,
               label: Optional[str] = None,
               comment: Optional[str] = None) -> List[AnyIRI | QName]:
        """
        Search for a given project. If no label or comment is given, all existing projects are returned. If both
        a search term for the label and comment are given, they will be combined by *AND*.
        :param con: Valid Connection object
        :type con: IConnection
        :param label: A string to search for in the labels. The search will check if the label of a project
        **contains** the string given here.
        :type label: str
        :param comment: A string to search for in the comments. The search will check if the comment of a project
        **contains** the string given here
        :type comment: str
        :return: List of IRIs matching the search criteria (AnyIRI | QName)
        """
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

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Create a new project in the triple store
        :param indent: Start indent level for generated SPARQL (debugging)
        :type indent: int
        :param indent_inc: Indent increment
        :type indent_inc: int
        :return: None
        :raises OmasErrorAlreadyExists: If a project with the projectIri already exists
        :raises OmasError: All other errors
        """
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(QName('omas:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            raise OmasErrorNoPermission(f'No permission to create a new project.')

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
            FILTER(?project = {repr(self.projectIri)})
        }}
        """

        blank = ''
        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql2 += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'
        sparql2 += f'{blank:{(indent + 2) * indent_inc}}{repr(self.projectIri)} a omas:Project ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}dcterms:creator {repr(self._con.userIri)} ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}dcterms:contributor {repr(self._con.userIri)} ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime ;\n'
        sparql2 += f'{blank:{(indent + 3) * indent_inc}}omas:projectShortName {repr(self.projectShortName)} ;\n'
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

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Write all the modifications that were applied to the project instqnce to the triple store.
        :param indent: Starting indent for SPARQL queries [Only used for debbugging purposes]
        :type indent: int
        :param indent_inc: Indent increment for SPARQL queries [Only used for debbugging purposes]
        :type indent_inc: int
        :return: None
        :Raises: OmasErrorNoPermission: No permission for operation
        :Raises: OmasErrorUpdateFailed: Update failed
        :Raises: Omas Error: Other Internal error
        """
        actor = self._con.userdata
        sysperms = actor.inProject.get(QName('omas:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            raise OmasErrorNoPermission(f'No permission to create a new project.')

        timestamp = datetime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []
        for field, change in self.__change_set.items():
            if field == ProjectFields.LABEL or field == ProjectFields.COMMENT:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self.__fields[field].update(graph=QName('omas:admin'),
                                                                   subject=self.projectIri,
                                                                   subjectvar='?project',
                                                                   field=QName(field.value)))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self.__fields[field].delete(graph=QName('omas:admin'),
                                                         subject=self.projectIri,
                                                         field=QName(field.value))
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self.__fields[field].create(graph=QName('omas:admin'),
                                                         subject=self.projectIri,
                                                         field=QName(field.value))
                    sparql_list.append(sparql)
                continue
            sparql = f'{blank:{indent * indent_inc}}# Project field "{field.value}" with action "{change.action.value}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH omas:admin\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {field.value} {self.__repr[field](change.old_value)} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {field.value} {self.__repr[field](self.__fields[field])} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({repr(self.projectIri)} as ?project)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?project {field.value} {self.__repr[field](change.old_value)} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(QName('omas:admin'), self.projectIri, self.modified, timestamp)
            modtime = self.get_modified_by_iri(QName('omas:admin'), self.projectIri)
        except OmasError:
            self._con.transaction_abort()
            raise
        if timestamp != modtime:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed("Update failed! Timestamp does not match")
        try:
            self._con.transaction_commit()
        except OmasError:
            self._con.transaction_abort()
            raise
        self.__modified = timestamp
        self.__contributor = self._con.userIri  # TODO: move creator, created etc. to Model!

    def delete(self) -> None:
        """
        Delete the given user from the triplestore
        :return: None
        :raises OmasErrorNoPermission: No permission for operation
        :raises OmasError: generic internal error
        """
        actor = self._con.userdata
        sysperms = actor.inProject.get(QName('omas:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            raise OmasErrorNoPermission(f'No permission to delete project "{str(self.projectIri)}".')

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            BIND({repr(self.projectIri)} as ?project)
            ?project a omas:Project .
            ?project ?prop ?val .
        }} 
        """
        # TODO: use transaction for error handling
        self._con.update_query(sparql)


if __name__ == "__main__":
    pass
    # con = Connection(server='http://localhost:7200',
    #                  repo="omas",
    #                  userId="rosenth",
    #                  credentials="RioGrande",
    #                  context_name="DEFAULT")
    # project = Project.read(con, QName("omas:SystemProject"))
    # print(str(project))
    #
    # hyha = Project.read(con, QName("omas:HyperHamlet"))
    # print(str(hyha))
    #
    # swissbritnet = Project.read(con, AnyIRI('http://www.salsah.org/version/2.0/SwissBritNet'))
    # print(swissbritnet)
    #
    # p = Project.search(con=con)
    # print(p)
    # print("=================")
    # p = Project.search(con=con, label="Hamlet")
    # print(p)
    # p = Project.search(con=con, comment="Britain")
    # print(p)

