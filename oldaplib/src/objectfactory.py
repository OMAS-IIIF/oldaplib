import re
import threading
from datetime import datetime
from enum import Enum, EnumMeta
from functools import partial
from pprint import pprint
from typing import Type, Any, Self

from oldaplib.src.datamodel import DataModel
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.haspropertyattr import HasPropertyAttr
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.convert2datatype import convert2datatype
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorValue, OldapErrorInconsistency, \
    OldapErrorNoPermission, OldapError, OldapErrorUpdateFailed, OldapErrorInUse
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
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

ValueType = LangString | ObservableSet


#@strict
class ResourceInstance:
    _iri: Iri
    _values: dict[Iri, LangString | ObservableSet]
    _graph: Xsd_NCName
    _changeset: dict[Iri, AttributeChange]

    #@staticmethod
    # def convert2datatype(value: Any, datatype: XsdDatatypes) -> Xsd | LangString:
    #     match datatype:
    #         case XsdDatatypes.string:
    #             return Xsd_string(value)
    #         case XsdDatatypes.langString:
    #             return LangString(value)
    #         case XsdDatatypes.boolean:
    #             return Xsd_boolean(value)
    #         case XsdDatatypes.decimal:
    #             return Xsd_decimal(value)
    #         case XsdDatatypes.float:
    #             return Xsd_float(value)
    #         case XsdDatatypes.double:
    #             return Xsd_double(value)
    #         case XsdDatatypes.duration:
    #             return Xsd_duration(value)
    #         case XsdDatatypes.dateTime:
    #             return Xsd_dateTime(value)
    #         case XsdDatatypes.dateTimeStamp:
    #             return Xsd_dateTimeStamp(value)
    #         case XsdDatatypes.time:
    #             return Xsd_time(value)
    #         case XsdDatatypes.date:
    #             return Xsd_date(value)
    #         case XsdDatatypes.gYearMonth:
    #             return Xsd_gYearMonth(value)
    #         case XsdDatatypes.gYear:
    #             return Xsd_gYear(value)
    #         case XsdDatatypes.gMonthDay:
    #             return Xsd_gMonthDay(value)
    #         case XsdDatatypes.gDay:
    #             return Xsd_gDay(value)
    #         case XsdDatatypes.gMonth:
    #             return Xsd_gMonth(value)
    #         case XsdDatatypes.hexBinary:
    #             return Xsd_hexBinary(value)
    #         case XsdDatatypes.base64Binary:
    #             return Xsd_base64Binary(value)
    #         case XsdDatatypes.anyURI:
    #             return Xsd_anyURI(value)
    #         case XsdDatatypes.QName:
    #             return Xsd_QName(value)
    #         case XsdDatatypes.normalizedString:
    #             return Xsd_normalizedString(value)
    #         case XsdDatatypes.token:
    #             return Xsd_token(value)
    #         case XsdDatatypes.language:
    #             return Xsd_language(value)
    #         case XsdDatatypes.NCName:
    #             return Xsd_NCName(value)
    #         case XsdDatatypes.NMTOKEN:
    #             return Xsd_NMTOKEN(value)
    #         case XsdDatatypes.ID:
    #             return Xsd_ID(value)
    #         case XsdDatatypes.IDREF:
    #             return Xsd_IDREF(value)
    #         case XsdDatatypes.integer:
    #             return Xsd_int(value)
    #         case XsdDatatypes.nonPositiveInteger:
    #             return Xsd_nonPositiveInteger(value)
    #         case XsdDatatypes.negativeInteger:
    #             return Xsd_negativeInteger(value)
    #         case XsdDatatypes.long:
    #             return Xsd_long(value)
    #         case XsdDatatypes.int:
    #             return Xsd_int(value)
    #         case XsdDatatypes.short:
    #             return Xsd_short(value)
    #         case XsdDatatypes.byte:
    #             return Xsd_byte(value)
    #         case XsdDatatypes.nonNegativeInteger:
    #             return Xsd_nonNegativeInteger(value)
    #         case XsdDatatypes.unsignedLong:
    #             return Xsd_unsignedLong(value)
    #         case XsdDatatypes.unsignedInt:
    #             return Xsd_unsignedInt(value)
    #         case XsdDatatypes.unsignedShort:
    #             return Xsd_unsignedShort(value)
    #         case XsdDatatypes.unsignedByte:
    #             return Xsd_unsignedByte(value)
    #         case XsdDatatypes.positiveInteger:
    #             return Xsd_positiveInteger(value)
    #         case None:
    #             return Iri(value)
    #         case _:
    #             raise OldapErrorValue(f'Invalid datatype "{datatype}" for value "{value}"')

    def __init__(self, *,
                 iri: Iri | None = None,
                 **kwargs):
        self._iri = iri or Iri()
        self._values = {}
        self._graph = self.project.projectShortName
        self._superclass_objs = {}
        self._changeset = {}

        def set_values(propclass: dict[Iri, HasProperty]):
            for prop_iri, hasprop in propclass.items():
                if kwargs.get(prop_iri.fragment):
                    value = kwargs[prop_iri.fragment]
                    if isinstance(value, (list, tuple, set, LangString)):  # we may have multiple values...
                        if hasprop.prop.datatype == XsdDatatypes.langString:
                            self._values[prop_iri] = LangString(value,
                                                                notifier=self.notifier, notify_data=prop_iri)
                        else:
                            self._values[prop_iri] = ObservableSet({convert2datatype(x, hasprop.prop.datatype) for x in value},
                                                                   notifier=self.notifier, notify_data=prop_iri)
                    else:
                        try:
                            self._values[prop_iri] = ObservableSet({convert2datatype(value, hasprop.prop.datatype)})
                        except TypeError as err:
                            self._values[prop_iri] = convert2datatype(value, hasprop.prop.datatype)

            for prop_iri, hasprop in propclass.items():
                #
                # Validate
                #
                if hasprop.get(HasPropertyAttr.MIN_COUNT):  # testing for MIN_COUNT conformance
                    if hasprop[HasPropertyAttr.MIN_COUNT] > 0 and not self._values.get(prop_iri):
                        raise OldapErrorValue(f'{self.name}: Property {prop_iri} with MIN_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} is missing')
                    elif isinstance(self._values[prop_iri], ObservableSet) and len(self._values[prop_iri]) < 1:
                        raise OldapErrorValue(f'{self.name}: Property {prop_iri} with MIN_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} is missing')
                if hasprop.get(HasPropertyAttr.MAX_COUNT):  # testing for MAX_COUNT conformance
                    if isinstance(self._values.get(prop_iri), ObservableSet) and len(self._values[prop_iri]) > hasprop[HasPropertyAttr.MAX_COUNT]:
                        raise OldapErrorValue(f'{self.name}: Property {prop_iri} with MAX_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} has to many values (n={len(self._values[prop_iri.fragment])})')
                if self._values.get(prop_iri):
                    if isinstance(self._values[prop_iri], LangString):
                        self.validate_value(self._values[prop_iri], hasprop.prop)
                    else:
                        if isinstance(self._values[prop_iri], ObservableSet):
                            for val in self._values[prop_iri]:
                                self.validate_value(val, hasprop.prop)
                        else:
                            self.validate_value(self._values[prop_iri], hasprop.prop)

        def process_superclasses(superclass: dict[Iri, ResourceClass]):
           for sc_iri, sc in superclass.items():
                if sc.superclass:
                    process_superclasses(sc.superclass)
                if sc.owl_class_iri == Iri("oldap:Thing", validate=False):
                    timestamp = Xsd_dateTimeStamp()
                    if not self._values.get('oldap:createdBy'):
                        self._values[Iri('oldap:createdBy', validate=False)] = ObservableSet({self._con.userIri})
                    if not self._values.get('oldap:creationDate'):
                        self._values[Iri('oldap:creationDate', validate=False)] = ObservableSet({timestamp})
                    if not self._values.get('oldap:lastModifiedBy'):
                        self._values[Iri('oldap:lastModifiedBy', validate=False)] = ObservableSet({self._con.userIri})
                    if not self._values.get('oldap:lastModificationDate'):
                        self._values[Iri('oldap:lastModificationDate', validate=False)] = ObservableSet({timestamp})
                set_values(sc.properties)
                for iri, prop in sc.properties.items():
                    self.properties[iri] = prop


        if self.superclass:
            process_superclasses(self.superclass)

        set_values(self.properties)

        for propname in self.properties.keys():
            setattr(ResourceInstance, propname.fragment, property(
                partial(ResourceInstance.__get_value, prefix=propname.prefix, fragment=propname.fragment),
                partial(ResourceInstance.__set_value, prefix=propname.prefix, fragment=propname.fragment),
                partial(ResourceInstance.__del_value, prefix=propname.prefix, fragment=propname.fragment)))
        self.clear_changeset()

    def validate_value(self, values: ValueType, property: PropertyClass):
        if property.get(PropClassAttr.LANGUAGE_IN):  # testing for LANGUAGE_IN conformance
            if not isinstance(values, LangString):
                raise OldapErrorInconsistency(f'Property {property.property_class_iri} with LANGUAGE_IN requires datatype rdf:langstring, got {type(values).__name__}.')
            for lang, dummy in values.items():
                if not lang in property[PropClassAttr.LANGUAGE_IN]:
                    raise OldapErrorValue(f'Property {property.property_class_iri} with LANGUAGE_IN={property[PropClassAttr.LANGUAGE_IN]} has invalid language "{lang.value}"')
        if property.get(PropClassAttr.UNIQUE_LANG):
            return  # TODO: LangString does not yet allow multiple entries of the same language...
        if property.get(PropClassAttr.IN):
            for val in values:
                if not val in property[PropClassAttr.IN]:
                    raise OldapErrorValue(f'Property {property} with IN={property[PropClassAttr.IN]} has invalid value "{val}"')
        if property.get(PropClassAttr.MIN_LENGTH):
            for val in values:
                l = 0
                try:
                    l = len(val)
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MIN_LENGTH]} has no length.')
                if l < property[PropClassAttr.MIN_LENGTH]:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MIN_LENGTH]} has length "{len(val)}".')
        if property.get(PropClassAttr.MAX_LENGTH):
            for val in values:
                l = 0
                try:
                    l = len(val)
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_LENGTH={property[PropClassAttr.MAX_LENGTH]} has no length.')
                if l > property[PropClassAttr.MAX_LENGTH]:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MAX_LENGTH]} has length "{len(val)}".')
        if property.get(PropClassAttr.PATTERN):
            for val in values:
                if not re.fullmatch(str(property[PropClassAttr.PATTERN]), str(val)):
                    raise OldapErrorInconsistency(f'Property {property} with PATTERN={property[PropClassAttr.PATTERN]} does not conform ({val}).')
        if property.get(PropClassAttr.MIN_EXCLUSIVE):
            for val in values:
                v: bool | None = None
                try:
                    v = val > property[PropClassAttr.MIN_EXCLUSIVE]
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_EXCLUSIVE]} cannot be compared to "{val}".')
                if not v:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_EXCLUSIVE]} has invalid "{val}".')
        if property.get(PropClassAttr.MIN_INCLUSIVE):
            for val in values:
                v: bool | None = None
                try:
                    v = val >= property[PropClassAttr.MIN_INCLUSIVE]
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_INCLUSIVE]} cannot be compared to "{value}".')
                if not v:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_INCLUSIVE]} has invalid "{value}".')
        if property.get(PropClassAttr.MAX_EXCLUSIVE):
            for val in values:
                v: bool | None = None
                try:
                    v = val < property[PropClassAttr.MAX_EXCLUSIVE]
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_EXCLUSIVE={property[PropClassAttr.MAX_EXCLUSIVE]} cannot be compared to "{value}".')
                if not v:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_EXCLUSIVE={property[PropClassAttr.MAX_EXCLUSIVE]} has invalid "{value}".')
        if property.get(PropClassAttr.MAX_INCLUSIVE):
            for val in values:
                v: bool | None = None
                try:
                    v = val <= property[PropClassAttr.MAX_INCLUSIVE]
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_INCLUSIVE={property[PropClassAttr.MAX_INCLUSIVE]} cannot be compared to "{value}".')
                if not v:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_INCLUSIVE={property[PropClassAttr.MAX_INCLUSIVE]} has invalid "{value}".')
        if property.get(PropClassAttr.LESS_THAN):
            other_values = self._values.get(property[PropClassAttr.LESS_THAN])
            if other_values is not None:
                b: bool | None = None
                try:
                    min_other_value = min(other_values)
                    max_value = max(values)
                    b = max_value < min_other_value
                except TypeError:
                    raise OldapErrorInconsistency(
                        f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} cannot be compared "{max_value} / {min_other_value}".')
                if not b:
                    raise OldapErrorInconsistency(
                        f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} has invalid value: "{max_value}" NOT LESS_THAN "{min_other_value}".')
        if property.get(PropClassAttr.LESS_THAN_OR_EQUALS):
            other_values = self._values.get(property[PropClassAttr.LESS_THAN])
            if other_values is not None:
                b: bool | None = None
                try:
                    min_other_value = min(other_values)
                    max_value = max(values)
                    b = max_value <= min_other_value
                except TypeError:
                    raise OldapErrorInconsistency(
                        f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN_OR_EQUALS]} cannot be compared "{max_value} / {min_other_value}".')
                if not b:
                    raise OldapErrorInconsistency(
                        f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN_OR_EQUALS]} has invalid value: "{max_value}" NOT LESS_THAN "{min_other_value}".')

    def notifier(self, prop_iri: Iri):
        hasprop = self.properties[prop_iri]
        self.validate_value(self._values[prop_iri], hasprop)

        if hasprop.get(HasPropertyAttr.MIN_COUNT):  # testing for MIN_COUNT conformance
            n = len(self._values[prop_iri])
            if n < hasprop[HasPropertyAttr.MIN_COUNT]:
                self._values[prop_iri].undo()
                raise OldapErrorValue(
                    f'{self.name}: Property {prop_iri} with MIN_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} has not enough values (n={n}).')

        if hasprop.get(HasPropertyAttr.MAX_COUNT):  # testing for MAX_COUNT conformance
            n = len(self._values[prop_iri])
            if n > hasprop[HasPropertyAttr.MAX_COUNT]:
                self._values[prop_iri].undo()
                raise OldapErrorValue(
                    f'{self.name}: Property {prop_iri} with MAX_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} has to many values (n={n}).')

        self._changeset[prop_iri] = AttributeChange(None, Action.MODIFY)

    def check_for_permissions(self, permission: AdminPermission) -> (bool, str):
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject', validate=False))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK – IS ROOT"
        else:
            perms = actor.inProject.get(self.project.projectIri)
            if permission in perms:
                return True, "OK",
            else:
                return False, f'Actor does not have {permission} in project "{self.project.projectShortName}".'

    def __get_value(self: Self, prefix: str, fragment: str) -> Xsd | ValueType | None:
        attr = Iri(Xsd_QName(prefix, fragment, validate=False), validate=False)
        tmp = self._values.get(attr, None)
        if tmp is not None and str(attr) in {'oldap:createdBy', 'oldap:creationDate', 'oldap:lastModifiedBy', 'oldap:lastModificationDate'}:
            return next(iter(tmp))
        return tmp

    def __set_value(self: Self, value: ValueType | Xsd | None, prefix: str, fragment: str) -> None:
        prop_iri = Iri(Xsd_QName(prefix, fragment, validate=False), validate=False)
        hasprop = self.properties.get(prop_iri)

        #
        # Validate
        #
        if hasprop.get(HasPropertyAttr.MIN_COUNT):  # testing for MIN_COUNT conformance
            if hasprop[HasPropertyAttr.MIN_COUNT] > 0 and not value:
                raise OldapErrorValue(
                    f'{self.name}: Property {prop_iri} with MIN_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} is missing')
            elif isinstance(value, (list, tuple, set, ObservableSet)) and len(value) < hasprop[HasPropertyAttr.MIN_COUNT]:
                raise OldapErrorValue(
                    f'{self.name}: Property {prop_iri} with MIN_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} has not enough values')
        if hasprop.get(HasPropertyAttr.MAX_COUNT):  # testing for MAX_COUNT conformance
            if isinstance(value, (list, tuple, set, ObservableSet)) and len(value) > hasprop[HasPropertyAttr.MAX_COUNT]:
                raise OldapErrorValue(
                    f'{self.name}: Property {prop_iri} with MAX_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} has to many values (n={len(value)})')
        if value:
            if isinstance(value, LangString):
                self.validate_value(value, hasprop.prop)
            else:
                if isinstance(value, (list, tuple, set, ObservableSet)):
                    for val in self._values[prop_iri]:
                        self.validate_value(val, hasprop.prop)
                else:
                    self.validate_value(value, hasprop.prop)

        if not value:
            self._changeset[prop_iri] = AttributeChange(self._values.get(prop_iri), Action.DELETE)
            del self._values[prop_iri]
        elif isinstance(value, (list, tuple, set, LangString)):  # we may have multiple values...
            if self._values.get(prop_iri):
                self._changeset[prop_iri] = AttributeChange(self._values.get(prop_iri), Action.REPLACE)
            else:
                self._changeset[prop_iri] = AttributeChange(None, Action.CREATE)
            if hasprop.prop.datatype == XsdDatatypes.langString:
                self._values[prop_iri] = LangString(value, notifier=self.notifier, notify_data=prop_iri)
            else:
                self._values[prop_iri] = ObservableSet({
                    convert2datatype(x, hasprop.prop.datatype) for x in value
                }, notifier=self.notifier, notify_data=prop_iri)
        else:
            if self._values.get(prop_iri):
                self._changeset[prop_iri] = AttributeChange(self._values.get(prop_iri), Action.REPLACE)
            else:
                self._changeset[prop_iri] = AttributeChange(None, Action.CREATE)
            try:
                self._values[prop_iri] = ObservableSet({convert2datatype(value, hasprop.prop.datatype)})
            except TypeError:
                self._values[prop_iri] = convert2datatype(value, hasprop.prop.datatype)

    def __del_value(self: Self, prefix: str, fragment: str) -> None:
        prop_iri = Iri(Xsd_QName(prefix, fragment, validate=False), validate=False)
        hasprop = self.properties.get(prop_iri)

        if hasprop.get(HasPropertyAttr.MIN_COUNT):  # testing for MIN_COUNT conformance
            if hasprop[HasPropertyAttr.MIN_COUNT] > 0:
                raise OldapErrorValue(f'{self.name}: Property {prop_iri} with MIN_COUNT={hasprop[HasPropertyAttr.MIN_COUNT]} cannot be deleted.')

        self._changeset[prop_iri] = AttributeChange(self._values.get(prop_iri), Action.DELETE)
        attr = Iri(Xsd_QName(prefix, fragment, validate=False), validate=False)
        del self._values[attr]

    @property
    def iri(self) -> Iri:
        return self._iri

    @property
    def changeset(self) -> dict[Iri, AttributeChange]:
        return self._changeset

    def clear_changeset(self) -> None:
        for item in self._values:
            if hasattr(self._values[item], 'clear_changeset'):
                self._values[item].clear_changeset()
        self._changeset = {}


    def get_data_permission(self, context: Context, permission: DataPermission) -> bool:
        permission_query = context.sparql_context
        permission_query += f'''
        SELECT (COUNT(?permset) as ?numOfPermsets)
        FROM oldap:onto
        FROM shared:onto
        FROM {self._graph}:onto
        FROM NAMED oldap:admin
        FROM NAMED {self._graph}:data
        WHERE {{
            BIND({self._iri.toRdf} as ?iri)
            GRAPH {self._graph}:data {{
                ?iri oldap:grantsPermission ?permset .
            }}
            BIND({self._con.userIri.toRdf} as ?user)
            GRAPH oldap:admin {{
                ?user oldap:hasPermissions ?permset .
                ?permset oldap:givesPermission ?DataPermission .
                ?DataPermission oldap:permissionValue ?permval .
            }}
            FILTER(?permval >= {permission.numeric.toRdf})
        }}'''
        if self._con.in_transaction():
            jsonobj = self._con.transaction_query(permission_query)
        else:
            jsonobj = self._con.query(permission_query)
        res = QueryProcessor(context, jsonobj)
        return res[0]['numOfPermsets'] > 0

    def create(self, indent: int = 0, indent_inc: int = 4) -> str:
        result, message = self.check_for_permissions(AdminPermission.ADMIN_CREATE)
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTimeStamp()
        if self.name == "Thing":
            self._values[Iri('oldap:createdBy', validate=False)] = ObservableSet({self._con.userIri})
            self._values[Iri('oldap:creationDate', validate=False)] = ObservableSet({timestamp})
            self._values[Iri('oldap:lastModifiedBy', validate=False)] = ObservableSet({self._con.userIri})
            self._values[Iri('oldap:lastModificationDate', validate=False)] = ObservableSet({timestamp})

        indent: int = 0
        indent_inc: int = 4

        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:data {{'

        sparql += f'\n{blank:{(indent + 2) * indent_inc}}{self._iri.toRdf} a {self._graph}:{self.name}'

        for prop_iri, values in self._values.items():
            if self.properties.get(prop_iri) and self.properties[prop_iri].prop.datatype == XsdDatatypes.QName:
                qnames = {f'"{x}"^^xsd:QName' for x in values}
                qnames_rdf = ', '.join(qnames)
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{prop_iri.toRdf} {qnames_rdf}'
            else:
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{prop_iri.toRdf} {values.toRdf}'
        sparql += f' .\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        self._con.transaction_start()
        try:
            self._con.transaction_update(sparql)
        except OldapError as e:
            self._con.transaction_abort()
            raise
        self._con.transaction_commit()


    @classmethod
    def read(cls,
             con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             iri: Iri) -> Self:
        # if not isinstance(project, Project):
        #     project = Project.read(con, project)
        graph = cls.project.projectShortName
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f'''
SELECT ?predicate ?value
FROM oldap:onto
FROM shared:onto
FROM {graph}:onto
FROM NAMED oldap:admin
FROM NAMED {graph}:data
WHERE {{
	BIND({iri.toRdf} as ?iri)
    GRAPH {graph}:data {{
        ?iri ?predicate ?value .
        ?iri oldap:grantsPermission ?permset .
    }}
    BIND({con.userIri.toRdf} as ?user)
    GRAPH oldap:admin {{
    	?user oldap:hasPermissions ?permset .
    	?permset oldap:givesPermission ?DataPermission .
    	?DataPermission oldap:permissionValue ?permval .
    }}
    FILTER(?permval >= {DataPermission.DATA_VIEW.numeric.toRdf})
}}'''
        jsonres = con.query(sparql)
        res = QueryProcessor(context, jsonres)
        objtype = None
        kwargs: dict[str, Any] = {}
        for r in res:
            if r['predicate'] == 'rdf:type':
                if r['value'].is_qname:
                    objtype = r['value'].as_qname.fragment
                else:
                    raise OldapErrorInconsistency(f"Expected QName as value, got {r['value']}")
            else:
                if r['predicate'].is_qname:
                    if kwargs.get(r['predicate'].as_qname.fragment):
                        if isinstance(kwargs[r['predicate'].as_qname.fragment], set):
                            kwargs[r['predicate'].as_qname.fragment].add(r['value'])
                        else:
                            kwargs[r['predicate'].as_qname.fragment] = r['value']
                    else:
                        try:
                            kwargs[r['predicate'].as_qname.fragment] = {r['value']}
                        except TypeError:
                            kwargs[r['predicate'].as_qname.fragment] = r['value']
                else:
                    raise OldapErrorInconsistency(f"Expected QName as predicate, got {r['predicate']}")
        if objtype is None:
            raise OldapErrorNotFound(f'Resource with iri <{iri}> not found.')
        if cls.__name__ != objtype:
            raise OldapErrorInconsistency(f'Expected class {cls.__name__}, got {objtype} instead.')
        return cls(iri=iri, **kwargs)

    def update(self, indent: int = 0, indent_inc: int = 4) -> None:
        admin_resources, message = self.check_for_permissions(AdminPermission.ADMIN_RESOURCES)

        context = Context(name=self._con.context_name)
        blank = ''
        timestamp = Xsd_dateTimeStamp()

        sparql_list = []
        required_permission = DataPermission.DATA_EXTEND
        for field, change in self._changeset.items():
            if field == 'oldap:grantsPermission':
                required_permission = DataPermission.DATA_PERMISSIONS
            if change.action == Action.MODIFY:
                continue  # will be processed below!
            if change.action != Action.CREATE:
                if required_permission < DataPermission.DATA_UPDATE:
                    required_permission = DataPermission.DATA_UPDATE
            sparql = f'# Processing field "{field}"\n'
            sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:data\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                if isinstance(change.old_value, (ObservableSet, LangString)):
                    for val in change.old_value:
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?res_iri {field.toRdf} {val.toRdf} .\n'
                else:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?res_iri {field.toRdf} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                if isinstance(change.old_value, (ObservableSet, LangString)):
                    for val in self._values[field]:
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?res_iri {field.toRdf} {val.toRdf} .\n'
                else:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?res_iri {field.toRdf} {self._values[field].toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._iri.toRdf} as ?res_iri)\n'
            if change.action != Action.CREATE:
                if isinstance(change.old_value, (ObservableSet, LangString)):
                    for val in change.old_value:
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?res_iri {field.toRdf} {val.toRdf} .\n'
                else:
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?res_iri {field.toRdf} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)

        for field, change in self._changeset.items():
            if change.action != Action.MODIFY:
                continue  # has been processed above
            if self.properties[field].prop.datatype == XsdDatatypes.langString:
                sparqls = self._values[field].update(graph=f'{self._graph}:data',
                                                     subject=self._iri,
                                                     field=field)
                for lang, lchange in self._values[field].changeset.items():
                    if lchange.action != Action.CREATE:
                        if required_permission < DataPermission.DATA_UPDATE:
                            required_permission = DataPermission.DATA_UPDATE
                sparql_list.extend(sparqls)
            else:
                #
                # first we rectify the datatype of all "new" values added to the set
                #
                newset = {convert2datatype(x, self.properties[field].prop.datatype) for x in self._values[field]}
                self._values[field] = ObservableSet(newset, old_value=self._values[field].old_value, notifier=self.notifier, notify_data=field)
                sparqls = self._values[field].update_sparql(graph=f'{self._graph}:data',
                                                            subject=self._iri,
                                                            field=field)
                sparql_list.extend(sparqls)

        sparql = context.sparql_context
        sparql += f'# Updating resource "{self._iri}"\n'
        sparql += " ;\n".join(sparql_list)

        modtime_update = context.sparql_context
        modtime_update += f'''
WITH {self._graph}:data
DELETE {{
    ?res oldap:lastModificationDate {self.lastModificationDate.toRdf} .
    ?res oldap:lastModifiedBy ?contributor .
}}
INSERT {{
    ?res oldap:lastModificationDate {timestamp.toRdf} .
    ?res oldap:lastModifiedBy {self._con.userIri.toRdf} .
}}
WHERE {{
    BIND({self._iri.toRdf} as ?res)
    ?res oldap:lastModificationDate {self.lastModificationDate.toRdf} .
    ?res oldap:lastModifiedBy ?contributor .
}}
'''

        context = Context(name=self._con.context_name)
        modtime_get = context.sparql_context
        modtime_get += f"""
        SELECT ?modified
        FROM {self._graph}:data
        WHERE {{
            {self._iri.toRdf} oldap:lastModificationDate ?modified
        }}
        """

        self._con.transaction_start()
        #
        # Test permission for Action.REPLACE
        #
        if not admin_resources:
            if not self.get_data_permission(context, required_permission):
                self._con.transaction_abort()
                raise OldapErrorNoPermission(f'No permission to update resource "{self._iri}"')
        try:
            self._con.transaction_update(sparql)
            self._con.transaction_update(modtime_update)
            jsonobj = self._con.transaction_query(modtime_get)
            res = QueryProcessor(context, jsonobj)
            modtime = res[0]['modified']
            if timestamp != modtime:
                raise OldapErrorUpdateFailed(f"Update failed! Timestamp does not match (modtime={modtime}, timestamp={timestamp}).")
        except OldapError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.clear_changeset()

    def delete(self) -> None:
        admin_resources, message = self.check_for_permissions(AdminPermission.ADMIN_RESOURCES)

        context = Context(name=self._con.context_name)
        inuse = context.sparql_context
        inuse = f'''
        SELECT (COUNT(?res) as ?nres)
        WHERE {{
            ?res ?prop {self._iri.toRdf} .
        }}
        '''

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        DELETE WHERE {{
            GRAPH {self._graph}:data {{
                {self._iri.toRdf} ?prop ?val .
            }}
        }} 
        """

        self._con.transaction_start()
        if not admin_resources:
            if not self.get_data_permission(context, DataPermission.DATA_DELETE):
                self._con.transaction_abort()
                raise OldapErrorNoPermission(f'No permission to update resource "{self._iri}"')
        try:
            jsonobj = self._con.transaction_query(inuse)
            res = QueryProcessor(context, jsonobj)
            if res[0]['nres'] > 0:
                raise OldapErrorInUse(f'Resource "{self._iri}" is in use and cannot be deleted.')
        except OldapError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_update(sparql)
        except OldapError:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise


class ResourceInstanceFactory:
    _con: IConnection
    _project: Project
    _datamodel: DataModel

    def __init__(self,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str):
        self._con = con
        if isinstance(project, Project):
            self._project = project
        else:
            self._project = Project.read(self._con, project)

        self._datamodel = DataModel.read(con=self._con, project=self._project)

        #self._oldap_project = Project.read(self._con, "oldap")
        #self._oldap_datamodel = DataModel.read(con=self._con, project=self._oldap_project)

    def createObjectInstance(self, name: Xsd_NCName | str) -> Type:  ## ToDo: Get name automatically from IRI
        classiri = Xsd_QName(self._project.projectShortName, name)
        resclass = self._datamodel.get(classiri)
        if not isinstance(name, Xsd_NCName):
            name = Xsd_NCName(name)
        if resclass is None:
            raise OldapErrorNotFound(f'Given Resource Class "{classiri}" not found.')
        return type(str(name), (ResourceInstance,), {
            '_con': self._con,
            'project': self._project,
            'name': name,
            'factory': self,
            'properties': resclass.properties,
            'superclass': resclass.superclass})





