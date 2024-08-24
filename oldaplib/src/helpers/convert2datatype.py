from typing import Any

from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_base64binary import Xsd_base64Binary
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_byte import Xsd_byte
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_double import Xsd_double
from oldaplib.src.xsd.xsd_duration import Xsd_duration
from oldaplib.src.xsd.xsd_float import Xsd_float
from oldaplib.src.xsd.xsd_gday import Xsd_gDay
from oldaplib.src.xsd.xsd_gmonth import Xsd_gMonth
from oldaplib.src.xsd.xsd_gmonthday import Xsd_gMonthDay
from oldaplib.src.xsd.xsd_gyear import Xsd_gYear
from oldaplib.src.xsd.xsd_gyearmonth import Xsd_gYearMonth
from oldaplib.src.xsd.xsd_hexbinary import Xsd_hexBinary
from oldaplib.src.xsd.xsd_id import Xsd_ID
from oldaplib.src.xsd.xsd_idref import Xsd_IDREF
from oldaplib.src.xsd.xsd_int import Xsd_int
from oldaplib.src.xsd.xsd_language import Xsd_language
from oldaplib.src.xsd.xsd_long import Xsd_long
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_negativeinteger import Xsd_negativeInteger
from oldaplib.src.xsd.xsd_nmtoken import Xsd_NMTOKEN
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from oldaplib.src.xsd.xsd_nonpositiveinteger import Xsd_nonPositiveInteger
from oldaplib.src.xsd.xsd_normalizedstring import Xsd_normalizedString
from oldaplib.src.xsd.xsd_positiveinteger import Xsd_positiveInteger
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_short import Xsd_short
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.xsd.xsd_time import Xsd_time
from oldaplib.src.xsd.xsd_token import Xsd_token
from oldaplib.src.xsd.xsd_unsignedbyte import Xsd_unsignedByte
from oldaplib.src.xsd.xsd_unsignedint import Xsd_unsignedInt
from oldaplib.src.xsd.xsd_unsignedlong import Xsd_unsignedLong
from oldaplib.src.xsd.xsd_unsignedshort import Xsd_unsignedShort


def convert2datatype(value: Any, datatype: XsdDatatypes) -> Xsd | LangString:
    match datatype:
        case XsdDatatypes.string:
            return Xsd_string(value)
        case XsdDatatypes.langString:
            return LangString(value)
        case XsdDatatypes.boolean:
            return Xsd_boolean(value)
        case XsdDatatypes.decimal:
            return Xsd_decimal(value)
        case XsdDatatypes.float:
            return Xsd_float(value)
        case XsdDatatypes.double:
            return Xsd_double(value)
        case XsdDatatypes.duration:
            return Xsd_duration(value)
        case XsdDatatypes.dateTime:
            return Xsd_dateTime(value)
        case XsdDatatypes.dateTimeStamp:
            return Xsd_dateTimeStamp(value)
        case XsdDatatypes.time:
            return Xsd_time(value)
        case XsdDatatypes.date:
            return Xsd_date(value)
        case XsdDatatypes.gYearMonth:
            return Xsd_gYearMonth(value)
        case XsdDatatypes.gYear:
            return Xsd_gYear(value)
        case XsdDatatypes.gMonthDay:
            return Xsd_gMonthDay(value)
        case XsdDatatypes.gDay:
            return Xsd_gDay(value)
        case XsdDatatypes.gMonth:
            return Xsd_gMonth(value)
        case XsdDatatypes.hexBinary:
            return Xsd_hexBinary(value)
        case XsdDatatypes.base64Binary:
            return Xsd_base64Binary(value)
        case XsdDatatypes.anyURI:
            return Xsd_anyURI(value)
        case XsdDatatypes.QName:
            return Xsd_QName(value)
        case XsdDatatypes.normalizedString:
            return Xsd_normalizedString(value)
        case XsdDatatypes.token:
            return Xsd_token(value)
        case XsdDatatypes.language:
            return Xsd_language(value)
        case XsdDatatypes.NCName:
            return Xsd_NCName(value)
        case XsdDatatypes.NMTOKEN:
            return Xsd_NMTOKEN(value)
        case XsdDatatypes.ID:
            return Xsd_ID(value)
        case XsdDatatypes.IDREF:
            return Xsd_IDREF(value)
        case XsdDatatypes.integer:
            return Xsd_int(value)
        case XsdDatatypes.nonPositiveInteger:
            return Xsd_nonPositiveInteger(value)
        case XsdDatatypes.negativeInteger:
            return Xsd_negativeInteger(value)
        case XsdDatatypes.long:
            return Xsd_long(value)
        case XsdDatatypes.int:
            return Xsd_int(value)
        case XsdDatatypes.short:
            return Xsd_short(value)
        case XsdDatatypes.byte:
            return Xsd_byte(value)
        case XsdDatatypes.nonNegativeInteger:
            return Xsd_nonNegativeInteger(value)
        case XsdDatatypes.unsignedLong:
            return Xsd_unsignedLong(value)
        case XsdDatatypes.unsignedInt:
            return Xsd_unsignedInt(value)
        case XsdDatatypes.unsignedShort:
            return Xsd_unsignedShort(value)
        case XsdDatatypes.unsignedByte:
            return Xsd_unsignedByte(value)
        case XsdDatatypes.positiveInteger:
            return Xsd_positiveInteger(value)
        case None:
            return Iri(value)
        case _:
            raise OldapErrorValue(f'Invalid datatype "{datatype}" for value "{value}"')
