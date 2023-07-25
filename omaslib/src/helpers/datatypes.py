from typing import Dict, Any, Union
from pystrict import strict
from .xsd_datatypes import XsdDatatypes, XsdValidator
from .omaserror import OmasError
from dataclasses import dataclass


@strict
class QName:
    _value: str

    def __init__(self, value: str) -> None:
        if not XsdValidator.validate(XsdDatatypes.QName, value):
            raise OmasError("Invalid string for QName")
        self._value = value

    def __add__(self, other: Any) -> 'QName':
        return QName(self._value + str(other))

    def __iadd__(self, other):
        return QName(self._value + str(other))

    def __repr__(self):
        return f"QName({self._value})"

    def __str__(self):
        return self._value

    def __eq__(self, other: Any):
        return self._value == str(other)

    def __ne__(self, other: Any):
        return self._value != str(other)

    def __hash__(self):
        return self._value.__hash__()

    @property
    def prefix(self):
        parts = self._value.split(':')
        return parts[0]

    @property
    def fragment(self):
        parts = self._value.split(':')
        return parts[1]

@strict
class AnyURI:
    _value: str
    _append_allowed: bool

    def __init__(self, value: Union['AnyURI', str]):
        if isinstance(value, AnyURI):
            self._value = str(value)
        else:
            if not XsdValidator.validate(XsdDatatypes.anyURI, value):
                raise OmasError("Invalid string for anyURI")
            self._value = value
        self._append_allowed = self._value[-1] == '/' or self._value[-1] == '#'

    def __add__(self, other: Any) -> 'AnyURI':
        return AnyURI(self._value + str(other))

    def __iadd__(self, other) -> 'AnyURI':
        return AnyURI(self._value + str(other))

    def __repr__(self) -> str:
        return f"AnyURI({self._value})"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: Any) -> bool:
        return self._value == str(other)

    def __ne__(self, other: Any) -> bool:
        return self._value != str(other)

    def __hash__(self) -> int:
        return self._value.__hash__()

    @property
    def append_allowed(self) -> bool:
        return self._append_allowed


@strict
class NCName:
    _value: str

    def __init__(self, value: Union['NCName', str]):
        if isinstance(value, NCName):
            self._value = str(value)
        else:
            if not XsdValidator.validate(XsdDatatypes.NCName, value):
                raise OmasError("Invalid string for NCName")
            self._value = value

    def __add__(self, other: Any) -> 'NCName':
        return NCName(self._value + str(other))

    def __iadd__(self, other) -> 'NCName':
        return NCName(self._value + str(other))

    def __repr__(self) -> str:
        return f"NCName({self._value})"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: Any) -> bool:
        return self._value == str(other)

    def __ne__(self, other: Any) -> bool:
        return self._value != str(other)

    def __hash__(self) -> int:
        return self._value.__hash__()


@strict
class Context:
    _context: Dict[NCName, AnyURI]

    def __init__(self):
        self._context = {
            NCName('rdf'): AnyURI('http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
            NCName('rdfs'): AnyURI('http://www.w3.org/2000/01/rdf-schema#'),
            NCName('owl'): AnyURI('http://www.w3.org/2002/07/owl#'),
            NCName('xsd'): AnyURI('http://www.w3.org/2001/XMLSchema#'),
            NCName('xml'): AnyURI('http://www.w3.org/XML/1998/namespace#'),
            NCName('sh'): AnyURI('http://www.w3.org/ns/shacl#'),
            NCName('skos'): AnyURI('http://www.w3.org/2004/02/skos/core#'),
            NCName('omas'): AnyURI('http://omas.org/base#')
        }

    def __getitem__(self, prefix: Union[NCName, str]) -> AnyURI:
        if not isinstance(prefix, NCName):
            prefix = NCName(prefix)
        return self._context[prefix]

    def __setitem__(self, prefix: Union[NCName, str], iri: Union[AnyURI, str]) -> None:
        if not isinstance(prefix, NCName):
            prefix = NCName(prefix)
        if not isinstance(iri, AnyURI):
            iri = AnyURI(iri)
        if not iri.append_allowed:
            raise OmasError("IRI must end with # or /")
        self._context[prefix] = iri

    def __delitem__(self, prefix: Union[NCName, str]):
        if not isinstance(prefix, NCName):
            prefix = NCName(prefix)
        self._context.pop(prefix)

    def __iter__(self):
        return self._context.__iter__()

    def items(self):
        return self._context.items()

    @property
    def sparql_context(self) -> str:
        contextlist = [f"PREFIX {str(x)}: <{str(y)}>" for x,y in self._context.items()]
        return "\n".join(contextlist)


if __name__ == '__main__':
    gaga = Context()
    gaga['hyha'] = 'http://omas.org/projects/hyperhamlet#'
    print(gaga.sparql_context)



