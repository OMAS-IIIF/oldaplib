import uuid
from dataclasses import dataclass
from enum import unique, Enum
from functools import partial

from pystrict import strict
from typing import List, Dict, Optional, Self
from datetime import date, datetime

from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.tools import lprint
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorValue, OldapErrorAlreadyExists, OldapErrorNoPermission, \
    OldapErrorUpdateFailed, OldapErrorImmutable, OldapErrorNotFound, OldapErrorInconsistency
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.xsd.xsd_string import Xsd_string

ProjectAttrTypes = LangString | Xsd | None

@dataclass
class ProjectAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: ProjectAttrTypes
    action: Action

@unique
class ProjectAttr(Enum):
    """
    This enum class represents the fields used in the project model
    """
    PROJECT_IRI = 'oldap:projectIri'  # virtual property, repents the RDF subject
    PROJECT_SHORTNAME = 'oldap:projectShortName'
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    NAMESPACE_IRI = 'oldap:namespaceIri'
    PROJECT_START = 'oldap:projectStart'
    PROJECT_END = 'oldap:projectEnd'

#@strict
class Project(Model):
    """
    # Project

    This class implements the Project model. A Project is a distinct research space within Oldap
    framework that offers dedicated space for data, its own data modeling and access control. A project
    needs the following metadata:

    - `projectIri: Iri | None` [optional]:
      The IRI that uniquely identifies this project. This can be an
      [Iri](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.Iri) instance or a string with either an Iri or Qname
      [QName](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.QName). If the `projectIri` is ommitted,
      a random IRI based on the URN semantics will be generated.
    - `projectShortName: Xsd_NCName | str` [mandatory]:
      The short name of the project that must be a NCName or a string
    - `label: LangString | None` [optional]:
      A multilingual string with a human-readable label for the project (`rdfs:label`)
    - `comment: LangString | None` [optional]:
      A multilingual description of the project (`rdfs:comment`)
    - `namespaceIri: NamespaceIri` [mandatory]:
       The namespace that the project uses for its data and data model. Must be
       a [NamespaceIRI](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.NamespaceIRI).
    - `projectStart: Xsd_date | date | None` [optional]:
      The start date of the project.  Must be a Python `date` type. If not set,
       the current date will be used.
    - `projectEnd: Xsd_date | None` [optional]:
      The optional end date of the project. Must be a Xsd_date or a Python `date` type.

    The class provides the following methods:

    - [Project(...)](/python_docstrings/project#oldaplib.src.project.Project.__init__)): Constructor
    - [read(...)](/python_docstrings/project#oldaplib.src.project.Project.read):
      Read project form triplestore and return a Project-instance
    - [search(...)](/python_docstrings/project#oldaplib.src.project.Project.search):
      Search a Project in the triplestore
    - [create(...)](/python_docstrings/project#oldaplib.src.project.Project.create): Create a new project in the triplestore
    - [update(...)](/python_docstrings/project#oldaplib.src.project.Project.update):
      Write changes to triplestore
    - [delete(...)](/python_docstrings/project#oldaplib.src.project.Project.update):
      Delete a project in the triplestore

    The class provides the following properties:

    - `projectIri` [read only]: The project IRI
    - `projectShortName` [read/write]: The project short name. Must be a NCName
    - `projectLabel` [read/write]: The projects label as multilingual LangString
    - `projectComment` [read/write]: The projects comment/description as multilingual
      [LangString](/python_docstrings/langstring)
    - `namespaceIri` [read only]: The namespace that the project uses for its data and data model. Must be
      a [NamespaceIRI](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.NamespaceIRI).
    - `projectStart` [read/write]: The start date of the project. Must be a Python `date` type
    - `projectEnd` [read/write]: The end date of the project. Must be a Python `date` type
    - `creator` [read only]: The creator of the project. Must be a
      [AnyIRI](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.AnyIRI) or
      [QName](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.AnyIRI)
    - `created` [read only]: The creation date of the project. Must be a Python `date` type
    - `contributor` [read only]: The person which made the last changes to the project data. Must be a
      [AnyIRI](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.AnyIRI) or
      [QName](/python_docstrings/datatypes#oldaplib.src.helpers.datatypes.AnyIRI)
    - `modified` [read only]: The modification date of the project. Must be a Python `date` type

    """
    __datatypes = {
        ProjectAttr.PROJECT_IRI: Iri,
        ProjectAttr.PROJECT_SHORTNAME: Xsd_NCName,
        ProjectAttr.LABEL: LangString,
        ProjectAttr.COMMENT: LangString,
        ProjectAttr.NAMESPACE_IRI: NamespaceIRI,
        ProjectAttr.PROJECT_START: Xsd_date,
        ProjectAttr.PROJECT_END: Xsd_date,
    }

    __creator: Iri | None
    __created: Xsd_dateTime | None
    __contributor: Iri | None
    __modified: Xsd_dateTime | None

    __attributes: dict[ProjectAttr, ProjectAttrTypes]

    __changeset: dict[ProjectAttr, ProjectAttrChange]

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 projectIri: Iri | str | None = None,
                 projectShortName: Xsd_NCName | str,
                 namespaceIri: NamespaceIRI,
                 label: LangString | str | None = None,
                 comment: LangString | str | None = None,
                 projectStart: Xsd_date | None = None,
                 projectEnd: Xsd_date | None = None):
        """
        Constructs a new Project
        :param con: [Connection](/python_docstrings/iconnection) instance
        :param creator: Creator of the project  [DO NOT SET!]
        :type creator: Xsd_anyURI | None
        :param created: Date the project was created  [DO NOT SET!]
        :type created: datetime | None
        :param contributor: person that made the last change  [DO NOT SET!]
        :type contributor: Xsd_anyURI
        :param modified: Last date the project was modified  [DO NOT SET!]
        :type modified: date | None
        :param projectIri: IRI to be used for the project. If no projectIRI is provied, the constrctor
         will create an arbitrary IRI based on thr URN scheme and a UUID. [optional].
        :type projectIri: Iri
        :param projectShortName: A short name for the project. Is used as prefix for named graphs that
           are being used for the project. [mandatory]
        :type projectShortName: NCname (strings are accepted only if conform to NCName syntax)
        :param namespaceIri: The namespace to be used for the projects data [mandatory]
        :type namespaceIri: NamespaceIRI
        :param label: Human-readable name for the project (multi-language) (`rdfs:label`) [optional]
        :type label: LangString
        :param comment: Description of the project (multi-language) (`rdfs:comment`)
        :type comment: LangString
        :param projectStart: Start date of the project
        :type projectStart: Python date
        :param projectEnd: End date of the project [Optional]
        :type projectEnd: Python date
        :raises OldapErrorValue: Invalid parameter supplied
        """
        super().__init__(con)
        self.__creator = creator if creator is not None else con.userIri
        if created and not isinstance(created, Xsd_dateTime):
            raise OldapErrorValue(f'Created must be "Xsd_dateTime", not "{type(created)}".')
        self.__created = created
        self.__contributor = contributor if contributor is not None else con.userIri
        if modified and not isinstance(modified, Xsd_dateTime):
            raise OldapErrorValue(f'Modified must be "Xsd_dateTime", not "{type(modified)}".')
        self.__modified = modified
        self.__attributes = {}

        if projectIri:
            if not isinstance(projectIri, Iri):
                self.__attributes[ProjectAttr.PROJECT_IRI] = Iri(projectIri)
            else:
                self.__attributes[ProjectAttr.PROJECT_IRI] = projectIri
        else:
            self.__attributes[ProjectAttr.PROJECT_IRI] = Iri()

        self.__attributes[ProjectAttr.PROJECT_SHORTNAME] = projectShortName if isinstance(projectShortName, Xsd_NCName) else Xsd_NCName(projectShortName)

        if namespaceIri and isinstance(namespaceIri, NamespaceIRI):
            self.__attributes[ProjectAttr.NAMESPACE_IRI] = namespaceIri
        else:
            raise OldapErrorValue(f'Invalid namespace iri: {namespaceIri}')

        self.__attributes[ProjectAttr.LABEL] = label if isinstance(label, LangString) else LangString(label)
        self.__attributes[ProjectAttr.LABEL].set_notifier(self.notifier, Xsd_QName(ProjectAttr.LABEL.value))
        self.__attributes[ProjectAttr.COMMENT] = comment if isinstance(comment, LangString) else LangString(comment)
        self.__attributes[ProjectAttr.COMMENT].set_notifier(self.notifier, Xsd_QName(ProjectAttr.COMMENT.value))
        self.__attributes[ProjectAttr.PROJECT_SHORTNAME] = projectShortName if isinstance(projectShortName, Xsd_NCName) else Xsd_NCName(projectShortName)
        #
        # Consistency checks
        #
        if not self.__attributes[ProjectAttr.LABEL]:
            raise OldapErrorInconsistency(f'Project must have at least one rdfs:label, none given.')
        if projectStart is not None:
            self.__attributes[ProjectAttr.PROJECT_START] = projectStart if isinstance(projectStart, Xsd_date) else Xsd_date(projectStart)
        else:
            self.__attributes[ProjectAttr.PROJECT_START] = Xsd_date()
        if projectEnd is not None:
            self.__attributes[ProjectAttr.PROJECT_END] = projectEnd if isinstance(projectEnd, Xsd_date) else Xsd_date(projectEnd)
            if self.__attributes[ProjectAttr.PROJECT_END] < self.__attributes[ProjectAttr.PROJECT_START]:
                raise OldapErrorInconsistency(f'Project start date {projectStart} is after project end date {projectEnd}.')

        #
        # create all the attributes of the class according to the ProjectFields dfinition
        #
        for attr in ProjectAttr:
            prefix, name = attr.value.split(':')
            setattr(Project, name, property(
                partial(Project.__get_value, attr=attr),
                partial(Project.__set_value, attr=attr),
                partial(Project.__del_value, attr=attr)))
        self.__changeset = {}

    def check_for_permissions(self) -> (bool, str):
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            return True, "OK"
        else:
            return False, "No permission to create a new project."

    def __get_value(self: Self, attr: ProjectAttr) -> ProjectAttrTypes | None:
        tmp = self.__attributes.get(attr)
        if not tmp:
            return None
        return tmp

    def __set_value(self: Self, value: ProjectAttrTypes, attr: ProjectAttr) -> None:
        self.__change_setter(attr, value)

    def __del_value(self: Self, attr: ProjectAttr) -> None:
        self.__changeset[attr] = ProjectAttrChange(self.__attributes[attr], Action.DELETE)
        del self.__attributes[attr]

    #
    # this private method handles the setting of a field. Whenever a field is being
    # set or modified, this method is called. It also puts the original value and the
    # action into the changeset.
    #
    def __change_setter(self, field: ProjectAttr, value: ProjectAttrTypes) -> None:
        if self.__attributes.get(field) == value:
            return
        if field == ProjectAttr.PROJECT_IRI or field == ProjectAttr.NAMESPACE_IRI or field == ProjectAttr.PROJECT_SHORTNAME:
            raise OldapErrorImmutable(f'Field {field.value} is immutable.')
        if field == ProjectAttr.PROJECT_START:
            if self.__attributes.get(ProjectAttr.PROJECT_END) and value >= self.__attributes[ProjectAttr.PROJECT_END]:
                raise OldapErrorInconsistency('Project start date must be less than project end date.')
        if field == ProjectAttr.PROJECT_END:
            if self.__attributes.get(ProjectAttr.PROJECT_START) and value <= self.__attributes[ProjectAttr.PROJECT_START]:
                raise OldapErrorInconsistency('Project end date must be greater than project start date.')
        if self.__attributes.get(field) is None:
            if self.__changeset.get(field) is None:
                self.__changeset[field] = ProjectAttrChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__changeset.get(field) is None:
                    self.__changeset[field] = ProjectAttrChange(self.__attributes[field], Action.DELETE)
            else:
                if self.__changeset.get(field) is None:
                    self.__changeset[field] = ProjectAttrChange(self.__attributes[field], Action.REPLACE)
        if value is None:
            del self.__attributes[field]
        else:
            if not isinstance(value, self.__datatypes[field]):
                self.__attributes[field] = self.__datatypes[field](value)
            else:
                self.__attributes[field] = value

    def __str__(self) -> str:
        """
        String representation of the project. This is a multiline string for the human reader.
        :return: str
        """
        res = f'Project: {self.__attributes[ProjectAttr.PROJECT_IRI]}\n'\
              f'  Creation: {self.__created} by {self.__creator}\n'\
              f'  Modified: {self.__modified} by {self.__contributor}\n'\
              f'  Label: {self.__attributes[ProjectAttr.LABEL]}\n'\
              f'  Comment: {self.__attributes[ProjectAttr.COMMENT]}\n'\
              f'  ShortName: {self.__attributes[ProjectAttr.PROJECT_SHORTNAME]}\n'\
              f'  Namespace IRI: {self.__attributes[ProjectAttr.NAMESPACE_IRI]}\n'\
              f'  Project start: {self.__attributes[ProjectAttr.PROJECT_START]}\n'
        if self.__attributes.get(ProjectAttr.PROJECT_END) is not None:
            res += f'  Project end: {self.__attributes[ProjectAttr.PROJECT_END]}\n'
        return res

    def __getitem__(self, attr: ProjectAttr) -> ProjectAttrTypes:
        return self.__attributes[attr]

    def get(self, attr: ProjectAttr) -> ProjectAttrTypes:
        return self.__attributes.get(attr)

    def __setitem__(self, attr: ProjectAttr, value: ProjectAttrTypes) -> None:
        self.__change_setter(attr, value)

    def __delitem__(self, attr: ProjectAttr) -> None:
        if self.__attributes.get(attr) is not None:
            self.__changeset[attr] = ProjectAttrChange(self.__attributes[attr], Action.DELETE)
            del self.__attributes[attr]


    @property
    def creator(self) -> Iri | None:
        """
        The creator of the project.
        :return: Iri of the creator of the project.
        :rtype: Iri | None
        """
        return self.__creator

    @property
    def created(self) -> Xsd_dateTime | None:
        """
        The creation date of the project.
        :return: Creation date of the project.
        :rtype: Xsd_dateTime | None
        """
        return self.__created

    @property
    def contributor(self) -> Iri | None:
        """
        The contributor of the project as Iri.
        :return: Iri of the contributor of the project.
        :rtype: Iri | None
        """
        return self.__contributor

    @property
    def modified(self) -> Xsd_dateTime | None:
        """
        Modification date of the project.
        :return: Modification date of the project.
        :rtype: Xsd_dateTime | None
        """
        return self.__modified

    @property
    def changeset(self) -> Dict[ProjectAttr, ProjectAttrChange]:
        """
        Return the changeset, that is dicst with information about all properties that have benn changed.
        This method is only for internal use or debugging...
        :return: A dictionary of all changes
        :rtype: Dict[ProjectAttr, ProjectAttrChange]
        """
        return self.__changeset

    def clear_changeset(self) -> None:
        """
        Clear the changeset. This method is only for internal use or debugging...
        :return: None
        """
        self.__changeset = {}

    def notifier(self, fieldname: Xsd_QName) -> None:
        """
        This method is called when a field is being changed.
        :param fieldname: Fieldname of the field being modified
        :return: None
        """
        field = ProjectAttr(fieldname)
        self.__changeset[field] = ProjectAttrChange(self.__attributes[field], Action.MODIFY)

    @classmethod
    def read(cls, con: IConnection, projectIri_SName: Iri | Xsd_NCName | str) -> Self:
        """
        Read the project from the triplestore and return an instance of the project
        :param con: A valid Connection object
        :type con: IConnection
        :param projectIri_SName: The IRI or shortname of the project to be read
        :type projectIri_SName: Iri | Xsd_NCName | str
        :return: Project instance
        :rtype: Project
        :raise: OldapErrorNotFound: project with given Iri not found
        :raise: OldapError: All other errors/problems
        """
        context = Context(name=con.context_name)
        query = context.sparql_context

        projectIri: Iri | None = None
        shortname: Xsd_NCName | None = None
        if isinstance(projectIri_SName, Iri):
            projectIri = projectIri_SName
        elif isinstance(projectIri_SName, Xsd_NCName):
            shortname = Xsd_NCName(projectIri_SName)
        else:
            if ':' in str(projectIri_SName):  # must be IRI or QName
                projectIri = Iri(projectIri_SName)
            else:
                shortname = Xsd_NCName(projectIri_SName)
        if projectIri is not None:
            query += f"""
                SELECT ?prop ?val
                FROM oldap:admin
                WHERE {{
                    {projectIri.toRdf} ?prop ?val
                }}
            """
        elif shortname is not None:
            query += f"""
                SELECT ?proj ?prop ?val
                FROM oldap:admin
                WHERE {{
                    ?proj a oldap:Project .
                    ?proj oldap:projectShortName ?shortname .
                    ?proj ?prop ?val .
                    FILTER(?shortname = {shortname.toRdf})
                }}
            """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'Project with IRI/shortname "{projectIri_SName}" not found.')
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        projectShortName = None
        namespaceIri = None
        label = LangString()
        comment = LangString()
        projectStart = None
        projectEnd = None
        for r in res:
            if projectIri is None:
                projectIri = r['proj']
            match str(r.get('prop')):
                case 'dcterms:creator':
                    creator = r['val']
                case 'dcterms:created':
                    created = r['val']
                case 'dcterms:contributor':
                    contributor = r['val']
                case 'dcterms:modified':
                    modified = r['val']
                case 'oldap:namespaceIri':
                    namespaceIri = NamespaceIRI(r['val'])
                case 'oldap:projectShortName':
                    projectShortName = r['val']
                case 'rdfs:label':
                    label.add(str(r['val']))
                case 'rdfs:comment':
                    comment.add(str(r['val']))
                case 'oldap:projectStart':
                    projectStart = r['val']
                case 'oldap:projectEnd':
                    projectEnd = r['val']
        label.changeset_clear()
        label.set_notifier(cls.notifier, Xsd_QName(ProjectAttr.LABEL.value))
        comment.changeset_clear()
        comment.set_notifier(cls.notifier, Xsd_QName(ProjectAttr.COMMENT.value))
        context[projectShortName] = namespaceIri
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
               label: Xsd_string | str | None = None,
               comment: Xsd_string | str | None = None) -> list[Iri]:
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
        :rtype: List[Iri]
        :raises OldapErrorNotFound: If the project does not exist
        """
        label = Xsd_string(label)
        comment = Xsd_string(comment)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?project\n'
        sparql += 'FROM oldap:admin\n'
        sparql += 'WHERE {\n'
        sparql += '   ?project a oldap:Project .\n'
        if label:
            sparql += '   ?project rdfs:label ?label .\n'
            sparql += f'   FILTER(CONTAINS(STR(?label), "{Xsd_string.escaping(label.value)}"))\n'
        if comment:
            sparql += '   ?project rdfs:comment ?comment .\n'
            sparql += f'   FILTER(CONTAINS(STR(?comment), "{Xsd_string.escaping(comment.value)}"))\n'
        sparql += '}\n'
        # sparql += f"""
        # SELECT DISTINCT ?project
        # FROM oldap:admin
        # WHERE {{
        #     ?project rdfs:label ?label
        #     FILTER(STRSTARTS(?label, "{label}"))
        # }}
        # """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        projects: list[Iri] = []
        if len(res) > 0:
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
        :raises OldapErrorAlreadyExists: If a project with the projectIri already exists
        :raises OldapError: All other errors
        """
        if self._con is None:
            raise OldapError("Cannot create: no connection")
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        indent: int = 0
        indent_inc: int = 4

        context = Context(name=self._con.context_name)

        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?project
        FROM oldap:admin
        WHERE {{
            ?project a oldap:Project .
            FILTER(?project = {self.projectIri.toRdf})
        }}
        """

        blank = ''
        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql2 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{'
        sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.projectIri.toRdf} a oldap:Project'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:projectShortName {self.projectShortName.toRdf}'
        if self.label:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}rdfs:label {self.label.toRdf}'
        if self.comment:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}rdfs:comment {self.comment.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:namespaceIri {self.namespaceIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:projectStart {self.projectStart.toRdf}'
        if self.projectEnd is not None:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:projectEnd {self.projectEnd.toRdf}'
        sparql2 += f' .\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql2 += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A Project with a projectIri "{self.projectIri}" already exists')

        try:
            self._con.transaction_update(sparql2)
        except OldapError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self.__created = timestamp
        self.__creator = self._con.userIri
        self.__modified = timestamp
        self.__contributor = self._con.userIri
        context[self.__attributes[ProjectAttr.PROJECT_SHORTNAME]] = self.__attributes[ProjectAttr.NAMESPACE_IRI]

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Write all the modifications that were applied to the project instqnce to the triple store.
        :param indent: Starting indent for SPARQL queries [Only used for debbugging purposes]
        :type indent: int
        :param indent_inc: Indent increment for SPARQL queries [Only used for debbugging purposes]
        :type indent_inc: int
        :return: None
        :Raises: OldapErrorNoPermission: No permission for operation
        :Raises: OldapErrorUpdateFailed: Update failed
        :Raises: Oldap Error: Other Internal error
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []
        for field, change in self.__changeset.items():
            if field == ProjectAttr.LABEL or field == ProjectAttr.COMMENT:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self.__attributes[field].update(graph=Xsd_QName('oldap:admin'),
                                                                       subject=self.projectIri,
                                                                       subjectvar='?project',
                                                                       field=Xsd_QName(field.value)))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self.__changeset[field].old_value.delete(graph=Xsd_QName('oldap:admin'),
                                                                      subject=self.projectIri,
                                                                      field=Xsd_QName(field.value))
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self.__attributes[field].create(graph=Xsd_QName('oldap:admin'),
                                                             subject=self.projectIri,
                                                             field=Xsd_QName(field.value))
                    sparql_list.append(sparql)
                continue
            sparql = f'{blank:{indent * indent_inc}}# Project field "{field.value}" with action "{change.action.value}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH oldap:admin\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {field.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {field.value} {self.__attributes[field].toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.projectIri.toRdf} as ?project)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?project {field.value} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName('oldap:admin'), self.projectIri, self.modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName('oldap:admin'), self.projectIri)
        except OldapError:
            self._con.transaction_abort()
            raise
        if timestamp != modtime:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed("Update failed! Timestamp does not match")
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self.__modified = timestamp
        self.__contributor = self._con.userIri  # TODO: move creator, created etc. to Model!

    def delete(self) -> None:
        """
        Delete the given user from the triplestore
        :return: None
        :raises OldapErrorNoPermission: No permission for operation
        :raises OldapError: generic internal error
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        #
        # TODO: Check if project as any datamodel and/or data. Decline the deletion if this is the case
        #
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            {self.projectIri.toRdf} a oldap:Project .
            {self.projectIri.toRdf} ?prop ?val .
        }} 
        """
        # TODO: use transaction for error handling
        self._con.update_query(sparql)

