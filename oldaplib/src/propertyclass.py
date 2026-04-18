"""
:Author: Lukas Rosenthaler <lukas.rosenthaler@unibas.ch>
:Copyright: © Lukas Rosenthaler (2023, 2024)

# Property Class

The class `PropertyClass`and it's helper companion `HasPropertyData` holds the Python representation of a
RDF property

## Caching

Datamodels, Resources and properties are being cached in order to avoid the timeconsuming access of the triple
store for each read. If these classes are modified, the `update()`-method will also update the cache. If one of these
classes is being deleted from the triple store, the class instance will also be deleted from the cache. The
cache is implemented using a metaclass based singleton and uses locking to be compatible in a threaded environment.
"""
import logging
import textwrap
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pprint import pprint
from secrets import token_urlsafe
from typing import Callable, Self, Any, Tuple

from rdflib.extras import shacl

from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.helpers.construct_processor import ConstructProcessor, ConstructResultDict
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.helpers.convert2datatype import convert2datatype
from oldaplib.src.helpers.numeric import Numeric
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_float import Xsd_float
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorAlreadyExists, \
    OldapErrorUpdateFailed, OldapErrorValue, OldapErrorInconsistency, OldapErrorNoPermission
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.helpers.query_processor import RowType, QueryProcessor
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.helpers.tools import RdfModifyItem, RdfModifyProp, RdfModifyRes
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.xsd.xsd_string import Xsd_string

PropTypes = Iri | Xsd_QName | OwlPropertyType | XsdDatatypes | LangString | Xsd_string | Xsd_integer | Xsd_boolean | LanguageIn | XsdSet | Numeric | None
PropClassAttrContainer = dict[PropClassAttr, PropTypes]
Attributes = dict[Xsd_QName, PropTypes]

