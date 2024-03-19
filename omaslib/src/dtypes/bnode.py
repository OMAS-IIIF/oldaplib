from typing import Any

from pystrict import strict

from omaslib.src.helpers.serializer import serializer


@strict
@serializer
class BNode:
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
    __value: str

    def __init__(self, value: str) -> None:
        """
        Construct a blank node from its name
        :param value: Name/id of the blank node
        :type value: str
        """
        self.__value = value

    def __str__(self) -> str:
        """
        Return the string representation of the BNode
        :return: string representation of the BNode
        """
        return self.__value

    def __repr__(self) -> str:
        """
        Return the Python representation of the BNode
        :return: Python representation of the BNode
        """
        return self.__value

    def __eq__(self, other: Any) -> bool:
        """
        Test for equality of two BNodes
        :param other: Another BNode to compare with
        :return: True of False
        """
        return isinstance(other, BNode) and self.__value == other.__value

    def __ne__(self, other: Any) -> bool:
        """
        Test for inequality of two BNodes
        :param other: Any BNode to compare with
        :type other: BNode
        :return: True or False
        """
        return self.__value != str(other)

    def __hash__(self):
        """
        Return the hash of the BNode
        :return: Hash of the BNode
        """
        return hash(self.__value)

    def _as_dict(self):
        """used for json serialization using serializer"""
        return {
            'value': self.__value
        }

    @property
    def value(self) -> str:
        """
        Return the BNode's value (equivalent to str())
        :return: String representation of the BNode
        :rtype: string
        """
        return self.__value
