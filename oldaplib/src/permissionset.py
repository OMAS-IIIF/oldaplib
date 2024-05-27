from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Dict, Self

from pystrict import strict

from oldaplib.src.enums.permissionsetattr import PermissionSetAttr
from oldaplib.src.enums.permissions import AdminPermission, DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorAlreadyExists, OldapErrorNoPermission, OldapError, \
    OldapErrorInconsistency, OldapErrorUpdateFailed, OldapErrorImmutable, OldapErrorNotFound
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.xsd.xsd_string import Xsd_string

PermissionSetAttrTypes = Xsd_NCName | LangString | DataPermission | None

@dataclass
class PermissionSetAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: PermissionSetAttrTypes
    action: Action


#@strict
class PermissionSet(Model):
    __datatypes = {
        PermissionSetAttr.PERMISSION_SET_ID: Xsd_NCName,
        PermissionSetAttr.LABEL: LangString,
        PermissionSetAttr.COMMENT: LangString,
        PermissionSetAttr.GIVES_PERMISSION: DataPermission,
        PermissionSetAttr.DEFINED_BY_PROJECT: Iri
    }

    __creator: Iri | None
    __created: Xsd_dateTime | None
    __contributor: Iri | None
    __modified: Xsd_dateTime | None

    __permset_iri: Iri | None

    __attributes: Dict[PermissionSetAttr, PermissionSetAttrTypes]

    __changeset: Dict[PermissionSetAttr, PermissionSetAttrChange]

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str |None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 permissionSetId: Xsd_NCName | str,
                 label: LangString | str | None = None,
                 comment: LangString | str | None = None,
                 givesPermission: DataPermission,
                 definedByProject: Iri | Xsd_NCName):
        """
        Constructor for a permission set.
        :param con: Subclass of IConnection
        :type con: IConnection
        :param creator: Usually not being used (internal use only)
        :type creator: Iri | None
        :param created: Usually not being used (internal use only)
        :type created: Xsd_dateTime | datetime | str | None
        :param contributor: Usually not being used (internal use only)
        :type contributor: Iri | None
        :param modified: Usually not being used (internal use only)
        :type modified: Xsd_dateTime | datetime | str | None
        :param permissionSetId: A unique identifier for the permission set (unique within the project as given be :definedByProject)
        :type permissionSetId: Xsd_NCName | str
        :param label: A meaninful label for the permission set (several languages allowed)
        :type label: LangString | str
        :param comment: A meaningful comment for the permission set (several languages allowed)
        :type comment: LangString | str
        :param givesPermission: The permission that this permision set grants
        :type givesPermission: DataPermission
        :param definedByProject: The project that defines this permission set (either the IRI or the shortname)
        :type definedByProject: Iri | Xsd_NCName
        :raises OldapErrorNoFound: Given project does not exist
        """
        super().__init__(con)
        self.__creator = Iri(creator) if creator else con.userIri
        self.__created = Xsd_dateTime(created) if created else None
        self.__contributor = Iri(contributor) if contributor else con.userIri
        self.__modified = Xsd_dateTime(modified) if modified else None
        self.__attributes = {}

        self.__attributes[PermissionSetAttr.PERMISSION_SET_ID] = Xsd_NCName(permissionSetId)
        self.__attributes[PermissionSetAttr.LABEL] = LangString(label)
        self.__attributes[PermissionSetAttr.LABEL].set_notifier(self.notifier, PermissionSetAttr.LABEL)
        self.__attributes[PermissionSetAttr.COMMENT] = LangString(comment)
        self.__attributes[PermissionSetAttr.COMMENT].set_notifier(self.notifier, PermissionSetAttr.COMMENT)
        self.__attributes[PermissionSetAttr.GIVES_PERMISSION] = givesPermission
        #
        # get the project IRI
        #
        project = Project.read(self._con, definedByProject)
        self.__attributes[PermissionSetAttr.DEFINED_BY_PROJECT] = project.projectIri

        if not self.__attributes[PermissionSetAttr.PERMISSION_SET_ID]:
            raise OldapErrorInconsistency(f'PermissionSet must have a unique ID, none given.')
        if not self.__attributes[PermissionSetAttr.LABEL]:
            raise OldapErrorInconsistency(f'PermissionSet must have at least one rdfs:label, none given.')
        if not self.__attributes[PermissionSetAttr.GIVES_PERMISSION]:
            raise OldapErrorInconsistency(f'PermissionSet must have at least one oldap:givesPermission, none given.')
        if not self.__attributes[PermissionSetAttr.DEFINED_BY_PROJECT]:
            raise OldapErrorInconsistency(f'PermissionSet must have at least one oldap:definedByProject, none given.')

        project = Project.read(self._con, self.__attributes[PermissionSetAttr.DEFINED_BY_PROJECT])
        self.__permset_iri = Iri.fromPrefixFragment(project.projectShortName, self.__attributes[PermissionSetAttr.PERMISSION_SET_ID], validate=False)

        for field in PermissionSetAttr:
            prefix, name = field.value.split(':')
            setattr(PermissionSet, name, property(
                partial(self.__get_value, field=field),
                partial(self.__set_value, field=field),
                partial(self.__del_value, field=field)))
        self.__changeset = {}

    def check_for_permissions(self) -> (bool, str):
        """
        Internal method to check if a user may modify the permission set.
        :return: a tuple with a boolean (True, False) and the error message (or "OK")
        """
        #
        # First we check if the logged-in user ("actor") has the ADMIN_PERMISSION_SETS permission for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK"
        else:
            if actor.inProject.get(self.definedByProject) is None:
                return False, f'Actor has no ADMIN_PERMISSION_SETS permission for project {self.definedByProject}'
            else:
                if AdminPermission.ADMIN_PERMISSION_SETS not in actor.inProject.get(self.definedByProject):
                    return False, f'Actor has no ADMIN_PERMISSION_SETS permission for project {self.definedByProject}'
            return True, "OK"

    def __get_value(self: Self, self2: Self, field: PermissionSetAttr) -> PermissionSetAttrTypes | None:
        return self.__attributes.get(field)

    def __set_value(self: Self, self2: Self, value: PermissionSetAttrTypes, field: PermissionSetAttr) -> None:
        if field == PermissionSetAttr.PERMISSION_SET_ID and self.__attributes.get(PermissionSetAttr.PERMISSION_SET_ID) is not None:
            OldapErrorAlreadyExists(f'A permission set ID already has been assigned: "{repr(self.__attributes.get(PermissionSetAttr.PERMISSION_SET_IRI))}".')
        self.__change_setter(field, value)

    def __del_value(self: Self, self2: Self, field: PermissionSetAttr) -> None:
        del self.__attributes[field]

    def __change_setter(self, attr: PermissionSetAttr, value: PermissionSetAttrTypes) -> None:
        if self.__attributes[attr] == value:
            return
        if attr in {PermissionSetAttr.PERMISSION_SET_ID, PermissionSetAttr.DEFINED_BY_PROJECT}:
            raise OldapErrorImmutable(f'Field {attr.value} is immutable.')
        if self.__attributes[attr] is None:
            if self.__changeset.get(attr) is None:
                self.__changeset[attr] = PermissionSetAttrChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__changeset.get(attr) is None:
                    self.__changeset[attr] = PermissionSetAttrChange(self.__attributes[attr], Action.DELETE)
            else:
                if self.__changeset.get(attr) is None:
                    self.__changeset[attr] = PermissionSetAttrChange(self.__attributes[attr], Action.REPLACE)

        if value is None:
            del self.__attributes[attr]
        else:
            if isinstance(self.__datatypes[attr], set):
                dtypes = list(self.__datatypes[attr])
                for dtype in dtypes:
                    try:
                        self.__attributes[attr] = dtype(value)
                        break;
                    except OldapErrorValue:
                        pass
            else:
                self.__attributes[attr] = self.__datatypes[attr](value)

    def __str__(self) -> str:
        res = f'PermissionSet: {self.__attributes[PermissionSetAttr.PERMISSION_SET_ID]}\n'\
              f'  Creation: {self.__created} by {self.__creator}\n'\
              f'  Modified: {self.__modified} by {self.__contributor}\n' \
              f'  Label: {self.__attributes.get(PermissionSetAttr.LABEL, "-")}\n' \
              f'  Comment: {self.__attributes.get(PermissionSetAttr.COMMENT, "-")}\n'\
              f'  Permission: {self.__attributes[PermissionSetAttr.GIVES_PERMISSION].name}\n'\
              f'  By project: {self.__attributes[PermissionSetAttr.DEFINED_BY_PROJECT]}\n'
        return res

    def __getitem__(self, attr: PermissionSetAttr) -> PermissionSetAttrTypes:
        return self.__attributes[attr]

    def get(self, attr: PermissionSetAttr) -> PermissionSetAttrTypes:
        return self.__attributes.get(attr)

    def __setitem__(self, attr: PermissionSetAttr, value: PermissionSetAttrTypes) -> None:
        self.__change_setter(attr, value)

    def __delitem__(self, attr: PermissionSetAttr) -> None:
        if self.__attributes.get(attr) is not None:
            self.__changeset[attr] = PermissionSetAttrChange(self.__attributes[attr], Action.DELETE)
            del self.__attributes[attr]

    @property
    def creator(self) -> Xsd_anyURI | None:
        return self.__creator

    @property
    def created(self) -> datetime | None:
        return self.__created

    @property
    def contributor(self) -> Xsd_anyURI | None:
        return self.__contributor

    @property
    def modified(self) -> datetime | None:
        return self.__modified

    def notifier(self, what: PermissionSetAttr) -> None:
        self.__changeset[what] = PermissionSetAttrChange(None, Action.MODIFY)

    @property
    def changeset(self) -> Dict[PermissionSetAttr, PermissionSetAttrChange]:
        """
        Return the changeset, that is dicst with information about all properties that have benn changed.
        :return: A dictionary of all changes
        """
        return self.__changeset

    def clear_changeset(self) -> None:
        """
        Clear the changeset.
        :return: None
        """
        self.__changeset = {}

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Create the given permission set in the triple store.
        :param indent: indentation for SPARQL text
        :type indent: int
        :param indent_inc: indentation increment for the SPARQL text
        :type indent_inc: int
        :return: None
        """
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        context = Context(name=self._con.context_name)
        blank = ''

        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?permset
        FROM oldap:admin
        WHERE {{
            ?permset a oldap:PermissionSet .
            FILTER(?permset = {self.__permset_iri.toRdf})       
        }}
        """

        timestamp = Xsd_dateTime()
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH oldap:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}} {self.__permset_iri.toRdf} a oldap:PermissionSet'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{PermissionSetAttr.LABEL.value} {self.label.toRdf}'
        if self.comment:
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{PermissionSetAttr.COMMENT.value} {self.comment.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{PermissionSetAttr.GIVES_PERMISSION.value} oldap:{self.givesPermission.name}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{PermissionSetAttr.DEFINED_BY_PROJECT.value} {self.definedByProject.toRdf}'

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OldapError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'A permission set "{self.__permset_iri}" already exists')

        try:
            self._con.transaction_update(sparql)
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

    @classmethod
    def read(cls, con: IConnection, permissionSetId: Xsd_NCName | str, definedByProject: Iri | Xsd_NCName | str) -> Self:
        """
        Reads a given permission set. The permission set is defined by its ID (which must be unique within
        one project) and the project IRI.
        :param con: A Connection object.
        :type con: IConnection
        :param permissionSetId: The ID of the permission set.
        :type permissionSetId: Xsd_NCName | str
        :param definedByProject: Iri or the shortname of the project
        :type definedByProject: Iri | Xsd_NCName | str
        :return: A PermissionSet instance
        :rtype: OldapPermissionSet
        :raises OldapErrorNot found: If the permission set cannot be found.
        """
        id = Xsd_NCName(permissionSetId)
        definedByProject = Iri(definedByProject)

        project = Project.read(con, definedByProject)
        permset_iri = Iri.fromPrefixFragment(project.projectShortName, permissionSetId, validate=False)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?permset ?p ?o
        FROM oldap:admin
        WHERE {{
            BIND({permset_iri.toRdf} as ?permset)
            ?permset a oldap:PermissionSet .
            ?permset ?p ?o .
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'No permission set "{permset_iri}"')

        permset_iri: Iri | None = None
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        label: LangString = LangString()
        comment: LangString = LangString()
        givesPermission: DataPermission | None = None
        definedByProject: Iri | None = None
        for r in res:
            if not permset_iri:
                try:
                    permset_iri = r['permset']
                except Exception as e:
                    raise OldapErrorInconsistency(f'Invalid project identifier "{r['o']}".')
            match str(r['p']):
                case 'dcterms:creator':
                    creator = r['o']
                case 'dcterms:created':
                    created = r['o']
                case 'dcterms:contributor':
                    contributor = r['o']
                case 'dcterms:modified':
                    modified = r['o']
                case 'rdfs:label':
                    label.add(r['o'])
                case 'rdfs:comment':
                    comment.add(r['o'])
                case 'oldap:givesPermission':
                    givesPermission = DataPermission.from_string(str(r['o']))
                case 'oldap:definedByProject':
                    definedByProject = r['o']
        cls.__permset_iri = permset_iri
        return cls(con=con,
                   permissionSetId=permissionSetId,
                   creator=creator,
                   created=created,
                   contributor=contributor,
                   modified=modified,
                   label=label,
                   comment=comment,
                   givesPermission=givesPermission,
                   definedByProject=Iri(definedByProject, validate=False))

    @staticmethod
    def search(con: IConnection, *,
               permissionSetId: str | None = None,
               definedByProject: Iri | str | None = None,
               givesPermission: DataPermission | None = None,
               label: Xsd_string | str | None = None) -> list[Iri | Xsd_QName]:
        """
        Search for a permission set. At least one of the search criteria is required. Multiple search criteria are
        combined using a logical AND.
        :param con: A valid Connection object.
        :type con: IConnection
        :param permissionSetId: Search for the given ID. The given string must be _contained_ in the ID (substring)
        :type permissionSetId: str | None
        :param definedByProject: The project which is responsible for the permission set
        :type definedByProject: str | None
        :param givesPermission: The permission that the permission set should grant
        :type givesPermission: str | None
        :param label: The label string. The given string must be within at least one language label.
        :type label: str | None
        :return: A list or permission set Iri's (possibly as Xsd_QName
        :rtype: list[Iri | Xsd_QName]
        """
        if definedByProject:
            definedByProject = Iri(definedByProject)
        label = Xsd_string(label)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        if definedByProject:
            sparql += 'SELECT DISTINCT ?permsetIri ?namespaceIri ?projectShortName'
            context = Context(name=con.context_name)
        else:
            sparql += 'SELECT DISTINCT ?permsetIri'
        sparql += '\n'
        sparql += 'FROM oldap:admin\n'
        sparql += 'WHERE {\n'
        sparql += '   ?permsetIri rdf:type oldap:PermissionSet .\n'
        if definedByProject:
            sparql += '   ?permsetIri oldap:definedByProject ?definedByProject .\n'
            sparql += '   ?definedByProject oldap:namespaceIri ?namespaceIri .\n'
            sparql += '   ?definedByProject oldap:projectShortName ?projectShortName .\n'
        if givesPermission:
            sparql += '   ?permsetIri oldap:givesPermission ?givesPermission .\n'
        if label:
            sparql += '   ?permsetIri rdfs:label ?label .\n'
        if permissionSetId or definedByProject or givesPermission or label:
            sparql += '   FILTER('
            use_and = False
            if permissionSetId:
                sparql += f'CONTAINS(STR(?permsetIri), "{Xsd_string.escaping(permissionSetId)}")'
                use_and = True
            if definedByProject:
                if use_and:
                    sparql += ' && '
                sparql += f'?definedByProject = {definedByProject.toRdf}'
                use_and = True
            if givesPermission:
                if use_and:
                    sparql += ' && '
                sparql += f'?givesPermission = {givesPermission.toRdf}'
                use_and = True
            if label:
                if use_and:
                    sparql += ' && '
                if label.lang:
                    sparql += f'?label = {label.toRdf}'
                else:
                    sparql += f'CONTAINS(STR(?label), "{Xsd_string.escaping(label.value)}")'
            sparql += ')\n'
        sparql += '}\n'
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        permissionSets: list[Iri] = []
        for r in res:
            if definedByProject:
                #context[r['projectShortName']] = r['namespaceIri']
                psqname = r['permsetIri'].as_qname or context.iri2qname(str(r['permsetIri']), validate=False)
                permissionSets.append(psqname or r['permsetIri'])
            else:
                permissionSets.append(r['permsetIri'])
        return permissionSets

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Update a changed permission set
        :param indent: Internal use (indent of SPARQL text)
        :type indent: int
        :param indent_inc: Internal use (indent increment of SPARQL text)
        :type indent_inc: int
        :return: None
        :rtype: None
        :raises OldapErrorUpdateFailed: Update failed
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)
        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []

        for attr, change in self.__changeset.items():
            if attr == PermissionSetAttr.LABEL or attr == PermissionSetAttr.COMMENT:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self.__attributes[attr].update(graph=Xsd_QName('oldap:admin'),
                                                                      subject=self.__permset_iri,
                                                                      subjectvar='?project',
                                                                      field=Xsd_QName(attr.value)))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self.__attributes[attr].delete(graph=Xsd_QName('oldap:admin'),
                                                            subject=self.__permset_iri,
                                                            field=Xsd_QName(attr.value))
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self.__attributes[attr].create(graph=Xsd_QName('oldap:admin'),
                                                            subject=self.__permset_iri,
                                                            field=Xsd_QName(attr.value))
                    sparql_list.append(sparql)
                continue
            sparql = f'{blank:{indent * indent_inc}}# PermissionSet attribute "{attr.value}" with action "{change.action.value}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH oldap:admin\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {self.__attributes[attr].toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.__permset_iri.toRdf} as ?project)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName('oldap:admin'), self.__permset_iri, self.__modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName('oldap:admin'), self.__permset_iri)
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
        Delete the given permission set.
        :return: None
        :rtype: None
        """
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            {self.__permset_iri.toRdf} a oldap:PermissionSet .
            {self.__permset_iri.toRdf} ?prop ?val .
        }} 
        """
        # TODO: use transaction for error handling
        self._con.update_query(sparql)

