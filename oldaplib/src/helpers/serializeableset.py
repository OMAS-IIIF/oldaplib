from typing import Set, Iterable

from oldaplib.src.helpers.serializer import serializer


@serializer
class SerializeableSet(Set):

    def __init__(self, setitems: Iterable | None = None, *items):
        if setitems:
            super().__init__(setitems)
        else:
            super().__init__(items)

    def _as_dict(self) -> dict:
        return {'setitems': list(self)}
