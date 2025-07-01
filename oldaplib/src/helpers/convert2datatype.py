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


def convert2datatype(value: Any, datatype: XsdDatatypes, validate: bool = False) -> Xsd | LangString:
    match datatype:
        case XsdDatatypes.string:
            return Xsd_string(value, validate=validate)
        case XsdDatatypes.langString:
            return LangString(value, validate=validate)
        case XsdDatatypes.boolean:
            return Xsd_boolean(value, validate=validate)
        case XsdDatatypes.decimal:
            return Xsd_decimal(value, validate=validate)
        case XsdDatatypes.float:
            return Xsd_float(value, validate=validate)
        case XsdDatatypes.double:
            return Xsd_double(value, validate=validate)
        case XsdDatatypes.duration:
            return Xsd_duration(value, validate=validate)
        case XsdDatatypes.dateTime:
            return Xsd_dateTime(value, validate=validate)
        case XsdDatatypes.dateTimeStamp:
            return Xsd_dateTimeStamp(value, validate=validate)
        case XsdDatatypes.time:
            return Xsd_time(value, validate=validate)
        case XsdDatatypes.date:
            return Xsd_date(value, validate=validate)
        case XsdDatatypes.gYearMonth:
            return Xsd_gYearMonth(value, validate=validate)
        case XsdDatatypes.gYear:
            return Xsd_gYear(value, validate=validate)
        case XsdDatatypes.gMonthDay:
            return Xsd_gMonthDay(value, validate=validate)
        case XsdDatatypes.gDay:
            return Xsd_gDay(value, validate=validate)
        case XsdDatatypes.gMonth:
            return Xsd_gMonth(value, validate=validate)
        case XsdDatatypes.hexBinary:
            return Xsd_hexBinary(value, validate=validate)
        case XsdDatatypes.base64Binary:
            return Xsd_base64Binary(value, validate=validate)
        case XsdDatatypes.anyURI:
            return Xsd_anyURI(value, validate=validate)
        case XsdDatatypes.QName:
            return Xsd_QName(value, validate=validate)
        case XsdDatatypes.normalizedString:
            return Xsd_normalizedString(value, validate=validate)
        case XsdDatatypes.token:
            return Xsd_token(value, validate=validate)
        case XsdDatatypes.language:
            return Xsd_language(value, validate=validate)
        case XsdDatatypes.NCName:
            return Xsd_NCName(value, validate=validate)
        case XsdDatatypes.NMTOKEN:
            return Xsd_NMTOKEN(value, validate=validate)
        case XsdDatatypes.ID:
            return Xsd_ID(value, validate=validate)
        case XsdDatatypes.IDREF:
            return Xsd_IDREF(value, validate=validate)
        case XsdDatatypes.integer:
            return Xsd_int(value, validate=validate)
        case XsdDatatypes.nonPositiveInteger:
            return Xsd_nonPositiveInteger(value, validate=validate)
        case XsdDatatypes.negativeInteger:
            return Xsd_negativeInteger(value, validate=validate)
        case XsdDatatypes.long:
            return Xsd_long(value, validate=validate)
        case XsdDatatypes.int:
            return Xsd_int(value, validate=validate)
        case XsdDatatypes.short:
            return Xsd_short(value, validate=validate)
        case XsdDatatypes.byte:
            return Xsd_byte(value, validate=validate)
        case XsdDatatypes.nonNegativeInteger:
            return Xsd_nonNegativeInteger(value, validate=validate)
        case XsdDatatypes.unsignedLong:
            return Xsd_unsignedLong(value, validate=validate)
        case XsdDatatypes.unsignedInt:
            return Xsd_unsignedInt(value, validate=validate)
        case XsdDatatypes.unsignedShort:
            return Xsd_unsignedShort(value, validate=validate)
        case XsdDatatypes.unsignedByte:
            return Xsd_unsignedByte(value, validate=validate)
        case XsdDatatypes.positiveInteger:
            return Xsd_positiveInteger(value, validate=validate)
        case None:
            return Iri(value, validate=validate)
        case _:
            raise OldapErrorValue(f'Invalid datatype "{datatype}" for value "{value}"')
