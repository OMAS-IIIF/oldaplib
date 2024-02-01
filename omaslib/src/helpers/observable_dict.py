import json
from collections import UserDict
from typing import Callable, Self, Any, Iterable, Mapping

from pystrict import strict

from omaslib.src.helpers.serializer import serializer


@strict
@serializer
class ObservableDict(UserDict):
    __on_change: Callable[[Self], None]

    def __init__(self,
                 obj: Iterable | Mapping | None = None, *,
                 on_change: Callable[[Self], None] | None = None,
                 **kwargs):
        self.__on_change = on_change
        if obj:
            super().__init__(obj, **kwargs)
        else:
            super().__init__(**kwargs)

    def __setitem__(self, key, value):
        if self.__on_change:
            self.__on_change(self.copy())
        super().__setitem__(key, value)

    def copy(self) -> Self:
        return ObservableDict(self.data.copy())

    def set_on_change(self, on_change: Callable[[Self], None]) -> None:
        self.__on_change = on_change

    def _as_dict(self):
        return self.data


if __name__ == "__main__":
    def cb(old: ObservableDict):
        print("---->CALLBACK", old)

    gaga = ObservableDict({'a': 'AA', 'b': 'BB'}, on_change=cb)
    print(gaga)
    jsonstr = json.dumps(gaga, default=serializer.encoder_default)
    print(jsonstr)
    gaga2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    print(type(gaga2), gaga2)
    gaga2.set_on_change(cb)
    gaga2['xx'] = 'XXXXXX'
    print(gaga2)
    #gugusta: ObservableDict[str] = ObservableDict(cb)
    # gaga.update({'c': 'CC'})
    # print(gaga)
    # print(gaga.get('c'), gaga.get('x'))
    #
    # gugus = {'a': 'AAAA', 'b': 'BBBB'}
    # g = ObservableDict(cb, gugus)
    # print(g)
    # for k, v in gaga.items():
    #     print(k, '->', v)