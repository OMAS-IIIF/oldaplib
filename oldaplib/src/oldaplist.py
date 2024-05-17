from dataclasses import dataclass
from enum import Enum, unique
from functools import partial
from typing import Self

from oldaplib.src.enums.action import Action
from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorInconsistency, OldapErrorImmutable, OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorInUse
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

OldapListAttrTypes = LangString | Iri | None

@dataclass
class OldapListAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: OldapListAttrTypes
    action: Action


@unique
class OldapListAttr(Enum):
    """
    This enum class represents the fields used in the project model
    """
    OLDAPLIST_IRI = 'oldap:oldapListIri'  # virtual property, repents the RDF subject
    PREF_LABEL = 'skos:prefLabel'
    DEFINITION = 'skos:definition'

class OldapList(Model):

    __datatypes = {
        OldapListAttr.OLDAPLIST_IRI: Iri,
        OldapListAttr.PREF_LABEL: LangString,
        OldapListAttr.DEFINITION: LangString,
    }

    __creator: Iri | None
    __created: Xsd_dateTime | None
    __contributor: Iri | None
    __modified: Xsd_dateTime | None
    __project: Project
    __graph: Xsd_NCName

    __attributes: dict[OldapListAttr, OldapListAttrTypes]

    __changeset: dict[OldapListAttr, OldapListAttrChange]

    def __init__(self, *,
                 con: IConnection,
                 project: Project,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 oldapListIri: Iri | str | None = None,
                 prefLabel: LangString | str | None = None,
                 definition: LangString | str | None = None):
        super().__init__(con)
        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')
        self.__project = project
        context = Context(name=self._con.context_name)
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        self.__graph = project.projectShortName

        self.__creator = creator if creator is not None else con.userIri
        if created and not isinstance(created, Xsd_dateTime):
            raise OldapErrorValue(f'Created must be "Xsd_dateTime", not "{type(created)}".')
        self.__created = created
        self.__contributor = contributor if contributor is not None else con.userIri
        if modified and not isinstance(modified, Xsd_dateTime):
            raise OldapErrorValue(f'Modified must be "Xsd_dateTime", not "{type(modified)}".')
        self.__modified = modified
        self.__attributes = {}

        if oldapListIri:
            if not isinstance(oldapListIri, Iri):
                self.__attributes[OldapListAttr.OLDAPLIST_IRI] = Iri(oldapListIri)
            else:
                self.__attributes[OldapListAttr.OLDAPLIST_IRI] = oldapListIri
        else:
            self.__attributes[OldapListAttr.OLDAPLIST_IRI] = Iri()

        self.__attributes[OldapListAttr.PREF_LABEL] = prefLabel if isinstance(prefLabel, LangString) else LangString(prefLabel)
        self.__attributes[OldapListAttr.PREF_LABEL].set_notifier(self.notifier, Iri(OldapListAttr.PREF_LABEL.value))
        self.__attributes[OldapListAttr.DEFINITION] = definition if isinstance(definition, LangString) else LangString(definition)
        self.__attributes[OldapListAttr.DEFINITION].set_notifier(self.notifier, Iri(OldapListAttr.DEFINITION.value))

        #
        # Consistency checks
        #
        if not self.__attributes[OldapListAttr.PREF_LABEL]:
            raise OldapErrorInconsistency(f'Project must have at least one skos:prefLabel, none given.')

        #
        # create all the attributes of the class according to the OldapListAttr definition
        #
        for attr in OldapListAttr:
            prefix, name = attr.value.split(':')
            setattr(OldapList, name, property(
                partial(OldapList.__get_value, attr=attr),
                partial(OldapList.__set_value, attr=attr),
                partial(OldapList.__del_value, attr=attr)))
        self.__changeset = {}

    def check_for_permissions(self) -> (bool, str):
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK – IS ROOT"
        else:
            if len(self.inProject) == 0:
                return False, f'Actor has no ADMIN_LISTS permission for user {self.userId}.'
            allowed: list[Iri] = []
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    return False, f'Actor has no ADMIN_LISTS permission for project {proj}'
                else:
                    if AdminPermission.ADMIN_LISTS not in actor.inProject.get(proj):
                        return False, f'Actor has no ADMIN_LISTS permission for project {proj}'
            return True, "OK"

    def __get_value(self: Self, attr: OldapListAttr) -> OldapListAttrTypes | None:
        return self.__attributes.get(attr)

    def __set_value(self: Self, value: OldapListAttrTypes, attr: OldapListAttr) -> None:
        self.__change_setter(attr, value)

    def __del_value(self: Self, attr: OldapListAttr) -> None:
        self.__changeset[attr] = OldapListAttrChange(self.__attributes[attr], Action.DELETE)
        del self.__attributes[attr]

    def __change_setter(self, attr: OldapListAttr, value: OldapListAttrTypes) -> None:
        if self.__attributes.get(attr) == value:
            return
        if attr == OldapListAttr.OLDAPLIST_IRI:
            raise OldapErrorImmutable(f'Field {attr.value} is immutable.')
        if self.__attributes.get(attr) is None:
            if self.__changeset.get(attr) is None:
                self.__changeset[attr] = OldapListAttrChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__changeset.get(attr) is None:
                    self.__changeset[attr] = OldapListAttrChange(self.__attributes[attr], Action.DELETE)
            else:
                if self.__changeset.get(attr) is None:
                    self.__changeset[attr] = OldapListAttrChange(self.__attributes[attr], Action.REPLACE)
        if value is None:
            del self.__attributes[attr]
        else:
            if not isinstance(value, self.__datatypes[attr]):
                self.__attributes[attr] = self.__datatypes[attr](value)
            else:
                self.__attributes[attr] = value

    def __str__(self):
        res = f'OldapList: {self.__attributes[OldapListAttr.OLDAPLIST_IRI]}\n'\
              f'  Creation: {self.__created} by {self.__creator}\n'\
              f'  Modified: {self.__modified} by {self.__contributor}\n'\
              f'  Preferred label: {self.__attributes.get(OldapListAttr.PREF_LABEL)}\n'\
              f'  Definition: {self.__attributes.get(OldapListAttr.DEFINITION)}'
        return res

    def __getitem__(self, attr: OldapListAttr) -> OldapListAttrTypes:
        return self.__attributes[attr]

    def get(self, attr: OldapListAttr) -> OldapListAttrTypes:
        return self.__attributes.get(attr)

    def __setitem__(self, attr: OldapListAttr, value: OldapListAttrTypes) -> None:
        self.__change_setter(attr, value)

    def __delitem__(self, attr: OldapListAttr) -> None:
        if self.__attributes.get(attr) is not None:
            self.__changeset[attr] = OldapListAttrChange(self.__attributes[attr], Action.DELETE)
            del self.__attributes[attr]


    @property
    def creator(self) -> Iri | None:
        """
        The creator of the OldapList.
        :return: Iri of the creator of the OldapList.
        :rtype: Iri | None
        """
        return self.__creator

    @property
    def created(self) -> Xsd_dateTime | None:
        """
        The creation date of the OldapList.
        :return: Creation date of the OldapList.
        :rtype: Xsd_dateTime | None
        """
        return self.__created

    @property
    def contributor(self) -> Iri | None:
        """
        The contributor of the OldapList as Iri.
        :return: Iri of the contributor of the OldapList.
        :rtype: Iri | None
        """
        return self.__contributor

    @property
    def modified(self) -> Xsd_dateTime | None:
        """
        Modification date of the OldapList.
        :return: Modification date of the OldapList.
        :rtype: Xsd_dateTime | None
        """
        return self.__modified

    @property
    def changeset(self) -> dict[OldapListAttr, OldapListAttrChange]:
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

    def notifier(self, attrname: Iri) -> None:
        """
        This method is called when a field is being changed.
        :param fieldname: Fieldname of the field being modified
        :return: None
        """
        attr = OldapListAttr(attrname)
        self.__changeset[attr] = OldapListAttrChange(self.__attributes[attr], Action.MODIFY)

    @classmethod
    def read(cls, con: IConnection, project: Project, oldapListIri: Iri | str) -> Self:
        oldapListIri = Iri(oldapListIri)

        context = Context(name=con.context_name)
        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        graph = project.projectShortName

        query = context.sparql_context
        query += f"""
            SELECT ?prop ?val
            FROM {graph}:lists
            WHERE {{
                {oldapListIri.toRdf} ?prop ?val
            }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'OldapList with IRI "{oldapListIri}" not found.')
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        oldapList: Iri | None = None
        prefLabel: LangString | None = None
        definition: LangString | None = None
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
                case OldapListAttr.PREF_LABEL.value:
                    if not prefLabel:
                        prefLabel = LangString()
                    prefLabel.add(r['val'])
                case OldapListAttr.DEFINITION.value:
                    if not definition:
                        definition = LangString()
                    definition.add(r['val'])
        return cls(con=con,
                   project=project,
                   creator=creator,
                   created=created,
                   contributor=contributor,
                   modified=modified,
                   oldapListIri=oldapListIri,
                   prefLabel=prefLabel,
                   definition=definition)

    @staticmethod
    def search(con: IConnection,
               project: Project,
               prefLabel: Xsd_string | str | None = None,
               definition: str | None = None) -> list[Iri]:
        context = Context(name=con.context_name)
        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        graph = project.projectShortName

        prefLabel = Xsd_string(prefLabel)
        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        graph = project.projectShortName
        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?list\n'
        sparql += f'FROM {graph}:lists\n'
        sparql += 'WHERE {\n'
        sparql += '   ?list a oldap:OldapList .\n'
        if prefLabel:
            sparql += '   ?list skos:prefLabel ?label .\n'
            if prefLabel.lang:
                sparql += f'   FILTER(?label = "{prefLabel.toRdf}")\n'
            else:
                sparql += f'   FILTER(STR(?label) = "{Xsd_string.escaping(prefLabel.value)}")\n'
        if definition:
            sparql += '   ?list skos:definition ?definition .\n'
            sparql += f'   FILTER(CONTAINS(STR(?definition), "{Xsd_string.escaping(definition.value)}"))\n'
        sparql += '}\n'

        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        lists: list[Iri] = []
        if len(res) > 0:
            for r in res:
                lists.append(r['list'])
        return lists

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
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
        SELECT ?list
        FROM {self.__graph}:lists
        WHERE {{
            ?list a oldap:OldapList .
            FILTER(?list = {self.oldapListIri.toRdf})
        }}
        """

        blank = ''
        sparql2 = context.sparql_context
        sparql2 += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql2 += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:lists {{'
        sparql2 += f'\n{blank:{(indent + 2) * indent_inc}}{self.oldapListIri.toRdf} a oldap:OldapList'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListAttr.PREF_LABEL.value} {self.prefLabel.toRdf}'
        if self.definition:
            sparql2 += f' ;\n{blank:{(indent + 3) * indent_inc}}{OldapListAttr.DEFINITION.value} {self.definition.toRdf}'
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
            raise OldapErrorAlreadyExists(f'A list with a oldapListIri "{self.oldapListIri}" already exists')

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

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []

        for field, change in self.__changeset.items():
            if field == OldapListAttr.PREF_LABEL or field == OldapListAttr.DEFINITION:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self.__attributes[field].update(graph=Xsd_QName(f'{self.__graph}:lists'),
                                                                       subject=self.oldapListIri,
                                                                       subjectvar='?list',
                                                                       field=Xsd_QName(field.value)))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    # sparql = self.__attributes[field].delete(graph=Xsd_QName(f'{self.__graph}:lists'),
                    #                                          subject=self.oldapListIri,
                    #                                          field=Xsd_QName(field.value))
                    sparql = self.__changeset[field].old_value.delete(graph=Xsd_QName(f'{self.__graph}:lists'),
                                                                      subject=self.oldapListIri,
                                                                      field=Xsd_QName(field.value))
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self.__attributes[field].create(graph=Xsd_QName(f'{self.__graph}:lists'),
                                                             subject=self.oldapListIri,
                                                             field=Xsd_QName(field.value))
                    sparql_list.append(sparql)

        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName(f'{self.__graph}:lists'), self.oldapListIri, self.modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName(f'{self.__graph}:lists'), self.oldapListIri)
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
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'''
        SELECT ?listnode
        FROM {self.__graph}:lists
        WHERE {{
            ?listnode a oldap:OldapListNode .
        }}
        '''
        jsonobj = self._con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            raise OldapErrorInUse(f'List {self.prefLabel} cannot be deleted since there are still nodes.')

        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            {self.oldapListIri.toRdf} a oldap:OldapList .
            {self.oldapListIri.toRdf} ?prop ?val .
        }} 
        """
        # TODO: use transaction for error handling
        self._con.update_query(sparql)



