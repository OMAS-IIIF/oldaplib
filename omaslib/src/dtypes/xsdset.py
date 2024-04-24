import json
from typing import Iterable

from pystrict import strict

from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.helpers.Notify import Notify
from omaslib.src.helpers.omaserror import OmasErrorType
from omaslib.src.helpers.serializer import serializer
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_string import Xsd_string


@serializer
class XsdSet(RdfSet[Xsd]):

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
                            raise OmasErrorType(f'Iterable contains element that is not an instance of "Xsd", but "{type(v).__name__}".')
                else:
                    if not isinstance(value, Xsd):
                        raise OmasErrorType(f'Value is not an instance of "Xsd", but "{type(value).__name__}".')
        elif len(args) == 1:
            if isinstance(args[0], Iterable):
                for v in args[0]:
                    if not isinstance(v, Xsd):
                        raise OmasErrorType(f'Iterable contains element that is not an instance of "Xsd", but "{type(v).__name__}".')
            else:
                if not isinstance(args[0], Xsd):
                    raise OmasErrorType(f'Value is not an instance of "Xsd", but "{type(args[0]).__name__}".')
        super().__init__(*args, value=value)


if __name__ == "__main__":
    x = XsdSet(Xsd_string("gaga"), Xsd_string("gugus"))
    print(x)
    print(repr(x))
    print(x.toRdf)
    jsonstr = json.dumps(x, default=serializer.encoder_default)
    print(jsonstr)
    x2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    print(x2)
