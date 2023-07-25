import re
import xmlschema
from enum import Enum, unique
from pystrict import strict
from typing import Any

@unique
class XsdDatatypes(Enum):
    string = 'xsd:string'
    boolean = 'xsd:boolean'
    decimal = 'xsd:decimal'
    float = 'xsd:float'
    double = 'xsd:double'
    duration = 'xsd:duration'
    dateTime = 'xsd:dateType'
    time = 'xsd:time'
    date = 'xsd:date'
    gYearMonth = 'xsd:gYearMonth'
    gYear = 'xsd:gYear'
    gMonthDay = 'xsd:gMonthDay'
    gDay = 'xsd:gDay'
    gMonth = 'xsd:gMonth'
    hexBinary = 'xsd:hexBinary'
    base64Binary = 'xsd:base64Binary'
    anyURI = 'xsd:anyURI'
    QName = 'xsd:QName'
    normalizedString = 'xsd:normalizedString'
    token = 'xsd:token'
    language = 'xsd:language'
    Name = 'xsd:name'
    NCName = 'xsd:NCName'
    ID = 'xsd:ID'
    IDREF = 'xsd:IDREF'
    IDREFS = 'xsd: IDREFS'
    integer = 'xsd:integer'
    nonPositiveInteger = 'xsd:nonPositiveInteger'
    negativeInteger = 'xsd:negativeInteger'
    long = 'xsd:long'
    int = 'xsd:int'
    short = 'xsd:short'
    byte = 'xsd:byte'
    nonNegativeInteger = 'xsd:nonNegativeInteger'
    unsignedLong = 'xsd:unsignedLong'
    unsignedInt = 'xsd:unsignedInt'
    unsignedShort = 'xsd:unsignedShort'
    unsignedByte = 'xsd:unsignedByte'
    positiveInteger = 'xsd:positiveInteger'

@strict
class IriValidator:
    __iri_regexp = re.compile("^(http)s?://([\\w\\.\\-~]+)?(:\\d{,6})?(/[\\w\\-~]+)*([#/][\\w\\-~]*)?")

    @classmethod
    def validate(cls, val: str) -> bool:
        m = cls.__iri_regexp.match(val)
        return m.span()[1] == len(val) if m else False

@strict
class XsdValidator:

    @classmethod
    def validate(cls,
                 datatype: XsdDatatypes,
                 value: Any) -> bool:
        xsd_string = f"""
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <xsd:element name="tag" type="{datatype.value}"/>
        </xsd:schema>
        """
        namespace = ""
        if datatype == XsdDatatypes.QName:
            parts = str(value).split(':')
            if len(parts) == 2:
                namespace = f"xmlns:{parts[0]}=\"http://dummy.net/dum\""
            else:
                namespace = "xmlns:dummy=\"http://dummy.net/dum\""
        elif datatype == XsdDatatypes.anyURI:
            return IriValidator.validate(value)
        try:
            xsd_validator = xmlschema.XMLSchema11(xsd_string)
            return xsd_validator.is_valid(f"""<?xml version="1.0" encoding="UTF-8"?><tag {namespace}>""" + str(value) + "</tag>")
        except xmlschema.XMLSchemaParseError as e:
            return False


if __name__ == '__main__':
    print(XsdValidator.validate(XsdDatatypes.anyURI, "http://waelo.org/data/gaga#uuu"))