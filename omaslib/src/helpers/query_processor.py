from dataclasses import dataclass
from datetime import datetime, time, date, timedelta
from typing import List, Dict

from isodate import Duration
from pystrict import strict

from omaslib.src.helpers.oldap_string_literal import OldapStringLiteral
from omaslib.src.helpers.context import Context
from omaslib.src.dtypes.bnode import BNode
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_name import Xsd_name
from omaslib.src.xsd.xsd_nmtoken import Xsd_NMTOKEN
from omaslib.src.xsd.xsd_positiveinteger import Xsd_positiveInteger
from omaslib.src.xsd.xsd_unsignedbyte import Xsd_unsignedByte
from omaslib.src.xsd.xsd_unsignedshort import Xsd_unsignedShort
from omaslib.src.xsd.xsd_unsignedint import Xsd_unsignedInt
from omaslib.src.xsd.xsd_unsignedlong import Xsd_unsignedLong
from omaslib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from omaslib.src.xsd.xsd_byte import Xsd_byte
from omaslib.src.xsd.xsd_short import Xsd_short
from omaslib.src.xsd.xsd_long import Xsd_long
from omaslib.src.xsd.xsd_int import Xsd_int
from omaslib.src.xsd.xsd_negativeinteger import Xsd_negativeInteger
from omaslib.src.xsd.xsd_nonpositiveinteger import Xsd_nonPositiveInteger
from omaslib.src.xsd.xsd_integer import Xsd_integer
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_language import Xsd_language
from omaslib.src.xsd.xsd_token import Xsd_token
from omaslib.src.xsd.xsd_normalizedstring import Xsd_normalizedString
from omaslib.src.xsd.xsd_base64binary import Xsd_base64Binary
from omaslib.src.xsd.xsd_hexbinary import Xsd_hexBinary
from omaslib.src.xsd.xsd_gmonth import Xsd_gMonth
from omaslib.src.xsd.xsd_gday import Xsd_gDay
from omaslib.src.xsd.xsd_gyear import Xsd_gYear
from omaslib.src.xsd.xsd_gyearmonth import Xsd_gYearMonth
from omaslib.src.xsd.xsd_date import Xsd_date
from omaslib.src.xsd.xsd_time import Xsd_time
from omaslib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_duration import Xsd_duration
from omaslib.src.xsd.xsd_double import Xsd_double
from omaslib.src.xsd.xsd_float import Xsd_float
from omaslib.src.xsd.xsd_decimal import Xsd_decimal
from omaslib.src.xsd.xsd_string import Xsd_string
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd import Xsd

RowElementType = bool | int | float | str | datetime | time | date | Duration | timedelta | Xsd_QName | BNode | Xsd_anyURI | Xsd_NCName | OldapStringLiteral | Xsd
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
                        row[name] = Xsd_anyURI(valobj["value"])
                elif valobj["type"] == "bnode":
                    row[name] = BNode(valobj["value"])
                elif valobj["type"] == "literal":
                    dt = valobj.get("datatype")
                    if dt is None:
                        if valobj.get("xml:lang") is not None:
                            row[name] = OldapStringLiteral.fromRdf(valobj["value"], valobj.get("xml:lang"))
                        else:
                            row[name] = Xsd_string.fromRdf(valobj["value"])
                    else:
                        dt = context.iri2qname(dt)
                        match str(dt):
                            case 'xsd:string':
                                row[name] = Xsd_string.fromRdf(valobj["value"])
                            case 'xsd:boolean':
                                row[name] = Xsd_boolean(valobj["value"])
                            case 'xsd:decimal':
                                row[name] = Xsd_decimal.fromRdf(valobj["value"])
                            case 'xsd:float':
                                row[name] = Xsd_float.fromRdf(valobj["value"])
                            case 'xsd:double':
                                row[name] = Xsd_double.fromRdf(valobj["value"])
                            case 'xsd:duration':
                                row[name] = Xsd_duration.fromRdf(valobj["value"])
                            case 'xsd:dateTime':
                                row[name] = Xsd_dateTime.fromRdf(valobj["value"])
                            case 'xsd:dateTimeStamp':
                                row[name] = Xsd_dateTimeStamp.fromRdf(valobj["value"])
                            case 'xsd:time':
                                row[name] = Xsd_time.fromRdf(valobj["value"])
                            case 'xsd:date':
                                row[name] = Xsd_date.fromRdf(valobj["value"])
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
                                row[name] = Xsd_QName(valobj["value"])
                            case 'xsd:normalizedString':
                                row[name] = Xsd_normalizedString.fromRdf(valobj["value"])
                            case 'xsd:token:':
                                row[name] = Xsd_token.fromRdf(valobj["value"])
                            case 'xsd:NMTOKEN':
                                row[name] = Xsd_NMTOKEN.fromRdf(valobj["value"])
                            case 'xsd:language':
                                row[name] = Xsd_language.fromRdf(valobj["value"])
                            case 'xsd:name':
                                row[name] = Xsd_name.fromRdf(valobj["value"])
                            case 'xsd:NCName':
                                row[name] = Xsd_NCName.fromRdf(valobj["value"])
                            case 'xsd:integer':
                                row[name] = Xsd_integer.fromRdf(valobj["value"])
                            case 'xsd:int':
                                row[name] = Xsd_int.fromRdf(valobj["value"])
                            case 'xsd:nonPositiveInteger':
                                row[name] = Xsd_nonPositiveInteger.fromRdf(valobj["value"])
                            case 'xsd:negativeInteger':
                                row[name] = Xsd_negativeInteger.fromRdf(valobj["value"])
                            case 'xsd:long':
                                row[name] = Xsd_long.fromRdf(valobj["value"])
                            case 'xsd:short':
                                row[name] = Xsd_short.fromRdf(valobj["value"])
                            case 'xsd:byte':
                                row[name] = Xsd_byte.fromRdf(valobj["value"])
                            case 'xsd:nonNegativeInteger':
                                row[name] = Xsd_nonNegativeInteger(valobj["value"])
                            case 'xsd:unsignedLong':
                                row[name] = Xsd_unsignedLong(valobj["value"])
                            case 'xsd:unsignedInt':
                                row[name] = Xsd_unsignedInt(valobj["value"])
                            case 'xsd:unsignedShort':
                                row[name] = Xsd_unsignedShort(valobj["value"])
                            case 'xsd:unsignedByte':
                                row[name] = Xsd_unsignedByte(valobj["value"])
                            case 'xsd:positiveInteger':
                                row[name] = Xsd_positiveInteger(valobj["value"])
                            case 'xsd:dateTime':
                                row[name] = datetime.fromisoformat(valobj["value"])
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