#@strict
@serializer
class PropertyClass(Model, Notify):
    _graph: Xsd_NCName
    _projectShortName: Xsd_NCName
    _projectIri: Iri
    _property_class_iri: Xsd_QName | None
    _appliesToProperty: Xsd_QName | None
    _inResourceClass: Xsd_QName | None
    _test_in_use: bool
    _notifier: Callable[[type], None] | None

    #
    # The following attributes of this class cannot be set explicitely by the used
    # They are automatically managed by the OMAS system
    #
    __from_triplestore: bool

    __slots__ = ('subPropertyOf', 'type', 'toClass', 'datatype', 'name', 'description', 'languageIn', 'uniqueLang',
                 'inSet', 'minCount', 'maxCount', 'order', 'pattern',
                 'minExclusive', 'maxExclusive', 'minInclusive', 'maxInclusive', 'minLength', 'maxLength',
                 'lessThan', 'lessThanOrEquals', 'inverseOf', 'equivalentProperty')


    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str | None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 project: Project | Iri | Xsd_NCName | str,
                 property_class_iri: Xsd_QName | str | None = None,
                 appliesToProperty: Xsd_QName | str | None = None,
                 notifier: Callable[[PropClassAttr], None] | None = None,
                 notify_data: PropClassAttr | None = None,
                 _inResourceClass: Xsd_QName | None = None,  # DO NOT USE!! Only for serialization!
                 _from_triplestore: bool = False,  # DO NOT USE!! Only for serialization!
                 validate: bool = False,
                 **kwargs):
        Model.__init__(self,
                       connection=con,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified,
                       validate=validate)
        Notify.__init__(self, notifier, notify_data)

        if not isinstance(project, Project):
            project = Project.read(self._con, IriOrNCName(project, validate=validate))
        self._projectShortName = project.projectShortName
        self._projectIri = project.projectIri
        self._appliesToProperty = Xsd_QName(appliesToProperty, validate=validate) if appliesToProperty else None
        self._inResourceClass = Xsd_QName(_inResourceClass, validate=validate) if _inResourceClass else None
        context = Context(name=self._con.context_name)
        context[self._projectShortName] = project.namespaceIri
        context.use(self._projectShortName)
        self._graph = self._projectShortName

        self._property_class_iri = Xsd_QName(property_class_iri, validate=validate) if property_class_iri else None
        datatype: XsdDatatypes | None = kwargs.get('datatype', None)
        if datatype and kwargs.get('inSet'):
            if datatype == XsdDatatypes.langString:
                kwargs['inSet'] = {convert2datatype(x, XsdDatatypes.string) for x in kwargs['inSet']}
            else:
                kwargs['inSet'] = {convert2datatype(x, datatype) for x in kwargs['inSet']}
        toClass = kwargs.get('toClass', None)
        if toClass and kwargs.get('inSet'):
            kwargs['inSet'] = {Iri(x) for x in kwargs['inSet']}

        self.set_attributes(kwargs, PropClassAttr)

        if toClass:
            if self._attributes.get(PropClassAttr.DATATYPE) or \
                    self._attributes.get(PropClassAttr.LANGUAGE_IN) or \
                    self._attributes.get(PropClassAttr.LESS_THAN) or \
                    self._attributes.get(PropClassAttr.LESS_THAN_OR_EQUALS) or \
                    self._attributes.get(PropClassAttr.MAX_EXCLUSIVE) or \
                    self._attributes.get(PropClassAttr.MAX_INCLUSIVE) or \
                    self._attributes.get(PropClassAttr.MIN_EXCLUSIVE) or \
                    self._attributes.get(PropClassAttr.MIN_INCLUSIVE) or \
                    self._attributes.get(PropClassAttr.MIN_LENGTH) or \
                    self._attributes.get(PropClassAttr.PATTERN) or \
                    self._attributes.get(PropClassAttr.UNIQUE_LANG):
                raise OldapErrorInconsistency("A property pointing to a resource (link) may not have restrictions.")
            if self._attributes[PropClassAttr.CLASS].is_qname:
                tmp = self._attributes[PropClassAttr.CLASS].as_qname
                if tmp.prefix == "rdf" or tmp.prefix == "xml":
                    raise OldapErrorValue(f'A class that has a prefix of "rdf", "rdfs" and "xml" is not allowed.')
                if context.get(tmp.prefix) is None:
                    raise OldapErrorValue(f'The prefix "{tmp.prefix}" is not known in the context.')

        #
        # Consistency checks
        #
        if self._attributes.get(PropClassAttr.LANGUAGE_IN) is not None:
            if self._attributes[PropClassAttr.DATATYPE] not in {XsdDatatypes.langString, XsdDatatypes.string}:
                raise OldapErrorValue(f'Using restriction LANGUAGE_IN requires DATATYPE "rdf:langString", not "{self._attributes[PropClassAttr.DATATYPE].value}"')
        if self._attributes.get(PropClassAttr.DATATYPE) is not None and self._attributes.get(PropClassAttr.CLASS) is not None:
            raise OldapErrorInconsistency(f'It\'s not possible to use both DATATYPE="{self._attributes[PropClassAttr.DATATYPE]}" and CLASS={self._attributes[PropClassAttr.CLASS]} restrictions.')

        if not self._attributes.get(PropClassAttr.TYPE):
            self._attributes[PropClassAttr.TYPE] = ObservableSet(notifier=self.notifier, notify_data=PropClassAttr.TYPE)

        #
        # setting property type for OWL which distinguished between Data- and Object-properties
        #
        if self._attributes.get(PropClassAttr.CLASS) is not None:
            if OwlPropertyType.OwlDataProperty in self._attributes[PropClassAttr.TYPE]:
                raise OldapErrorInconsistency(f'Property {self._property_class_iri} cannot be both a link property and a data property.')
            self._attributes[PropClassAttr.TYPE].add(OwlPropertyType.OwlObjectProperty)
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                raise OldapError(f'Datatype "{self._attributes.get(PropClassAttr.DATATYPE)}" not possible for OwlObjectProperty')
        elif self._attributes.get(PropClassAttr.DATATYPE) is not None:
            if OwlPropertyType.OwlObjectProperty in self._attributes[PropClassAttr.TYPE]:
                raise OldapErrorInconsistency(f'Property {self._property_class_iri} cannot be both a link property and a data property.')
            self._attributes[PropClassAttr.TYPE].add(OwlPropertyType.OwlDataProperty)

        #
        # set the class properties
        #
        for attr in PropClassAttr:
            name = attr.value.fragment
            if name == 'in':
                name = 'inSet'
            elif name == 'class':
                name = 'toClass'
            setattr(PropertyClass, name, property(
                partial(PropertyClass._get_value, attr=attr),
                partial(PropertyClass._set_value, attr=attr),
                partial(PropertyClass._del_value, attr=attr)))

        self.update_notifier()
        self._test_in_use = False
        self._inResourceClass = _inResourceClass
        self.__from_triplestore = _from_triplestore
        self.clear_changeset()

    def __len__(self) -> int:
        return len(self._attributes)

    def update_notifier(self,
                        notifier: Callable[[PropClassAttr], None] | None = None,
                        notify_data: PropClassAttr | None = None,):
        self.set_notifier(notifier, notify_data)
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)


    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict() | {
            'project': self._projectShortName,
            'property_class_iri': self.property_class_iri,
            **({'_inResourceClass': self._inResourceClass} if self._inResourceClass else {}),
            **({'appliesToProperty': self._appliesToProperty} if self._appliesToProperty else {}),
            '_from_triplestore': self.__from_triplestore,
        }

    def __eq__(self, other: Self):
        return self._as_dict() == other._as_dict()

    def check_for_permissions(self) -> (bool, str):
        """
        Checks if the current logged-in user (actor) has the necessary permissions to create a user
        for a given project. The method determines permissions based on system and project-specific
        privileges. If the user has root privileges or the required project permissions, the function
        returns success; otherwise, it provides a failure message.

        :raises TypeError: Raised if function arguments are of invalid types.
        :raises ValueError: Raised if provided IRI is not formatted properly.

        :return: A tuple where the first element is a boolean indicating whether the check succeeded
            or failed, and the second element is a string containing an explanatory message.
        :rtype: tuple[bool, str]
        """
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK – IS ROOT"
        else:
            if not self._projectShortName:
                return False, f'Actor has no ADMIN_MODEL permission. Actor not associated with a project.'
            proj = self._projectShortName
            if actor.inProject.get(self._projectIri) is None:
                return False, f'Actor has no ADMIN_MODEL permission for project "{self._projectIri}"'
            else:
                if AdminPermission.ADMIN_MODEL not in actor.inProject.get(self._projectIri):
                    return False, f'Actor has no ADMIN_MODEL permission for project "{self._projectIri}"'
            return True, "OK"


    def pre_transform(self, attr: AttributeClass, value: Any, validate: bool = False) -> Any:
        """
        INTERNAL USE ONLY! Overrides the method pre_transform from the Model class.
        :param attr: Attribute name
        :type attr: AttributeClass
        :param value: The value to be transformed
        :type value: Any
        :return: Transformed value
        :rtype: Any
        """
        if attr == PropClassAttr.IN:
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                datatype = self._attributes[PropClassAttr.DATATYPE]
                if datatype == XsdDatatypes.langString:
                    return {convert2datatype(x, XsdDatatypes.string, validate=validate) for x in value}
                else:
                    return {convert2datatype(x, datatype, validate=validate) for x in value}
            elif self._attributes.get(PropClassAttr.CLASS) is not None:
                toClass = self._attributes[PropClassAttr.CLASS]
                return {Iri(x) for x in value}
        else:
            return value

    def check_consistency(self, attr: PropClassAttr, value: Any) -> None:
        """
        INTERNAL USE ONLY! Overrides the method check_consistency from the Model class.
        :param attr: Attribute name
        :type attr: AttributeClass
        :param value: The value to check
        :type value: Any
        :return: None
        """
        if attr == PropClassAttr.CLASS:
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                self._changeset[PropClassAttr.DATATYPE] = AttributeChange(self._attributes[PropClassAttr.DATATYPE], Action.DELETE)
                del self._attributes[PropClassAttr.DATATYPE]
            if self._attributes.get(PropClassAttr.CLASS) is not None:
                self._changeset[PropClassAttr.CLASS] = AttributeChange(self._attributes[PropClassAttr.CLASS], Action.REPLACE)
            else:
                self._changeset[PropClassAttr.CLASS] = AttributeChange(None, Action.CREATE)
            self._attributes[PropClassAttr.CLASS] = value
        elif attr == PropClassAttr.DATATYPE:
            if self._attributes.get(PropClassAttr.CLASS) is not None:
                self._changeset[PropClassAttr.CLASS] = AttributeChange(self._attributes[PropClassAttr.CLASS], Action.DELETE)
                del self._attributes[PropClassAttr.CLASS]
            if self._attributes.get(PropClassAttr.DATATYPE) is not None:
                self._changeset[PropClassAttr.DATATYPE] = AttributeChange(self._attributes[PropClassAttr.DATATYPE], Action.REPLACE)
            else:
                self._changeset[PropClassAttr.DATATYPE] = AttributeChange(None, Action.CREATE)
            self._attributes[PropClassAttr.DATATYPE] = value

    def _del_value(self, attr: PropClassAttr) -> None:
        if attr == PropClassAttr.TYPE:
            remaining = self._attributes.get(attr) & {OwlPropertyType.OwlObjectProperty, OwlPropertyType.OwlDataProperty}
            to_delete = self._attributes.get(attr) - remaining
            for x in to_delete:
                self._attributes[attr].discard(x)
            return
        super()._del_value(attr)

    def _change_setter(self: Self, attr: PropClassAttr, value: PropTypes) -> None:
        """
        INTERNAL USE ONLY! Overrides the method _change_setter from the Model class.
        :param attr: Attribute
        :type attr: AttributeClass
        :param value: The value to be set
        :type value: Any
        :return: None
        :raises OldapError: If an Attribute is not aa PropClassAttr
        """
        if not isinstance(attr, PropClassAttr):
            raise OldapError(f'Unsupported prop {attr}')
        if attr == PropClassAttr.TYPE:
            if value is None:
                remaining = self._attributes.get(attr) & {OwlPropertyType.OwlObjectProperty, OwlPropertyType.OwlDataProperty}
                to_delete = self._attributes.get(attr) - remaining
                for x in to_delete:
                    self._attributes[attr].discard(x)
                return
            else:
                to_add = set(value) - set(self._attributes.get(attr))
                to_delete = set(self._attributes.get(attr)) - set(value)
                if OwlPropertyType.OwlObjectProperty in to_delete:
                    to_delete.remove(OwlPropertyType.OwlObjectProperty)
                if OwlPropertyType.OwlDataProperty in to_delete:
                    to_delete.remove(OwlPropertyType.OwlDataProperty)
                for x in to_delete:
                    self._attributes[attr].discard(x)
                for x in to_add:
                    self._attributes[attr].add(x)
                return
        if self._attributes.get(attr) == value:
            return
        super()._change_setter(attr, value)
        #
        # set the notifier, if the value
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, attr)

    def oldapSetAttr(self, attrname: str, attrval: PropTypes):
        propClassAttr = PropClassAttr.from_name(attrname)
        val = propClassAttr.datatype(attrval)
        self._change_setter(propClassAttr, val)

    def __deepcopy__(self, memo: dict[Any, Any]) -> Self:
        if id(self) in memo:
            return memo[id(self)]
        cls = self.__class__
        instance = cls.__new__(cls)
        memo[id(self)] = instance
        Model.__init__(instance,
                       connection=deepcopy(self._con, memo),
                       creator=deepcopy(self._creator, memo),
                       created=deepcopy(self._created, memo),
                       contributor=deepcopy(self._contributor, memo),
                       modified=deepcopy(self._modified, memo))
        Notify.__init__(instance,
                        notifier=self._notifier,
                        data=deepcopy(self._notify_data, memo))
        # Copy internals of Model:
        instance._appliesToProperty = deepcopy(self._appliesToProperty, memo)
        instance._attributes = deepcopy(self._attributes, memo)
        instance._changset = deepcopy(self._changeset, memo)
        # Copy remaining PropertyClass attributes
        instance._graph = deepcopy(self._graph, memo)
        instance._projectShortName = deepcopy(self._projectShortName, memo)
        instance._projectIri = deepcopy(self._projectIri, memo)
        instance._property_class_iri = deepcopy(self._property_class_iri, memo)
        instance._inResourceClass = deepcopy(self._inResourceClass, memo)
        instance._test_in_use = self._test_in_use
        instance.__from_triplestore = self.__from_triplestore
        return instance

    def __len__(self) -> int:
        return len(self._attributes)

    def __str__(self) -> str:
        propstr = f'Property: {str(self._property_class_iri)};'
        for attr, value in self._attributes.items():
            propstr += f' {attr.value}: {value};'
        propstr += f' internal: {self._inResourceClass};'
        return propstr

    @property
    def projectShortName(self) -> Xsd_NCName:
        return self._projectShortName

    @property
    def projectIri(self) -> Iri:
        return self._projectIri

    @property
    def property_class_iri(self) -> Xsd_QName:
        return self._property_class_iri

    @property_class_iri.setter
    def property_class_iri(self, property_class_iri: Xsd_QName):
        self._property_class_iri = property_class_iri

    @property
    def inResourceClass(self) -> Xsd_QName | None:
        return self._inResourceClass

    @inResourceClass.setter
    def inResourceClass(self, inResourceClass: Xsd_QName):
        self._inResourceClass = inResourceClass

    @property
    def appliesToProperty(self) -> Xsd_QName | None:
        return self._appliesToProperty

    @property
    def from_triplestore(self) -> bool:
        return self.__from_triplestore

    def undo(self, attr: PropClassAttr | None = None) -> None:
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


    def notifier(self, attr: PropClassAttr) -> None:
        if attr.datatype in [XsdSet, LanguageIn]:
            # we can *not* modify sets, we have to replace them if an item is added or discarded
            if self._changeset.get(attr) is None:
                tmp = deepcopy(self._attributes[attr])
                self._changeset[attr] = AttributeChange(tmp, Action.REPLACE)
        else:
            self._changeset[attr] = AttributeChange(None, Action.MODIFY)
        self.notify()

    @property
    def in_use(self) -> bool:
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        ASK {{
            ?rinstances {self._property_class_iri.toRdf} ?value .
        }}
        """
        jsonres = self._con.query(query)

        try:
            return bool(jsonres["boolean"])
        except (KeyError, TypeError) as err:
            raise OldapError('Internal Error in "propertyClass.in_use"') from err


    @staticmethod
    def read_shacl(con: IConnection, project: Project, property_class_iri: Xsd_QName) -> ConstructResultDict:
        context = Context(name=con.context_name)
        sparql = context.sparql_context
        sparql += textwrap.dedent(f"""
        CONSTRUCT {{
            ?shape ?p ?o .
            ?prop ?pp ?oo .
            ?listnode rdf:first ?item .
            ?listnode rdf:rest ?rest .
        }}
        WHERE {{
            GRAPH {project.projectShortName}:shacl {{
                BIND({property_class_iri}Shape AS ?shape)
                ?shape ?p ?o .
                OPTIONAL {{
                    ?shape sh:property ?prop .
                    ?prop ?pp ?oo .
                    OPTIONAL {{
                        ?prop ?pp ?list .
                        ?list rdf:rest* ?listnode .
                        ?listnode rdf:first ?item ;
                        rdf:rest ?rest .
                    }}
                }}
            }}
        }}
        """)
        graph = con.query(sparql, format=SparqlResultFormat.JSONLD)
        obj = ConstructProcessor.process(context, graph)
        if obj.get(property_class_iri + 'Shape') is None:
            raise OldapErrorNotFound(f'Property {property_class_iri} not found in SHACL of {project.projectShortName}')

        return obj[property_class_iri + 'Shape']


    def read_owl(self) -> None:
        propkeys = {Xsd_QName(x.value) for x in PropClassAttr}
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o
        FROM {self._graph}:onto
        FROM oldap:onto
        FROM shared:onto
        WHERE {{
            {self._property_class_iri} ?p ?o
        }}
        """
        jsonobj = self._con.query(query1)
        res = QueryProcessor(context=context, query_result=jsonobj)
        for r in res:
            attr = r['p']
            obj = r['o']
            match attr:
                case 'rdf:type':
                    try:
                        # If obj is already a member, keep it; otherwise look it up by value
                        prop_type = obj if isinstance(obj, OwlPropertyType) else OwlPropertyType(obj)
                    except ValueError as e:
                        raise OldapErrorNotFound(f'{self._property_class_iri}: Unknown owl:Property type "{obj}"') from e
                    self._attributes[PropClassAttr.TYPE].add(prop_type)
                case _:
                    if attr in propkeys:
                        pcattr = PropClassAttr.from_value(attr)
                        if pcattr.in_owl:
                            self._attributes[pcattr] = pcattr.datatype(obj)

    @classmethod
    def read(cls, con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             property_class_iri: Xsd_QName | str,
             ignore_cache: bool = False) -> Self:
        logger = logging.getLogger(__name__)

        if not isinstance(property_class_iri, Xsd_QName):
            prop_iri: Xsd_QName = Xsd_QName(property_class_iri)
        else:
            prop_iri: Xsd_QName = property_class_iri
        cache = CacheSingletonRedis()
        if not ignore_cache:
            tmp = cache.get(prop_iri, connection=con)
            if tmp is not None:
                tmp.update_notifier()
                return tmp
        if not isinstance(project, Project):
            proj: Project = Project.read(con, project)
        else:
            proj: Project = project

        obj = PropertyClass.read_shacl(con, proj, prop_iri)

        attributes = {attr.fragment: value for attr, value in obj[Xsd_QName("sh:property")].items()}
        if attributes.get("path") is not None:
            del attributes["path"]

        property = cls(con=con,
                       project=project,
                       property_class_iri=property_class_iri,
                       creator=obj[Xsd_QName("dcterms:creator")],
                       created=obj[Xsd_QName("dcterms:created")],
                       modified=obj[Xsd_QName("dcterms:modified")],
                       contributor=obj[Xsd_QName("dcterms:contributor")],
                       appliesToProperty=obj[Xsd_QName("oldap:appliesToProperty")],
                       validate=False,
                       **attributes)

        property.read_owl()
        property.clear_changeset()

        property.update_notifier()
        cache.set(property.property_class_iri, property)

        return property

    def read_modified_shacl(self, *,
                            context: Context,
                            graph: Xsd_NCName,
                            indent: int = 0, indent_inc: int = 4) -> Xsd_dateTime | None:
        blank = ''
        sparql = context.sparql_context
        owlclass_iri = self._inResourceClass
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:shacl\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        if owlclass_iri: # TODO: check if "if" is necessary....
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

    def property_node_shacl(self, *,
                            bnode: Xsd_QName | None = None,
                            indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        if bnode:
            sparql += f'\n{blank:{indent * indent_inc}} {bnode} sh:path {self._property_class_iri.toRdf}'
        else:
            sparql += f'\n{blank:{indent * indent_inc}}sh:path {self._property_class_iri.toRdf}'
        for prop, value in self._attributes.items():
            if not prop.in_shacl:
                continue
            if not value and not isinstance(value, bool):
                continue
            sparql += f' ;\n{blank:{indent * indent_inc}}{prop.value} {value.toRdf}'
        return sparql

    def create_shacl(self, *,
                     timestamp: Xsd_dateTime,
                     owlclass_iri: Xsd_QName | None = None,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        if self._appliesToProperty:
            sparql += f'\n{blank:{indent * indent_inc}}{self._property_class_iri}Shape a sh:NodeShape'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {timestamp.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {timestamp.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}oldap:appliesToProperty {self._appliesToProperty.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}sh:property ['
            sparql += self.property_node_shacl(indent=indent + 2, indent_inc=indent_inc)
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}]'
        elif owlclass_iri:
            bnode = Xsd_QName(f'_:node{token_urlsafe(5)}')
            sparql += self.property_node_shacl(bnode=bnode,
                                               indent=indent, indent_inc=indent_inc)
            sparql += ' .\n'
            sparql += f'\n{blank:{indent * indent_inc}}{owlclass_iri}Shape sh:property {bnode}'
        sparql += ' .\n'
        return sparql

    def create_owl(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}{self._property_class_iri.toRdf} {PropClassAttr.TYPE.toRdf} {self._attributes[PropClassAttr.TYPE].toRdf}'
        for attr, val in self._attributes.items():
            attr: PropClassAttr
            if not attr.in_owl or attr == PropClassAttr.TYPE or val is None:
                continue
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{attr.toRdf} {val.toRdf}'
        sparql += ' .\n'

        return sparql

    def set_creation_metadata(self, timestamp: Xsd_dateTime):
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.__from_triplestore = True


    def create(self, *,
               indent: int = 0, indent_inc: int = 4) -> None:

        if not self._appliesToProperty:
            raise OldapErrorInconsistency(f'Property "{self._property_class_iri}" is not an annotation property: missing the "appliesToProperty" parameter')
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        if self.__from_triplestore:
            raise OldapErrorAlreadyExists(f'Cannot create property that was read from TS before (property: {self._property_class_iri}')
        timestamp = Xsd_dateTime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
        # TODO: Check the following lines, if the "if" is necessary
        if self._inResourceClass is not None:  # internal property, add minCount, maxCount if defined
            sparql += self.create_shacl(timestamp=timestamp,
                                        owlclass_iri=self._inResourceClass,
                                        indent=2)
        else:  # standalone (reusable) property -> no minCount, maxCount
            sparql += self.create_shacl(timestamp=timestamp,
                                        indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
        sparql += self.create_owl(indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        try:
            self._con.transaction_start()
        except OldapError as err:
            self._con.transaction_abort()
            raise
        try:
            r = self.read_modified_shacl(context=context, graph=self._graph)
        except OldapError as err:
            self._con.transaction_abort()
            raise
        if r is not None:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'Property "{self._property_class_iri}" already exists.')
        try:
            self._con.transaction_update(sparql)
        except OldapError as err:
            self._con.transaction_abort()
            raise
        try:
            modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
        except OldapError as err:
            self._con.transaction_abort()
            raise
        if modtime_shacl == timestamp:
            self._con.transaction_commit()
        else:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f"Update of RDF didn't work!")
        self.set_creation_metadata(timestamp)

        self.clear_changeset()

        cache = CacheSingletonRedis()
        cache.set(self._property_class_iri, self)


    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Writes the content of the current object to a file in Trig format.

        The method generates a timestamp, initializes a context and produces
        content based on the internal state of the object. The content is written
        to a file in valid Trig format.

        :param filename: The name of the output file where Trig-formatted data
            will be written.
        :param indent: The base indentation level to be applied to the written
            content. Default value is 0.
        :param indent_inc: The incremental spaces for each indentation level.
            Default value is 4.
        :return: None
        """
        with open(filename, 'w') as f:
            timestamp = Xsd_dateTime().now()
            blank = ''
            context = Context(name=self._con.context_name)
            f.write(context.turtle_context)

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:shacl {{\n')
            if self._inResourceClass is not None:
                f.write(self.create_shacl(timestamp=timestamp, owlclass_iri=self._inResourceClass, indent=1))
            else:
                f.write(self.create_shacl(timestamp=timestamp, indent=1))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
            f.write(self.create_owl(indent=1))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

    def update_shacl(self, *,
                     owlclass_iri: Xsd_QName | None = None,
                     timestamp: Xsd_dateTime,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            sparql = ''
            if change.action == Action.MODIFY:
                if prop.datatype == LangString:
                    sparql += self._attributes[prop].update_shacl(graph=self._graph,
                                                                  owlclass_iri=owlclass_iri,
                                                                  prop_iri=self._property_class_iri,
                                                                  attr=prop,
                                                                  modified=self._modified if self.appliesToProperty else None,
                                                                  indent=indent, indent_inc=indent_inc)
                elif prop.datatype == (ObservableSet, OwlPropertyType):
                    if prop == PropClassAttr.TYPE:
                        if self._attributes[prop].old_value:
                            added = set(self._attributes[PropClassAttr.TYPE]) - set(self._attributes[prop].old_value)
                        else:
                            added = set(self._attributes[PropClassAttr.TYPE])
                        if self._attributes[prop].old_value:
                            removed = set(self._attributes[prop].old_value) - set(self._attributes[PropClassAttr.TYPE])
                        else:
                            removed = set()
                else:
                    raise OldapError(f'SHACL property {prop.value} should not have update action "MODIFY" ({prop.datatype}).')
                sparql_list.append(sparql)
            else:
                if change.action == Action.DELETE:
                    old_value = change.old_value.toRdf
                    new_value = None
                elif change.action == Action.CREATE:
                    old_value = None
                    new_value = self._attributes[prop].toRdf
                elif change.action == Action.REPLACE:
                    old_value = change.old_value.toRdf
                    new_value = self._attributes[prop].toRdf
                else:
                    raise OldapError(f'An unexpected Action occured: {change.action} for {prop.value}.')
                ele = RdfModifyItem(prop.value, old_value, new_value)
                if prop.datatype == XsdSet or prop.datatype == LanguageIn:
                    sparql += RdfModifyProp.replace_rdfset(action=change.action,
                                                           graph=Xsd_QName(self._graph, 'shacl'),
                                                           owlclass_iri=owlclass_iri,
                                                           pclass_iri=self._property_class_iri,
                                                           ele=ele,
                                                           last_modified=self._modified)
                else:
                    sparql += RdfModifyProp.shacl(action=change.action,
                                                  graph=self._graph,
                                                  owlclass_iri=owlclass_iri,
                                                  pclass_iri=self._property_class_iri,
                                                  ele=ele)
                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        if not owlclass_iri:
            #
            # do update modified/contributor only if it's a assertion property (RDF*star)
            #
            sparql = RdfModifyRes.update_timestamp_contributors(contributor=self._con.userIri,
                                                                timestamp=timestamp,
                                                                old_timestamp=self._modified,
                                                                iri=self._property_class_iri,
                                                                graph=Xsd_QName(f'{self._graph}:shacl'))
            sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update_owl(self, *,
                   owlclass_iri: Xsd_QName | None = None,
                   indent: int = 0, indent_inc: int = 4) -> str:
        owl_propclass_attributes = {x for x in PropClassAttr if x.in_owl and x != PropClassAttr.TYPE}
        owl_prop = {x: x.value.toRdf for x in PropClassAttr if x.in_owl and x != PropClassAttr.TYPE}
        blank = ''
        sparql_list = []
        datatype_class_change = False
        for prop, change in self._changeset.items():
            if prop in owl_propclass_attributes:
                sparql = f'#\n# OWL:\n# PropertyClass(2): Process "{owl_prop[prop]}" with Action "{change.action.value}"\n#\n'
                ele = RdfModifyItem(property=owl_prop[prop],
                                    old_value=str(change.old_value) if change.action != Action.CREATE else None,
                                    new_value=str(self._attributes[prop]) if change.action != Action.DELETE else None)
                sparql += RdfModifyProp.onto(action=change.action,
                                             graph=self._graph,
                                             owlclass_iri=owlclass_iri,
                                             pclass_iri=self._property_class_iri,
                                             ele=ele,
                                             indent=indent, indent_inc=indent_inc)
                sparql_list.append(sparql)

            if prop == PropClassAttr.DATATYPE or prop == PropClassAttr.CLASS:
                if not datatype_class_change:
                    if self._attributes.get(PropClassAttr.CLASS):
                        fromType = 'owl:DatatypeProperty'
                        toType = 'owl:ObjectProperty'
                    else:
                        fromType = 'owl:ObjectProperty'
                        toType = 'owl:DatatypeProperty'
                    sparql = textwrap.dedent(f'''
                    WITH {self._graph}:onto
                        DELETE {{ {self._property_class_iri} rdf:type {fromType} }}
                        INSERT {{ {self._property_class_iri} rdf:type {toType} . }}
                        WHERE {{ {self._property_class_iri} rdf:type {fromType} . }}
                    ''')
                    datatype_class_change = True
                sparql_list.append(sparql)
            if prop == PropClassAttr.TYPE:
                actual_items = set(self._attributes[prop])
                old_items = set(self._attributes[prop].old_value)
                added_items = actual_items - old_items
                removed_items = old_items - actual_items
                if added_items:
                    tmp = [x.toRdf for x in added_items]
                    tmpstr = ", ".join(tmp)
                    sparql = textwrap.dedent(f'''
                    INSERT DATA {{
                        GRAPH {self._graph}:onto {{
                            {self._property_class_iri} rdf:type {tmpstr} .
                        }}
                    }}
                    ''')
                    sparql_list.append(sparql)
                if removed_items:
                    tmp = [x.toRdf for x in removed_items]
                    tmpstr = ", ".join(tmp)
                    sparql = textwrap.dedent(f'''
                    DELETE DATA {{
                        GRAPH {self._graph}:onto {{
                            {self._property_class_iri} rdf:type {tmpstr} .
                        }}
                    }}
                    ''')
                    sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update(self) -> None:
        """
        Updates the RDF graph and applies the necessary modifications to the property class
        based on the changeset. This method performs operations such as validating permissions,
        updating data types, deleting unwanted restrictions based on the new data type, and handling
        transaction updates. The method ensures consistency between SHACL and OWL modifications.

        :raises OldapErrorNoPermission: If the user does not have permission to perform the update.
        :raises OldapError: If the property type is being changed while it is in use, or if specific
            operations fail during the update process.
        :raises OldapErrorUpdateFailed: If the SHACL and OWL updates do not reflect the expected
            modifications after a successful attempt.
        :return: None

        :raises OldapErrorNoPermission: Generic error indicating an issue when updating data in the triple store.
        :raises OldapError: Generic error indicating an issue when updating data in the triple store.
        :raises OldapErrorInconsistency: Inconsistency between SHACL and OWL.
        :raises OldapErrorUpdateFailed: If the SHACL and OWL updates do not reflect the expected
            modifications after a successful attempt.
        """
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        logger = logging.getLogger(__name__)
        logger.debug(f'Updating property class {self._property_class_iri.toRdf}')

        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)
        timestamp = Xsd_dateTime.now()

        if (PropClassAttr.CLASS in self.changeset and PropClassAttr.DATATYPE in self.changeset):
            # we change the Property type!!
            if self.in_use:
                raise OldapError("Cannot change Property type while in use")
            if self.changeset[PropClassAttr.DATATYPE].action == Action.DELETE:
                # we change from a literal to a class pointer
                if self.minLength is not None:
                    self.minLength = None
                if self.maxLength is not None:
                    self.maxLength = None
                if self.languageIn is not None:
                    self.languageIn = None
                if self.uniqueLang is not None:
                    self.uniqueLang = None
                if self.pattern is not None:
                    self.pattern = None
                if self.minExclusive is not None:
                    self.minExclusive = None
                if self.minInclusive is not None:
                    self.minInclusive = None
                if self.maxExclusive is not None:
                    self.maxExclusive = None
                if self.maxInclusive is not None:
                    self.maxInclusive = None
                if self.lessThan is not None:
                    self.lessThan = None
                if self.lessThanOrEquals is not None:
                    self.lessThanOrEquals = None
        if PropClassAttr.DATATYPE in self.changeset and self.changeset[PropClassAttr.DATATYPE].action == Action.REPLACE:
            if self.datatype in {XsdDatatypes.int, XsdDatatypes.float, XsdDatatypes.double, XsdDatatypes.decimal,
                                 XsdDatatypes.long, XsdDatatypes.integer, XsdDatatypes.short, XsdDatatypes.byte,
                                 XsdDatatypes.nonNegativeInteger, XsdDatatypes.positiveInteger, XsdDatatypes.unsignedLong,
                                 XsdDatatypes.unsignedInt, XsdDatatypes.unsignedShort, XsdDatatypes.unsignedByte,
                                 XsdDatatypes.date, XsdDatatypes.dateTime, XsdDatatypes.dateTimeStamp, XsdDatatypes.time, XsdDatatypes.gYearMonth,
                                 XsdDatatypes.gYear}:
                # numeric literal datatypes, delete string restrictions
                if self.minLength is not None:
                    self.minLength = None
                if self.maxLength is not None:
                    self.maxLength = None
                if self.uniqueLang is not None:
                    self.uniqueLang = None
                if self.pattern is not None:
                    self.pattern = None
            elif self.datatype in {XsdDatatypes.langString, XsdDatatypes.string, XsdDatatypes.ID, XsdDatatypes.NCName,
                                   XsdDatatypes.NMTOKEN, XsdDatatypes.anyURI, XsdDatatypes.QName, XsdDatatypes.token}:
                # string literal datatypes, delete all numeric restrictions
                if self.minInclusive is not None:
                    self.minInclusive = None
                if self.maxInclusive is not None:
                    self.maxInclusive = None
                if self.minExclusive is not None:
                    self.minExclusive = None
                if self.maxExclusive is not None:
                    self.maxExclusive = None
                if self.lessThan is not None:
                    self.lessThan = None
                if self.lessThanOrEquals is not None:
                    self.lessThanOrEquals = None

        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        self._con.transaction_start()

        sparql += self.update_shacl(owlclass_iri=self._inResourceClass,
                                    timestamp=timestamp)

        sparql += " ;\n"
        sparql += self.update_owl(owlclass_iri=self._inResourceClass)
        try:
            self._con.transaction_update(sparql)
        except OldapError as e:
            self._con.transaction_abort()
            raise

        try:
            modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
        except OldapError as e:
            self._con.transaction_abort()
            raise

        if modtime_shacl == timestamp:
            self._con.transaction_commit()
        else:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Update RDF of "{self._property_class_iri}" didn\'t work: shacl={modtime_shacl} timestamp={timestamp}')

        self._modified = timestamp
        self._contributor = self._con.userIri
        for prop, change in self._changeset.items():
            if change.action == Action.MODIFY:
                self._attributes[prop].clear_changeset()
        self._changeset = {}
        cache = CacheSingletonRedis()
        cache.set(self._property_class_iri, self)

    def delete_shacl(self, *,
                     indent: int = 0, indent_inc: int = 4) -> str:
        #
        # TODO: Test here if property is in use
        #

        sparql_list = []
        if self.inResourceClass:
            shacl_node = self.inResourceClass
        else:
            shacl_node = self._property_class_iri
        sparql = textwrap.dedent(f"""
        WITH {self._graph}:shacl
        DELETE {{
            ?z rdf:first ?head ;
               rdf:rest ?tail .
        }}
        WHERE {{
            {shacl_node}Shape sh:property ?prop .
            ?prop sh:path {self._property_class_iri} .
            ?prop ?listprop ?list .
            ?list rdf:rest* ?z .
            ?z rdf:first ?head ;
               rdf:rest ?tail .
            {shacl_node}Shape dcterms:modified ?modified .
            FILTER(?modified = {self._modified.toRdf})
        }}
        """)
        sparql_list.append(sparql)

        sparql = textwrap.dedent(f"""
        DELETE {{
            ?prop ?listprop ?list .
            ?z rdf:first ?head ;
            rdf:rest ?tail .
        }}
        WHERE {{
            {shacl_node}Shape sh:property ?prop .
            ?prop sh:path {self._property_class_iri} .
            ?prop ?listprop ?list .
            ?list rdf:rest* ?z .
            ?z rdf:first ?head ;
               rdf:rest ?tail .
            {shacl_node}Shape dcterms:modified ?modified .
            FILTER(?modified = {self._modified.toRdf})
        }}
        """)
        sparql_list.append(sparql)
        # blank = ''
        # sparql = f'#\n# Delete {self._property_class_iri} from shacl\n#\n'
        # #
        # # First we delete all list (sh:languageIn/sh:in restrictions) if existing
        # #
        # sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:shacl\n'
        # sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
        # sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
        # sparql += f'{blank:{indent * indent_inc}}}}'
        # sparql += f'{blank:{indent * indent_inc}}WHERE{{\n'
        # if owlclass_iri is not None:
        #     sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        #     sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:path {self._property_class_iri} .\n'
        # else:
        #     sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri}Shape as ?propnode)\n'
        # #sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:languageIn ?list .\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?listprop ?list .\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}?list rdf:rest* ?z .\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
        # sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode dcterms:modified ?modified .\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        # sparql += f'{blank:{indent * indent_inc}}}}'

        # sparql = ''
        #
        # Now we delete the remaining triples
        #
        if self.inResourceClass:  # it's a property in a resource definition...
            sparql = textwrap.dedent(f"""
            WITH {self._graph}:shacl
            DELETE {{
                {self.inResourceClass}Shape sh:property ?prop .
                ?prop ?p ?o .
            }}
            WHERE {{
                {self.inResourceClass}Shape sh:property ?prop .
                ?prop sh:path {self._property_class_iri} .
                ?prop ?p ?o .
            }}
            """)
        else:  # it's an annotation resource
            sparql = textwrap.dedent(f"""
            WITH {self._graph}:shacl
            DELETE {{
                {self._property_class_iri}Shape ?p ?o .
                ?prop ?prop_p ?prop_o
            }}
            WHERE {{
                OPTIONAL {{
                    {self._property_class_iri}Shape ?p ?o .
                    {self._property_class_iri}Shape dcterms:modified ?modified .
                    FILTER(?modified = {self._modified.toRdf})
                }}
                OPTIONAL {{
                    {self._property_class_iri}Shape sh:property ?prop .
                    ?prop ?prop_p ?prop_o .
                }}
                {self._property_class_iri}Shape dcterms:modified ?modified .
            }}
            """)
        # sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:shacl\n'
        # sparql += f'{blank:{indent * indent_inc}}DELETE{{\n'
        # if owlclass_iri is not None:
        #     sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v\n'
        # sparql += f'{blank:{indent * indent_inc}}}}\n'
        # sparql += f'{blank:{indent * indent_inc}}WHERE{{\n'
        # if owlclass_iri is not None:
        #     sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        #     sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:path {self._property_class_iri} .\n'
        # else:
        #     sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri}Shape as ?propnode)\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode dcterms:modified ?modified .\n'
        # sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        # sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def delete_owl_subclass_str(self, *,
                                owlclass_iri: Xsd_QName,
                                indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri.toRdf} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri.toRdf} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode owl:onProperty {self._property_class_iri.toRdf} .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def delete_owl(self, *,
                   indent: int = 0, indent_inc: int = 4) -> str:

        sparql = textwrap.dedent(f"""
        WITH {self._graph}:shacl
        DELETE {{
            {self._property_class_iri} ?pp ?oo .
            ?s ?p {self._property_class_iri} .
        }}
        WHERE {{
            {{
                {self._property_class_iri} ?pp ?oo .
            }}
            UNION
            {{
                ?s ?p {self._property_class_iri} .
            }}
        }}
        """)

        owlclass_iri = self._inResourceClass
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
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        # if owlclass_iri is not None:
        #     sparql = self.delete_owl_subclass_str(owlclass_iri=owlclass_iri)
        #     sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def delete(self) -> None:
        """
        Delete the current property from the triplestore, ensuring proper permissions and transactional
        integrity. This method validates the user's permissions prior to performing a SPARQL update for
        deleting SHACL and OWL properties. It handles potential errors encountered during the deletion
        process and interacts with a Redis cache to ensure proper state management after deletion.

        :raises OldapErrorNoPermission: If the logged-in user lacks sufficient permissions.
        :raises OldapErrorUpdateFailed: If the deletion process fails due to modifications detected.
        :raises OldapError: Generic error indicating an issue when updating data in the triple store.
        :return: None
        """
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        context = Context(name=self._con.context_name)


        sparql_shacl = context.sparql_context
        sparql_shacl += self.delete_shacl()

        query = context.sparql_context
        query += textwrap.dedent(f"""
        ASK {{
            GRAPH test:shacl {{
                ?shape sh:property ?prop .
                ?prop sh:path {self._property_class_iri} .
            }}
        }}
        """)

        sparql_onto = context.sparql_context
        sparql_onto += self.delete_owl()

        self.__from_triplestore = False
        self._con.transaction_start()

        try:
            modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
        except OldapError as e:
            self._con.transaction_abort()
            raise

        #
        # delete SHACL data of property
        #
        self.safe_update(sparql_shacl)

        #
        # test if property is used in another shape. If so don't delete the OWL in onto! Otherwise delete
        # the onto data
        #
        result = self.safe_query(query)
        if not bool(result['boolean']):
            self._con.transaction_update(sparql_onto)  # not used, delete onto

        if modtime_shacl != self.modified:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed("Deleting Property failed")
        else:
            self._con.transaction_commit()
        cache = CacheSingletonRedis()
        cache.delete(self._property_class_iri)

