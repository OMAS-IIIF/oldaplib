import json
from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from pprint import pprint

from typing import List, Self, Any, Callable
from datetime import date, datetime

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.projectattr import ProjectAttr
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.helpers.tools import lprint
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorAlreadyExists, OldapErrorNoPermission, \
    OldapErrorUpdateFailed, OldapErrorNotFound, OldapErrorInconsistency
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.xsd.xsd_string import Xsd_string

@serializer
@dataclass(frozen=True)
class ProjectSearchResult:
    projectIri: IriOrNCName
    projectShortName: Xsd_NCName

    def _as_dict(self):
        return {'projectIri': self.projectIri, 'projectShortName': self.projectShortName}


#@strict
@serializer
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

    #_attributes: dict[ProjectAttr, ProjectAttrTypes]
    #__changeset: dict[ProjectAttr, ProjectAttrChange]

    __slots__ = ('projectIri', 'projectShortName', 'label', 'comment', 'namespaceIri', 'projectStart', 'projectEnd')

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str | None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | str | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 validate: bool = False,
                 **kwargs):
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
        super().__init__(connection=con,
                         created=created,
                         creator=creator,
                         modified=modified,
                         contributor=contributor,
                         validate=validate)

        self.set_attributes(kwargs, ProjectAttr)
        #
        # Consistency checks
        #
        if not self._attributes.get(ProjectAttr.PROJECT_IRI):
            self._attributes[ProjectAttr.PROJECT_IRI] = Iri()
        if not self._attributes.get(ProjectAttr.PROJECT_START):
            self._attributes[ProjectAttr.PROJECT_START] = Xsd_date()
        if self._attributes.get(ProjectAttr.PROJECT_END):
            self.check_consistency(ProjectAttr.PROJECT_END, self._attributes[ProjectAttr.PROJECT_END])
        if self._attributes.get(ProjectAttr.PROJECT_START):
            self.check_consistency(ProjectAttr.PROJECT_START, self._attributes[ProjectAttr.PROJECT_START])
        #
        # create all the attributes of the class according to the ProjectFields dfinition
        #
        for attr in ProjectAttr:
            setattr(Project, attr.value.fragment, property(
                partial(Project._get_value, attr=attr),
                partial(Project._set_value, attr=attr),
                partial(Project._del_value, attr=attr)))
        self._changeset = {}

    def update_notifier(self):
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict()

    def __deepcopy__(self, memo: dict[Any, Any]) -> Self:
        if id(self) in memo:
            return memo[id(self)]
        cls = self.__class__
        instance = cls.__new__(cls)
        memo[id(self)] = instance
        Model.__init__(instance,
                       connection=deepcopy(self._con, memo),
                       creator=deepcopy(self._creator, memo),
                       created=deepcopy(self._created, memo),
                       contributor=deepcopy(self._contributor, memo),
                       modified=deepcopy(self._modified, memo))
        # Copy internals of Model:
        instance._attributes = deepcopy(self._attributes, memo)
        instance._changset = deepcopy(self._changeset, memo)
        return instance

    def __eq__(self, other: Self) -> bool:
        if not isinstance(other, Project):
            return False
        return self._as_dict() == other._as_dict()

    def check_consistency(self, attr: ProjectAttr, value: Any) -> None:
        if attr == ProjectAttr.PROJECT_END:
            if self._attributes.get(ProjectAttr.PROJECT_START) and value < self._attributes[ProjectAttr.PROJECT_START]:
                raise OldapErrorInconsistency(f'Project start date {self._attributes[ProjectAttr.PROJECT_START]} is after project end date {value}.')

        if attr == ProjectAttr.PROJECT_START:
            if self._attributes.get(ProjectAttr.PROJECT_END) and value > self._attributes[ProjectAttr.PROJECT_END]:
                raise OldapErrorInconsistency(f'Project start date {value} is after project end date {self._attributes[ProjectAttr.PROJECT_END]}.')

    def check_for_permissions(self) -> (bool, str):
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            return True, "OK"
        else:
            return False, "No permission to create/change a project."

    def notifier(self, attr: ProjectAttr) -> None:
        """
        This method is called when a field is being changed.
        :param fieldname: Fieldname of the field being modified
        :return: None
        """
        self._changeset[attr] = AttributeChange(self._attributes[attr], Action.MODIFY)



    @classmethod
    def read(cls,
             con: IConnection,
             projectIri_SName: IriOrNCName | Iri | Xsd_NCName | str,
             ignore_cache: bool = False) -> Self:
        """
        Reads the project from the triplestore and returns an instance of the project.

        This method queries the triplestore based on a provided IRI or shortname of the project,
        optionally utilizing a cache for optimization. If the project is found, it fetches and
        processes the project's data including metadata and creates an instance of the project.
        If not found, an appropriate error is raised.

        :param con: A valid connection to the triplestore.
        :type con: IConnection
        :param projectIri_SName: The IRI or shortname of the project to be read.
        :type projectIri_SName: IriOrNCName | Iri | Xsd_NCName | str
        :param ignore_cache: Whether to bypass the cache and query the triplestore directly.
        :type ignore_cache: bool
        :return: An instance of the project with the fetched data.
        :rtype: Self
        :raises OldapErrorNotFound: If the project with the specified IRI or shortname is not found.
        :raises OldapError: If other errors or problems occur during the process.
        """
        context = Context(name=con.context_name)
        query = context.sparql_context

        if not isinstance(projectIri_SName, IriOrNCName):
            projectIri_SName = IriOrNCName(projectIri_SName, validate=True)
        shortname, projectIri = projectIri_SName.value()
        # projectIri: Iri | None = None
        # shortname: Xsd_NCName | None = None
        # if isinstance(projectIri_SName, Iri):
        #     projectIri = projectIri_SName
        # elif isinstance(projectIri_SName, Xsd_NCName):
        #     shortname = Xsd_NCName(projectIri_SName)
        # else:
        #     if ':' in str(projectIri_SName):  # must be IRI or QName
        #         projectIri = Iri(projectIri_SName)
        #     else:
        #         shortname = Xsd_NCName(projectIri_SName)
        cache = CacheSingletonRedis()
        if projectIri is not None:
            if not ignore_cache:
                tmp = cache.get(projectIri, connection=con)
                if tmp is not None:
                    tmp.update_notifier()
                    return tmp
            query += f"""
                SELECT ?prop ?val
                FROM NAMED oldap:admin
                WHERE {{
                    GRAPH oldap:admin {{
                        {projectIri.toRdf} ?prop ?val
                    }}
                }}
            """
        elif shortname is not None:
            if not ignore_cache:
                tmp = cache.get(shortname, connection=con)
                if tmp is not None:
                    tmp._con = con
                    return tmp
            query += f"""
                SELECT ?proj ?prop ?val ?prefix ?iri
                WHERE {{
                    GRAPH oldap:admin {{
                        ?proj a oldap:Project .
                        ?proj oldap:projectShortName {shortname.toRdf} .
                        ?proj ?prop ?val .
                        OPTIONAL {{
                            ?val oldap:prefix ?prefix .
                            ?val oldap:fullIri ?iri
                        }}
                    }}
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
        if label:
            label.clear_changeset()
            label.set_notifier(cls.notifier, Xsd_QName(ProjectAttr.LABEL.value))
        if comment:
            comment.clear_changeset()
            comment.set_notifier(cls.notifier, Xsd_QName(ProjectAttr.COMMENT.value))
        context[projectShortName] = namespaceIri
        instance = cls(con=con,
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
        cache = CacheSingletonRedis()
        cache.set(instance.projectIri, instance, instance.projectShortName)
        return instance

    @staticmethod
    def search(con: IConnection,
               label: Xsd_string | str | None = None,
               comment: Xsd_string | str | None = None) -> list[ProjectSearchResult]:
        """
        Search for projects based on the provided label and/or comment. If no label or comment is provided, all
        existing projects are returned. When both label and comment are specified, the search combines their
        conditions using logical AND.

        :param con: Valid connection object representing the current context
        :type con: IConnection
        :param label: String to search within project labels. The label search is performed by checking
            if a project's label contains the specified string.
        :type label: Xsd_string or str or None
        :param comment: String to search within project comments. The comment search is performed by
            checking if a project's comment contains the specified string.
        :type comment: Xsd_string or str or None
        :return: List of project search results matching the specified criteria.
        :rtype: list[ProjectSearchResult]
        :raises OldapErrorNotFound: Raised if the project does not exist in the repository or cannot
            be located based on the search criteria.
        """
        label = Xsd_string(label, validate=True)
        comment = Xsd_string(comment, validate=True)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?project ?shortname\n'
        sparql += 'FROM oldap:onto\n'
        sparql += 'FROM shared:onto\n'
        sparql += 'FROM NAMED oldap:admin\n'
        sparql += 'WHERE {\n'
        sparql += '    GRAPH oldap:admin {\n'
        sparql += '        ?project a oldap:Project .\n'
        sparql += '        ?project oldap:projectShortName ?shortname .\n'
        if label:
            sparql += '        ?project rdfs:label ?label .\n'
            sparql += '    }\n'
            sparql += f'    FILTER(CONTAINS(STR(?label), "{Xsd_string.escaping(label.value)}"))\n'
        if comment:
            sparql += '        ?project rdfs:comment ?comment .\n'
            sparql += '    }\n'
            sparql += f'    FILTER(CONTAINS(STR(?comment), "{Xsd_string.escaping(comment.value)}"))\n'
        if not label and not comment:
            sparql += '    }\n'
        sparql += '}\n'
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        projects: list[tuple(Iri, Xsd_NCName)] = []
        if len(res) > 0:
            for r in res:
                projects.append(ProjectSearchResult(r['project'], r['shortname']))
        return projects


    def trig_to_str(self, created: Xsd_dateTime, modified: Xsd_dateTime,indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        sparql += f'\n{blank:{indent * indent_inc}}{self.projectIri.toRdf} a oldap:Project'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {created.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {modified.toRdf}'
        for attr, value in self._attributes.items():
            if not value:
                continue
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{attr.value.toRdf} {value.toRdf}'
        return sparql

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Creates a new project in the triple store. The function starts by
        checking if the connection is available, verifies if the user
        has the required permissions, and then proceeds to execute
        SPARQL queries to ensure the project does not already exist.
        If the project doesn't exist, it creates the project by
        constructing and executing SPARQL INSERT queries. It also
        updates the project metadata, including timestamps and user
        information.

        :param indent: The start indent level for the generated SPARQL
            query, primarily used for debugging.
        :type indent: int
        :param indent_inc: The increment for indentation level, which
            affects how the SPARQL query is formatted.
        :type indent_inc: int
        :return: None
        :raises OldapErrorAlreadyExists: If a project already exists with
            the same project IRI.
        :raises OldapError: If any other errors occur during execution.
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
        #indent: int = 0
        #indent_inc: int = 4

        context = Context(name=self._con.context_name)

        #
        # SPARQL to check if project with the given projectShortName already exists
        #
        sparql0 = context.sparql_context
        sparql0 += f"""
        ASK {{
            GRAPH oldap:admin {{
    	        ?p a oldap:Project ;
    		        oldap:projectShortName ?sname .
    	        FILTER(?sname = {self.projectShortName.toRdf})
	        }}
        }}
        """

        #
        # SPARQL to check if the given namespaceIri is already used by another project
        #
        sparql1a = context.sparql_context
        sparql1a += f"""
        ASK {{
            GRAPH oldap:admin {{
                ?project oldap:namespaceIri {self.namespaceIri.toRdf} .
            }}
        }}
        """

        #
        # SPARQL to check if project with the given projectIri already exists
        #
        sparql1b = context.sparql_context
        sparql1b += f"""
        ASK {{
            GRAPH oldap:admin {{
                {self.projectIri.toRdf} ?p ?o .
            }}
        }}
        """

        blank = ''
        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql2 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{'
        sparql2 += self.trig_to_str(created=timestamp, modified=timestamp, indent=indent + 2, indent_inc=indent_inc)
        # sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.projectIri.toRdf} a oldap:Project'
        # sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        # sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        # sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        # sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        # for attr, value in self._attributes.items():
        #     if not value:
        #         continue
        #     sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{attr.value.toRdf} {value.toRdf}'
        sparql2 += f' .\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql2 += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        result = self.safe_query(sparql0)
        if result['boolean']:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A Project with a shortname "{self.projectShortName}" already exists.')

        result = self.safe_query(sparql1a)
        if result['boolean']:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A Project with a namespace IRI "{self.namespaceIri}" already exists.')

        result = self.safe_query(sparql1b)
        if result['boolean']:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A Project with a project IRI "{self.projectIri}" already exists.')

        self.safe_update(sparql2)
        self.safe_commit()
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        context[self._attributes[ProjectAttr.PROJECT_SHORTNAME]] = self._attributes[ProjectAttr.NAMESPACE_IRI]

        cache = CacheSingletonRedis()
        cache.set(self.projectIri, self, self.projectShortName)

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Updates all modifications made to the project instance and writes them to the triple store.

        The function ensures changes contained within the project instance are written to the triple store
        by serializing them into SPARQL queries and executing them. Permissions are checked before
        execution, and transactions are used to ensure atomicity. If the update fails, appropriate
        exceptions are raised, and operations are rolled back.

        :param indent: Starting indentation level used for SPARQL query formatting.
        :type indent: int
        :param indent_inc: Increment of indentation for formatting SPARQL queries.
        :type indent_inc: int
        :return: None
        :raises OldapErrorNoPermission: Raised if the user does not have permissions for the operation.
        :raises OldapErrorUpdateFailed: Raised if the update fails due to timestamp mismatch or other inconsistencies.
        :raises OldapError: Raised for other internal errors.
        """

        def dict_diff(a: dict, b: dict) -> dict:
            """
            Compare two dicts and return added, removed, and changed key–values.
            """
            a_keys = set(a) if a else set()
            b_keys = set(b) if b else set()
            shared = a_keys & b_keys

            return {
                'added': {k: b[k] for k in b_keys - a_keys},
                'removed': {k: a[k] for k in a_keys - b_keys},
                'changed': {k: (a[k], b[k]) for k in shared if a[k] != b[k]},
                'same': {k: a[k] for k in shared if a[k] == b[k]},
            }

        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []
        for field, change in self._changeset.items():
            if field == ProjectAttr.LABEL or field == ProjectAttr.COMMENT:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self._attributes[field].update(graph=Xsd_QName('oldap:admin'),
                                                                      subject=self.projectIri,
                                                                      field=Xsd_QName(field.value)))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self._changeset[field].old_value.delete(graph=Xsd_QName('oldap:admin'),
                                                                      subject=self.projectIri,
                                                                      field=Xsd_QName(field.value))
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self._attributes[field].create(graph=Xsd_QName('oldap:admin'),
                                                            subject=self.projectIri,
                                                            field=Xsd_QName(field.value))
                    sparql_list.append(sparql)
                continue

            sparql = f'{blank:{indent * indent_inc}}# Project field "{field.value}" with action "{change.action.value}"\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?project {field.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{(indent + 1)* indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?project {field.value} {self._attributes[field].toRdf} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.projectIri.toRdf} as ?project)\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}?project {field.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
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
            print(sparql)
            self._con.transaction_abort()
            raise
        if timestamp != modtime:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed("Update failed! Timestamp does not match")
        self.safe_commit()
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.clear_changeset()
        cache = CacheSingletonRedis()
        cache.set(self.projectIri, self, self.projectShortName)

    def delete(self) -> None:
        """
        Delete the specified user from the triplestore. The function ensures that the
        user has the necessary permissions before proceeding with the deletion process.
        Additionally, it cleans up related cache entries.

        :raises OldapErrorNoPermission: Raised if the user lacks the necessary
            permissions to perform the operation.
        :raises OldapError: Raised in case of generic internal errors.
        :return: None
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        #
        # TODO: Check if project has any datamodel and/or data. Decline the deletion if this is the case
        #
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            GRAPH oldap:admin {{
                {self.projectIri.toRdf} a oldap:Project .
                {self.projectIri.toRdf} ?prop ?val .
            }}
        }} 
        """
        self._con.update_query(sparql)
        cache = CacheSingletonRedis()
        cache.delete(self.projectIri)
        cache.delete(self.projectShortName)

    @staticmethod
    def get_shortname_from_iri(con: IConnection, iri: Iri) -> Xsd_NCName:
        """
        Extracts the project short name from the given IRI using a SPARQL query executed
        in the provided connection. The method communicates with the server to fetch
        the short name associated with the specified IRI. If the IRI does not resolve
        to exactly one short name, an exception is raised.

        :param con: The connection object used to interact with the data source.
        :type con: IConnection
        :param iri: An instance of Iri or a value representing the IRI to query.
        :type iri: Iri
        :return: The project short name associated with the provided IRI.
        :rtype: Xsd_NCName
        :raises OldapError: If the connection object is not an instance of IConnection.
        :raises OldapErrorNotFound: If no short name is found or if multiple results are
            returned for the specified IRI.
        """
        if not isinstance(con, IConnection):
            raise OldapError("Connection must be an instance of IConnection")
        if not isinstance(iri, Iri):
            iri = Iri(iri, validate=True)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += 'SELECT ?shortname\n'
        sparql += 'FROM oldap:onto\n'
        sparql += 'FROM shared:onto\n'
        sparql += 'FROM NAMED oldap:admin\n'
        sparql += 'WHERE {\n'
        sparql += '    GRAPH oldap:admin {\n'
        sparql += f'        {iri.toRdf} oldap:projectShortName ?shortname .\n'
        sparql += '    }\n'
        sparql += '}\n'
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            raise OldapErrorNotFound(f"No project shortname found for {iri}")
        return res[0]['shortname']


