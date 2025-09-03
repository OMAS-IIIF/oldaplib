import json
from typing import Iterable

from pystrict import strict

from oldaplib.src.dtypes.rdfset import RdfSet
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.oldaperror import OldapErrorType, OldapErrorInconsistency
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_string import Xsd_string


@serializer
class XsdSet(RdfSet[Xsd]):
    """
    The XsdSet is a specialized subclass of RdfSet that restricts the set values
    to instances or subclasses of the Xsd class, ensuring compatibility with Xsd
    data types.

    This class enforces strict type constraints to maintain the integrity of the
    data structure. It provides methods to initialize the set, ensuring that all
    values are valid Xsd objects, and to add new Xsd-compatible elements while
    adhering to the set's internal consistency.

    :ivar _data: A set that contains the actual data stored in the XsdSet.
    :type _data: set
    """

    def __init__(self, *args: Iterable[Xsd] | Xsd, value: Iterable[Xsd] | Xsd | None = None, validate: bool = False):
        """
        Initializes an instance of the class with type checking for provided arguments. This constructor
        ensures the provided arguments are instances of the "Xsd" type or iterables containing only
        instances of "Xsd". If the type checking fails, an appropriate exception is raised.

        :param args: A single instance of Xsd, an iterable containing Xsd instances, or an empty tuple.
        :param value: Optional; An instance of Xsd, an iterable of Xsd instances, or None.
        :param validate: Optional; A boolean indicating whether validation should occur.
        :raises OldapErrorType: Raised when the provided value or elements of iterables in args
            or value are not instances of Xsd.
        """
        #
        # Here we first do some fancy type checking, before we call the superclass' __init__() method
        #
        if len(args) == 0:
            if value is None:
                pass
            else:
                if isinstance(value, Iterable):
                    for v in value:
                        if not isinstance(v, Xsd):
                            raise OldapErrorType(f'Iterable contains element that is not an instance of "Xsd", but "{type(v).__name__}".')
                else:
                    if not isinstance(value, Xsd):
                        raise OldapErrorType(f'Value is not an instance of "Xsd", but "{type(value).__name__}".')
        elif len(args) == 1:
            if isinstance(args[0], Iterable):
                for v in args[0]:
                    if not isinstance(v, Xsd):
                        raise OldapErrorType(f'Iterable contains element that is not an instance of "Xsd", but "{type(v).__name__}".')
            else:
                if not isinstance(args[0], Xsd):
                    raise OldapErrorType(f'Value is not an instance of "Xsd", but "{type(args[0]).__name__}".')
        else:
            for arg in args:
                if not isinstance(args[0], Xsd):
                    raise OldapErrorType(f'Value is not an instance of "Xsd", but "{type(args[0]).__name__}".')
        super().__init__(*args, value=value)

    def add(self, val: Xsd) -> None:
        """
        Adds a new element to the data set.

        The method validates the input, ensuring it matches the valid type
        or converts it appropriately before addition. If the data set is
        empty and the input type is invalid, an exception is raised.

        :param val: The value to be added to the data set.
        :type val: Xsd
        :return: None
        :raises OldapErrorInconsistency: If the data set is empty and the provided
            value is incompatible with the expected data type.
        """
        self.notify()
        if isinstance(val, Xsd) and not type(val) is Xsd:
            self._data.add(val)
        else:
            if not self._data:
                raise OldapErrorInconsistency(f"It's not possible to add {val} to an empty set.")
            item_type = type(next(iter(self._data)))
            self._data.add(item_type(val))


if __name__ == "__main__":
    gaga = XsdSet(None)