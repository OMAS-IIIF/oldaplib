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
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pprint import pprint
from typing import Callable, Self, Any

from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.oldaplogging import get_logger
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
from oldaplib.src.helpers.tools import RdfModifyItem, RdfModifyProp
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.xsd.xsd_string import Xsd_string

PropTypes = Iri | Xsd_QName | OwlPropertyType | XsdDatatypes | LangString | Xsd_string | Xsd_integer | Xsd_boolean | LanguageIn | XsdSet | Numeric | None
PropClassAttrContainer = dict[PropClassAttr, PropTypes]
Attributes = dict[Xsd_QName, PropTypes]

@dataclass
@serializer
class HasPropertyData:
    refprop: Xsd_QName | None = None
    minCount: Xsd_integer | None = None
    maxCount: Xsd_integer | None = None
    order: Xsd_decimal | None = None
    group: Xsd_QName | None = None

    def create_shacl(self, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        if self.minCount is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:minCount {self.minCount.toRdf}'
        if self.maxCount is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:maxCount {self.maxCount.toRdf}'
        if self.order is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:order {self.order.toRdf}'
        if self.group is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:group {self.group.toRdf}'
        return sparql

    def create_owl(self, indent: int = 0, indent_inc: int = 4):
        def create_owl(self, indent: int = 0, indent_inc: int = 4):
            blank = ''
            sparql = ''

            if self.minCount and self.maxCount and self.minCount == self.maxCount:
                tmp = Xsd_nonNegativeInteger(self.minCount)  # Convert to nonNegativeInteger
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:qualifiedCardinality {tmp.toRdf}'
            else:
                if self.minCount:
                    tmp = Xsd_nonNegativeInteger(self.minCount)
                    sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:minQualifiedCardinality {tmp.toRdf}'
                if self.maxCount:
                    tmp = Xsd_nonNegativeInteger(self.maxCount)
                    sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:maxQualifiedCardinality {tmp.toRdf}'
            return sparql

#@strict
@serializer
class PropertyClass(Model, Notify):
    """
    This class represents a property as utilized within the context of OMASlib. Properties in this
    framework are categorized into two main types:

    - **External properties**: These are properties defined outside a specific resource class and
      are designed to be reusable across multiple resources. In SHACL, they correspond to instances
      of "sh:PropertyShape".
    - **Internal or exclusive properties**: These are properties defined as blank nodes within
      the resource class definition. A "sh:property" predicate refers to the blank node that specifies
      the property. Internal properties are resource-specific and cannot be reused across different
      resources.

    **Note**: External properties must be defined and instantiated before being referenced as
    properties within a resource definition. When referencing external properties, their QName
    should be used.

    :ivar subPropertyOf: Specifies the super-property of the property represented by this instance.
    :type subPropertyOf: Any
    :ivar type: The type of the property (e.g., data or object property).
    :type type: Any
    :ivar toClass: Points to the associated resource class (for object property definitions).
    :type toClass: Any
    :ivar datatype: Defines the datatype of the property for data properties.
    :type datatype: Any
    :ivar name: The name of the property.
    :type name: Any
    :ivar description: A textual description of the property.
    :type description: Any
    :ivar languageIn: Restrictions on languages if the datatype is language-sensitive.
    :type languageIn: Any
    :ivar uniqueLang: Indicates whether only unique languages are allowed for the property.
    :type uniqueLang: Any
    :ivar inSet: Provides a set of restricted allowed values for the property.
    :type inSet: Any
    :ivar minCount: Specifies the minimum number of occurrences allowed for the property.
    :type minCount: Any
    :ivar maxCount: Specifies the maximum number of occurrences allowed for the property.
    :type maxCount: Any
    :ivar pattern: A regular expression pattern the property value must conform to.
    :type pattern: Any
    :ivar minExclusive: Restricts the property value to be strictly greater than this value.
    :type minExclusive: Any
    :ivar maxExclusive: Restricts the property value to be strictly less than this value.
    :type maxExclusive: Any
    :ivar minInclusive: Restricts the property value to be greater than or equal to this value.
    :type minInclusive: Any
    :ivar maxInclusive: Restricts the property value to be less than or equal to this value.
    :type maxInclusive: Any
    :ivar minLength: Specifies the minimal length for the property value (for strings, etc.).
    :type minLength: Any
    :ivar maxLength: Specifies the maximum length for the property value (for strings, etc.).
    :type maxLength: Any
    :ivar lessThan: Indicates the property must have smaller values compared to another property.
    :type lessThan: Any
    :ivar lessThanOrEqual: Indicates the property must have values less than or equal to another property.
    :type lessThanOrEqual: Any
    """
    _graph: Xsd_NCName
    _projectShortName: Xsd_NCName
    _projectIri: Iri
    _property_class_iri: Xsd_QName | None
    __statementProperty: Xsd_boolean
    _externalOntology: Xsd_boolean
    _internal: Xsd_QName | None
    _force_external: bool
    #_attributes: PropClassAttrContainer
    _test_in_use: bool
    _notifier: Callable[[type], None] | None

    #
    # The following attributes of this class cannot be set explicitely by the used
    # They are automatically managed by the OMAS system
    #
    __version: SemanticVersion
    __from_triplestore: bool

    __slots__ = ('subPropertyOf', 'type', 'toClass', 'datatype', 'name', 'description', 'languageIn', 'uniqueLang',
                 'inSet', 'minCount', 'maxCount', 'pattern',
                 'minExclusive', 'maxExclusive', 'minInclusive', 'maxInclusive', 'minLength', 'maxLength',
                 'lessThan', 'lessThanOrEqual', 'inverseOf', 'equivalentProperty')


    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str | None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 project: Project | Iri | Xsd_NCName | str,
                 property_class_iri: Xsd_QName | str | None = None,
                 notifier: Callable[[PropClassAttr], None] | None = None,
                 notify_data: PropClassAttr | None = None,
                 _externalOntology: bool | Xsd_boolean = False,
                 _internal: Xsd_QName | None = None,  # DO NOT USE!! Only for serialization!
                 _force_external: bool | None = None,  # DO NOT USE!! Only for serialization!
                 _from_triplestore: bool = False,  # DO NOT USE!! Only for serialization!
                 validate: bool = False,
                 **kwargs):
        """
        Defines the constructor for the PropertyClass. This class is used to define
        properties in a given project context. Properties can point to resources,
        supporting restrictions such as "inSet" for valid resource IRIs. Furthermore,
        this class ensures consistency in validation, datatype restrictions, and
        relationships with other project attributes.

        :param con: Connection instance to a database or triplestore
        :type con: IConnection
        :param creator: Creator's IRI or string, defaults to None. [internal use only].
        :type creator: Iri | str | None
        :param created: Date and time of creation, defaults to None. [internal use only].
        :type created: Xsd_dateTime | datetime | str | None
        :param contributor: IRI of the last contributor, defaults to None. [internal use only].
        :type contributor: Iri | None
        :param modified: Date and time of the last modification, defaults to None. [internal use only].
        :type modified: Xsd_dateTime | datetime | str | None
        :param project: Project to which the property belongs; can be a Project object,
            IRI, QName, or string representation.
        :type project: Project | Iri | Xsd_NCName | str
        :param property_class_iri: IRI of the property class; can be a full IRI or a QName,
            optional.
        :type property_class_iri: Iri | str | None
        :param notifier: Function or method used internally as callback for notifications, optional.
        :type notifier: Callable[[PropClassAttr], None] | None
        :param notify_data: Data or attribute passed to the notifier function, optional.
        :type notify_data: PropClassAttr | None
        :param _statementProperty: Boolean indicating if the property is a statement-property
            (used for RDF*star statements).
        :type _statementProperty: bool
        :param _externalOntology: Boolean indicating whether this property comes from an
            external ontology (false by default).
        :type _externalOntology: bool
        :param validate: Boolean that determines whether validation is active.
        :type validate: bool
        :param kwargs: Arbitrary additional named arguments that might be used
            for attribute settings.

        :raises OldapErrorInconsistency: If a link property is created with invalid or
            unsupported restrictions.
        :raises OldapErrorValue: If certain invalid combinations of restrictions, datatypes,
            or prefixes are found during property creation.
        """
        Model.__init__(self,
                       connection=con,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified,
                       validate=validate)
        Notify.__init__(self, notifier, notify_data)

        self._externalOntology = _externalOntology if isinstance(_externalOntology, Xsd_boolean) else Xsd_boolean(_externalOntology, validate=True)
        if self._externalOntology:
            self._force_external = True
        if not isinstance(project, Project):
            if not isinstance(project, (Iri, Xsd_NCName)):
                project = IriOrNCName(project, validate=validate)
            project = Project.read(self._con, project)
        self._projectShortName = project.projectShortName
        self._projectIri = project.projectIri
        context = Context(name=self._con.context_name)
        context[self._projectShortName] = project.namespaceIri
        context.use(self._projectShortName)
        self._graph = self._projectShortName

        self._property_class_iri = Xsd_QName(property_class_iri, validate=validate) if property_class_iri else None
        datatype = kwargs.get('datatype', None)
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
            if self._attributes.get(PropClassAttr.DATATYPE) is None:
                self._attributes[PropClassAttr.DATATYPE] = XsdDatatypes.langString
            elif self._attributes[PropClassAttr.DATATYPE] != XsdDatatypes.langString:
                raise OldapErrorValue(f'Using restriction LANGUAGE_IN requires DATATYPE "rdf:langString", not "{self._attributes[PropClassAttr.DATATYPE].value}"')
        if self._attributes.get(PropClassAttr.DATATYPE) is not None and self._attributes.get(PropClassAttr.CLASS) is not None:
            raise OldapErrorInconsistency(f'It\'s not possible to use both DATATYPE="{self._attributes[PropClassAttr.DATATYPE]}" and CLASS={self._attributes[PropClassAttr.CLASS]} restrictions.')

        if not self._attributes.get(PropClassAttr.TYPE):
            self._attributes[PropClassAttr.TYPE] = ObservableSet(notifier=self.notifier, notify_data=PropClassAttr.TYPE)

        #
        # process the statement property stuff
        #
        if OwlPropertyType.StatementProperty in self._attributes[PropClassAttr.TYPE]:
            self.__statementProperty = Xsd_boolean(True)
        else:
            self.__statementProperty = Xsd_boolean(False)

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
        self._internal = _internal
        self._force_external = _force_external
        if self._externalOntology:  # a property from an external ontology must be a standalone property!!
            self._force_external = True
        self.__version = SemanticVersion()
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
            **({'_internal': self._internal} if self._internal else {}),
            **({'_force_external': self._force_external} if self._force_external else {}),
            **({'_externalOntology': self._externalOntology} if self._externalOntology else {}),
            #**({'__statementProperty': self.__statementProperty} if self.__statementProperty else {}),
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
        instance.__statementProperty = deepcopy(self.__statementProperty, memo)
        instance._externalOntology = deepcopy(self._externalOntology, memo)
        instance._attributes = deepcopy(self._attributes, memo)
        instance._changset = deepcopy(self._changeset, memo)
        # Copy remaining PropertyClass attributes
        instance._graph = deepcopy(self._graph, memo)
        instance._projectShortName = deepcopy(self._projectShortName, memo)
        instance._projectIri = deepcopy(self._projectIri, memo)
        instance._property_class_iri = deepcopy(self._property_class_iri, memo)
        instance._internal = deepcopy(self._internal, memo)
        instance._force_external = self._force_external
        instance._test_in_use = self._test_in_use
        instance.__from_triplestore = self.__from_triplestore
        instance.__version = deepcopy(self.__version)
        return instance

    def __len__(self) -> int:
        return len(self._attributes)

    def __str__(self) -> str:
        propstr = f'Property: {str(self._property_class_iri)};'
        for attr, value in self._attributes.items():
            propstr += f' {attr.value}: {value};'
        propstr += f' internal: {self._internal};'
        return propstr

    @property
    def projectShortName(self) -> Xsd_NCName:
        return self._projectShortName

    @property
    def projectIri(self) -> Iri:
        return self._projectIri

    @property
    def property_class_iri(self) -> Xsd_QName:
        """
        Return the Iri identifying the property
        :return: Iri identifying the property
        :rtype: Iri
        """
        return self._property_class_iri

    @property
    def version(self) -> SemanticVersion:
        """
        Return the version
        :return: Version
        :rtype: SemanticVersion
        """
        return self.__version

    @property
    def internal(self) -> Xsd_QName | None:
        """
        Return the Iri of the ResourceClass, if the property is internal to a ResourceClass.
        If it is a standalone property, return None
        :return: Iri of associated ResourceClass or None
        :rtype: Iri | None
        """
        return self._internal

    # @property
    # def statementProperty(self) -> Xsd_boolean:
    #     """
    #     Return the statementProperty
    #     :return: statementProperty
    #     :rtype: bool
    #     """
    #     return self.__statementProperty

    @property
    def externalOntology(self) -> Xsd_boolean:
        """
        Return the externalOntology
        :return: externalOntology
        :rtype: bool
        """
        return self._externalOntology

    def force_external(self) -> None:
        """
        Ensures that the property is created as a standalone property not tied to any resource.
        This method must be invoked right after the property's constructor is called.

        :return: None
        """
        self._force_external = True

    @property
    def from_triplestore(self) -> bool:
        """
        Indicates if the `PropertyClass` instance was instantiated via the `read()`-classmethod.

        This property identifies whether the object was created by reading from a triple store or
        through the standard Python constructor.

        :return: True if the object was created using the `read()` method; False otherwise.
        :rtype: bool
        """
        """
        Returns True if the PropertyClass instance was created by the `read()`-classmethod. If the property
        has been created using the Python constructor.
        :return: True if read from triple store, otherwise False
        :rtype: bool
        """
        return self.__from_triplestore

    def undo(self, attr: PropClassAttr | None = None) -> None:
        """
        Undo's all changes to the property
        :param attr: The attribute
        :return: None
        """
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
        """
        INTERNAL USE ONLY! Overrides the method _notifier from the Model class.
        :param attr: The attribute
        :return: None
        """
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
        """
        Checks if the property is already in use. This is determined by querying
        the associated context to check if there are existing instances using
        this property. If the property is in use, modifications to its
        attributes may lead to unintended behaviors or errors.

        :return: True if the property is currently in use, otherwise False
        :rtype: bool
        :raises OlapError: Internal error
        """
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?rinstances) as ?nrinstances)
        WHERE {{
            ?rinstances {self._property_class_iri.toRdf} ?value
        }} LIMIT 2
        """
        jsonres = self._con.query(query)
        res = QueryProcessor(context, jsonres)
        if len(res) != 1:
            raise OldapError('Internal Error in "propertyClass.in_use"')
        for r in res:
            if r['nrinstances'] > 0:
                return True
            else:
                return False

    @staticmethod
    def process_triple(r: RowType, attributes: Attributes, propiri: Xsd_QName | None = None) -> None:
        """
        INTERNAL USE ONLY! Used for processing triple while rreading a property.
        :param r:
        :param attributes:
        :param propiri:
        :return: None
        """
        attriri = r['attriri']
        if r['attriri'].fragment == 'languageIn':
            if attributes.get(attriri) is None:
                attributes[attriri] = LanguageIn()
            attributes[attriri].add(r['oo'])
        elif r['attriri'].fragment == 'in':
            if attributes.get(attriri) is None:
                attributes[attriri] = XsdSet()
            attributes[attriri].add(r['oo'])
        elif r['attriri'].fragment == 'or':
            return  # TODO: ignore sh:or for the moment... It's in SHACL, but we do not yet support it
        else:
            if isinstance(r['value'], Xsd_string) and r['value'].lang is not None:
                if attributes.get(attriri) is None:
                    attributes[attriri] = LangString()
                try:
                    attributes[attriri].add(r['value'])
                except AttributeError as err:
                    raise OldapError(f'Invalid value for attribute {attriri}: {err}.')
            else:
                if attributes.get(attriri) is not None:
                    raise OldapError(f'Property ({propiri}) attribute "{attriri}" already defined (value="{r['value']}", type="{type(r['value']).__name__}").')
                attributes[attriri] = r['value']

    @staticmethod
    def __query_shacl(con: IConnection, graph: Xsd_NCName, property_class_iri: Xsd_QName) -> Attributes:
        context = Context(name=con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT ?attriri ?value ?oo
        FROM {graph}:shacl
        FROM shared:shacl
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
            raise OldapErrorNotFound(f'Property "{property_class_iri}" not found.')
        attributes: Attributes = {}
        for r in res:
            PropertyClass.process_triple(r, attributes, property_class_iri)
        return attributes

    def parse_shacl(self, attributes: Attributes) -> HasPropertyData | None:
        """
        Read the SHACL of a non-exclusive (shared) property (that is a sh:PropertyNode definition)
        :return:
        """
        #
        # Create a set of all PropertyClassProp-strings, e.g. {"sh:path", "sh:datatype" etc.}
        #
        refprop: Xsd_QName | None = None
        minCount: Xsd_integer | None = None
        maxCount: Xsd_integer | None = None
        order: Xsd_decimal | None = None
        group: Xsd_QName | None = None
        nodeKind: Xsd_QName | None = None
        propkeys = {Xsd_QName(x.value) for x in PropClassAttr}
        for key, val in attributes.items():
            if key == 'rdf:type':
                if val != 'sh:PropertyShape':
                    raise OldapError(f'Inconsistency, expected "sh:PropertyType", got "{val}".')
                continue
            elif key == 'sh:nodeKind':
                nodeKind = val
                continue
            elif key == 'sh:path':
                if isinstance(val, Xsd_QName):
                    self._property_class_iri = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "sh:path" of "{self._property_class_iri}" ->"{val}" (type={type(val).__name__}).')
            elif key == 'schema:version':
                if isinstance(val, Xsd_string):
                    self.__version = SemanticVersion.fromString(str(val))
                else:
                    raise OldapError(f'Inconsistency in SHACL "schema:version (type={type(val)})"')
            elif key == 'dcterms:creator':
                if isinstance(val, Iri):
                    self._creator = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:creator (type={type(val)})"')
            elif key == 'dcterms:created':
                if isinstance(val, Xsd_dateTime):
                    self._created = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:created (type={type(val)})"')
            elif key == 'dcterms:contributor':
                if isinstance(val, Iri):
                    self._contributor = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:contributor (type={type(val)})"')
            elif key == 'dcterms:modified':
                if isinstance(val, Xsd_dateTime):
                    self._modified = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "dcterms:modified (type={type(val)})"')
            elif key == 'oldap:statementProperty':
                if isinstance(val, Xsd_boolean):
                    self.__statementProperty = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "oldap:statementProperty (type={type(val)})"')
            elif key == 'oldap:externalOntology':
                if isinstance(val, Xsd_boolean):
                    self._externalOntology = val
                else:
                    raise OldapError(f'Inconsistency in SHACL "oldap:externalOntology (type={type(val)}"')
            elif key == 'sh:node':
                if str(val).endswith("Shape"):
                    refprop = Xsd_QName(str(val)[:-5], validate=False)
                else:
                    refprop = val
            elif key == 'sh:minCount':
                minCount = val
            elif key == 'sh:maxCount':
                maxCount = val
            elif key == 'sh:order':
                order = val
            elif key == 'sh:group':
                group = val
            elif key in propkeys:
                attr = PropClassAttr.from_value(key)
                if not attr.in_shacl:
                    continue
                if attr.datatype == Numeric:
                    if not isinstance(val, (Xsd_integer, Xsd_float)):
                        raise OldapErrorInconsistency(f'SHACL inconsistency: "{attr.value}" expects a "Xsd:integer" or "Xsd:float", but got "{type(val).__name__}".')
                    self._attributes[attr] = val
                else:
                    self._attributes[attr] = attr.datatype(val)

        if refprop:
            return HasPropertyData(refprop=refprop,
                                   minCount=minCount,
                                   maxCount=maxCount,
                                   order=order,
                                   group=group)

        if self._attributes.get(PropClassAttr.CLASS) is not None:
            self._attributes[PropClassAttr.TYPE].add(OwlPropertyType.OwlObjectProperty)
            dt = self._attributes.get(PropClassAttr.DATATYPE)
            if dt and (dt != XsdDatatypes.anyURI and dt != XsdDatatypes.QName):
                raise OldapError(f'Datatype "{dt}" not valid for OwlObjectProperty')
        else:
            if nodeKind in {Xsd_QName('sh:IRI'), Xsd_QName('sh:BlankNode'), Xsd_QName('sh:BlankNodeOrIRI')}:
                self._attributes[PropClassAttr.TYPE].add(OwlPropertyType.OwlObjectProperty)
            else:
                self._attributes[PropClassAttr.TYPE].add(OwlPropertyType.OwlDataProperty)
        #
        # update all notifiers of properties
        #
        self.update_notifier()

        self.__from_triplestore = True
        return HasPropertyData(refprop, minCount, maxCount, order, group)

    def read_owl(self) -> None:
        if self._externalOntology:
            return
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
        datatype = None
        to_node_iri = None
        for r in res:
            attr = r['p']
            obj = r['o']
            match attr:
                case 'rdf:type':
                    try:
                        # If obj is already a member, keep it; otherwise look it up by value
                        prop_type = obj if isinstance(obj, OwlPropertyType) else OwlPropertyType(obj)
                    except ValueError as e:
                        raise OldapErrorNotFound(f'Unknown owl:Property type "{obj}"') from e
                    self._attributes[PropClassAttr.TYPE].add(prop_type)
                case 'owl:subPropertyOf':
                    self._attributes[PropClassAttr.SUBPROPERTY_OF] = obj
                case 'rdfs:range':
                    if obj.prefix == 'xsd' or obj.prefix == 'rdf':
                        datatype = obj
                    else:
                        to_node_iri = obj
                case 'rdfs:domain':
                    self._internal = obj
                case 'dcterms:creator':
                    if self._creator != obj:
                        raise OldapError(f'Inconsistency between SHACL and OWL: creator "{self._creator}" vs "{obj}" for property "{self._property_class_iri}".')
                case 'dcterms:created':
                    dt = obj
                    if self._created != dt:
                        raise OldapError(f'Inconsistency between SHACL and OWL: created "{self._created}" vs "{dt}" for property "{self._property_class_iri}".')
                case 'dcterms:contributor':
                    if self._creator != obj:
                        raise OldapError(f'Inconsistency between SHACL and OWL: contributor "{self._contributor}" vs "{obj}" for property "{self._property_class_iri}".')
                case 'dcterms:modified':
                    dt = obj
                    if self._modified != dt:
                        raise OldapError(f'Inconsistency between SHACL and OWL: created "{self._modified}" vs "{dt}" for property "{self._property_class_iri}".')
                case _:
                    if attr in propkeys:
                        pcattr = PropClassAttr.from_value(attr)
                        if pcattr.in_owl:
                            self._attributes[pcattr] = pcattr.datatype(obj)
        #
        # Consistency checks
        #
        if self.__statementProperty:
            if OwlPropertyType.StatementProperty not in self._attributes.get(PropClassAttr.TYPE):
                raise OldapErrorInconsistency(f'Property "{self._property_class_iri}" has SHACL oldap:statementProperty, but missing rdf:type rdf:Property.')
        else:
            if OwlPropertyType.StatementProperty in self._attributes.get(PropClassAttr.TYPE):
                raise OldapErrorInconsistency(f'Property "{self._property_class_iri}" has no SHACL oldap:statementProperty, but a rdf:type rdf:Property.')
        if OwlPropertyType.OwlDataProperty in self._attributes[PropClassAttr.TYPE]:
            if not datatype:
                raise OldapError(f'OwlDataProperty "{self._property_class_iri}" has no rdfs:range datatype defined!')
            if datatype != self._attributes.get(PropClassAttr.DATATYPE).value:
                raise OldapError(
                    f'Property "{self._property_class_iri}" has inconsistent datatype definitions: OWL: "{datatype}" vs. SHACL: "{self._attributes[PropClassAttr.DATATYPE].value}"')
        if OwlPropertyType.OwlObjectProperty in self._attributes[PropClassAttr.TYPE]:
            if not to_node_iri:
                raise OldapError(f'OwlObjectProperty "{self._property_class_iri}" has no rdfs:range resource class defined!')
            if to_node_iri != self._attributes.get(PropClassAttr.CLASS):
                raise OldapError(
                    f'Property "{self._property_class_iri}" has inconsistent object type definition: OWL: "{to_node_iri}" vs. SHACL: "{self._attributes.get(PropClassAttr.CLASS)}".')

    @classmethod
    def read(cls, con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             property_class_iri: Xsd_QName | str,
             ignore_cache: bool = False) -> Self:
        """
        Reads a property from the triple store.

        This method initializes or retrieves an instance of a property class
        from the triple store. It utilizes caching mechanisms if applicable and may
        bypass the cache based on the input parameters.

        :param con: Instance of a valid connection to the triple store.
        :type con: IConnection
        :param project: Project instance, project IRI, project shortname, or equivalent identifier.
        :type project: Project | Iri | Xsd_NCName | str
        :param property_class_iri: The IRI identifying the property class.
        :type property_class_iri: Iri | str
        :param ignore_cache: Determines if the cached data is ignored
                             and the property is read directly from the triple store.
        :type ignore_cache: bool
        :return: Instance of the appropriate property class.
        :rtype: Self
        :raises OldapError: Generic error indicating an issue when reading from the triple store.
        :raises OldapErrorInconsistency: Inconsistency between SHACL and OWL.
        """
        logger = get_logger()

        if not isinstance(property_class_iri, Xsd_QName):
            property_class_iri = Xsd_QName(property_class_iri)
        cache = CacheSingletonRedis()
        if not ignore_cache:
            tmp = cache.get(property_class_iri, connection=con)
            if tmp is not None:
                tmp.update_notifier()
                #logger.info(f'Property class "{property_class_iri}" already cached in triple store!')
                return tmp
        property = cls(con=con, project=project, property_class_iri=property_class_iri)
        attributes = PropertyClass.__query_shacl(con, property._graph, property_class_iri)
        property.parse_shacl(attributes=attributes)
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
                            bnode: Xsd_QName | None = None,
                            haspropdata: HasPropertyData | None = None,
                            indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{(indent + 1) * indent_inc}}# >>PropertyClass.property_node_shacl()'
        if bnode:
            sparql += f'\n{blank:{(indent + 1) * indent_inc}} {bnode} sh:path {self._property_class_iri.toRdf}'
        else:
            sparql += f'\n{blank:{(indent + 1) * indent_inc}}sh:path {self._property_class_iri.toRdf}'
        if len(self._attributes) > 0:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}schema:version {self.__version.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {timestamp.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}oldap:statementProperty {self.__statementProperty.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}oldap:externalOntology {self._externalOntology.toRdf}'
        for prop, value in self._attributes.items():
            if not prop.in_shacl:
                continue
            if not value and not isinstance(value, bool):
            #if value is None:
                continue
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{prop.value} {value.toRdf}'
        if haspropdata:
            sparql += haspropdata.create_shacl(indent=indent + 1)
        return sparql

    def create_shacl(self, *,
                     timestamp: Xsd_dateTime,
                     owlclass_iri: Xsd_QName | None = None,
                     haspropdata: HasPropertyData | None = None,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'\n{blank:{indent * indent_inc}}# PropertyClass.create_shacl()'
        if owlclass_iri is None:  # standalone property! Therefor no minCount, maxCount!
            sparql += f'\n{blank:{indent * indent_inc}}{self._property_class_iri}Shape a sh:PropertyShape ;\n'
            sparql += self.property_node_shacl(timestamp=timestamp,
                                               haspropdata=haspropdata,
                                               indent=indent, indent_inc=indent_inc)
        else:
            bnode = Xsd_QName('_:propnode')
            sparql += f'\n{blank:{indent * indent_inc}}{owlclass_iri}Shape sh:property {bnode} .\n'
            sparql += self.property_node_shacl(timestamp=timestamp, bnode=bnode,
                                               haspropdata=haspropdata,
                                               indent=indent, indent_inc=indent_inc)
        sparql += ' .\n'
        return sparql

    def create_owl_part1(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}{self._property_class_iri.toRdf} {PropClassAttr.TYPE.toRdf} {self._attributes[PropClassAttr.TYPE].toRdf}'
        if self._internal:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:domain {self._internal.toRdf}'
        if self._attributes.get(PropClassAttr.TYPE) and  OwlPropertyType.OwlDataProperty in self._attributes[PropClassAttr.TYPE]:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:range {self._attributes[PropClassAttr.DATATYPE].value}'
        elif self._attributes.get(PropClassAttr.TYPE) and OwlPropertyType.OwlObjectProperty in self._attributes[PropClassAttr.TYPE]:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:range {self._attributes[PropClassAttr.CLASS].toRdf}'
        for attr, val in self._attributes.items():
            #attr = PropClassAttr.from_value(key)
            if not attr.in_owl or attr == PropClassAttr.TYPE or val is None:
                continue
            if attr == PropClassAttr.NAME:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:label {val.toRdf}'
            elif attr == PropClassAttr.DESCRIPTION:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:comment {val.toRdf}'
            else:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}{attr.toRdf} {val.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += ' .\n'

        # sparql = f'{blank:{indent * indent_inc}}{self._property_class_iri.toRdf} rdf:type {self._attributes[PropClassAttr.TYPE].toRdf}'
        # if self._attributes.get(PropClassAttr.SUBPROPERTY_OF):
        #     sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:subPropertyOf {self._attributes[PropClassAttr.SUBPROPERTY_OF].toRdf}'
        # if self._internal:
        #     sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:domain {self._internal.toRdf}'
        # if self._attributes.get(PropClassAttr.TYPE) and  OwlPropertyType.OwlDataProperty in self._attributes[PropClassAttr.TYPE]:
        #     sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:range {self._attributes[PropClassAttr.DATATYPE].value}'
        # elif self._attributes.get(PropClassAttr.TYPE) and OwlPropertyType.OwlObjectProperty in self._attributes[PropClassAttr.TYPE]:
        #     sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:range {self._attributes[PropClassAttr.CLASS].toRdf}'
        # sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        # sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:created {timestamp.toRdf}'
        # sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        # sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        # if self.name:
        #     sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:label {self.name.toRdf}'
        # if self.description:
        #     sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}rdfs:comment {self.description.toRdf}'
        # sparql += ' .\n'
        return sparql

    def create_owl_part2(self, *,
                         haspropdata: HasPropertyData | None = None,
                         indent: int = 0, indent_inc: int = 4) -> str:
        if not (haspropdata.minCount or haspropdata.maxCount or self._attributes.get(PropClassAttr.DATATYPE) or self._attributes.get(PropClassAttr.CLASS)):
            return ''  # no OWL to be added!
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}[\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:type owl:Restriction ;\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}owl:onProperty {self._property_class_iri.toRdf}'

        if haspropdata.minCount and haspropdata.maxCount  and haspropdata.minCount == haspropdata.maxCount:
            tmp = Xsd_nonNegativeInteger(haspropdata.minCount)
            sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}owl:qualifiedCardinality {tmp.toRdf}'
        else:
            if haspropdata.minCount:
                tmp = Xsd_nonNegativeInteger(haspropdata.minCount)
                sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}owl:minQualifiedCardinality {tmp.toRdf}'
            if haspropdata.maxCount:
                tmp = Xsd_nonNegativeInteger(haspropdata.maxCount)
                sparql += f' ;\n{blank:{(indent + 1)*indent_inc}}owl:maxQualifiedCardinality {tmp.toRdf}'
        #
        # (NOTE: owl:onClass and owl:onDataRange can be used only in a restriction and are "local" to the use
        # of the property within the given resource. However, rdfs:range is "global" for all use of this property!
        #
        if self._attributes.get(PropClassAttr.DATATYPE) or self._attributes.get(PropClassAttr.CLASS):
            if OwlPropertyType.OwlDataProperty in self._attributes[PropClassAttr.TYPE]:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onDataRange {self._attributes[PropClassAttr.DATATYPE].value}'
            elif OwlPropertyType.OwlObjectProperty in self._attributes[PropClassAttr.TYPE]:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:onClass {self._attributes[PropClassAttr.CLASS]}'
        sparql += f' ;\n{blank:{indent * indent_inc}}]'
        return sparql

    def set_creation_metadata(self, timestamp: Xsd_dateTime):
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.__from_triplestore = True


    def create(self, *,
               haspropdata: HasPropertyData | None = None,
               indent: int = 0, indent_inc: int = 4) -> None:
        """
        Create the triple store data from a newly constructed PropertyClass instance.

        This method constructs the necessary SPARQL statements to insert data into
        triple stores. It ensures proper permissions before proceeding and handles both
        internal and external properties. Conflicts with preexisting data and updates
        are managed through transactions. Metadata is updated upon successful creation,
        and the local cache is refreshed accordingly.

        :param haspropdata: A HasPropertyData instance for internal properties.
                            Defaults to None for external properties.
        :type haspropdata: HasPropertyData | None
        :param indent: Indentation level for formatting SPARQL code [default: 0].
        :type indent: int
        :param indent_inc: Increment for adding additional indentation levels
                           [default: 4].
        :type indent_inc: int
        :return: None

        :raises OldapError: Generic error indicating an issue when creating data in the triple store.
        :raises OldapErrorInconsistency: Inconsistency between SHACL and OWL.
        :raises OldapErrorAlreadyExists: The PropertyClass is already existing.
        """
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
        if self._internal is not None:  # internal property, add minCount, maxCount if defined
            sparql += self.create_shacl(timestamp=timestamp,
                                        owlclass_iri=self._internal,
                                        haspropdata=haspropdata,
                                        indent=2)
        else:  # standalone (reusable) property -> no minCount, maxCount
            sparql += self.create_shacl(timestamp=timestamp,
                                        indent=2)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        if not self._externalOntology:  # project specific property, write also OWL!
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
            sparql += self.create_owl_part1(timestamp=timestamp, indent=2)
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
            print(sparql)
            self._con.transaction_abort()
            raise
        if not self._externalOntology:  # it's a project specific property -> OWL has been written -> check consistency!
            try:
                modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
                modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
            except OldapError as err:
                self._con.transaction_abort()
                raise
            if modtime_shacl == timestamp and modtime_owl == timestamp:
                self._con.transaction_commit()
            else:
                self._con.transaction_abort()
                raise OldapErrorUpdateFailed(f"Update of RDF didn't work!")
        else:
            self._con.transaction_commit()
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
            if self._internal is not None:
                f.write(self.create_shacl(timestamp=timestamp, owlclass_iri=self._internal, indent=2))
            else:
                f.write(self.create_shacl(timestamp=timestamp, indent=2))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

            if not self._externalOntology:  # project specific property, write also OWL!
                f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
                f.write(self.create_owl_part1(timestamp=timestamp, indent=2))
                f.write(f'{blank:{indent * indent_inc}}}}\n')

    def update_shacl(self, *,
                     owlclass_iri: Xsd_QName | None = None,
                     timestamp: Xsd_dateTime,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for prop, change in self._changeset.items():
            sparql = f'#\n# SHACL\n# PrpoertyClass(1): Process "{prop.value}" with Action "{change.action.value}"\n#\n'
            if change.action == Action.MODIFY:
                if prop.datatype == LangString:
                    sparql += self._attributes[prop].update_shacl(graph=self._graph,
                                                                  owlclass_iri=owlclass_iri,
                                                                  prop_iri=self._property_class_iri,
                                                                  attr=prop,
                                                                  modified=self._modified,
                                                                  indent=indent, indent_inc=indent_inc)
                elif prop.datatype == ObservableSet:
                    if prop == PropClassAttr.TYPE:
                        if self._attributes[prop].old_value:
                            added = set(self._attributes[PropClassAttr.TYPE]) - set(self._attributes[prop].old_value)
                        else:
                            added = set(self._attributes[PropClassAttr.TYPE])
                        if OwlPropertyType.StatementProperty in added:
                            self.__statementProperty = Xsd_boolean(True)
                            ele = RdfModifyItem(Xsd_QName('oldap:statementProperty'), Xsd_boolean(False), Xsd_boolean(True))
                            sparql += RdfModifyProp.shacl(action=change.action,
                                                          graph=self._graph,
                                                          owlclass_iri=owlclass_iri,
                                                          pclass_iri=self._property_class_iri,
                                                          ele=ele,
                                                          last_modified=self._modified)
                        if self._attributes[prop].old_value:
                            removed = set(self._attributes[prop].old_value) - set(self._attributes[PropClassAttr.TYPE])
                        else:
                            removed = set()
                        if OwlPropertyType.StatementProperty in removed:
                            self.__statementProperty = Xsd_boolean(False)
                            ele = RdfModifyItem(Xsd_QName('oldap:statementProperty'), Xsd_boolean(True), Xsd_boolean(False))
                            sparql += RdfModifyProp.shacl(action=change.action,
                                                          graph=self._graph,
                                                          owlclass_iri=owlclass_iri,
                                                          pclass_iri=self._property_class_iri,
                                                          ele=ele,
                                                          last_modified=self._modified)
                else:
                    raise OldapError(f'SHACL property {prop.value} should not have update action "MODIFY" ({prop.datatype}).')
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
                    raise OldapError(f'An unexpected Action occured: {change.action} for {prop.value}.')
                ele = RdfModifyItem(prop.value, old_value, new_value)
                if prop.datatype in {XsdSet, LanguageIn}:
                    sparql += RdfModifyProp.replace_rdfset(action=change.action,
                                                           graph=self._graph,
                                                           owlclass_iri=owlclass_iri,
                                                           pclass_iri=self._property_class_iri,
                                                           ele=ele,
                                                           last_modified=self._modified)
                else:
                    sparql += RdfModifyProp.shacl(action=change.action,
                                                  graph=self._graph,
                                                  owlclass_iri=owlclass_iri,
                                                  pclass_iri=self._property_class_iri,
                                                  ele=ele,
                                                  last_modified=self._modified)
                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor in {self._graph}:shacl\n#\n'
        sparql += RdfModifyProp.shacl(action=Action.REPLACE if self._contributor else Action.CREATE,
                                      graph=self._graph,
                                      owlclass_iri=owlclass_iri,
                                      pclass_iri=self._property_class_iri,
                                      ele=RdfModifyItem('dcterms:contributor', f'{self._contributor.toRdf}', f'{self._con.userIri.toRdf}'),
                                      last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified in {self._graph}:shacl\n#\n'
        sparql += RdfModifyProp.shacl(action=Action.REPLACE if self._modified else Action.CREATE,
                                      graph=self._graph,
                                      owlclass_iri=owlclass_iri,
                                      pclass_iri=self._property_class_iri,
                                      ele=RdfModifyItem('dcterms:modified', f'{self._modified.toRdf}', f'{timestamp.toRdf}'),
                                      last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update_owl(self, *,
                   owlclass_iri: Xsd_QName | None = None,
                   timestamp: Xsd_dateTime,
                   indent: int = 0, indent_inc: int = 4) -> str:
        tmp = {x for x in PropClassAttr if x.in_owl and x != PropClassAttr.TYPE}
        owl_propclass_attributes = {PropClassAttr.SUBPROPERTY_OF,  # should be in OWL ontology
                                    PropClassAttr.DATATYPE,  # used for rdfs:range in OWL ontology
                                    PropClassAttr.CLASS} | tmp # used for rdfs:range in OWL ontology
        tmp = {x: x.value.toRdf for x in PropClassAttr if x.in_owl and x != PropClassAttr.TYPE}
        owl_prop = {PropClassAttr.SUBPROPERTY_OF: PropClassAttr.SUBPROPERTY_OF.value,
                    PropClassAttr.DATATYPE: "rdfs:range",
                    PropClassAttr.CLASS: "rdfs:range"} | tmp
        blank = ''
        sparql_list = []
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
                                             last_modified=self._modified,
                                             indent=indent, indent_inc=indent_inc)
                sparql_list.append(sparql)

            if prop == PropClassAttr.DATATYPE or prop == PropClassAttr.CLASS:
                ele: RdfModifyItem
                if self._attributes.get(PropClassAttr.CLASS):
                    ele = RdfModifyItem('rdf:type', 'owl:DatatypeProperty', 'owl:ObjectProperty')
                else:
                    ele = RdfModifyItem('rdf:type', 'owl:ObjectProperty', 'owl:DatatypeProperty')
                sparql = f'#\n# OWL:\n# Correct OWL property type with Action "{change.action.value}\n#\n'
                sparql += RdfModifyProp.onto(action=Action.REPLACE,
                                             graph=self._graph,
                                             owlclass_iri=owlclass_iri,
                                             pclass_iri=self._property_class_iri,
                                             ele=ele,
                                             last_modified=self._modified,
                                             indent=indent, indent_inc=indent_inc)
                sparql_list.append(sparql)
            if prop == PropClassAttr.TYPE:

                sparql = self._attributes[prop].update_sparql(graph=Xsd_QName(str(self._graph), 'onto'),
                                                              subject=self._property_class_iri,
                                                              ignoreitems={OwlPropertyType.OwlDataProperty,OwlPropertyType.OwlObjectProperty},
                                                              field=prop)
                sparql_list.extend(sparql)
            if prop == PropClassAttr.NAME:
                if change.action == Action.CREATE:
                    sparql = self.name.create(graph=Xsd_QName(self._graph, 'onto'),
                                              subject=self._property_class_iri,
                                              field=Xsd_QName('rdfs:label'),
                                              indent=indent, indent_inc=indent_inc)
                    sparql_list.append(sparql)
                if change.action == Action.MODIFY:
                    sparqls = self.name.update(graph=Xsd_QName(self._graph, 'onto'),
                                               subject=self._property_class_iri,
                                               field=Xsd_QName('rdfs:label'),
                                               indent=indent, indent_inc=indent_inc)
                    for sparql in sparqls:
                        sparql_list.append(sparql)
                if change.action == Action.DELETE:
                    sparql = change.old_value.delete(graph=Xsd_QName(self._graph, 'onto'),
                                               subject=self._property_class_iri,
                                               field=Xsd_QName('rdfs:label'),
                                               indent=indent, indent_inc=indent_inc)
                    sparql_list.append(sparql)

            if prop == PropClassAttr.DESCRIPTION:
                if change.action == Action.CREATE:
                    sparql = self.description.create(graph=Xsd_QName(self._graph, 'onto'),
                                                     subject=self._property_class_iri,
                                                     field=Xsd_QName('rdfs:comment'),
                                                     indent=indent, indent_inc=indent_inc)
                    sparql_list.append(sparql)
                if change.action == Action.MODIFY:
                    sparqls = self.description.update(graph=Xsd_QName(self._graph, 'onto'),
                                                      subject=self._property_class_iri,
                                                      field=Xsd_QName('rdfs:comment'),
                                                      indent=indent, indent_inc=indent_inc)
                    for sparql in sparqls:
                        sparql_list.append(sparql)
                if change.action == Action.DELETE:
                    sparql = change.old_value.delete(graph=Xsd_QName(self._graph, 'onto'),
                                                     subject=self._property_class_iri,
                                                     field=Xsd_QName('rdfs:comment'),
                                                     indent=indent, indent_inc=indent_inc)
                    sparql_list.append(sparql)


        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor {self._graph}:onto\n#\n'
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:contributor {self._contributor.toRdf}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:contributor {self._con.userIri.toRdf}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._property_class_iri} AS ?prop)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
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
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
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
                                 XsdDatatypes.dateTime, XsdDatatypes.dateTimeStamp, XsdDatatypes.time, XsdDatatypes.gYearMonth,
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
                if self.lessThanOrEqual is not None:
                    self.lessThanOrEqual = None

        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        self._con.transaction_start()

        sparql += self.update_shacl(owlclass_iri=self._internal,
                                    timestamp=timestamp)

        if not self._externalOntology:  # it's a project specific property, write also OWL!
            sparql += " ;\n"
            sparql += self.update_owl(owlclass_iri=self._internal,
                                      timestamp=timestamp)
        try:
            self._con.transaction_update(sparql)
        except OldapError as e:
            print(sparql)
            self._con.transaction_abort()
            raise

        if not self._externalOntology:
            try:
                modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
                modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
            except OldapError as e:
                self._con.transaction_abort()
                raise

            if modtime_shacl == timestamp and modtime_owl == timestamp:
                self._con.transaction_commit()
            else:
                self._con.transaction_abort()
                raise OldapErrorUpdateFailed(f'Update RDF of "{self._property_class_iri}" didn\'t work: shacl={modtime_shacl} owl={modtime_owl} timestamp={timestamp}')
        else:
            self._con.transaction_commit()

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
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
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
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
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
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        if owlclass_iri is not None:
            sparql = self.delete_owl_subclass_str(owlclass_iri=owlclass_iri)
            sparql_list.append(sparql)

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
        sparql = context.sparql_context

        sparql += self.delete_shacl()
        if not self._externalOntology:  # it's a project specific property, delete also OWL!'
            sparql += ' ;\n'
            sparql += self.delete_owl()

        self.__from_triplestore = False
        self._con.transaction_start()
        self._con.transaction_update(sparql)
        if not self._externalOntology:
            try:
                modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
                modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
            except OldapError as e:
                self._con.transaction_abort()
                raise
            if modtime_shacl is not None or modtime_owl is not None:
                self._con.transaction_abort()
                raise OldapErrorUpdateFailed("Deleting Property failed")
            else:
                self._con.transaction_commit()
        else:
            self._con.transaction_commit()
        cache = CacheSingletonRedis()
        cache.delete(self._property_class_iri)

