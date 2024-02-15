import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from functools import partial
from typing import Dict, Optional, Self

from pystrict import strict

from omaslib.src.connection import Connection
from omaslib.src.helpers.datatypes import QName, AnyIRI, Action
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorAlreadyExists
from omaslib.src.model import Model

PermissionSetFieldTypes = AnyIRI | QName | LangString | None

@dataclass
class PermissionSetFieldChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: PermissionSetFieldTypes
    action: Action


@unique
class PermissionSetFields(Enum):
    PERMISSION_SET_IRI = 'omas:permissionSetIri'  # virtual property, no equivalent in RDF
    LABEL = 'rdfs:label'
    COMMENT = 'rdfs:comment'
    GIVES_PERMISSION = 'omas:givesPermission'
    DEFINED_BY_PROJECT = 'omas:definedByProject'


@strict
class PermissionSet(Model):
    __datatypes = {
        PermissionSetFields.LABEL: LangString,
        PermissionSetFields.COMMENT: LangString,
        PermissionSetFields.GIVES_PERMISSION: QName,
        PermissionSetFields.DEFINED_BY_PROJECT: AnyIRI
    }

    __creator: AnyIRI | None
    __created: datetime | None
    __contributor: AnyIRI | None
    __modified: datetime | None

    __fields: Dict[PermissionSetFields, PermissionSetFieldTypes]

    __change_set: Dict[PermissionSetFields, PermissionSetFieldChange]

    def __init__(self, *,
                 con: Connection,
                 creator: Optional[AnyIRI] = None,
                 created: Optional[datetime] = None,
                 contributor: Optional[AnyIRI] = None,
                 modified: Optional[datetime] = None,
                 permissionSetIri: Optional[AnyIRI] = None,
                 label: Optional[LangString | str],
                 comment: Optional[LangString | str],
                 givesPermission: QName | str,
                 definedByProject: AnyIRI | QName | str):
        super().__init__(con)
        self.__creator = creator if creator is not None else con.userIri
        self.__created = created
        self.__contributor = contributor if contributor is not None else con.userIri
        self.__modified = modified
        self.__fields = {}

        if permissionSetIri:
            if isinstance(permissionSetIri, AnyIRI):
                self.__fields[PermissionSetFields.PERMISSION_SET_IRI] = permissionSetIri
            else:
                raise OmasErrorValue(f'permissionSetIri {permissionSetIri} must be an instance of AnyIRI, not {type(permissionSetIri)}')
        else:
            self.__fields[PermissionSetFields.PERMISSION_SET_IRI] = AnyIRI(uuid.uuid4().urn)

        if label:
            self.__fields[PermissionSetFields.LABEL] = label if isinstance(label, LangString) else LangString(label)
        if comment:
            self.__fields[PermissionSetFields.COMMENT] = comment if isinstance(comment, LangString) else LangString(comment)
        self.__fields[PermissionSetFields.GIVES_PERMISSION] = givesPermission if isinstance(givesPermission, QName) else QName(givesPermission)
        self.__fields[PermissionSetFields.DEFINED_BY_PROJECT] = definedByProject

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
            self.__fields[field] = self.__datatypes[field](value)

    def __str__(self) -> str:
        res = f'PermissionSet: {self.__fields[PermissionSetFields.PERMISSION_SET_IRI]}\n'\
              f'  Creation: {self.__created.isoformat()} by {self.__creator}\n'\
              f'  Modified: {self.__modified.isoformat()} by {self.__contributor}\n' \
              f'  Label: {self.__fields[PermissionSetFields.LABEL]}\n' \
              f'  Comment: {self.__fields[PermissionSetFields.COMMENT]}\n'\
              f'  Permission {self.__fields[PermissionSetFields.GIVES_PERMISSION]}\n'\
              f'  For project: {self.__fields[PermissionSetFields.GIVES_PERMISSION]}\n'
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

