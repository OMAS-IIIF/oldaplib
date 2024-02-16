from dataclasses import dataclass
from datetime import datetime, time, date, timedelta
from typing import List, Dict, Optional, Self

import isodate
from isodate import Duration
from pystrict import strict

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import BNode, QName, AnyIRI, NCName
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.serializer import serializer


@dataclass
@strict
@serializer
class OmasStringLiteral:
    __value: str
    __lang: Language | None

    def __init__(self, value: str, lang: Optional[str] = None):
        self.__value = value
        self.__lang = Language[lang.upper()] if lang else None

    def __str__(self) -> str:
        if self.__lang:
            return f'{self.__value}@{self.__lang.name.lower()}'
        else:
            return self.__value

    def __repr__(self) -> str:
        if self.__lang:
            return f'"{self.__value}"@{self.__lang.name.lower()}'
        else:
            return f'"self.__value"'

    def __eq__(self, other: str | Self) -> bool:
        if isinstance(other, OmasStringLiteral):
            return self.__value == other.__value and self.__lang == other.__lang
        elif isinstance(other, str):
            return self.__value == other

    def __hash__(self) -> int:
        if self.__lang:
            return hash(self.__value + '@' + self.__lang.value)
        else:
            return hash(self.__value)

    def _as_dict(self) -> dict:
        return {
            "value": self.__value,
            "lang": self.__lang
        }


    @property
    def value(self) -> str:
        return self.__value

    @property
    def lang(self) -> Language | None:
        return self.__lang


RowElementType = bool | int | float | str | datetime | time | date | Duration | timedelta | QName | BNode | AnyIRI | NCName | OmasStringLiteral
RowType = Dict[str, RowElementType]


@dataclass
@strict
class QueryProcessor:

    __names: List[str]
    __context: Context
    __rows: List[Dict[str, RowElementType]]
    __pos: int

    def __init__(self, context: Context, query_result: Dict) -> None:
        self.__context = context
        self.__pos = 0
        self.__rows = []
        self.__names = query_result["head"]["vars"]
        for tmprow in query_result["results"]["bindings"]:
            row: Dict[str, RowElementType] = {}
            for name, valobj in tmprow.items():
                if valobj["type"] == "uri":
                    row[name] = context.iri2qname(valobj["value"])
                    if row[name] is None:
                         row[name] = AnyIRI(valobj["value"])

                elif valobj["type"] == "bnode":
                    row[name] = BNode(valobj["value"])
                elif valobj["type"] == "literal":
                    dt = valobj.get("datatype")
                    if dt is None:
                        row[name] = OmasStringLiteral(valobj["value"], valobj.get("xml:lang"))
                    else:
                        dt = context.iri2qname(dt)
                        match str(dt):
                            case 'xsd:NCName':
                                row[name] = NCName(valobj["value"])
                            case 'xsd:string':
                                row[name] = OmasStringLiteral(valobj["value"], valobj.get("xml:lang"))
                            case 'xsd:boolean':
                                row[name] = True if valobj["value"] == 'true' else False
                            case 'xsd:integer':
                                row[name] = int(valobj["value"])
                            case 'xsd:int':
                                row[name] = int(valobj["value"])
                            case 'xsd:float':
                                row[name] = float(valobj["value"])
                            case 'xsd:double':
                                row[name] = float(valobj["value"])
                            case 'xsd:decimal':
                                row[name] = float(valobj["value"])
                            case 'xsd:dateTime':
                                row[name] = datetime.fromisoformat(valobj["value"])
                            case 'xsd:time':
                                row[name] = time.fromisoformat(valobj["value"])
                            case 'xsd:date':
                                row[name] = date.fromisoformat(valobj["value"])
                            case 'xsd:duration':
                                row[name] = isodate.parse_duration(valobj["value"])
                            case _:
                                row[name] = str(valobj["value"])
            self.__rows.append(row)

    def __len__(self) -> int:
        return len(self.__rows)

    def __iter__(self):
        self.__pos = 0
        return self

    def __next__(self):
        if self.__pos >= len(self.__rows):
            raise StopIteration
        self.__pos += 1
        return self.__rows[self.__pos - 1]
        # self.__pos += 1
        # if self.__pos < len(self.__rows):
        #     return self.__rows[self.__pos]
        # else:
        #     raise StopIteration

    def __getitem__(self, item: int) -> Dict[str, RowElementType]:
        return self.__rows[item]

    @property
    def names(self) -> List[str]:
        return list(self.__names)





