import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from functools import partial
from typing import Dict, Optional, Self

from pystrict import strict

from omaslib.src.connection import Connection
from omaslib.src.enums.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.context import Context
from omaslib.src.enums.action import Action
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorAlreadyExists, OmasErrorNoPermission, OmasError, \
    OmasErrorInconsistency
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.tools import str2qname_anyiri
from omaslib.src.iconnection import IConnection
from omaslib.src.model import Model

@unique
class PermissionSetFields(Enum):
    PERMISSION_SET_IRI = 'omas:permissionSetIri'  # virtual property, no equivalent in RDF
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    GIVES_PERMISSION = 'omas:givesPermission'
    DEFINED_BY_PROJECT = 'omas:definedByProject'


PermissionSetFieldTypes = Xsd_anyURI | Xsd_QName | LangString | DataPermission | None

@dataclass
class PermissionSetFieldChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: PermissionSetFieldTypes
    action: Action


@strict
class PermissionSet(Model):
    __datatypes = {
        PermissionSetFields.PERMISSION_SET_IRI: {Xsd_QName, Xsd_anyURI},
        PermissionSetFields.LABEL: LangString,
        PermissionSetFields.COMMENT: LangString,
        PermissionSetFields.GIVES_PERMISSION: DataPermission,
        PermissionSetFields.DEFINED_BY_PROJECT: {Xsd_QName, Xsd_anyURI}
    }

    __creator: Xsd_anyURI | None
    __created: datetime | None
    __contributor: Xsd_anyURI | None
    __modified: datetime | None

    __fields: Dict[PermissionSetFields, PermissionSetFieldTypes]

    __change_set: Dict[PermissionSetFields, PermissionSetFieldChange]

    def __init__(self, *,
                 con: Connection,
                 creator: Optional[Xsd_anyURI] = None,
                 created: Optional[datetime] = None,
                 contributor: Optional[Xsd_anyURI] = None,
                 modified: Optional[datetime] = None,
                 permissionSetIri: Optional[Xsd_anyURI | Xsd_QName] = None,
                 label: Optional[LangString | str],
                 comment: Optional[LangString | str],
                 givesPermission: DataPermission,
                 definedByProject: Xsd_anyURI | Xsd_QName | str):
        super().__init__(con)
        self.__creator = creator if creator is not None else con.userIri
        self.__created = created
        self.__contributor = contributor if contributor is not None else con.userIri
        self.__modified = modified
        self.__fields = {}

        if permissionSetIri:
            if isinstance(permissionSetIri, Xsd_anyURI) or isinstance(permissionSetIri, Xsd_QName):
                self.__fields[PermissionSetFields.PERMISSION_SET_IRI] = permissionSetIri
            elif isinstance(permissionSetIri, str):
                try:
                    self.__fields[PermissionSetFields.PERMISSION_SET_IRI] = str2qname_anyiri(permissionSetIri)
                except:
                    raise OmasErrorValue(f'permissionSetIri {permissionSetIri} must be an convertible to AnyIRI or QName: {permissionSetIri} ({type(permissionSetIri)}) does not work.')
            else:
                raise OmasErrorValue(f'permissionSetIri {permissionSetIri} must be an instance of AnyIRI, QName or str, not {type(permissionSetIri)}.')
        else:
            self.__fields[PermissionSetFields.PERMISSION_SET_IRI] = Xsd_anyURI(uuid.uuid4().urn)

        if label:
            self.__fields[PermissionSetFields.LABEL] = label if isinstance(label, LangString) else LangString(label)
        if comment:
            self.__fields[PermissionSetFields.COMMENT] = comment if isinstance(comment, LangString) else LangString(comment)
        self.__fields[PermissionSetFields.GIVES_PERMISSION] = givesPermission

        if isinstance(definedByProject, Xsd_QName) or isinstance(definedByProject, Xsd_anyURI):
            self.__fields[PermissionSetFields.DEFINED_BY_PROJECT] = definedByProject
        elif isinstance(definedByProject, str):
            try:
                self.__fields[PermissionSetFields.DEFINED_BY_PROJECT] = str(definedByProject)
            except Exception as e:
                raise OmasErrorValue(f'definedByProject {definedByProject} must be an instance of AnyIRI, QName or str, not {type(definedByProject)}.')

        for field in PermissionSetFields:
            prefix, name = field.value.split(':')
            setattr(PermissionSet, name, property(
                partial(self.__get_value, field=field),
                partial(self.__set_value, field=field),
                partial(self.__del_value, field=field)))
        self.__change_set = {}

    def __get_value(self: Self, self2: Self, field: PermissionSetFields) -> PermissionSetFieldTypes | None:
        return self.__fields.get(field)

    def __set_value(self: Self, self2: Self, value: PermissionSetFieldTypes, field: PermissionSetFields) -> None:
        if field == PermissionSetFields.PERMISSION_SET_IRI and self.__fields.get(PermissionSetFields.PERMISSION_SET_IRI) is not None:
            OmasErrorAlreadyExists(f'A project IRI already has been assigned: "{repr(self.__fields.get(PermissionSetFields.PERMISSION_SET_IRI))}".')
        self.__change_setter(field, value)

    def __del_value(self: Self, self2: Self, field: PermissionSetFields) -> None:
        del self.__fields[field]

    def __change_setter(self, field: PermissionSetFields, value: PermissionSetFieldTypes) -> None:
        if self.__fields[field] == value:
            return
        if field == PermissionSetFields.PERMISSION_SET_IRI:
            raise OmasErrorAlreadyExists(f'Field {field.value} is immutable.')
        if self.__fields[field] is None:
            if self.__change_set.get(field) is None:
                self.__change_set[field] = PermissionSetFieldChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__change_set.get(field) is None:
                    self.__change_set[field] = PermissionSetFieldChange(self.__fields[field], Action.DELETE)
            else:
                if self.__change_set.get(field) is None:
                    self.__change_set[field] = PermissionSetFieldChange(self.__fields[field], Action.REPLACE)

        if value is None:
            del self.__fields[field]
        else:
            if isinstance(self.__datatypes[field], set):
                dtypes = list(self.__datatypes[field])
                for dtype in dtypes:
                    try:
                        self.__fields[field] = dtype(value)
                        break;
                    except OmasErrorValue:
                        pass
            else:
                self.__fields[field] = self.__datatypes[field](value)

    def __str__(self) -> str:
        res = f'PermissionSet: {self.__fields[PermissionSetFields.PERMISSION_SET_IRI]}\n'\
              f'  Creation: {self.__created.isoformat()} by {self.__creator}\n'\
              f'  Modified: {self.__modified.isoformat()} by {self.__contributor}\n' \
              f'  Label: {self.__fields.get(PermissionSetFields.LABEL, "-")}\n' \
              f'  Comment: {self.__fields.get(PermissionSetFields.COMMENT, "-")}\n'\
              f'  Permission: {self.__fields[PermissionSetFields.GIVES_PERMISSION].name}\n'\
              f'  For project: {self.__fields[PermissionSetFields.DEFINED_BY_PROJECT]}\n'
        return res

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

    @property
    def changeset(self) -> Dict[PermissionSetFields, PermissionSetFieldChange]:
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

    def create(self, indent: int = 0, indent_inc: int = 4) ->None:
        if self._con is None:
            raise OmasError("Cannot create: no connection")

        actor = self._con.userdata
        sysperms = actor.inProject.get(Xsd_QName('omas:SystemProject'))
        is_root: bool = False
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            is_root = True
        if not is_root:
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    raise OmasErrorNoPermission(f'No permission to create permission sets in project {proj}.')
                if AdminPermission.ADMIN_PERMISSION_SETS not in actor.inProject.get(proj):
                    raise OmasErrorNoPermission(f'No permission to create permission sets for project {proj}.')
            projs = self.inProject.keys()
            if not self.definedByProject in projs:
                raise OmasErrorNoPermission(f'No permission to create permission sets for project {self.definedByProject}.')

        context = Context(name=self._con.context_name)
        blank = ''

        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?permset
        FROM omas:admin
        WHERE {{
            ?permset a omas:PermissionSet .
            FILTER(?permset = {self.permissionSetIri.resUri})       
        }}
        """

        timestamp = datetime.now()
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH omas:admin {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}} {self.permissionSetIri.resUri} a omas:PermissionSet'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}rdfs:label {self.label}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}rdfs:comment {self.comment}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:givesPermission omas:{self.givesPermission.name}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}omas:defineByProject {self.definedByProject}'

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

    @classmethod
    def read(cls, con: IConnection, permissionSetIri: Xsd_QName | Xsd_anyURI | str) -> Self:
        if isinstance(permissionSetIri, Xsd_anyURI) or isinstance(permissionSetIri, Xsd_QName):
            pass
        elif isinstance(permissionSetIri, str):
            try:
                permissionSetIri = str2qname_anyiri(permissionSetIri)
            except:
                raise OmasErrorValue(f'permissionSetIri {permissionSetIri} must be an convertible to AnyIRI or QName: {permissionSetIri} ({type(permissionSetIri)}) does not work.')
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?permset ?p ?o
        FROM omas:admin
        WHERE {{
            BIND({repr(permissionSetIri)} as ?permset)
            ?permset a omas:PermissionSet .
            ?permset ?p ?o .
        }}
        """
        jsonobj = con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        permissionSetIri: Xsd_QName | Xsd_anyURI | None = None
        creator: Xsd_QName | Xsd_anyURI | None = None
        created: datetime | None = None
        contributor: Xsd_QName | Xsd_anyURI | None = None
        modified: datetime | None = None
        label: LangString = LangString()
        comment: LangString = LangString()
        givesPermission: DataPermission | None = None
        definedByProject: Xsd_QName | Xsd_anyURI | None = None
        for r in res:
            if not permissionSetIri:
                try:
                    permissionSetIri = str2qname_anyiri(r['permset'])
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
                    label.add(str(r['o']))
                case 'rdfs:comment':
                    comment.add(str(r['o']))
                case 'omas:givesPermission':
                    givesPermission = DataPermission.from_string(str(r['o']))
                case 'omas:definedByProject':
                    try:
                        definedByProject = str2qname_anyiri(str(r['o']))
                    except:
                        raise OmasErrorInconsistency(f'Invalid project identifier "{r['o']}".')
        return cls(con=con,
                   permissionSetIri=permissionSetIri,
                   creator=creator,
                   created=created,
                   contributor=contributor,
                   modified=modified,
                   label=label,
                   comment=comment,
                   givesPermission=givesPermission,
                   definedByProject=definedByProject)


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    ps = PermissionSet.read(con, Xsd_QName('omas:GenericView'))
    print(str(ps))
