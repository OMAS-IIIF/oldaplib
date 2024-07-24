from dataclasses import dataclass
from typing import Any

from oldaplib.src.enums.action import Action


@dataclass
class AttributeChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: Any
    action: Action
