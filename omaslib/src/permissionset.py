from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Dict, Self

from pystrict import strict

from omaslib.src.enums.permissionsetattr import PermissionSetAttr
from omaslib.src.enums.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.context import Context
from omaslib.src.enums.action import Action
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorAlreadyExists, OmasErrorNoPermission, OmasError, \
    OmasErrorInconsistency, OmasErrorUpdateFailed, OmasErrorImmutable, OmasErrorNotFound
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.iconnection import IConnection
from omaslib.src.model import Model
from omaslib.src.xsd.xsd_string import Xsd_string

PermissionSetAttrTypes = Iri | LangString | DataPermission | None

@dataclass
class PermissionSetAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: PermissionSetAttrTypes
    action: Action


@strict
class PermissionSet(Model):
    __datatypes = {
        PermissionSetAttr.PERMISSION_SET_IRI: Iri,
        PermissionSetAttr.LABEL: LangString,
        PermissionSetAttr.COMMENT: LangString,
        PermissionSetAttr.GIVES_PERMISSION: DataPermission,
        PermissionSetAttr.DEFINED_BY_PROJECT: Iri
    }

    __creator: Iri | None
    __created: Xsd_dateTime | None
    __contributor: Iri | None
    __modified: Xsd_dateTime | None

    __attributes: Dict[PermissionSetAttr, PermissionSetAttrTypes]

    __changeset: Dict[PermissionSetAttr, PermissionSetAttrChange]

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str |None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 permissionSetIri: Iri | None = None,
                 label: LangString | str | None = None,
                 comment: LangString | str | None = None,
                 givesPermission: DataPermission,
                 definedByProject: Iri):
        super().__init__(con)
        self.__creator = Iri(creator) if creator else con.userIri
        self.__created = Xsd_dateTime(created) if created else None
        self.__contributor = Iri(contributor) if contributor else con.userIri
        self.__modified = Xsd_dateTime(modified) if modified else None
        self.__attributes = {}

        self.__attributes[PermissionSetAttr.PERMISSION_SET_IRI] = Iri(permissionSetIri)
        self.__attributes[PermissionSetAttr.LABEL] = LangString(label)
        self.__attributes[PermissionSetAttr.LABEL].set_notifier(self.notifier, PermissionSetAttr.LABEL)
        self.__attributes[PermissionSetAttr.COMMENT] = LangString(comment)
        self.__attributes[PermissionSetAttr.COMMENT].set_notifier(self.notifier, PermissionSetAttr.COMMENT)
        self.__attributes[PermissionSetAttr.GIVES_PERMISSION] = givesPermission
        self.__attributes[PermissionSetAttr.DEFINED_BY_PROJECT] = Iri(definedByProject)

        if not self.__attributes[PermissionSetAttr.LABEL]:
            raise OmasErrorInconsistency(f'PermissionSet must have at least one rdfs:label, none given.')

        for field in PermissionSetAttr:
            prefix, name = field.value.split(':')
            setattr(PermissionSet, name, property(
                partial(self.__get_value, field=field),
                partial(self.__set_value, field=field),
                partial(self.__del_value, field=field)))
        self.__changeset = {}

    def check_for_permissions(self) -> (bool, str):
        #
        # First we check if the logged-in user ("actor") has the ADMIN_PERMISSION_SETS permission for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('omas:SystemProject'))
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
        if field == PermissionSetAttr.PERMISSION_SET_IRI and self.__attributes.get(PermissionSetAttr.PERMISSION_SET_IRI) is not None:
            OmasErrorAlreadyExists(f'A project IRI already has been assigned: "{repr(self.__attributes.get(PermissionSetAttr.PERMISSION_SET_IRI))}".')
        self.__change_setter(field, value)

    def __del_value(self: Self, self2: Self, field: PermissionSetAttr) -> None:
        del self.__attributes[field]

    def __change_setter(self, attr: PermissionSetAttr, value: PermissionSetAttrTypes) -> None:
        if self.__attributes[attr] == value:
            return
        if attr in {PermissionSetAttr.PERMISSION_SET_IRI, PermissionSetAttr.DEFINED_BY_PROJECT}:
            raise OmasErrorImmutable(f'Field {attr.value} is immutable.')
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
                    except OmasErrorValue:
                        pass
            else:
                self.__attributes[attr] = self.__datatypes[attr](value)

    def __str__(self) -> str:
        res = f'PermissionSet: {self.__attributes[PermissionSetAttr.PERMISSION_SET_IRI]}\n'\
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
        if self._con is None:
            raise OmasError("Cannot create: no connection")

        result, message = self.check_for_permissions()
        if not result:
            raise OmasErrorNoPermission(message)

        context = Context(name=self._con.context_name)
        blank = ''

        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?permset
        FROM omas:admin
        WHERE {{
            ?permset a omas:PermissionSet .
            FILTER(?permset = {self.permissionSetIri.toRdf})       
        }}
        """

        timestamp = Xsd_dateTime()
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}} {self.permissionSetIri.toRdf} a omas:PermissionSet'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{PermissionSetAttr.LABEL.value} {self.label.toRdf}'
        if self.comment:
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{PermissionSetAttr.COMMENT.value} {self.comment.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{PermissionSetAttr.GIVES_PERMISSION.value} omas:{self.givesPermission.name}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{PermissionSetAttr.DEFINED_BY_PROJECT.value} {self.definedByProject.toRdf}'

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        self._con.transaction_start()
        try:
            jsonobj = self._con.transaction_query(sparql1)
        except OmasError:
            self._con.transaction_abort()
            raise
        res = QueryProcessor(context, jsonobj)
        if len(res) > 0:
            self._con.transaction_abort()
            raise OmasErrorAlreadyExists(f'A permission set "{self.permissionSetIri}" already exists')

        try:
            self._con.transaction_update(sparql)
        except OmasError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OmasError:
            self._con.transaction_abort()
            raise
        self.__created = timestamp
        self.__creator = self._con.userIri
        self.__modified = timestamp
        self.__contributor = self._con.userIri

    @classmethod
    def read(cls, con: IConnection, permissionSetIri: Iri | str) -> Self:
        permissionSetIri = Iri(permissionSetIri)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?permset ?p ?o
        FROM omas:admin
        WHERE {{
            BIND({permissionSetIri.toRdf} as ?permset)
            ?permset a omas:PermissionSet .
            ?permset ?p ?o .
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OmasErrorNotFound(f'No permission set "{permissionSetIri}"')

        permissionSetIri: Iri | None = None
        creator: Iri | None = None
        created: Xsd_dateTime | None = None
        contributor: Iri | None = None
        modified: Xsd_dateTime | None = None
        label: LangString = LangString()
        comment: LangString = LangString()
        givesPermission: DataPermission | None = None
        definedByProject: Iri | None = None
        for r in res:
            if not permissionSetIri:
                try:
                    permissionSetIri = r['permset']
                except Exception as e:
                    raise OmasErrorInconsistency(f'Invalid project identifier "{r['o']}".')
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
                case 'omas:givesPermission':
                    givesPermission = DataPermission.from_string(str(r['o']))
                case 'omas:definedByProject':
                    definedByProject = r['o']
        return cls(con=con,
                   permissionSetIri=permissionSetIri,
                   creator=creator,
                   created=created,
                   contributor=contributor,
                   modified=modified,
                   label=label,
                   comment=comment,
                   givesPermission=givesPermission,
                   definedByProject=Iri(definedByProject))

    @staticmethod
    def search(con: IConnection,
               definedByProject: Iri | str | None = None,
               givesPermission: DataPermission | None = None,
               label: Xsd_string | str | None = None) -> list[Iri]:
        label = Xsd_string(label)
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += 'SELECT DISTINCT ?permsetIri'
        # if definedByProject:
        #     sparql += ' ?definedByProject'
        # if givesPermission:
        #     sparql += ' ?givesPermission'
        # if label:
        #     sparql += ' ?label'
        sparql += '\n'
        sparql += 'FROM omas:admin\n'
        sparql += 'WHERE {\n'
        sparql += '   ?permsetIri rdf:type omas:PermissionSet .\n'
        if definedByProject:
            sparql += '   ?permsetIri omas:definedByProject ?definedByProject .\n'
        if givesPermission:
            sparql += '   ?permsetIri omas:givesPermission ?givesPermission .\n'
        if label:
            sparql += '   ?permsetIri rdfs:label ?label .\n'
        if definedByProject or givesPermission or label:
            sparql += '   FILTER('
            use_and = False
            if definedByProject:
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
                    sparql += f'str(?label) = "{Xsd_string.escaping(label.value)}"'
            sparql += ')\n'
        sparql += '}\n'
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        permissionSets: list[Iri] = []
        for r in res:
            permissionSets.append(r['permsetIri'])
        return permissionSets

    def update(self, indent: int = 0, indent_inc: int = 4):
        result, message = self.check_for_permissions()
        if not result:
            raise OmasErrorNoPermission(message)
        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        blank = ''
        sparql_list = []

        for attr, change in self.__changeset.items():
            if attr == PermissionSetAttr.LABEL or attr == PermissionSetAttr.COMMENT:
                if change.action == Action.MODIFY:
                    sparql_list.extend(self.__attributes[attr].update(graph=Xsd_QName('omas:admin'),
                                                                   subject=self.permissionSetIri,
                                                                   subjectvar='?project',
                                                                   field=Xsd_QName(attr.value)))
                if change.action == Action.DELETE or change.action == Action.REPLACE:
                    sparql = self.__attributes[attr].delete(graph=Xsd_QName('omas:admin'),
                                                         subject=self.permissionSetIri,
                                                         field=Xsd_QName(attr.value))
                    sparql_list.append(sparql)
                if change.action == Action.CREATE or change.action == Action.REPLACE:
                    sparql = self.__attributes[attr].create(graph=Xsd_QName('omas:admin'),
                                                         subject=self.permissionSetIri,
                                                         field=Xsd_QName(attr.value))
                    sparql_list.append(sparql)
                continue
            sparql = f'{blank:{indent * indent_inc}}# PermissionSet attribute "{attr.value}" with action "{change.action.value}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH omas:admin\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {self.__attributes[attr].toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.permissionSetIri.toRdf} as ?project)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?project {attr.value} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = context.sparql_context
        sparql += " ;\n".join(sparql_list)

        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
            self.set_modified_by_iri(Xsd_QName('omas:admin'), self.permissionSetIri, self.__modified, timestamp)
            modtime = self.get_modified_by_iri(Xsd_QName('omas:admin'), self.permissionSetIri)
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
        result, message = self.check_for_permissions()
        if not result:
            raise OmasErrorNoPermission(message)

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            {self.permissionSetIri.toRdf} a omas:PermissionSet .
            {self.permissionSetIri.toRdf} ?prop ?val .
        }} 
        """
        # TODO: use transaction for error handling
        self._con.update_query(sparql)

