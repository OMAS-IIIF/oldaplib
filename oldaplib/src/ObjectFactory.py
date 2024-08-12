import re
from datetime import datetime
from functools import partial
from pprint import pprint
from typing import Type, Any, Self

from pystrict import strict

from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.haspropertyattr import HasPropertyAttr
from oldaplib.src.enums.permissions import AdminPermission
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorValue, OldapErrorInconsistency, \
    OldapErrorNoPermission, OldapError
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.tools import lprint
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
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

    def __init__(self, *,
                 iri: Iri | None = None,
                 **kwargs):
        self._iri = iri or Iri()
        self._values = {}
        self._graph = self.project.projectShortName
        self._superclass_objs = {}

        def set_values(propclass: dict[Iri, HasProperty]):
            for prop_iri, hasprop in propclass.items():
                if kwargs.get(prop_iri.fragment):
                    value = kwargs[prop_iri.fragment]
                    if isinstance(value, (list, tuple, set, LangString)):  # we may have multiple values...
                        if hasprop.prop.datatype == XsdDatatypes.langString:
                            self._values[prop_iri] = LangString(value,
                                                                notifier=self.notifier, notify_data=prop_iri)
                        else:
                            self._values[prop_iri] = ObservableSet({self.convert2datatype(x, hasprop.prop.datatype) for x in value},
                                                                   notifier=self.notifier, notify_data=prop_iri)
                    else:
                        try:
                            self._values[prop_iri] = ObservableSet({self.convert2datatype(value, hasprop.prop.datatype)})
                        except TypeError:
                            self._values[prop_iri] = self.convert2datatype(value, hasprop.prop.datatype)

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
                    if self._values.get(prop_iri):
                        if isinstance(self._values[prop_iri], LangString):
                            self.validate_value(self._values[prop_iri], hasprop.prop)
                        else:
                            if self._values.get(prop_iri):
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


        if self.superclass:
            process_superclasses(self.superclass)

        set_values(self.properties)

        for propname in self._values.keys():
            setattr(ResourceInstance, propname.fragment, property(
                partial(ResourceInstance.__get_value, prefix=propname.prefix, fragment=propname.fragment),
                partial(ResourceInstance.__set_value, prefix=propname.prefix, fragment=propname.fragment),
                partial(ResourceInstance.__del_value, prefix=propname.prefix, fragment=propname.fragment)))

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

    def notifier(self, prop: Iri):
        pass  # TODO: react to change!!!

    def check_for_permissions(self) -> (bool, str):
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
            if len(self.inProject) == 0:
                return False, f'Actor has no ADMIN_CREATE permission for user {self.userId}.'
            allowed: list[Iri] = []
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    return False, f'Actor has no ADMIN_CREATE permission for project {proj}'
                else:
                    if AdminPermission.ADMIN_CREATE not in actor.inProject.get(proj):
                        return False, f'Actor has no ADMIN_CREATE permission for project {proj}'
            return True, "OK"

    def __get_value(self: Self, prefix: str, fragment: str) -> Xsd | ValueType | None:
        attr = Iri(Xsd_QName(prefix, fragment, validate=False), validate=False)
        tmp = self._values.get(attr)
        if not tmp:
            return None
        if isinstance(tmp, ObservableSet):
            if len(tmp) > 1:
                return tmp  # return the observable set
            else:
                return next(iter(tmp))  # return the single element
        else:
            return tmp  # return the single element

    def __set_value(self: Self, value: ValueType, prefix: str, fragment: str) -> None:
        attr = Iri(Xsd_QName(prefix, fragment, validate=False), validate=False)
        self.validate_value(value, attr)
        self._values[attr] = value
        #self.__change_setter(attr, value)

    def __del_value(self: Self, prefix: str, fragment: str) -> None:
        #self.__changeset[attr] = ProjectAttrChange(self.__attributes[attr], Action.DELETE)
        attr = Iri(Xsd_QName(prefix, fragment, validate=False), validate=False)
        del self._values[attr]

    @property
    def iri(self) -> Iri:
        return self._iri

    def create(self, indent: int = 0, indent_inc: int = 4) -> str:
        result, message = self.check_for_permissions()
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
        if not isinstance(project, Project):
            project = Project.read(con, project)
        graph = project.projectShortName
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += f'''
SELECT ?predicate ?value
FROM oldap:onto
FROM shared:onto
FROM test:onto
FROM NAMED oldap:admin
FROM NAMED test:data
WHERE {{
	BIND({iri.toRdf} as ?iri)
    GRAPH test:data {{
        ?iri ?predicate ?value .
        ?iri oldap:grantsPermission ?permset .
    }}
    BIND({con.userIri.toRdf} as ?user)
    GRAPH oldap:admin {{
    	?user oldap:hasPermissions ?permset .
    	?permset oldap:givesPermission ?DataPermission .
    	?DataPermission oldap:permissionValue ?permval .
    }}
    FILTER(?permval >= "2"^^xsd:integer)
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
                        kwargs[r['predicate'].as_qname.fragment].add(r['value'])
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
        return cls(**kwargs)


#@strict
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





