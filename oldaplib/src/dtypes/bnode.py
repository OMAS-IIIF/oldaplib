from typing import Any

from pystrict import strict
from rdflib import BNode

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd_qname import Xsd_QName


#@strict
@serializer
class BNode(Xsd_QName):
    """
    Represents a blank node in the triple store.

    This class provides functionality to handle blank nodes which are
    used as identifiers in a triple store. Blank nodes are unique,
    non-reusable, and have no intrinsic meaning outside of their use as
    identifiers. This class ensures that blank nodes adhere to specific
    conventions and provides methods for their manipulation.

    :ivar value: Name/id of the blank node.
    :type value: Xsd_QName | str
    """

    def __init__(self, value: Xsd_QName | str, validate: bool = False) -> None:
        """
        Construct a blank node with a specified name or id.

        :param value: Name or id of the blank node.
        :type value: Xsd_QName | str
        :param validate: Determines whether to validate the blank node.
        :type validate: bool
        :raises OldapErrorValue: If the prefix of the blank node is not '_'.
        """
        super().__init__(value, validate=validate)
        if self.prefix != '_':
            raise OldapErrorValue('BNode prefix is not "_"')

    def __repr__(self) -> str:
        """
        Return the Python representation of the BNode
        :return: Python representation of the BNode
        """
        return f'BNode("{self._value}")'

