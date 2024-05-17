from datetime import datetime
from functools import partial
from typing import Type, Any, Self

from pystrict import strict

from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorValue, OldapErrorInconsistency
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_base64binary import Xsd_base64Binary
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_byte import Xsd_byte
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
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

ValueType = Xsd | LangString | list[Xsd]

#@strict
class ResourceInstance(Model):
    _iri: Iri
    _values: dict[str, Xsd | LangString | list[Xsd | LangString]]

    @staticmethod
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
                return Xsd_date(value)
            case XsdDatatypes.dateTimeStamp:
                return Xsd_dateTime(value)
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

    def __init__(self, *,
                 iri: Iri | None = None,
                 **kwargs):
        super().__init__(self.connection)
        self._iri = iri or Iri()
        self._values = {}
        #
        # get and transform values
        #
        for prop_iri, prop in self.properties.items():
            if kwargs.get(prop_iri.fragment):
                value = kwargs[prop_iri.fragment]
                if isinstance(value, (list, tuple, set)):  # we may have multiple values...
                    if prop.datatype == XsdDatatypes.langString:
                        self._values[prop_iri.fragment] = LangString(value)
                    else:
                        self._values[prop_iri.fragment] = [self.convert2datatype(x, prop.datatype) for x in value]
                else:
                    self._values[prop_iri.fragment] = self.convert2datatype(value, prop.datatype)

        for prop_iri in self.properties.keys():
            setattr(ResourceInstance, prop_iri.fragment, property(
                partial(ResourceInstance.__get_value, attr=prop_iri.fragment),
                partial(ResourceInstance.__set_value, attr=prop_iri.fragment),
                partial(ResourceInstance.__del_value, attr=prop_iri.fragment)))

        if not self._values.get('creator'):
            self._values['creator'] = self._con.userIri
        if not self._values.get('created'):
            self._values['created'] = Xsd_dateTime()
        if not self._values.get('contributor'):
            self._values['contributor'] = self._con.userIri
        if not self._values.get('modified'):
            self._values['modified'] = Xsd_dateTime()
        #
        # consistency and conformance tests
        #
        for prop_iri, prop in self.properties.items():
            if prop.get(PropClassAttr.MIN_COUNT):  # testing for MIN_COUNT conformance
                if prop[PropClassAttr.MIN_COUNT] > 0 and not self._values.get(prop_iri.fragment):
                    raise OldapErrorValue(f'Property {prop_iri} with MIN_COUNT={prop[PropClassAttr.MIN_COUNT]} is missing')
                elif isinstance(self._values[prop_iri.fragment], (list, tuple, set)) and len(self._values[prop_iri.fragment]) < 1:
                    raise OldapErrorValue(f'Property {prop_iri} with MIN_COUNT={prop[PropClassAttr.MIN_COUNT]} is missing')
            if prop.get(PropClassAttr.MAX_COUNT):  # testing for MAX_COUNT conformance
                if isinstance(self._values.get(prop_iri.fragment), (list, tuple, set)) and len(self._values[prop_iri.fragment]) > prop[PropClassAttr.MAX_COUNT]:
                    raise OldapErrorValue(f'Property {prop_iri} with MAX_COUNT={prop[PropClassAttr.MIN_COUNT]} has to many values (n={len(self._values[prop_iri.fragment])})')
            else:
                if self._values.get(prop_iri):
                    if isinstance(self._values.get(prop_iri), (list, tuple, set)):
                        for val in self._values.get(prop_iri.fragment):
                            self.validate_value(val, prop)
                    else:
                        self.validate_value(self._values[prop_iri.fragment], prop)

    def validate_value(self, value: ValueType, property: PropertyClass):
        if property.get(PropClassAttr.LANGUAGE_IN):  # testing for LANGUAGE_IN conformance
            if not isinstance(value, LangString):
                raise OldapErrorInconsistency(f'Property {property} with LANGUAGE_IN requires datatype rdf:langstring.')
            for lang, dummy in value.items():
                if not lang in property[PropClassAttr.LANGUAGE_IN]:
                    raise OldapErrorValue(f'Property {property} with LANGUAGE_IN={property[PropClassAttr.LANGUAGE_IN]} has invalid language "{lang.value}"')
        if property.get(PropClassAttr.UNIQUE_LANG):
            return  # TODO: LangString does not yet allow multiple entries of the same language...
        if property.get(PropClassAttr.IN):
            if not value in property[PropClassAttr.IN]:
                raise OldapErrorValue(f'Property {property} with IN={property[PropClassAttr.IN]} has invalid value "{value}"')
        if property.get(PropClassAttr.MIN_LENGTH):
            l = 0
            try:
                l = len(value)
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MIN_LENGTH]} has no length.')
            if l < property[PropClassAttr.MIN_LENGTH]:
                raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MIN_LENGTH]} has length "{len(value)}".')
        if property.get(PropClassAttr.MAX_LENGTH):
            l = 0
            try:
                l = len(value)
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MAX_LENGTH={property[PropClassAttr.MAX_LENGTH]} has no length.')
            if l > property[PropClassAttr.MAX_LENGTH]:
                raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MAX_LENGTH]} has length "{len(value)}".')
        if property.get(PropClassAttr.PATTERN):
            pass  # TODO: regex pattern match!
        if property.get(PropClassAttr.MIN_EXCLUSIVE):
            v: bool | None = None
            try:
                v = value > property[PropClassAttr.MIN_EXCLUSIVE]
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_EXCLUSIVE]} cannot be compared to "{value}".')
            if not v:
                raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_EXCLUSIVE]} has invalid "{value}".')
        if property.get(PropClassAttr.MIN_INCLUSIVE):
            v: bool | None = None
            try:
                v = value >= property[PropClassAttr.MIN_INCLUSIVE]
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_INCLUSIVE]} cannot be compared to "{value}".')
            if not v:
                raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_INCLUSIVE]} has invalid "{value}".')
        if property.get(PropClassAttr.MAX_EXCLUSIVE):
            v: bool | None = None
            try:
                v = value < property[PropClassAttr.MAX_EXCLUSIVE]
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MAX_EXCLUSIVE={property[PropClassAttr.MAX_EXCLUSIVE]} cannot be compared to "{value}".')
            if not v:
                raise OldapErrorInconsistency(f'Property {property} with MAX_EXCLUSIVE={property[PropClassAttr.MAX_EXCLUSIVE]} has invalid "{value}".')
        if property.get(PropClassAttr.MAX_INCLUSIVE):
            v: bool | None = None
            try:
                v = value <= property[PropClassAttr.MAX_INCLUSIVE]
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MAX_INCLUSIVE={property[PropClassAttr.MAX_INCLUSIVE]} cannot be compared to "{value}".')
            if not v:
                raise OldapErrorInconsistency(f'Property {property} with MAX_INCLUSIVE={property[PropClassAttr.MAX_INCLUSIVE]} has invalid "{value}".')
        if property.get(PropClassAttr.LESS_THAN):
            other_value = self._values.get(property[PropClassAttr.LESS_THAN])
            if isinstance(other_value, (list, tuple, list)):
                for oval in other_value:
                    b: bool | None = None
                    try:
                        b = value < oval
                    except TypeError:
                        raise OldapErrorInconsistency(
                            f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} cannot be compared "{value} / {oval}".')
                    if not b:
                        raise OldapErrorInconsistency(
                            f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} has invalid value: "{value}" NOT LESS_THAN "{oval}".')
            else:
                b: bool | None = None
                try:
                    b = value < other_value
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} cannot be compared "{value} / {other_value}".')
                if not b:
                    raise OldapErrorInconsistency(f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} has invalid value: "{value}" NOT LESS_THAN "{other_value}".')
        if property.get(PropClassAttr.LESS_THAN_OR_EQUAL):
            other_value = self._values.get(property[PropClassAttr.LESS_THAN])
            if isinstance(other_value, (list, tuple, list)):
                for oval in other_value:
                    b: bool | None = None
                    try:
                        b = value < oval
                    except TypeError:
                        raise OldapErrorInconsistency(
                            f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} cannot be compared "{value} / {oval}".')
                    if not b:
                        raise OldapErrorInconsistency(
                            f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} has invalid value: "{value}" NOT LESS_THAN "{oval}".')
            else:
                b: bool | None = None
                try:
                    b = value < other_value
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} cannot be compared "{value} / {other_value}".')
                if not b:
                    raise OldapErrorInconsistency(f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} has invalid value: "{value}" NOT LESS_THAN "{other_value}".')

    def __get_value(self: Self, attr: str) -> ValueType | None:
        tmp = self._values.get(attr)
        if not tmp:
            return None
        return tmp

    def __set_value(self: Self, value: ValueType, attr: str) -> None:
        self._values[attr] = value
        #self.__change_setter(attr, value)

    def __del_value(self: Self, attr: str) -> None:
        #self.__changeset[attr] = ProjectAttrChange(self.__attributes[attr], Action.DELETE)
        del self._values[attr]


#@strict
class ResourceInstanceFactory:
    _con: IConnection
    _project: Project
    _datamodel: DataModel

    def __init__(self, con: IConnection, project: Project):
        self._con = con
        self._project = project
        self._datamodel = DataModel.read(con=self._con, project=self._project)

    def createObjectInstance(self, classiri: Iri, name: str) -> Type:  ## ToDo: Get name automatically from IRI
        resclass = self._datamodel.get(classiri)
        if resclass is None:
            raise OldapErrorNotFound(f'Given Resource Class "{classiri}" not found.')
        return type(name, (ResourceInstance,), {
            'connection': self._con,
            'project': self._project,
            'classiri': classiri,
            'properties': resclass.properties})





