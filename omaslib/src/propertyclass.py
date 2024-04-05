"""
:Author: Lukas Rosenthaler <lukas.rosenthaler@unibas.ch>
:Copyright: © Lukas Rosenthaler (2023, 2024)
"""
from dataclasses import dataclass
from enum import Enum, unique
from functools import partial
from typing import Optional, Dict, Callable, List, Self

from pystrict import strict

from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.dtypes.string_literal import StringLiteral
from omaslib.src.enums.language import Language
from omaslib.src.helpers.Notify import Notify
from omaslib.src.helpers.context import Context
from omaslib.src.dtypes.bnode import BNode
from omaslib.src.enums.action import Action
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_decimal import Xsd_decimal
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNotFound, OmasErrorAlreadyExists, OmasErrorUpdateFailed, OmasErrorValue
from omaslib.src.enums.propertyclassattr import PropClassAttr
from omaslib.src.helpers.query_processor import RowType, QueryProcessor
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.tools import RdfModifyItem, RdfModifyProp, str2qname_anyiri, lprint
from omaslib.src.enums.xsd_datatypes import XsdDatatypes
from omaslib.src.iconnection import IConnection
from omaslib.src.model import Model
from omaslib.src.propertyrestrictions import PropertyRestrictions
from omaslib.src.enums.propertyrestrictiontype import PropertyRestrictionType
from omaslib.src.xsd.xsd_string import Xsd_string


@unique
class OwlPropertyType(Enum):
    OwlDataProperty = 'owl:DatatypeProperty'
    OwlObjectProperty = 'owl:ObjectProperty'

    @property
    def toRdf(self):
        return self.value


PropTypes = Iri | OwlPropertyType | XsdDatatypes | PropertyRestrictions | LangString | Xsd_decimal | None
PropClassAttrContainer = Dict[PropClassAttr, PropTypes]
Attributes = Dict[Xsd_QName, LangString | RdfSet | LanguageIn | List[Xsd]]


@dataclass
class PropClassAttrChange:
    old_value: PropTypes
    action: Action
    test_in_use: bool


