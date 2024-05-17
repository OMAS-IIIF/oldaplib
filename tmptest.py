import json
from enum import Enum

from oldaplib.src.helpers.serializer import serializer


@serializer
class ExtendedEnum(Enum):
    def __init__(self, value: str, description: str):
        self._value_ = value
        self.description = description

    def _as_dict(self):
        return {'value': self._value_, 'description': self.description}

def create_enum(enum_name: str, query: str):
    if query == 'a':
        items = {
            'A': ('aa', 'An aa'),
            'B': ('bb', 'A bb'),
            'C': ('cc', 'A cc'),
        }
    elif query == 'x':
        items = {
            'X': ('xx', 'A xx'),
            'Y': ('yy', 'A yy'),
            'Z': ('zz', 'A ZZ'),
        }
    else:
        items = {
            'ONE': ('1', 'A one'),
            'TWO': ('2', 'A two'),
            'THREE': ('3', 'A three'),
        }
    return Enum(enum_name, items, type=ExtendedEnum)

if __name__ == '__main__':
    EnumA = create_enum('EnumA', 'a')
    EnumB = create_enum('EnumX', 'x')

    a = EnumA.A
    print(a)

    a_jsonstr = json.dumps(a, default=serializer.encoder_default)
    print(a_jsonstr)
