from enum import unique, Enum
from typing import Dict

from omaslib.src.helpers.serializer import serializer


@unique
@serializer
class Action(Enum):
    """
    # Action

    An Enumeration of the Actions that are supported on PropertyClass and ResourceClass attributes/restrictions

    - `Action.CREATE` = 'create'
    - `Action.MODIFY` = 'modify'
    - `Action.REPLACE` = 'replace'
    - `Action.DELETE` = 'delete'
    """
    CREATE = 'create'  # a new value has been added
    MODIFY = 'modify'  # a complex value (LangString, PropertyRestriction) has been modified
    REPLACE = 'replace'  # an existing value has been replaced by a new value
    DELETE = 'delete'  # an existing value has been deleted

    def _as_dict(self) -> Dict[str, str]:
        return {__class__: self.__class__.__name__, 'value': self.value}