@strict
class PropertyClass(Model, Notify):
    """
    This class implements a property as used by OMASlib. There are 2 types of properties:
    - _External properties_: External properties are defined outside a specific resource class
      and can be (re-)used by several resources. In SHACL, they are defined as "sh:PropertyShape"
      instance.
    - _Internal or exclusive properties_: These Properties ate defined as blank node within the
      definition of a resource class. A "sh:property" predicate points to the blank node that
      defines the property. These properties cannot be re-used!

    *NOTE*: External properties have to be defined and created before being referenced as
    property within a resource definition. In order to reference an external property, the
    QName has to be used!

    """
    _graph: Xsd_NCName
    _property_class_iri: Iri | None
    _internal: Iri | None
    _force_external: bool
    _attributes: PropClassAttrContainer
    _changeset: Dict[PropClassAttr, PropClassAttrChange]
    _test_in_use: bool
    _notifier: Callable[[type], None] | None
    #
    # The following attributes of this class cannot be set explicitely by the used
    # They are automatically managed by the OMAS system
    #
    __creator: Iri | None
    __created: Xsd_dateTime | None
    __contributor: Iri | None
    __modified: Xsd_dateTime | None
    __version: SemanticVersion
    __from_triplestore: bool

    __datatypes: Dict[PropClassAttr, PropTypes] = {
        PropClassAttr.SUBPROPERTY_OF: Iri,
        PropClassAttr.PROPERTY_TYPE: OwlPropertyType,
        PropClassAttr.TO_NODE_IRI: Iri,
        PropClassAttr.DATATYPE: XsdDatatypes,
        PropClassAttr.RESTRICTIONS: PropertyRestrictions,
        PropClassAttr.NAME: LangString,
        PropClassAttr.DESCRIPTION: LangString,
        PropClassAttr.ORDER: Xsd_decimal
    }

    def __init__(self, *,
                 con: IConnection,
                 graph: Xsd_NCName | str,
                 property_class_iri: Iri | str | None = None,
                 subPropertyOf: Iri | str | None = None,
                 toNodeIri: Iri | str | None = None,
                 datatype: XsdDatatypes | None = None,
                 restrictions: PropertyRestrictions | None = None,
                 name: LangString | str | None = None,
                 description: LangString | str | None = None,
                 order: Xsd_decimal | None = None,
                 notifier: Callable[[PropClassAttr], None] | None = None,
                 notify_data: PropClassAttr | None = None):
        """
        TODO: 1) check if a valid datatype is defined!
        Constructor for a PropertyClass instance. It represents all the information about a PropertyClass
        necessary to perform the CRUD (Create, Read, Update and Delete) operations in both the SHACL and
        OWL representations.

        :param con: A valid IConnection instance
        :param graph: The name of the named graph the information is stored in
        :param property_class_iri: The QName of the property (as used in OWL)
        :param attrs: A PropertyClassAttributesContainer containing all the attributes
        :param notifier: The notifier which is called when an complex atribute such as a LangString or
                         a restriction has changed
        :param notify_data: The data that should be given to the notifier
        """
        Model.__init__(self, con)
        Notify.__init__(self, notifier, notify_data)
        self._graph = Xsd_NCName(graph)
        self._property_class_iri = Iri(property_class_iri)
        self._attributes: PropClassAttrContainer = {}
        if subPropertyOf is not None:
            self._attributes[PropClassAttr.SUBPROPERTY_OF] = Iri(subPropertyOf)
        if toNodeIri is not None:
            self._attributes[PropClassAttr.TO_NODE_IRI] = Iri(toNodeIri)
        if datatype is not None:
            if isinstance(datatype, XsdDatatypes):
                self._attributes[PropClassAttr.DATATYPE] = datatype
            else:
                try:
                    self._attributes[PropClassAttr.DATATYPE] = XsdDatatypes(datatype)
                except ValueError as err:
                    raise OmasErrorValue(str(err))
        if restrictions is not None:
            if not isinstance(restrictions, PropertyRestrictions):
                raise OmasErrorValue(f'restrictions must be a "PropertyRestrictions" object, is "{type(restrictions).__name__}"')
            self._attributes[PropClassAttr.RESTRICTIONS] = restrictions
            self._attributes[PropClassAttr.RESTRICTIONS].set_notifier(self.notifier, PropClassAttr.RESTRICTIONS)
        if name is not None:
            self._attributes[PropClassAttr.NAME] = name if isinstance(name, LangString) else LangString(name)
            self._attributes[PropClassAttr.NAME].set_notifier(self.notifier, PropClassAttr.NAME)
        if description is not None:
            self._attributes[PropClassAttr.DESCRIPTION] = description if isinstance(description, LangString) else LangString(description)
            self._attributes[PropClassAttr.DESCRIPTION].set_notifier(self.notifier, PropClassAttr.DESCRIPTION)
        if order is not None:
            self._attributes[PropClassAttr.ORDER] = order if isinstance(order, Xsd_decimal) else Xsd_decimal(order)

        # setting property type for OWL which distinguished between Data- and Object-properties
        if self._attributes.get(PropClassAttr.TO_NODE_IRI) is not None:
            self._attributes[PropClassAttr.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                raise OmasError(f'Datatype not possible for OwlObjectProperty')
        else:
            self._attributes[PropClassAttr.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty

        for attr in PropClassAttr:
            prefix, name = attr.value.split(':')
            if name == 'type':
                name = 'propertyType'
            elif name == 'class':
                name = 'toNodeIri'
            setattr(PropertyClass, name, property(
                partial(PropertyClass.__get_value, attr=attr),
                partial(PropertyClass.__set_value, attr=attr),
                partial(PropertyClass.__del_value, attr=attr)))

        self._changeset = {}  # initialize changeset to empty set
        self._test_in_use = False
        self._internal = None
        self._force_external = False
        self.__creator = None
        self.__created = None
        self.__contributor = None
        self.__modified = None
        self.__version = SemanticVersion()
        self.__from_triplestore = False

    def __get_value(self: Self, attr: PropClassAttr) -> PropTypes | None:
        return self._attributes.get(attr)

    def __set_value(self: Self, value: PropTypes, attr: PropClassAttr) -> None:
        self.__change_setter(attr, value)

    def __del_value(self: Self, attr: PropClassAttr) -> None:
        if self._attributes.get(attr) is not None:
            self._changeset[attr] = PropClassAttrChange(self._attributes[attr], Action.DELETE, True)
            del self._attributes[attr]
            self.notify()

    def __change_setter(self: Self, attr: PropClassAttr, value: PropTypes) -> None:
        if not isinstance(attr, PropClassAttr):
            raise OmasError(f'Unsupported prop {attr}')
        if not isinstance(value, PropertyClass.__datatypes[attr]):
            raise OmasError(f'Datatype of {attr.value} is not in {PropertyClass.__datatypes[attr]}')
        if self._attributes.get(attr) == value:
            return
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, attr)

        if attr == PropClassAttr.TO_NODE_IRI:
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                self._changeset[PropClassAttr.DATATYPE] = PropClassAttrChange(self._attributes[PropClassAttr.DATATYPE], Action.DELETE, True)
                del self._attributes[PropClassAttr.DATATYPE]
            if self._attributes.get(PropClassAttr.TO_NODE_IRI) is not None:
                self._changeset[PropClassAttr.TO_NODE_IRI] = PropClassAttrChange(self._attributes[PropClassAttr.TO_NODE_IRI], Action.REPLACE, True)
            else:
                self._changeset[PropClassAttr.TO_NODE_IRI] = PropClassAttrChange(None, Action.CREATE, True)
            self._attributes[PropClassAttr.TO_NODE_IRI] = value
        elif attr == PropClassAttr.DATATYPE:
            if self._attributes.get(PropClassAttr.TO_NODE_IRI) is not None:
                self._changeset[PropClassAttr.TO_NODE_IRI] = PropClassAttrChange(self._attributes[PropClassAttr.TO_NODE_IRI], Action.DELETE, True)
                del self._attributes[PropClassAttr.TO_NODE_IRI]
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                self._changeset[PropClassAttr.DATATYPE] = PropClassAttrChange(self._attributes[PropClassAttr.DATATYPE], Action.REPLACE, True)
            else:
                self._changeset[PropClassAttr.DATATYPE] = PropClassAttrChange(None, Action.CREATE, True)
            self._attributes[PropClassAttr.DATATYPE] = value
        else:
            if self._changeset.get(attr) is None:
                if self._attributes.get(attr) is not None:
                    self._changeset[attr] = PropClassAttrChange(self._attributes[attr], Action.REPLACE, True)
                else:
                    self._changeset[attr] = PropClassAttrChange(None, Action.CREATE, True)
            self._attributes[attr] = value
        self.notify()

    def __len__(self) -> int:
        return len(self._attributes)

    def __str__(self) -> str:
        propstr = f'Property: {str(self._property_class_iri)};'
        for attr, value in self._attributes.items():
            propstr += f' {attr.value}: {value};'
        return propstr

    def __getitem__(self, attr: PropClassAttr) -> PropTypes:
        return self._attributes[attr]

    def get(self, attr: PropClassAttr) -> PropTypes | None:
        return self._attributes.get(attr)

    def __setitem__(self, attr: PropClassAttr, value: PropTypes) -> None:
        self.__change_setter(attr, value)

    def __delitem__(self, attr: PropClassAttr) -> None:
        if self._attributes.get(attr) is not None:
            self._changeset[attr] = PropClassAttrChange(self._attributes[attr], Action.DELETE, True)
            del self._attributes[attr]
            self.notify()

    @property
    def property_class_iri(self) -> Iri:
        return self._property_class_iri

    @property
    def version(self) -> SemanticVersion:
        return self.__version

    @property
    def creator(self) -> Iri | None:
        return self.__creator

    @property
    def created(self) -> Xsd_dateTime | None:
        return self.__created

    @property
    def contributor(self) -> Iri | None:
        return self.__contributor

    @property
    def modified(self) -> Xsd_dateTime | None:
        return self.__modified

    @property
    def changeset(self) -> Dict[PropClassAttr, PropClassAttrChange]:
        return self._changeset

    @property
    def internal(self) -> Iri:
        return self._internal

    def force_external(self):
        self._force_external = True

    def changeset_clear(self):
        self._changeset = {}

    @property
    def from_triplestore(self) -> bool:
        return self.__from_triplestore

    def undo(self, attr: Optional[PropClassAttr | PropertyRestrictionType] = None) -> None:
        if attr is None:
            for p, change in self._changeset.items():
                if change.action == Action.MODIFY:
                    self._attributes[p].undo()
                    if len(self._attributes[p]) == 0:
                        del self._attributes[p]
                else:
                    if change.action == Action.CREATE:
                        del self._attributes[p]
                    else:
                        self._attributes[p] = change.old_value
            self._changeset = {}
        else:
            if type(attr) is PropClassAttr:
                if self._changeset.get(attr) is not None:  # this prop really changed...
                    if self._changeset[attr].action == Action.MODIFY:
                        self._attributes[attr].undo()
                        if len(self._attributes[attr]) == 0:
                            del self._attributes[attr]
                    elif self._changeset[attr].action == Action.CREATE:
                        del self._attributes[attr]
                    else:
                        self._attributes[attr] = self._changeset[attr].old_value
                    del self._changeset[attr]
            elif type(attr) is PropertyRestrictionType:
                if self._attributes.get(PropClassAttr.RESTRICTIONS) is None:
                    return
                self._attributes[PropClassAttr.RESTRICTIONS].undo(attr)
                if len(self._attributes[PropClassAttr.RESTRICTIONS].changeset) == 0:
                    if self._changeset.get(PropClassAttr.RESTRICTIONS) is not None:
                        del self._changeset[PropClassAttr.RESTRICTIONS]
                if self._attributes.get(PropClassAttr.RESTRICTIONS) is not None:
                    if len(self._attributes[PropClassAttr.RESTRICTIONS]) == 0:
                        del self._attributes[PropClassAttr.RESTRICTIONS]

    def __changeset_clear(self) -> None:
        for attr, change in self._changeset.items():
            if change.action == Action.MODIFY:
                self._attributes[attr].changeset_clear()
        self._changeset = {}

    def notifier(self, attr: PropClassAttr) -> None:
        self._changeset[attr] = PropClassAttrChange(None, Action.MODIFY, True)
        self.notify()

    @property
    def in_use(self):
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?rinstances) as ?nrinstances)
        WHERE {{
            ?rinstances {self._property_class_iri.toRdf} ?value
        }} LIMIT 2
        """
        jsonres = self._con.query(query)
        res = QueryProcessor(jsonres)
        if len(res) != 1:
            raise OmasError('Internal Error in "propertyClass.in_use"')
        for r in res:
            if r['nresinstances'] > 0:
                return True
            else:
                return False

    @staticmethod
    def process_triple(r: RowType, attributes: Attributes) -> None:
        attriri = r['attriri']
        if r['attriri'].fragment == 'languageIn':
            if attributes.get(attriri) is None:
                attributes[attriri] = LanguageIn()
            attributes[attriri].add(r['oo'])
        elif r['attriri'].fragment == 'in':
            if attributes.get(attriri) is None:
                attributes[attriri] = RdfSet()
            attributes[attriri].add(r['oo'])
        else:
            if attributes.get(attriri) is None:
                attributes[attriri] = []
            attributes[attriri].append(r['value'])

        # attriri = r['attriri']
        # if isinstance(r['value'], Xsd_QName):
        #     if attributes.get(attriri) is None:
        #         attributes[attriri] = []
        #     attributes[attriri].append(r['value'])
        # elif isinstance(r['value'], StringLiteral):
        #     if attributes.get(attriri) is None:
        #         attributes[attriri] = []
        #     attributes[attriri].append(str(r['value']))
        # elif isinstance(r['value'], BNode):
        #     pass
        # else:
        #     if attributes.get(attriri) is None:
        #         attributes[attriri] = []
        #     attributes[attriri].append(r['value'])
        # if r['attriri'].fragment == 'languageIn':
        #     #print("\n===>", r['attriri'], r['oo'])
        #     if not attributes.get(attriri):
        #         attributes[attriri] = set()
        #     attributes[attriri].add(Language[str(r['oo']).upper()])
        # if r['attriri'].fragment == 'in':
        #     if not attributes.get(attriri):
        #         attributes[attriri] = set()
        #     attributes[attriri].add(r['oo'])

    @staticmethod
    def __query_shacl(con: IConnection, graph: Xsd_NCName, property_class_iri: Iri) -> Attributes:
        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?attriri ?value ?oo
        FROM {graph}:shacl
        WHERE {{
            BIND({property_class_iri}Shape AS ?shape)
            ?shape ?attriri ?value .
            OPTIONAL {{
                ?value rdf:rest*/rdf:first ?oo
            }}
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OmasErrorNotFound(f'Property "{property_class_iri}" not found.')
        attributes: Attributes = {}
        for r in res:
            PropertyClass.process_triple(r, attributes)
        return attributes

    def parse_shacl(self, attributes: Attributes) -> None:
        """
        Read the SHACL of a non-exclusive (shared) property (that is a sh:PropertyNode definition)
        :return:
        """
        self._attributes[PropClassAttr.RESTRICTIONS] = PropertyRestrictions()
        #
        # Create a set of all PropertyClassProp-strings, e.g. {"sh:path", "sh:datatype" etc.}
        #
        propkeys = {Iri(x.value) for x in PropClassAttr}
        for key, val in attributes.items():
            if key == 'rdf:type':
                if val[0] != 'sh:PropertyShape':
                    raise OmasError(f'Inconsistency, expected "sh:PropertyType", got "{val[0]}".')
                continue
            elif key == 'sh:path':
                if isinstance(val, list) and len(val) == 1 and isinstance(val[0], Iri):
                    self._property_class_iri = val[0]
                else:
                    raise OmasError(f'Inconsistency in SHACL "sh:path"')
            elif key == 'dcterms:hasVersion':
                if isinstance(val, list) and len(val) == 1 and isinstance(val[0], Xsd_string):
                    self.__version = SemanticVersion.fromString(str(val[0]))
                else:
                    raise OmasError(f'Inconsistency in SHACL "dcterms:hasVersion"')
            elif key == 'dcterms:creator':
                if isinstance(val, list) and isinstance(val[0], Iri):
                    self.__creator = val[0]
                else:
                    raise OmasError(f'Inconsistency in SHACL "dcterms:creator"')
            elif key == 'dcterms:created':
                if isinstance(val, list) and len(val) == 1 and isinstance(val[0], Xsd_dateTime):
                    self.__created = val[0]
                else:
                    raise OmasError(f'Inconsistency in SHACL "dcterms:created"')
            elif key == 'dcterms:contributor':
                if isinstance(val, list) and isinstance(val[0], Iri):
                    self.__contributor = val[0]
                else:
                    raise OmasError(f'Inconsistency in SHACL "dcterms:contributor"')
            elif key == 'dcterms:modified':
                if isinstance(val, list) and len(val) == 1 and isinstance(val[0], Xsd_dateTime):
                    self.__modified = val[0]
                else:
                    raise OmasError(f'Inconsistency in SHACL "dcterms:modified"')
            elif key == 'sh:group':
                pass  # TODO: Process property group correctly.... (at Moment only omas:SystemPropGroup)
            elif key in propkeys:
                attr = PropClassAttr(key)
                if self.__datatypes[attr] == Iri:
                    if isinstance(val, list) and len(val) == 1 and isinstance(val[0], Iri):
                        self._attributes[attr] = val[0]  # is already QName or AnyIRI from preprocessing
                    else:
                        raise OmasError(f'Inconsistency in SHACL "{attr.value}" (got {val[0]} of type {type(val[0]).__name__})')
                elif self.__datatypes[attr] == XsdDatatypes:
                    if isinstance(val, list) and len(val) == 1 and isinstance(val[0], Iri):
                        self._attributes[attr] = XsdDatatypes(str(val[0]))
                    else:
                        raise OmasError(f'Inconsistency in SHACL "{attr.value}" (got {val[0]} of type {type(val[0]).__name__})')
                elif self.__datatypes[attr] == LangString:
                    if isinstance(val, list):
                        if self._attributes.get(attr) is None:
                            self._attributes[attr] = LangString()
                        self._attributes[attr].add(val)
                    else:
                        raise OmasError(f'Inconsistency in SHACL "{attr.value}" (got {val} of type {type(val[0]).__name__})')
                elif self.__datatypes[attr] == Xsd_decimal:
                    if isinstance(val, list) and len(val) == 1 and isinstance(val[0], Xsd_decimal):
                        self._attributes[attr] = val[0]
                    else:
                        raise OmasError(f'Inconsistency in SHACL "{attr.value}" (got {val[0]} of type {type(val[0]).__name__})')
            else:
                try:
                    self._attributes[PropClassAttr.RESTRICTIONS][PropertyRestrictionType(key)] = val if (key == "sh:languageIn") or (key == "sh:in") else val[0]
                except (ValueError, TypeError) as err:
                    raise OmasError(f'Invalid shacl definition of PropertyClass attribute: "{key}" "{val}"')
        if self._attributes.get(PropClassAttr.RESTRICTIONS):
            self._attributes[PropClassAttr.RESTRICTIONS].changeset_clear()
        #
        # setting property type for OWL which distinguished between Data- and Object-properties
        #
        if self._attributes.get(PropClassAttr.TO_NODE_IRI) is not None:
            self._attributes[PropClassAttr.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
            dt = self._attributes.get(PropClassAttr.DATATYPE)
            if dt and (dt != XsdDatatypes.anyURI and dt != XsdDatatypes.QName):
                raise OmasError(f'Datatype "{dt}" not valid for OwlObjectProperty')
        else:
            self._attributes[PropClassAttr.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)
        self.__from_triplestore = True

    def read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o
        FROM {self._graph}:onto
        WHERE {{
            {self._property_class_iri} ?p ?o
        }}
        """
        jsonobj = self._con.query(query1)
        res = QueryProcessor(context=context, query_result=jsonobj)
        datatype = None
        to_node_iri = None
        for r in res:
            attr = r['p']
            obj = r['o']
            match attr:
                case 'rdf:type':
                    if obj == 'owl:DatatypeProperty':
                        self._attributes[PropClassAttr.PROPERTY_TYPE] = OwlPropertyType.OwlDataProperty
                    elif obj == 'owl:ObjectProperty':
                        self._attributes[PropClassAttr.PROPERTY_TYPE] = OwlPropertyType.OwlObjectProperty
                case 'owl:subPropertyOf':
                    self._attributes[PropClassAttr.SUBPROPERTY_OF] = obj
                case 'rdfs:range':
                    if obj.prefix == 'xsd':
                        datatype = obj
                    else:
                        to_node_iri = obj
                case 'rdfs:domain':
                    self._internal = obj
                case 'dcterms:creator':
                    if self.__creator != obj:
                        raise OmasError(f'Inconsistency between SHACL and OWL: creator "{self.__creator}" vs "{obj}" for property "{self._property_class_iri}".')
                case 'dcterms:created':
                    dt = obj
                    if self.__created != dt:
                        raise OmasError(f'Inconsistency between SHACL and OWL: created "{self.__created}" vs "{dt}".')
                case 'dcterms:contributor':
                    if self.__creator != obj:
                        raise OmasError(f'Inconsistency between SHACL and OWL: contributor "{self.__contributor}" vs "{obj}".')
                case 'dcterms:modified':
                    dt = obj
                    if self.__modified != dt:
                        raise OmasError(f'Inconsistency between SHACL and OWL: created "{self.__modified}" vs "{dt}".')
        #
        # Consistency checks
        #
        if self._attributes[PropClassAttr.PROPERTY_TYPE] == OwlPropertyType.OwlDataProperty:
            if not datatype:
                raise OmasError(f'OwlDataProperty "{self._property_class_iri}" has no rdfs:range datatype defined!')
            if datatype != self._attributes.get(PropClassAttr.DATATYPE).value:
                raise OmasError(
                    f'Property "{self._property_class_iri}" has inconsistent datatype definitions: OWL: "{datatype}" vs. SHACL: "{self._attributes[PropClassAttr.DATATYPE].value}"')
        if self._attributes[PropClassAttr.PROPERTY_TYPE] == OwlPropertyType.OwlObjectProperty:
            if not to_node_iri:
                raise OmasError(f'OwlObjectProperty "{self._property_class_iri}" has no rdfs:range resource class defined!')
            if to_node_iri != self._attributes.get(PropClassAttr.TO_NODE_IRI):
                raise OmasError(
                    f'Property "{self._property_class_iri}" has inconsistent object type definition: OWL: "{to_node_iri}" vs. SHACL: "{self._attributes.get(PropClassAttr.TO_NODE_IRI)}".')

    @classmethod
    def read(cls, con: IConnection, graph: Xsd_NCName, property_class_iri: Iri) -> Self:
        property = cls(con=con, graph=graph, property_class_iri=property_class_iri)
        attributes = PropertyClass.__query_shacl(con, graph, property_class_iri)
        property.parse_shacl(attributes=attributes)
        property.read_owl()
        return property

    def read_modified_shacl(self, *,
                            context: Context,
                            graph: Xsd_NCName,
                            indent: int = 0, indent_inc: int = 4) -> Xsd_dateTime | None:
        blank = ''
        sparql = context.sparql_context
        owlclass_iri = self._internal
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:shacl\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        if owlclass_iri:
            sparql += f"{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n"
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {self._property_class_iri} .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri}Shape as ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self._con.transaction_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')

    def read_modified_owl(self, *,
                          context: Context,
                          graph: Xsd_NCName,
                          indent: int = 0, indent_inc: int = 4) -> Xsd_dateTime | None:
        blank = ''
        sparql = context.sparql_context
        owlclass_iri = self._internal
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:onto\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri} AS ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self._con.transaction_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')


    def property_node_shacl(self, *,
                            timestamp: Xsd_dateTime,
                            bnode: Optional[Xsd_QName] = None,
                            indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{(indent + 1) * indent_inc}}# PropertyClass.property_node_shacl()'
        if bnode:
            sparql += f'\n{blank:{(indent + 1) * indent_inc}} {bnode} sh:path {self._property_class_iri.toRdf}'
        else:
            sparql += f'\n{blank:{(indent + 1) * indent_inc}}sh:path {self._property_class_iri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:hasVersion "{str(self.__version)}"'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        for prop, value in self._attributes.items():
            if prop == PropClassAttr.PROPERTY_TYPE:
                continue
            if prop != PropClassAttr.RESTRICTIONS:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{prop.value} {value.value if isinstance(value, Enum) else value}'
            else:
                sparql += self._attributes[PropClassAttr.RESTRICTIONS].create_shacl(indent + 1, indent_inc)
        #sparql += f' .\n'
        return sparql

    def create_shacl(self, *,
                     timestamp: Xsd_dateTime,
                     owlclass_iri: Iri | None = None,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'\n{blank:{indent * indent_inc}}# PropertyClass.create_shacl()'
        if owlclass_iri is None:
            sparql += f'\n{blank:{indent * indent_inc}}{self._property_class_iri}Shape a sh:PropertyShape ;\n'
            sparql += self.property_node_shacl(timestamp=timestamp, indent=indent, indent_inc=indent_inc)
        else:
            bnode = Xsd_QName('_:propnode')
            sparql += f'\n{blank:{indent * indent_inc}}{owlclass_iri}Shape sh:property {bnode} .\n'
            sparql += self.property_node_shacl(timestamp=timestamp, bnode=bnode, indent=indent, indent_inc=indent_inc)
        sparql += ' .\n'
        return sparql

    def create_owl_part1(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}{self._property_class_iri.toRdf} rdf:type {self._attributes[PropClassAttr.PROPERTY_TYPE].value}'
        if self._attributes.get(PropClassAttr.SUBPROPERTY_OF):
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:subPropertyOf {self._attributes[PropClassAttr.SUBPROPERTY_OF].toRdf}'
        if self._internal:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:domain {self._internal.toRdf}'
        if self._attributes.get(PropClassAttr.PROPERTY_TYPE) == OwlPropertyType.OwlDataProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:range {self._attributes[PropClassAttr.DATATYPE].value}'
        elif self._attributes.get(PropClassAttr.PROPERTY_TYPE) == OwlPropertyType.OwlObjectProperty:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:range {self._attributes[PropClassAttr.TO_NODE_IRI].toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += ' .\n'
        return sparql

    def create_owl_part2(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}[\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:type owl:Restriction ;\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}owl:onProperty {self._property_class_iri.toRdf}'
        sparql += self._attributes[PropClassAttr.RESTRICTIONS].create_owl(indent + 1, indent_inc)
        #
        # TODO: Add the possibility to use owl:onClass or owl:onDataRage instead of rdfs:range
        # (NOTE: owl:onClass and owl:onDataRange can be used only in a restriction and are "local" to the use
        # of the property within the given resource. However, rdfs:range is "global" for all use of this property!
        #
        # if self._attributes[PropertyClassAttribute.PROPERTY_TYPE] == OwlPropertyType.OwlDataProperty:
        #     sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} owl:onDataRange {self._attributes[PropertyClassAttribute.DATATYPE].value}'
        # elif self._attributes[PropertyClassAttribute.PROPERTY_TYPE] == OwlPropertyType.OwlObjectProperty:
        #     sparql += f' ;\n{blank:{(indent + 1) * indent_inc}} owl:onClass {self._attributes[PropertyClassAttribute.TO_NODE_IRI]}'
        sparql += f' ;\n{blank:{indent * indent_inc}}]'
        return sparql

    def set_creation_metadata(self, timestamp: Xsd_dateTime):
        self.__created = timestamp
        self.__creator = self._con.userIri
        self.__modified = timestamp
        self.__contributor = self._con.userIri
        self.__from_triplestore = True

    def create(self, *,
               indent: int = 0, indent_inc: int = 4) -> None:
        if self.__from_triplestore:
            raise OmasErrorAlreadyExists(f'Cannot create property that was read from TS before (property: {self._property_class_iri}')
        timestamp = Xsd_dateTime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
        if self._internal is not None:
            sparql += self.create_shacl(timestamp=timestamp,
                                        owlclass_iri=self._internal,
                                        indent=2)
        else:
            sparql += self.create_shacl(timestamp=timestamp, indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
        sparql += self.create_owl_part1(timestamp=timestamp, indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}}}\n'
        self.set_creation_metadata(timestamp)

        try:
            self._con.transaction_start()
        except OmasError as err:
            self._con.transaction_abort()
            raise
        try:
            r = self.read_modified_shacl(context=context, graph=self._graph)
        except OmasError as err:
            self._con.transaction_abort()
            raise
        if r is not None:
            self._con.transaction_abort()
            raise OmasErrorAlreadyExists(f'Property "{self._property_class_iri}" already exists.')
        try:
            self._con.transaction_update(sparql)
        except OmasError as err:
            self._con.transaction_abort()
            raise
        try:
            modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
            modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
        except OmasError as err:
            self._con.transaction_abort()
            raise
        if modtime_shacl == timestamp and modtime_owl == timestamp:
            self._con.transaction_commit()
        else:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed(f"Update of RDF didn't work!")

    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4) -> None:
        with open(filename, 'w') as f:
            timestamp = Xsd_dateTime().now()
            blank = ''
            context = Context(name=self._con.context_name)
            f.write(context.turtle_context)

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:shacl {{\n')
            if self._internal is not None:
                f.write(self.create_shacl(timestamp=timestamp, owlclass_iri=self._internal, indent=2))
            else:
                f.write(self.create_shacl(timestamp=timestamp, indent=2))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
            f.write(self.create_owl_part1(timestamp=timestamp, indent=2))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

    def update_shacl(self, *,
                     owlclass_iri: Iri | None = None,
                     timestamp: Xsd_dateTime,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            sparql = f'#\n# SHACL\n# Process "{prop.value}" with Action "{change.action.value}"\n#\n'
            if change.action == Action.MODIFY:
                if PropertyClass.__datatypes[prop] == LangString:
                    sparql += self._attributes[prop].update_shacl(graph=self._graph,
                                                                  owlclass_iri=owlclass_iri,
                                                                  prop_iri=self._property_class_iri,
                                                                  attr=prop,
                                                                  modified=self.__modified,
                                                                  indent=indent, indent_inc=indent_inc)
                elif PropertyClass.__datatypes[prop] == PropertyRestrictions:
                    sparql += self._attributes[prop].update_shacl(graph=self._graph,
                                                                  owlclass_iri=owlclass_iri,
                                                                  prop_iri=self._property_class_iri,
                                                                  modified=self.__modified,
                                                                  indent=indent, indent_inc=indent_inc)
                else:
                    raise OmasError(f'SHACL property {prop.value} should not have update action "Update" ({PropertyClass.__datatypes[prop]}).')
                sparql_list.append(sparql)
            else:
                if change.action == Action.DELETE:
                    old_value = '?val'
                    new_value = None
                elif change.action == Action.CREATE:
                    old_value = None
                    new_value = self._attributes[prop].toRdf
                elif change.action == Action.REPLACE:
                    old_value = change.old_value.toRdf
                    new_value = self._attributes[prop].toRdf
                else:
                    raise OmasError(f'==========UNEXPECTED ACTION============')
                ele = RdfModifyItem(prop.value, old_value, new_value)
                sparql += RdfModifyProp.shacl(action=change.action,
                                              graph=self._graph,
                                              owlclass_iri=owlclass_iri,
                                              pclass_iri=self._property_class_iri,
                                              ele=ele,
                                              last_modified=self.__modified)
                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor in {self._graph}:shacl\n#\n'
        sparql += RdfModifyProp.shacl(action=Action.REPLACE if self.__contributor else Action.CREATE,
                                      graph=self._graph,
                                      owlclass_iri=owlclass_iri,
                                      pclass_iri=self._property_class_iri,
                                      ele=RdfModifyItem('dcterms:contributor', f'{self.__contributor.toRdf}', f'{self._con.userIri.toRdf}'),
                                      last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified in {self._graph}:shacl\n#\n'
        sparql += RdfModifyProp.shacl(action=Action.REPLACE if self.__modified else Action.CREATE,
                                      graph=self._graph,
                                      owlclass_iri=owlclass_iri,
                                      pclass_iri=self._property_class_iri,
                                      ele=RdfModifyItem('dcterms:modified', f'{self.__modified.toRdf}', f'{timestamp.toRdf}'),
                                      last_modified=self.__modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update_owl(self, *,
                   owlclass_iri: Optional[Xsd_QName] = None,
                   timestamp: Xsd_dateTime,
                   indent: int = 0, indent_inc: int = 4) -> str:
        owl_propclass_attributes = {PropClassAttr.SUBPROPERTY_OF,  # should be in OWL ontology
                                    PropClassAttr.DATATYPE,  # used for rdfs:range in OWL ontology
                                    PropClassAttr.TO_NODE_IRI}  # used for rdfs:range in OWL ontology
        owl_prop = {PropClassAttr.SUBPROPERTY_OF: PropClassAttr.SUBPROPERTY_OF.value,
                    PropClassAttr.DATATYPE: "rdfs:range",
                    PropClassAttr.TO_NODE_IRI: "rdfs:range"}
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            if prop == PropClassAttr.RESTRICTIONS and change.action == Action.MODIFY:
                sparql = self._attributes[prop].update_owl(graph=self._graph,
                                                           owlclass_iri=owlclass_iri,
                                                           prop_iri=self._property_class_iri,
                                                           modified=self.__modified,
                                                           indent=indent, indent_inc=indent_inc)
                if sparql:
                    sparql_list.append(sparql)
            elif prop in owl_propclass_attributes:
                sparql = f'#\n# OWL:\n# Process "{owl_prop[prop]}" with Action "{change.action.value}"\n#\n'
                ele = RdfModifyItem(property=owl_prop[prop],
                                    old_value=str(change.old_value) if change.action != Action.CREATE else None,
                                    new_value=str(self._attributes[prop]) if change.action != Action.DELETE else None)
                sparql += RdfModifyProp.onto(action=change.action,
                                             graph=self._graph,
                                             owlclass_iri=owlclass_iri,
                                             pclass_iri=self._property_class_iri,
                                             ele=ele,
                                             last_modified=self.__modified,
                                             indent=indent, indent_inc=indent_inc)
                sparql_list.append(sparql)

            if prop == PropClassAttr.DATATYPE or prop == PropClassAttr.TO_NODE_IRI:
                ele: RdfModifyItem
                if self._attributes.get(PropClassAttr.TO_NODE_IRI):
                    ele = RdfModifyItem('rdf:type', 'owl:DatatypeProperty', 'owl:ObjectProperty')
                else:
                    ele = RdfModifyItem('rdf:type', 'owl:ObjectProperty', 'owl:DatatypeProperty')
                sparql = f'#\n# OWL:\n# Correct OWL property type with Action "{change.action.value}\n#\n'
                sparql += RdfModifyProp.onto(action=Action.REPLACE,
                                             graph=self._graph,
                                             owlclass_iri=owlclass_iri,
                                             pclass_iri=self._property_class_iri,
                                             ele=ele,
                                             last_modified=self.__modified,
                                             indent=indent, indent_inc=indent_inc)

                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor {self._graph}:onto\n#\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:contributor {self.__contributor.toRdf}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:contributor {self._con.userIri.toRdf}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri} AS ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self.__modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified in {self._graph}:onto\n#\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified {timestamp.toRdf}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri} AS ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self.__modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update(self) -> None:
        timestamp = Xsd_dateTime.now()

        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        self._con.transaction_start()

        sparql += self.update_shacl(owlclass_iri=self._internal,
                                    timestamp=timestamp)
        sparql += " ;\n"
        sparql += self.update_owl(owlclass_iri=self._internal,
                                  timestamp=timestamp)
        try:
            self._con.transaction_update(sparql)
        except OmasError as e:
            self._con.transaction_abort()
            raise
        try:
            modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
        except OmasError as e:
            self._con.transaction_abort()
            raise
        try:
            modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
        except OmasError as e:
            self._con.transaction_abort()
            raise

        if modtime_shacl == timestamp and modtime_owl == timestamp:
            self._con.transaction_commit()
            self.__modified = timestamp
            self.__contributor = self._con.userIri
            for prop, change in self._changeset.items():
                if change.action == Action.MODIFY:
                    self._attributes[prop].changeset_clear()
            self._changeset = {}
        else:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed(f'Update RDF of "{self._property_class_iri}" didn\'t work: shacl={modtime_shacl} owl={modtime_owl} timestamp={timestamp}')

    def __delete_shacl(self, *,
                       indent: int = 0, indent_inc: int = 4) -> str:
        #
        # TODO: Test here if property is in use
        #
        owlclass_iri = self._internal
        blank = ''
        sparql_list = []
        sparql = f'#\n# Delete {self._property_class_iri} from shacl\n#\n'
        #
        # First we delete all list (sh:languageIn/sh:in restrictions) if existing
        #
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:shacl\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql += f'{blank:{indent * indent_inc}}WHERE{{\n'
        if owlclass_iri is not None:
            sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:path {self._property_class_iri} .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri}Shape as ?propnode)\n'
        #sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:languageIn ?list .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?listprop ?list .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?list rdf:rest* ?z .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self.__modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        sparql = ''
        #
        # Now we delete the remaining triples
        #
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:shacl\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE{{\n'
        if owlclass_iri is not None:
            sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE{{\n'
        if owlclass_iri is not None:
            sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:path {self._property_class_iri} .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri}Shape as ?propnode)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self.__modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def delete_owl_subclass_str(self, *,
                                owlclass_iri: Xsd_QName,
                                indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode owl:onProperty {self._property_class_iri.toRdf} .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def __delete_owl(self, *,
                     indent: int = 0, indent_inc: int = 4) -> str:
        owlclass_iri = self._internal
        blank = ''
        sparql_list = []
        sparql = f'#\n# Delete {self._property_class_iri} from onto\n#\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{indent * indent_inc}}BIND({self._property_class_iri} as ?propnode)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self.__modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        if owlclass_iri is not None:
            sparql = self.delete_owl_subclass_str(owlclass_iri=owlclass_iri)
            sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def delete(self) -> None:
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        sparql += self.__delete_shacl()
        sparql += ' ;\n'
        sparql += self.__delete_owl()

        self.__from_triplestore = False
        self._con.transaction_start()
        self._con.transaction_update(sparql)
        modtime_shacl = self.read_modified_shacl(context=context, graph='test')
        modtime_owl = self.read_modified_owl(context=context, graph='test')
        if modtime_shacl is not None or modtime_owl is not None:
            self._con.transaction_abort()
            raise OmasErrorUpdateFailed("Deleting Property failed")
        else:
            self._con.transaction_commit()


if __name__ == '__main__':
    pass
    # con = Connection('http://localhost:7200', 'omas')
    # pclass1 = PropertyClass(con=con, graph=NCName('omas'), property_class_iri=QName('omas:comment'))
    # pclass1.read()
    # print(pclass1)
    #
    # pclass2 = PropertyClass(con=con, graph=NCName('omas'), property_class_iri=QName('omas:test'))
    # pclass2.read()
    # print(pclass2)
