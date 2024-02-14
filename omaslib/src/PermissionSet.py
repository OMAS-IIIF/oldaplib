from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from typing import Dict, Optional

from pystrict import strict

from omaslib.src.connection import Connection
from omaslib.src.helpers.datatypes import QName, AnyIRI, Action
from omaslib.src.helpers.langstring import LangString
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
                 label: Optional[LangString | str],
                 comment: Optional[LangString | str],
                 givesPermission: Optional[QName],
                 definedByProject: Optional[AnyIRI] = None):
        super().__init__(con)
        self.__creator = creator if creator is not None else con.userIri
        self.__created = created
        self.__contributor = contributor if contributor is not None else con.userIri
        self.__modified = modified
        self.__fields = {}

