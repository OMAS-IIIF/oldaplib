from dataclasses import dataclass
from datetime import datetime, time, date, timedelta
from typing import List, Dict

import isodate
from isodate import Duration
from pystrict import strict

from omaslib.src.helpers.oldap_string_literal import OldapStringLiteral
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import BNode, QName, AnyIRI, NCName, Xsd_gYearMonth, Xsd_gYear, Xsd, Xsd_gDay, Xsd_gMonth, Xsd_hexBinary, Xsd_base64Binary, \
    Xsd_anyURI, Xsd_normalizedString, Xsd_token, Xsd_language

RowElementType = bool | int | float | str | datetime | time | date | Duration | timedelta | QName | BNode | AnyIRI | NCName | OldapStringLiteral | Xsd
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
                        row[name] = OldapStringLiteral.fromRdf(valobj["value"], valobj.get("xml:lang"))
                    else:
                        dt = context.iri2qname(dt)
                        match str(dt):
                            case 'xsd:string':
                                row[name] = OldapStringLiteral.fromRdf(valobj["value"], valobj.get("xml:lang"))
                            case 'xsd:boolean':
                                row[name] = True if valobj["value"] == 'true' else False
                            case 'xsd:decimal':
                                row[name] = float(valobj["value"])
                            case 'xsd:float':
                                row[name] = float(valobj["value"])
                            case 'xsd:double':
                                row[name] = float(valobj["value"])
                            case 'xsd:duration':
                                row[name] = isodate.parse_duration(valobj["value"])
                            case 'xsd:dateTime':
                                row[name] = datetime.fromisoformat(valobj["value"])
                            case 'xsd:dateTimeStamp':
                                row[name] = datetime.fromisoformat(valobj["value"])
                            case 'xsd:time':
                                row[name] = time.fromisoformat(valobj["value"])
                            case 'xsd:date':
                                row[name] = date.fromisoformat(valobj["value"])
                            case 'xsd:gYearMonth':
                                row[name] = Xsd_gYearMonth.fromRdf(valobj["value"])
                            case 'xsd:gYear':
                                row[name] = Xsd_gYear.fromRdf(valobj["value"])
                            case 'xsd:gDay':
                                row[name] = Xsd_gDay.fromRdf(valobj["value"])
                            case 'xsd:gMonth':
                                row[name] = Xsd_gMonth.fromRdf(valobj["value"])
                            case 'xsd:hexBinary':
                                row[name] = Xsd_hexBinary.fromRdf(valobj["value"])
                            case 'xsd:base64Binary':
                                row[name] = Xsd_base64Binary.fromRdf(valobj["value"])
                            case 'xsd:anyURI':
                                row[name] = Xsd_anyURI.fromRdf(valobj["value"])
                            case 'xsd:QName':
                                row[name] = QName(valobj["value"])
                            case 'xsd:normalizedString':
                                row[name] = Xsd_normalizedString.fromRdf(valobj["value"])
                            case 'xsd:token:':
                                row[name] = Xsd_token.fromRdf(valobj["value"])
                            case 'xsd:language':
                                row[name] = Xsd_language.fromRdf(valobj["value"])
                            case 'xsd:NCName':
                                row[name] = NCName.fromRdf(valobj["value"])
                            case 'xsd:integer':
                                row[name] = int(valobj["value"])
                            case 'xsd:int':
                                row[name] = int(valobj["value"])
                            case 'xsd:nonPositiveInteger':
                                row[name] = int(valobj["value"])
                            case 'xsd:negativeInteger':
                                row[name] = int(valobj["value"])
                            case 'xsd:long':
                                row[name] = int(valobj["value"])
                            case 'xsd:short':
                                row[name] = int(valobj["value"])
                            case 'xsd:dateTime':
                                row[name] = datetime.fromisoformat(valobj["value"])
                            case 'xsd:time':
                                row[name] = time.fromisoformat(valobj["value"])
                            case 'xsd:date':
                                row[name] = date.fromisoformat(valobj["value"])
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
