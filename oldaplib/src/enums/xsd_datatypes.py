"""
# XSD Datatypes, IRI Validator, XSD Validator
"""
import re
from urllib.parse import urlparse

import xmlschema
from enum import Enum, unique
from pystrict import strict
from typing import Any

@unique
class XsdDatatypes(Enum):
    """
    Enumeration of the supported xsd datatypes:

    - `XsdDatatypes.string` = 'xsd:string'
    - `XsdDatatypes.boolean` = 'xsd:boolean'
    - `XsdDatatypes.decimal` = 'xsd:decimal'
    - `XsdDatatypes.float` = 'xsd:float'
    - `XsdDatatypes.double` = 'xsd:double'
    - `XsdDatatypes.duration` = 'xsd:duration'
    - `XsdDatatypes.dateTime` = 'xsd:dateTime'
    - `XsdDatatypes.dateTimeStamp` = 'xsd:dateTimeStamp'
    - `XsdDatatypes.time` = 'xsd:time'
    - `XsdDatatypes.date` = 'xsd:date'
    - `XsdDatatypes.gYearMonth` = 'xsd:gYearMonth'
    - `XsdDatatypes.gYear` = 'xsd:gYear'
    - `XsdDatatypes.gMonthDay` = 'xsd:gMonthDay'
    - `XsdDatatypes.gDay` = 'xsd:gDay'
    - `XsdDatatypes.gMonth` = 'xsd:gMonth'
    - `XsdDatatypes.hexBinary` = 'xsd:hexBinary'
    - `XsdDatatypes.base64Binary` = 'xsd:base64Binary'
    - `XsdDatatypes.anyURI` = 'xsd:anyURI'
    - `XsdDatatypes.QName` = 'xsd:QName'
    - `XsdDatatypes.normalizedString` = 'xsd:normalizedString'
    - `XsdDatatypes.token` = 'xsd:token'
    - `XsdDatatypes.language` = 'xsd:language'
    - `XsdDatatypes.Name` = 'xsd:name'
    - `XsdDatatypes.NCName` = 'xsd:NCName'
    - `XsdDatatypes.NMTOKEN` = 'xsd:NMTOKEN'
    - `XsdDatatypes.ID` = 'xsd:ID'
    - `XsdDatatypes.IDREF` = 'xsd:IDREF'
    - `XsdDatatypes.IDREFS` = 'xsd: IDREFS'
    - `XsdDatatypes.integer` = 'xsd:integer'
    - `XsdDatatypes.nonPositiveInteger` = 'xsd:nonPositiveInteger'
    - `XsdDatatypes.unsignedLong` = 'xsd:unsignedLong'
    - `XsdDatatypes.unsignedInt` = 'xsd:unsignedInt'
    - `XsdDatatypes.unsignedShort` = 'xsd:unsignedShort'
    - `XsdDatatypes.unsignedByte` = 'xsd:unsignedByte'
    - `XsdDatatypes.positiveInteger` = 'xsd:positiveInteger'

    """
    string = 'xsd:string'
    langString = 'rdf:langString'
    boolean = 'xsd:boolean'
    decimal = 'xsd:decimal'
    float = 'xsd:float'
    double = 'xsd:double'
    duration = 'xsd:duration'
    dateTime = 'xsd:dateTime'
    dateTimeStamp = 'xsd:dateTimeStamp'
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
    name_ = 'xsd:name'
    NCName = 'xsd:NCName'
    NMTOKEN = 'xsd:NMTOKEN'
    ID = 'xsd:ID'
    IDREF = 'xsd:IDREF'
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

    def __str__(self):
        return self.value

    @property
    def toRdf(self):
        return self.value


@strict
class IriValidator:
    """
    Calls to validate the syntax of an IRI
    """
    @classmethod
    def validate(cls, val: str) -> bool:
        """
        Class method which validates an IRI. Supported are the protocols "http", "https", and "urn"

        :param val: String to be validated as IRI
        :type val: str
        :return: True or False
        """
        try:
            result = urlparse(val)
            match result.scheme:
                case 'http':
                    return True if result.netloc else False
                case 'https':
                    return True if result.netloc else False
                case 'urn':
                    return True if result.path else False
                case _:
                    return False
            #return all([result.scheme, result.netloc])
        except Exception:
            return False

@strict
class XsdValidator:
    """
    Class to validate generic XSD datatypes
    """
    @classmethod
    def validate(cls,
                 datatype: XsdDatatypes,
                 value: Any) -> bool:
        """
        Validate a value against the given xsd datatype. It uses the xmlschema.XMLSchema11 validator.

        :param datatype: The xsd datatype the value should be validated against
        :type datatype: XsdDatatypes
        :param value: A value to be validated
        :return: True or False
        """
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
    print(XsdValidator.validate(XsdDatatypes.anyURI, "https://waelo.org/data/gaga#uuu"))
    print(XsdValidator.validate(XsdDatatypes.anyURI, "https://waelo.org/data/gaga#"))
    print(XsdValidator.validate(XsdDatatypes.NMTOKEN, "https://orcid.org/0000-0003-1681-4036"))
    print(XsdValidator.validate(XsdDatatypes.anyURI, "urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b"))
    print(XsdValidator.validate(XsdDatatypes.anyURI, "waselias"))
