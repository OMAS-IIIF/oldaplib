from typing import Any

from pystrict import strict
from rdflib import BNode

from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd_qname import Xsd_QName


@strict
@serializer
class BNode(Xsd_QName):
    """
    # BNode

    Represents a blank node in the triple store. The class has the following methods:

    - *Constructor*: Initialize a blank node
    - *str()*: Return the name of the blank node
    - *repr()*: Return the Python representation of the blank node
    - *==*: Test for equality of 2 blank nodes
    - *!=*: Test for inequality of 2 blank nodes
    - *hash()*: Return the hash of the blank node
    - *value()*: Return the value of the blank node (same as str())
    """

    def __init__(self, value: Xsd_QName | str) -> None:
        """
        Construct a blank node from its name
        :param value: Name/id of the blank node
        :type value: str
        """
        super().__init__(value)
        if self.prefix != '_':
            raise OmasErrorValue('BNode prefix is not "_"')

    def __repr__(self) -> str:
        """
        Return the Python representation of the BNode
        :return: Python representation of the BNode
        """
        return f'BNode("{self._value}")'
