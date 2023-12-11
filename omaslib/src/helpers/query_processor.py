from dataclasses import dataclass
from datetime import datetime, time, date, timedelta
from typing import List, Dict, Optional, Union

import isodate
from isodate import Duration
from pystrict import strict

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import BNode
from omaslib.src.helpers.language import Language


class StringLiteral:
    pass


RowElementType = Union[bool, int, float, str, datetime, time, Duration, timedelta, BNode, StringLiteral]


@dataclass
@strict
class StringLiteral:
    __value: str
    __lang: Union[Language, None]

    def __init__(self, value:str, lang: Optional[str] = None):
        self.__value = value
        self.__lang = Language[lang.upper()] if lang else None

    def __str__(self) -> str:
        return self.__value

    def __repr__(self) -> str:
        if self.__lang:
            return f'"{self.__value}"@{self.__lang.name.lower()}'
        else:
            return self.__value

    @property
    def value(self) -> str:
        return self.__value

    @property
    def lang(self) -> Union[Language, None]:
        return self.__lang


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
                elif valobj["type"] == "bnode":
                    row[name] = BNode(valobj["value"])
                elif valobj["type"] == "literal":
                    dt = valobj.get("datatype")
                    if dt is None:
                        row[name] = StringLiteral(valobj["value"], valobj.get("xml:lang"))
                    else:
                        dt = context.iri2qname(dt)
                        if dt == 'xsd:string':
                            row[name] = StringLiteral(valobj["value"], valobj.get("xml:lang"))
                        elif dt == 'xsd:boolean':
                            row[name] = True if valobj["value"] == 'true' else False
                        elif dt == 'xsd:integer':
                            row[name] = int(valobj["value"])
                        elif dt == 'xsd:float':
                            row[name] = float(valobj["value"])
                        elif dt == 'xsd:double':
                            row[name] = float(valobj["value"])
                        elif dt == 'xsd:decimal':
                            row[name] = float(valobj["value"])
                        elif dt == 'xsd:dateTime':
                            row[name] = datetime.fromisoformat(valobj["value"])
                        elif dt == 'xsd:time':
                            row[name] = time.fromisoformat(valobj["value"])
                        elif dt == 'xsd:date':
                            row[name] = date.fromisoformat(valobj["value"])
                        elif dt == 'xsd:duration':
                            row[name] = isodate.parse_duration(valobj["value"])
                        else:
                            row[name] = str(valobj["value"])
            self.__rows.append(row)

    def __iter__(self):
        self.__pos = 0
        return self

    def __next__(self):
        self.__pos += 1
        if self.__pos < len(self.__rows):
            return self.__rows[self.__pos]
        else:
            raise StopIteration





