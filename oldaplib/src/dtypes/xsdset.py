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
    The XsdSet is a subclass of [RdfSet](/python_docstrings/rdfset) that restricts the set values to
    subclasses of the Xsd class, that is Xsd compatible data types.
    """

    def __init__(self, *args: Iterable[Xsd] | Xsd, value: Iterable[Xsd] | Xsd | None = None):
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