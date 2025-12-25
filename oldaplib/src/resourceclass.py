from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pprint import pprint
from typing import Union, List, Dict, Callable, Self, Any, TypeVar

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.enums.haspropertyattr import HasPropertyAttr
from oldaplib.src.globalconfig import GlobalConfig
from oldaplib.src.hasproperty import HasProperty, PropType
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorAlreadyExists, \
    OldapErrorInconsistency, OldapErrorUpdateFailed, \
    OldapErrorValue, OldapErrorNotImplemented, OldapErrorNoPermission, OldapErrorInUse
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.enums.resourceclassattr import ResClassAttribute
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.helpers.tools import RdfModifyRes, RdfModifyItem, lprint
from oldaplib.src.dtypes.bnode import BNode
from oldaplib.src.enums.action import Action
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.context import Context
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.propertyclass import PropertyClass, Attributes, HasPropertyData, PropTypes
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

#
# Datatype definitions
#
RC = TypeVar('RC', bound='ResourceClass')
AttributeTypes = Xsd_QName | LangString | Xsd_boolean | ObservableDict | None
ResourceClassAttributesContainer = Dict[ResClassAttribute, AttributeTypes]
SuperclassParam = Union[Xsd_QName, str, list[Union[Xsd_QName, str]], tuple[Union[Xsd_QName, str], ...] , set[Union[Xsd_QName, str]], None]
AttributeParams = LangString | Xsd_boolean | SuperclassParam


@dataclass
class ResourceClassPropertyChange(AttributeChange):
    test_in_use: bool


#@strict
@serializer
class ResourceClass(Model, Notify):
    """
    Represents a resource class in a semantic model, enabling operations such as
    assignment, addition, and deletion of superclasses, as well as handling
    associated properties and attributes.

    This class provides mechanisms for defining, managing, and customizing superclasses
    and related properties within a resource hierarchy. It integrates with a
    connection object and supports handling validation and notifications for changes.

    :ivar superclass: The list of assigned superclasses for this resource class.
    :type superclass: dict
    :ivar label: Optional label providing a human-readable identifier for the resource.
    :type label: str
    :ivar comment: Optional comment describing the resource class in detail.
    :type comment: str
    :ivar closed: Indicates whether the resource class is closed, i.e., no further
        subclasses or properties can be added.
    :type closed: bool
    """
    _graph: Xsd_NCName
    _project: Project
    _sysproject: Project = None
    _sharedproject: Project = None
    _externalOntology: Xsd_boolean
    _owlclass_iri: Xsd_QName | None
    _attributes: ResourceClassAttributesContainer
    _properties: dict[Xsd_QName, HasProperty]
    __version: SemanticVersion
    __from_triplestore: bool
    _test_in_use: bool

    __slots__ = ['superclass', 'label', 'comment', 'closed']

    def __check(self, sc: Any, validate: bool = False):
        """
        Check if the given superclass is valid and return its IRI and ResourceClass instance. If the namespace
        is not known, it's assumed to be an external resource.

        :param sc: The superclass to check.
        :param validate: Whether to validate the IRI.
        :return: A tuple containing the IRI and ResourceClass instance.
        :raises OldapErrorNotFound: If the superclass is not found.
        :raises OldapErrorValue: If the superclass is not a valid IRI.
        """
        scval = Xsd_QName(sc, validate=validate)
        sucla = None
        if scval:
            match scval.prefix:
                case self._project.projectShortName:
                    sucla = ResourceClass.read(self._con, self._project, scval)
                case 'oldap':
                    sucla = ResourceClass.read(self._con, self._sysproject, scval)
                case 'shared':
                    sucla = ResourceClass.read(self._con, self._sharedproject, scval)
                case _:
                    # external resource not defined in Oldap
                    # -> we can not read it -> we pass None -> no "sh:node" in SHACL!
                    pass
        return scval, sucla

    def assign_superclass(self, superclass: SuperclassParam, validate = False) -> ObservableDict:
        """
        Assigns a superclass or multiple superclasses to an entity, verifying and
        processing them in the process. This method ensures the input is validated
        and appropriately structured within an `ObservableDict`.

        :param superclass: A single superclass or an iterable of superclasses to
            be assigned.
        :param validate: A boolean indicating whether input validation should
            be performed (default is False).
        :return: An ObservableDict containing the processed superclasses, with
            keys as their IRIs and values as the respective processed superclasses.
        :rtype: ObservableDict
        :raises ValueError: If the input is not a valid superclass or iterable of superclasses
        :raises OldapError: If the superclass is not valid or if it is not a valid IRI
        :raises OldapErrorValue: If the superclass is not a valid IRI
        :raises OldapErrorNotValid: If the superclass is not valid
        """
        data = ObservableDict()
        if isinstance(superclass, (list, tuple, set)):
            for sc in superclass:
                if sc is None:
                    continue
                iri, sucla = self.__check(sc, validate=validate)
                data[iri] = sucla
        else:
            iri, sucla = self.__check(superclass, validate=validate)
            data[iri] = sucla
        data.set_on_change(self.__sc_changed)
        return data

    def add_superclasses(self, superclass: SuperclassParam, validate = False):
        """
        Adds one or multiple superclasses to the existing list of superclasses. This method
        will check each provided superclass to ensure it does not already exist in
        the current superclass list. If a superclass is invalid, an appropriate error
        will be raised. After validation, the superclasses are added, and notifications
        are sent to relevant systems.

        :param superclass: A single superclass or a collection (list, tuple, set) of
            superclasses to be added to the current superclass list.
        :type superclass: SuperclassParam
        :param validate: A flag indicating whether to validate the provided superclasses
            during the addition process. Defaults to False.
        :type validate: bool
        :return: None
        :raises OldapErrorAlreadyExists: If a superclass already exists in the current superclass list.
        :raises OldapErrorValue: If a superclass to be added is not a valid Iri (e.g. None).
        :raises OldapError: If an error occurs during the addition process.
        :raises OldapErrorNotValid: If a superclass is not valid
        :raises OldapErrorNotFound: If a superclass is not found.
        """
        if isinstance(superclass, (list, tuple, set)):
            for sc in superclass:
                if sc is None or sc in self._attributes[ResClassAttribute.SUPERCLASS]:
                    continue
                iri, sucla = self.__check(sc, validate=validate)
                self._attributes[ResClassAttribute.SUPERCLASS][iri] = sucla
                self.notify()
        else:
            if superclass in self._attributes[ResClassAttribute.SUPERCLASS]:
                raise OldapErrorAlreadyExists(f'Superclass "{superclass}" already exists in superclass list of {self._owlclass_iri}.')
            iri, sucla = self.__check(superclass, validate=validate)
            self._attributes[ResClassAttribute.SUPERCLASS][iri] = sucla
            self.notify()

    def del_superclasses(self, superclass: SuperclassParam, validate = False):
        """
        Removes one or multiple superclasses from the current superclass list. If the provided
        superclass(es) do not exist in the current list, an exception will be raised. The function
        also allows optional validation of the input values before processing. Notifications
        will be triggered upon successful removal of the superclass or superclasses.

        :param superclass: One or more `superclass` entities to remove. It can be a single
            instance or a collection such as a list, tuple, or set.
        :type superclass: Union[SuperclassParam, List[SuperclassParam], Tuple[SuperclassParam], Set[SuperclassParam]]
        :param validate: Flag indicating whether to validate the provided `superclass` values
            before processing. Defaults to False.
        :type validate: bool
        :return: None
        :raises OldapErrorNotFound: If a superclass to be removed is not found in the current superclass list.
        :raises OldapErrorValue: If a superclass to be removed is not a valid Iri (e.g. None).
        :raises OldapErrorNotValid: If a superclass is not valid.
        :raises OldapError: If the provided `superclass` is not a valid collection.
        """
        if isinstance(superclass, (list, tuple, set)):
            for sc in superclass:
                scIri = Xsd_QName(sc, validate=validate)
                if scIri not in self._attributes[ResClassAttribute.SUPERCLASS]:
                    raise OldapErrorValue(f'Superclass "{scIri}" not found in superclass list')
                del self._attributes[ResClassAttribute.SUPERCLASS][scIri]
                self.notify()
        else:
            superclassIri = Xsd_QName(superclass, validate=validate)
            if superclassIri not in self._attributes[ResClassAttribute.SUPERCLASS]:
                raise OldapErrorValue(f'Superclass "{superclass}" not found in superclass list')
            del self._attributes[ResClassAttribute.SUPERCLASS][superclassIri]
            self.notify()


    def __init__(self, *,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 owlclass_iri: Xsd_QName | str | None = None,
                 hasproperties: List[HasProperty] | None = None,
                 _externalOntology: bool | Xsd_boolean = False,
                 notifier: Callable[[PropClassAttr], None] | None = None,
                 notify_data: PropClassAttr | None = None,
                 creator: Iri | None = None,  # DO NO USE! Only for jsonify!!
                 created: Xsd_dateTime | None = None,  # DO NO USE! Only for jsonify!!
                 contributor: Iri | None = None,  # DO NO USE! Only for jsonify!!
                 modified: Xsd_dateTime | None = None,  # DO NO USE! Only for jsonify!!
                 validate: bool = False,
                 **kwargs):
        """
        Initializes a new instance of the class with mandatory and optional parameters.

        This constructor creates and configures the required context, graph, and necessary
        properties. It sets up the project, defines the owl class IRI, adds the mandatory
        superclass “oldap:Thing” if required, and assigns attributes based on the provided
        parameters. Additional functionality includes handling of external/internal property
        definitions and configuring notifier settings.

        :param con: The connection object to interact with the required system.
        :type con: IConnection
        :param project: The project identifier or object which can be a Project instance, IRI,
            XSD NCName, or string.
        :type project: Project | Iri | Xsd_NCName | str
        :param owlclass_iri: The IRI to define the owl class. It can be IRI type, string,
            or None by default.
        :type owlclass_iri: Iri | str | None
        :param hasproperties: A list of HasProperty objects specifying the properties associated
            with the resource class.
        :type hasproperties: List[HasProperty] | None
        :param notifier: A callable function used for notification purposes. Notifier operates
            on PropClassAttr type objects.
        :type notifier: Callable[[PropClassAttr], None] | None
        :param notify_data: Notification data to be passed with the notifier.
        :type notify_data: PropClassAttr | None
        :param validate: Boolean flag used to enable or disable validation.
        :type validate: bool
        :param kwargs: Arbitrary additional keyword arguments to pass. This can include
            attributes like superclasses or other configurations.
        :type kwargs: Any

        :raises OldapErrorNotFound: If the project is not found.
        :raises OldapErrorValue: If the owlclass_iri is not a valid Iri.
        """
        Model.__init__(self,
                       connection=con,
                       creator=con.userIri,
                       created=created,
                       contributor=con.userIri,
                       modified=modified,
                       validate=validate)
        self._externalOntology = _externalOntology if isinstance(_externalOntology, Xsd_boolean) else Xsd_boolean(_externalOntology)
        if isinstance(project, Project):
            self._project = project
        else:
            if not isinstance(project, (Iri, Xsd_NCName)):
                project = IriOrNCName(project, validate=validate)
            self._project = Project.read(self._con, project)
        if self._sysproject is None:
            self._sysproject = Project.read(self._con, Xsd_NCName("oldap"))
        if self._sharedproject is None:
            self._sharedproject = Project.read(self._con, Xsd_NCName("shared"))

        context = Context(name=self._con.context_name)
        context[self._project.projectShortName] = self._project.namespaceIri
        context.use(self._project.projectShortName)
        self._graph = self._project.projectShortName

        if isinstance(owlclass_iri, Xsd_QName):
            self._owlclass_iri = owlclass_iri
        elif owlclass_iri is not None:
            self._owlclass_iri = Xsd_QName(owlclass_iri)
        else:
            self._owlclass_iri = None
        new_kwargs: dict[str, Any] = {}
        for name, value in kwargs.items():
            if name == ResClassAttribute.SUPERCLASS.value.fragment:
                if value:
                    new_kwargs[name] = self.assign_superclass(value)
            else:
                new_kwargs[name] = value
        #
        # now we add, if necessary, the mandatory superclass "oldap:Thing". Every ResourceClass is OLDAP must be
        # a subclass of "oldap:Thing"! We don't do it for system things with a prefix of "oldap".
        #
        if self._owlclass_iri.prefix != "oldap":
            thing_iri = Xsd_QName('oldap:Thing', validate=False)
            if self._owlclass_iri != thing_iri:
                if not new_kwargs.get(ResClassAttribute.SUPERCLASS.value.fragment):
                    new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment] = self.assign_superclass(thing_iri)
                else:
                    if not thing_iri in new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment]:
                        thing = ResourceClass.read(self._con, self._sysproject, thing_iri)
                        new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment][thing_iri] = thing
        self.set_attributes(new_kwargs, ResClassAttribute)

        self._properties = {}
        if hasproperties is not None:
            for hasprop in hasproperties:
                if isinstance(hasprop.prop, Xsd_QName):  # Reference to an external, standalone property definition
                    fixed_prop = Xsd_QName(str(hasprop.prop).removesuffix("Shape"), validate=validate)
                    try:
                        hasprop.prop = PropertyClass.read(self._con, self._project, fixed_prop)
                    except OldapErrorNotFound as err:
                        prop = PropertyClass(con=self._con,
                                             project=self._project,
                                             property_class_iri=fixed_prop,
                                             _externalOntology=Xsd_boolean(True))
                        hasprop.prop = prop
                elif isinstance(hasprop.prop, PropertyClass):  # an internal, private property definition
                    if hasprop.type == PropType.INTERNAL and not hasprop.prop._force_external:
                        hasprop.prop._internal = owlclass_iri
                else:
                    raise OldapErrorValue(f'Unexpected property type: {type(hasprop.prop).__name__}')
                iri = hasprop.prop.property_class_iri if isinstance(hasprop.prop, PropertyClass) else hasprop.prop
                self._properties[iri] = hasprop

        for attr in ResClassAttribute:
            setattr(ResourceClass, attr.value.fragment, property(
                partial(ResourceClass._get_value, attr=attr),
                partial(ResourceClass._set_value, attr=attr),
                partial(ResourceClass._del_value, attr=attr)))

        self.update_notifier(notifier, notify_data)

        self._test_in_use = False
        self.__version = SemanticVersion()
        self.__from_triplestore = False
        self.clear_changeset()

    def update_notifier(self,
                        notifier: Callable[[AttributeClass | Xsd_QName], None] | None = None,
                        notify_data: AttributeClass | None = None,):
        """
        Updates the notifier for the current instance and any nested attributes or
        properties that support notifier updates.

        This method assigns a notifier (callable function or None) and associate data
        to the current instance and propagates the notifier updates to contained
        attributes and properties, if they support the operation.

        :param notifier: Callable to be assigned as the notifier. It should accept
            an `AttributeClass` or `Iri` as arguments, or can be set to None to remove
            the notifier.
        :type notifier: Callable[[AttributeClass | Iri], None] | None
        :param notify_data: Associated data that may be passed to the notifier
            for processing. It can be `AttributeClass` or None.
        :type notify_data: AttributeClass | None
        :return: None
        :raises OldapError: If the provided `notifier` is not a callable function.
        """
        self.set_notifier(notifier, notify_data)
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)
        if  self._properties:
            for iri, hasprop in self._properties.items():
                hasprop.update_notifier(self.notifier, iri)


    def _as_dict(self):
        attributes = {}
        for key, value in self._attributes.items():
            if key.fragment == 'superclass':
                attributes[key.fragment] = [x for x in value.keys() if x != Xsd_QName('oldap:Thing')]
            else:
                attributes[key.fragment] = value
        return attributes | super()._as_dict() | {
            'project': self._project.projectShortName,
            'owlclass_iri': self._owlclass_iri,
            'hasproperties': [x for x in self._properties.values()],
            **({'_externalOntology': self._externalOntology} if self._externalOntology else {}),
        }

    def __eq__(self, other: Self):
        return self._as_dict() == other._as_dict()

    def check_for_permissions(self) -> (bool, str):
        """
        Evaluates whether the logged-in user (referred to as "actor") has the required
        permissions to create a user in the specified project or within the system. The
        function checks both system-level and project-level permissions and determines
        if the actor is authorized.

        :return: A tuple where the first element is a boolean indicating whether the
            actor has the necessary permissions, and the second element is a string
            detailing the result or reason for failure.
        :rtype: tuple[bool, str]
        :raises OldapError: If the logged-in user is not associated with a project.
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
            if not self._project:
                return False, f'Actor has no ADMIN_MODEL permission. Actor not associated with a project.'
            proj = self._project.projectShortName
            if actor.inProject.get(proj) is None:
                return False, f'Actor has no ADMIN_MODEL permission for project "{proj}"'
            else:
                if AdminPermission.ADMIN_MODEL not in actor.inProject.get(proj):
                    return False, f'Actor has no ADMIN_MODEL permission for project "{proj}"'
            return True, "OK"

    def pre_transform(self, attr: AttributeClass, value: Any, validate: bool = False) -> Any:
        if attr == ResClassAttribute.SUPERCLASS:
            return self.assign_superclass(value)
        else:
            return value

    def _change_setter(self, key: ResClassAttribute | Xsd_QName, value: AttributeParams | HasProperty) -> None:
        if not isinstance(key, (ResClassAttribute, Xsd_QName)):
            raise ValueError(f'Invalid key type {type(key)} of key {key}')
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, key)

        if isinstance(key, ResClassAttribute):
            assert isinstance(key, ResClassAttribute), f"Expected ResClassAttribute type, got {type(value)}"
            super()._change_setter(key, value)
            if self._attributes.get(key) is None:
                self._changeset[key] = ResourceClassPropertyChange(None, Action.CREATE, False)
            else:
                if self._changeset.get(key) is None:
                    self._changeset[key] = ResourceClassPropertyChange(self._attributes[key], Action.REPLACE, True)
                else:
                    self._changeset[key] = ResourceClassPropertyChange(self._changeset[key].old_value, Action.REPLACE, True)
            if key == ResClassAttribute.SUPERCLASS: # we can only change the superclass in the instance of ResourceClass if it's not in use
                self._test_in_use = True

        elif isinstance(key, Xsd_QName):  # Iri, we add a HasProrty instance
            if self._properties.get(key) is None:  # Property not set -> CREATE action
                self._changeset[key] = ResourceClassPropertyChange(None, Action.CREATE, False)
                if isinstance(value.prop, Xsd_QName):  # we just add a reference to an existing (!) standalone property!
                    try:
                        p = PropertyClass.read(self._con, project=self._project, property_class_iri=value.prop)
                        value.prop = p
                        self._properties[key] = value
                    except OldapErrorNotFound as err:
                        self._properties[key] = value
                else:
                    if value.type == PropType.INTERNAL:
                        value.prop._internal = self._owlclass_iri  # we need to access the private variable here
                        value.prop._property_class_iri = key  # we need to access the private variable here
                    self._properties[key] = value
            else:  # REPLACE action
                if self._changeset.get(key) is None:
                    self._changeset[key] = ResourceClassPropertyChange(self._properties[key], Action.REPLACE, True)
                else:
                    self._changeset[key] = ResourceClassPropertyChange(self._changeset[key].old_value, Action.REPLACE, True)
                if isinstance(value.prop, Xsd_QName):
                    try:
                        p = PropertyClass.read(self._con, project=self._project, property_class_iri=value.prop)
                        value.prop = p
                        self._properties[key] = value
                    except OldapErrorNotFound as err:
                        self._properties[key] = value
                else:
                    value.prop._internal = self._owlclass_iri  # we need to access the private variable here
                    value._property_class_iri = key  # we need to access the private variable here
                    self._properties[key] = value
                self._test_in_use = True  # change a property only when not in use!
        else:
            raise OldapError(f'Invalid key type {type(key).__name__} of key {key}')
        self.notify()

    def oldapSetAttr(self, attrname: str, attrval: PropTypes) -> None:
        resClassAttr = ResClassAttribute.from_name(attrname)
        val = ResClassAttribute.datatype(attrval)
        self._change_setter(resClassAttr, val)

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
        instance._attributes = deepcopy(self._attributes, memo)
        instance._changeset = deepcopy(self._changeset, memo)
        instance._externalOntology = deepcopy(self._externalOntology, memo)

        instance._graph = deepcopy(self._graph, memo)
        instance._project = deepcopy(self._project, memo)
        instance._sysproject = deepcopy(self._sysproject, memo)
        instance._sharedproject = deepcopy(self._sharedproject, memo)
        instance._owlclass_iri = deepcopy(self._owlclass_iri, memo)
        instance.__version = deepcopy(self.__version, memo)
        instance._properties = deepcopy(self._properties, memo)
        instance.__from_triplestore = self.__from_triplestore
        instance._test_in_use = self._test_in_use
        #
        # we have to set the callback for the associated props to the method in the new instance
        #
        instance.update_notifier()
        # for iri, hasprop in instance._properties.items():
        #     hasprop.set_notifier(instance.hp_notifier, hasprop.prop.property_class_iri)
        return instance


    def __getitem__(self, key: ResClassAttribute | Xsd_QName) -> AttributeTypes | HasProperty | Xsd_QName:
        if isinstance(key, ResClassAttribute):
            return super().__getitem__(key)
        elif isinstance(key, Xsd_QName):
            return self._properties.get(key)
        else:
            return None

    def get(self, key: ResClassAttribute | Xsd_QName) -> AttributeTypes | HasProperty | Xsd_QName | None:
        if isinstance(key, ResClassAttribute):
            return self._attributes.get(key)
        elif isinstance(key, Xsd_QName):
            return self._properties.get(key)
        else:
            return None

    def __setitem__(self, key: ResClassAttribute | Xsd_QName, value: AttributeParams | HasProperty) -> None:
        self._change_setter(key, value)

    def __delitem__(self, key: ResClassAttribute | Xsd_QName) -> None:
        """
        Removes the specified key from the ResourceClass instance. The method handles keys of type
        `ResClassAttribute` and `Iri` differently internally. For a `ResClassAttribute`
        it removes the attribute from the ResourceClass instance. For `Iri` keys, it
        manages a changeset to track deleted properties before removing the
        key-value pair. It also sets the _test_in_use attribute to True to avoid changing
        the resource class in use.

        :param key: The key to be removed from the collection.
        :type key: ResClassAttribute | Iri
        :raises ValueError: If the key type is not `ResClassAttribute` or `Iri`.
        """
        if not isinstance(key, (ResClassAttribute, Xsd_QName)):
            raise ValueError(f'Invalid key type {type(key).__name__} of key {key}')
        if isinstance(key, ResClassAttribute):
            super().__delitem__(key)
        elif isinstance(key, Xsd_QName):
            if self._changeset.get(key) is None:
                self._changeset[key] = ResourceClassPropertyChange(self._properties[key], Action.DELETE, False)
            else:
                self._changeset[key] = ResourceClassPropertyChange(self._changeset[key].old_value, Action.DELETE, False)
            del self._properties[key]
            self._test_in_use = True
        self.notify()

    def __delattr__(self, item: str | Xsd_QName):
        try:
            attr = ResClassAttribute.from_name(item)
            super().__delitem__(attr)
        except ValueError as err:
            try:
                iri = Xsd_QName(item, validate=True)
                if self._changeset.get(iri) is None:
                    self._changeset[iri] = ResourceClassPropertyChange(self._properties[iri], Action.DELETE, False)
                else:
                    self._changeset[iri] = ResourceClassPropertyChange(self._changeset[iri].old_value,
                                                                            Action.DELETE, False)
                del self._properties[iri]
            except OldapErrorValue as err:
                raise ValueError(f'Invalid key {item}')
        self.notify()

    @property
    def owl_class_iri(self) -> Xsd_QName:
        return self._owlclass_iri

    @property
    def version(self) -> SemanticVersion:
        return self.__version

    @property
    def externalOntology(self) -> Xsd_boolean:
        return self._externalOntology

    @property
    def properties(self) -> dict[Xsd_QName, HasProperty]:
        return self._properties

    @property
    def projectid(self) -> Xsd_NCName:
        return self._project.projectShortName

    def properties_items(self):
        return self._properties.items()

    def attributes_items(self):
        return self._attributes.items()

    def __str__(self):
        blank = ' '
        indent = 2
        s = f'Shape: {self._owlclass_iri}Shape\n'
        s += super().__str__()
        s += f'{blank:{indent*1}}Properties:\n'
        sorted_properties = sorted(self._properties.items(), key=lambda prop: prop[1].order if prop[1].order is not None else 9999)
        for qname, hasprop in sorted_properties:
            s += f'{blank:{indent*2}}{qname} = {hasprop.prop} (minCount={hasprop.minCount}, maxCount={hasprop.maxCount}\n'
        return s

    def clear_changeset(self) -> None:
        for prop in self._properties.values():
            prop.clear_changeset()
        super().clear_changeset()

    def notifier(self, what: ResClassAttribute | Xsd_QName):
        if isinstance(what, ResClassAttribute):
            self._changeset[what] = AttributeChange(None, Action.MODIFY)
        elif isinstance(what, Xsd_QName):
            self._changeset[what] = ResourceClassPropertyChange(None, Action.MODIFY, True)
        self.notify()

    def __sc_changed(self, oldval: ObservableDict[Xsd_QName, RC]):
        if self._changeset.get(ResClassAttribute.SUPERCLASS) is None:
            self._changeset[ResClassAttribute.SUPERCLASS] = AttributeChange(oldval, Action.MODIFY)

    @property
    def in_use(self) -> str:
        """
        Determines whether the resource instances of a specific OWL class in a SPARQL context
        are currently in use, excluding instances that match the specified shape type.

        The method generates a SPARQL query based on the class IRI and project context.
        The resulting query is returned as a string, enabling further evaluation or
        execution in the corresponding environment.

        :return: A SPARQL ASK query string used to check the usage status of
                 resource instances within a specific context.
        :rtype: str
        """
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        # query += f"""
        # ASK {{
        #     GRAPH {self._project.projectShortName}:data {{
        #         ?resinstance rdf:type {self._owlclass_iri} .
        #         FILTER(?resinstance != {self._owlclass_iri}Shape)
        #     }}
        # }}
        # """
        query += f"""
        ASK {{
            {{
                GRAPH {self._project.projectShortName}:data {{
                    ?resinstance rdf:type {self._owlclass_iri} .
                }}
            }}
            UNION
            {{
                GRAPH {self._project.projectShortName}:onto {{
                    ?subclass rdfs:subClassOf+ {self._owlclass_iri} .
                }}
            }}
        }}
        """
        return query

    @staticmethod
    def __query_shacl(con: IConnection,
                      project: Project,
                      owl_class_iri: Xsd_QName) -> Attributes:
        """
        Executes a SPARQL query to retrieve the attributes of a given OWL class from a SHACL
        graph using the provided connection and project context. This function processes the
        query results and organizes attributes into a dictionary format for further usage.
        NOTE: It reads only the attributes of a given OWL class, not the properties!

        :param con: Connection instance providing methods to interact with the ontology.
        :type con: IConnection
        :param project: Project instance associated with the ontology and used to build the
            query context and graph.
        :type project: Project
        :param owl_class_iri: The IRI of the OWL class for which attributes need to be
            retrieved.
        :type owl_class_iri: Iri
        :return: A dictionary containing attributes of the OWL class. Keys are attribute IRIs
            and values are lists of corresponding attribute values.
        :rtype: Attributes
        :raises OldapErrorNotFound: If the provided OWL class IRI does not correspond to any
            resource in the SHACL graph.
        :raises OldapError: If an inconsistent shape is found for the provided OWL class IRI.
        """
        context = Context(name=con.context_name)
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        graph = project.projectShortName

        query = context.sparql_context
        query += f"""
        SELECT ?attriri ?value
        FROM {graph}:shacl
        WHERE {{
            BIND({owl_class_iri}Shape AS ?shape)
            ?shape ?attriri ?value
        }}
         """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'Resource with iri "{owl_class_iri}" does not exist."')
        attributes: Attributes = {}
        for r in res:
            attriri = r['attriri']
            if attriri == 'rdf:type':
                tmp_owl_class_iri = r['value']
                if tmp_owl_class_iri == 'sh:NodeShape':
                    continue
                if tmp_owl_class_iri != owl_class_iri:
                    raise OldapError(f'Inconsistent Shape for "{owl_class_iri}": rdf:type="{tmp_owl_class_iri}"')
            elif attriri == 'sh:property':
                continue  # processes later – points to a BNode containing the property definition or to a PropertyShape...
            else:
                attriri = r['attriri']
                if isinstance(r['value'], Xsd_QName):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
                elif isinstance(r['value'], Xsd_string):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(str(r['value']))
                elif isinstance(r['value'], BNode):
                    pass
                else:
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
        return attributes

    def _parse_shacl(self, attributes: Attributes) -> None:
        for key, val in attributes.items():
            if key == 'sh:targetClass':
                continue
            if key == 'schema:version':
                self.__version = SemanticVersion.fromString(val[0])
            elif key == 'dcterms:creator':
                self._creator = val[0]
            elif key == 'dcterms:created':
                self._created = val[0]
            elif key == 'dcterms:contributor':
                self._contributor = val[0]
            elif key == 'dcterms:modified':
                self._modified = val[0]
            elif key == 'oldap:externalOntology':
                self._externalOntology = Xsd_boolean(val[0])
            elif key == 'sh:node':
                #
                # we expect sh:node only if the superclass is also defined as SHACL and we can read it's
                # definitions. All other superlcasses (referencing external ontologies) are only
                # used in the OWL definitions
                #
                if self._attributes.get(ResClassAttribute.SUPERCLASS) is None:
                    self._attributes[ResClassAttribute.SUPERCLASS] = ObservableDict(on_change=self.__sc_changed)
                for v in val:
                    if str(v).endswith("Shape"):
                        owliri = Xsd_QName(str(v)[:-5], validate=False)
                        if owliri.prefix == 'oldap':
                            conf = GlobalConfig(self._con)
                            sysproj = conf.sysproject
                            superclass = ResourceClass.read(self._con, sysproj, owliri)
                        elif owliri.prefix == 'shared':
                            conf = GlobalConfig(self._con)
                            sharedproj = conf.sharedproject
                            superclass = ResourceClass.read(self._con, sharedproj, owliri)
                        else:
                            superclass = ResourceClass.read(self._con, self._project, owliri)
                        self._attributes[ResClassAttribute.SUPERCLASS][owliri] = superclass
                    else:
                        raise OldapErrorInconsistency(f'Value "{val[0]}" must end with "Shape".')
            else:
                attr = ResClassAttribute.from_value(key.as_qname)
                if attr.datatype == LangString:
                    self._attributes[attr] = attr.datatype(val)
                else:
                    self._attributes[attr] = attr.datatype(val[0])
                if getattr(self._attributes[attr], 'set_hp', None) is not None:
                    self._attributes[attr].set_notifier(self.notifier, attr)

        self.__from_triplestore = True
        self.clear_changeset()

    @staticmethod
    def __query_resource_props(con: IConnection,
                               project: Project,
                               owlclass_iri: Xsd_QName,
                               sa_props: dict[Xsd_QName, PropertyClass] | None = None) -> List[HasProperty | Xsd_QName]:
        """
        This method queries and returns a list of properties defined in a sh:NodeShape. The properties may be
        given "inline" as BNode or may be a reference to an external sh:PropertyShape. These external shapes will be
        read when the ResourceClass is constructed (see __init__() of ResourceClass).

        :param con: IConnection instance
        :param graph: Name of the graph
        :param owlclass_iri: The QName of the OWL class defining the resource. The "Shape" ending will be added
        :return: List of PropertyClasses/QNames
        """

        context = Context(name=con.context_name)
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        graph = project.projectShortName

        #
        # first we query all the properties that part of this resource
        #
        # There may be several ways to define these properties:
        #
        # A. Standalone property where we add per-property-usage constraints
        #    HasProperty.type = HasProperty.STANDALONE
        #
        #    sh:property <iri>Shape ,
        #    [
        #       sh:path <iri> ;
        #       sh:maxCount 1 ;  # OPTIONAL
        #       ...  # minCount, orer, group
        #    ] ;
        #
        # B: Internal property
        #
        #    sh:property [
        #       sh:path <iri> ;
        #        dcterm:creation "..." ;
        #        ...
        #        sh:datatype: xsd:string ;
        #        ...
        #    ] ;
        #
        # C. External Property from an external ontology
        #    HasProperty.type = HasProperty.EXTERNAL
        #
        #    sh:property [
        #       sh:path <iri> ;
        #       sh:maxCount 1 ;  # OPTIONAL
        #       ...  # minCount, orer, group
        #    ] ;
        #
        #
        query = context.sparql_context
        query += f"""
        SELECT ?prop ?attriri ?value ?oo
        FROM {graph}:shacl
        WHERE {{
            {owlclass_iri.toRdf}Shape sh:property ?prop .
            OPTIONAL {{
                ?prop ?attriri ?value .
                OPTIONAL {{
                    ?value rdf:rest*/rdf:first ?oo
                }}
            }}
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=context, query_result=jsonobj)
        propinfos: Dict[Xsd_QName | BNode, Attributes] = {}
        #
        # first we run over all triples to gather the information about the properties of the possible
        # BNode based sh:property-Shapes.
        # NOTE: some of the nodes may actually be QNames referencing shapes defines as "standalone" sh:PropertyShape's.
        #
        for r in res:
            if isinstance(r['prop'], BNode):
                # it's a blank node containing the property information
                # if it's a new BNode, let's add the property attributes for this new property defintion
                if r['attriri'] == 'sh:path' and r['value'] == 'rdf:type':
                    continue  # TODO: get rid of the triple "BNODE sh:path sh:type !!!
                if r['prop'] not in propinfos:
                    propinfos[r['prop']]: Attributes = {}
                if r.get('attriri') and not isinstance(r['attriri'], Xsd_QName):
                    raise OldapError(f"There is some inconsistency in this shape! ({r['attriri']})")
                # now let's process the triples of the property (blank) node
                PropertyClass.process_triple(r, propinfos[r['prop']])
                continue
            if isinstance(r['prop'], Xsd_QName):
                # we have a reference to a property shape of a standalone property: we read it
                # and add it to the list of standalone properties if it does not exist yet
                if str(r['prop']).endswith("Shape"):
                    refprop = Xsd_QName(str(r['prop'])[:-5], validate=False)
                    if not sa_props:
                        sa_props: dict[Xsd_QName, PropertyClass] = {}
                    if not refprop in sa_props:
                        sa_props[refprop] = PropertyClass.read(con=con, project=project, property_class_iri=refprop)
                        sa_props[refprop]._externalOntology = Xsd_boolean(True)
                else:
                    raise OldapErrorInconsistency(f'Value "{r['prop']}" must end with "Shape".')

        propinfos2 = {v["sh:path"]: v for v in propinfos.values() if "sh:path" in v}

        #
        # now we collected all the information from the triple store. Let's process the information into
        # a list of full PropertyClasses or QName's to external definitions
        #
        proplist: List[HasProperty] = []
        for prop_iri, attributes in propinfos2.items():
            #
            # Case A, standalone property
            #
            if sa_props and prop_iri in sa_props:
                proplist.append(HasProperty(con=con,
                                            project=project,
                                            prop=sa_props[prop_iri],
                                            minCount=attributes.get(Xsd_QName('sh:minCount')),
                                            maxCount=attributes.get(Xsd_QName('sh:maxCount')),
                                            order=attributes.get(Xsd_QName('sh:order')),
                                            group=attributes.get(Xsd_QName('sh:group'))))
            else:
                prop = PropertyClass(con=con, project=project)
                haspropdata = prop.parse_shacl(attributes=attributes)
                if prop.property_class_iri.as_qname.prefix in [project.projectShortName, 'oldap', 'shared']:
                    #
                    # Case B, internal property
                    #
                    prop._internal = owlclass_iri
                    proplist.append(HasProperty(con=con,
                                                project=project,
                                                prop=prop,
                                                minCount=haspropdata.minCount,
                                                maxCount=haspropdata.maxCount,
                                                order=haspropdata.order,
                                                group=haspropdata.group))
                else:
                    #
                    # Case C, external property
                    #
                    # we check, if the external property is already defined somewhere in the project or the shared
                    prop._externalOntology = Xsd_boolean(True)
                    proplist.append(HasProperty(con=con,
                                                project=project,
                                                #prop=sa_props[prop_iri] if sa_props and prop_iri in sa_props else prop.property_class_iri,
                                                prop=prop,
                                                minCount=haspropdata.minCount,
                                                maxCount=haspropdata.maxCount,
                                                order=haspropdata.order,
                                                group=haspropdata.group))
        return proplist

    def __read_owl(self) -> None:
        if self._externalOntology:
            return
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?prop ?p ?o
        FROM {self._owlclass_iri.prefix}:onto
        WHERE {{
   	        {self._owlclass_iri.toRdf} rdfs:subClassOf ?prop .
            ?prop ?p ?o .
            FILTER(?o != owl:Restriction)
            FILTER NOT EXISTS {{ ?prop a owl:Class }} .
        }}
        """
        jsonobj = self._con.query(query1)
        res = QueryProcessor(context=context, query_result=jsonobj)
        propdict = {}
        for r in res:
            bnode_id = str(r['prop'])
            if not propdict.get(bnode_id):
                propdict[bnode_id] = {}
            p = r['p']
            if p == 'owl:onProperty':
                propdict[bnode_id]['property_iri'] = r['o']
            elif p == 'owl:onClass':
                propdict[bnode_id]['to_node_iri'] = r['o']
            elif p == 'owl:minQualifiedCardinality':
                propdict[bnode_id]['min_count'] = Xsd_integer(r['o'])
            elif p == 'owl:maxQualifiedCardinality':
                propdict[bnode_id]['max_count'] = Xsd_integer(r['o'])
            elif p == 'owl:qualifiedCardinality':
                propdict[bnode_id]['min_count'] = Xsd_integer(r['o'])
                propdict[bnode_id]['max_count'] = Xsd_integer(r['o'])
            elif p == 'owl:onDataRange':
                propdict[bnode_id]['datatype'] = r['o']
            else:
                print(f'ERROR ERROR ERROR: Unknown restriction property: "{p}"')
        for bn, pp in propdict.items():
            if pp.get('property_iri') is None:
                OldapError('Invalid restriction node: No property_iri!')
            property_iri = pp['property_iri']
            prop = [x for x in self._properties if x == property_iri]
            if len(prop) != 1:
                raise OldapError(f'Property "{property_iri}" of "{self._owlclass_iri}" from OWL has no SHACL definition!')
            if isinstance(self._properties[prop[0]].prop, PropertyClass) and not self._properties[prop[0]].prop._externalOntology:
                self._properties[prop[0]].prop.read_owl()
        #
        # now get all the subClassOf of other classes
        #
        query2 = context.sparql_context
        query2 += f"""
        SELECT ?superclass ?p ?o
        FROM {self._owlclass_iri.prefix}:onto
        WHERE {{
            {self._owlclass_iri.toRdf} rdfs:subClassOf ?superclass .
            FILTER isIRI(?superclass) 
        }}
        """
        jsonobj = self._con.query(query2)
        res = QueryProcessor(context=context, query_result=jsonobj)
        if not self._attributes.get(ResClassAttribute.SUPERCLASS):
            self._attributes[ResClassAttribute.SUPERCLASS] = ObservableDict(on_change=self.__sc_changed)
        superclasses = [r['superclass'] for r in res]
        self.add_superclasses(superclasses)

    @classmethod
    def read(cls,
             con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             owl_class_iri: Xsd_QName | str,
             sa_props: dict[Xsd_QName, PropertyClass] | None = None,
             ignore_cache: bool = False) -> Self:
        """
        Reads and retrieves a class instance from the data source based on the provided
        connection, project, and class IRI. This method ensures that the class instance
        is created with relevant properties and attributes queried from the data source.
        Additionally, caching mechanisms are used to optimize performance.

        :param con: Connection to the data source.
        :type con: IConnection
        :param project: The project associated with the class. This can be provided as
            a `Project`, `Iri`, `Xsd_NCName`, or `str`. If not already a `Project` instance,
            it will be converted accordingly.
        :type project: Project | Iri | Xsd_NCName | str
        :param owl_class_iri: The IRI of the OWL class to retrieve. It can be provided as
            an `Iri` or `str`. If not already an `Iri`, it will be wrapped accordingly
            with validation.
        :type owl_class_iri: Iri | str
        :param sa_props: Optional dictionary that maps IRI to `PropertyClass` instances.
            These properties enhance the definition of the retrieved class. If not provided,
            no additional properties are used.
        :type sa_props: dict[Iri, PropertyClass] | None
        :param ignore_cache: Determines whether to ignore cached values. If `True`, the
            cache is bypassed, and the instance is freshly retrieved. If `False`, cached
            values are used if available.
        :type ignore_cache: bool
        :return: The retrieved and prepared class instance.
        :rtype: Self

        :raises OldapErrorNotFound: If the class IRI is not found in the data source.
        :raises OldapError: If an error occurs during retrieval.
        :raises OldapErrorInconsistency: If the retrieved class IRI is not consistent with the provided IRI.
        """
        if not isinstance(project, Project):
            if not isinstance(project, (Iri, Xsd_NCName)):
                project = IriOrNCName(project, validate=True)
            project = Project.read(con, project)
        if not isinstance(owl_class_iri, Xsd_QName):
            owl_class_iri = Xsd_QName(owl_class_iri, validate=True)

        cache = CacheSingletonRedis()
        if not ignore_cache:
            tmp = cache.get(owl_class_iri, connection=con)
            if tmp is not None:
                tmp.update_notifier()
                return tmp

        hasproperties: list[HasProperty | Xsd_QName] = ResourceClass.__query_resource_props(con=con,
                                                                                      project=project,
                                                                                      owlclass_iri=owl_class_iri,
                                                                                      sa_props=sa_props)
        resclass = cls(con=con, project=project, owlclass_iri=owl_class_iri, hasproperties=hasproperties)
        resclass.update_notifier()
        attributes = ResourceClass.__query_shacl(con, project=project, owl_class_iri=owl_class_iri)
        resclass._parse_shacl(attributes=attributes)
        if not resclass.externalOntology:
            resclass.__read_owl()

        resclass.clear_changeset()

        resclass.update_notifier()

        cache = CacheSingletonRedis()
        cache.set(resclass._owlclass_iri, resclass)
        return resclass

    def read_modtime_shacl(self, *,
                           context: Context,
                           graph: Xsd_NCName,
                           indent: int = 0, indent_inc: int = 4) -> Union[datetime, None]:
        blank = ''
        sparql = context.sparql_context
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:shacl\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        sparql += f'{blank:{(indent + 1) * indent_inc}}{self._owlclass_iri}Shape dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self.safe_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')

    def read_modtime_owl(self, *,
                         context: Context,
                         graph: Xsd_NCName,
                         indent: int = 0, indent_inc: int = 4) -> Union[datetime, None]:
        blank = ''
        sparql = context.sparql_context
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:onto\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        sparql += f'{blank:{(indent + 1) * indent_inc}}{self._owlclass_iri} dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self.safe_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')

    def create_shacl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{(indent + 1)*indent_inc}}{self._owlclass_iri}Shape a sh:NodeShape'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:targetClass {self._owlclass_iri.toRdf}'
        self._created = timestamp
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:creator {self._creator.toRdf}'
        self._modified = timestamp
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:contributor {self._contributor.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}oldap:externalOntology {self._externalOntology.toRdf}'
        for attr, value in self._attributes.items():
            if attr == ResClassAttribute.SUPERCLASS:
                #
                # In SHACL, superclasses are only added if we have access to it's SHACL definition, that is,
                # if it's given as ResourceClass instance.
                # Superclasses without SHACL definition will be only added to the OWL file for reasoning.
                #
                scset = [f'{iri.toRdf}Shape' for iri, resclass in value.items() if resclass]
                valstr = ", ".join(scset)
                if valstr:
                    sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:node {valstr}'
            else:
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}{attr.value} {value.toRdf}'

        # TODO: Check if the following is needed.
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property ['
        sparql += f'\n{blank:{(indent + 3) * indent_inc}}sh:path rdf:type'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}]'

        for iri, hp in self._properties.items():
            if hp.type == PropType.STANDALONE:
                if hp.minCount or hp.maxCount or hp.order or hp.group:
                    sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property {iri}Shape, ['
                    sparql += f'\n{blank:{(indent + 3) * indent_inc}}sh:path {iri.toRdf}'
                    sparql += hp.create_shacl(indent=2)
                    sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}]'
                else:
                    sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property {iri}Shape'
            else:
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property ['
                sparql += hp.prop.property_node_shacl(timestamp=timestamp,
                                                      haspropdata=hp.haspropdata,
                                                      indent=3)
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}]'
        sparql += ' .\n'
        return sparql

    def create_owl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        if self._externalOntology:
            return ''
        blank = ''
        sparql = ''
        for iri, hp in self._properties.items():
            if hp.type == PropType.EXTERNAL:
                continue
            if not hp.prop.from_triplestore:
                sparql += hp.prop.create_owl_part1(timestamp, indent + 2) + '\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owlclass_iri} rdf:type owl:Class ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}schema:version {self.__version.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._creator.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._contributor.toRdf} ;\n'
        # we add, if available, rdfs:label and rdfs:comment to the OWL ontology
        if self._attributes.get(ResClassAttribute.LABEL):
            sparql += f'{blank:{(indent + 3) * indent_inc}}rdfs:label {self._attributes[ResClassAttribute.LABEL].toRdf} ;\n'
        if self._attributes.get(ResClassAttribute.COMMENT):
            sparql += f'{blank:{(indent + 3) * indent_inc}}rdfs:comment {self._attributes[ResClassAttribute.COMMENT].toRdf} ;\n'
        if self._attributes.get(ResClassAttribute.SUPERCLASS) is not None:
            sc = {x.toRdf for x in self._attributes[ResClassAttribute.SUPERCLASS].keys()}
            if Xsd_QName('oldap:Thing', validate=False).toRdf not in sc:
                sc.add(Xsd_QName('oldap:Thing', validate=False).toRdf)
        else:
            sc = {Xsd_QName('oldap:Thing', validate=False).toRdf}
        valstr = ", ".join(sc)
        sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {valstr}'
        i = 0
        for iri, hp in self._properties.items():
            if not (hp.minCount or hp.maxCount or self._attributes.get(PropClassAttr.DATATYPE) or self._attributes.get(PropClassAttr.CLASS)):
                continue
            sparql += ' ,\n'
            if isinstance(hp.prop, Xsd_QName):
                sparql += f'{blank:{(indent + 3) * indent_inc}}[\n'
                sparql += f'{blank:{(indent + 4) * indent_inc}}rdf:type owl:Restriction ;\n'
                sparql += f'{blank:{(indent + 4) * indent_inc}}owl:onProperty {hp.prop.toRdf}'
                sparql += hp.create_owl(4)
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}]'
            else:
                sparql += hp.prop.create_owl_part2(haspropdata=hp, indent=(indent + 4))
            i += 1
        sparql += ' .\n'
        return sparql

    def set_creation_metadata(self, timestamp: Xsd_dateTime) -> None:
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.__from_triplestore = True

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Creates a resource within the specified graph context while ensuring correct
        permissions, transaction handling, and metadata generation. This method manages
        SHACL and OWL data insertions, verifies existing records, handles cache updates,
        and performs necessary error handling for failed operations. It ensures that
        proper creation logic is followed without overwriting pre-existing resources.

        :param indent: Initial indentation level for constructing SPARQL statements.
        :param indent_inc: Incremental indentation for nested SPARQL structures.
        :raises OldapErrorNoPermission: When the current "actor" lacks the permissions
            to create a resource in the specified context.
        :raises OldapErrorAlreadyExists: When attempting to create a resource that
            already exists in the triplestore or has been previously detected.
        :raises OldapErrorUpdateFailed: When an attempt to create the resource fails,
            leading to a transaction abort.
        """
        #
        # First we check if the logged-in user ("actor") has the permission to create resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        if self.__from_triplestore:
            raise OldapErrorAlreadyExists(f'Cannot create property that was read from triplestore before (property: {self._owlclass_iri}')
        timestamp = Xsd_dateTime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
        sparql += self.create_shacl(timestamp=timestamp)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        if not self._externalOntology:
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
            sparql += self.create_owl(timestamp=timestamp)
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}}}\n'
        self._con.transaction_start()
        if self.read_modtime_shacl(context=context, graph=self._graph) is not None:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'Object "{self._owlclass_iri}" already exists.')
        try:
            self._con.transaction_update(sparql)
        except OldapError:
            print(sparql)
            self._con.transaction_abort()
            raise

        if not self._externalOntology:
            try:
                modtime_shacl = self.read_modtime_shacl(context=context, graph=self._graph)
                modtime_owl = self.read_modtime_owl(context=context, graph=self._graph)
            except:
                self._con.transaction_abort()
                raise
            if modtime_shacl == timestamp and modtime_owl == timestamp:
                self._con.transaction_commit()
                self.set_creation_metadata(timestamp=timestamp)
            else:
                self._con.transaction_abort()
                raise OldapErrorUpdateFailed(f'Creating resource "{self._owlclass_iri}" failed.')
        else:
            self._con.transaction_commit()
        self.clear_changeset()
        cache = CacheSingletonRedis()
        cache.set(self._owlclass_iri, self)

    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Writes the content of the graph in TriG format to the specified file.

        This method outputs the graph data in TriG serialization format using a
        specified filename. It generates timestamped SHACL and OWL content
        based on the graph and writes them into the file within corresponding contexts.

        :param filename: The path to the file where the TriG data will be saved.
        :type filename: str
        :param indent: The base indentation level for the TriG file formatting.
        :type indent: int
        :param indent_inc: The incremental indentation size for nested elements in
            the TriG file.
        :type indent_inc: int
        :return: None
        """
        with open(filename, 'w') as f:
            timestamp = Xsd_dateTime.now()
            blank = ''
            context = Context(name=self._con.context_name)
            f.write(context.turtle_context)

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:shacl {{\n')
            f.write(self.create_shacl(timestamp=timestamp))
            f.write(f'\n{blank:{indent * indent_inc}}}}\n')

            if not self._externalOntology:
                f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
                f.write(self.create_owl(timestamp=timestamp))
                f.write(f'{blank:{indent * indent_inc}}}}\n')

    def __add_new_property_ref_shacl(self, *,
                                     iri: Xsd_QName,
                                     hasprop: HasProperty | None = None,
                                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'INSERT DATA {{#B\n'
        sparql += f'    GRAPH {self._graph}:shacl {{\n'
        sparql += f'{blank:{indent * indent_inc}}{self._owlclass_iri}Shape sh:property [\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}sh:path {iri.toRdf}'
        sparql += hasprop.create_shacl()
        sparql += f' ; \n{blank:{indent * indent_inc}}] .\n'
        sparql += f'    }}\n'
        sparql += f'}}\n'
        return sparql

    def __delete_property_ref_shacl(self,
                                    owlclass_iri: Xsd_QName,
                                    propclass_iri: Xsd_QName,
                                    indent: int = 0,
                                    indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:shacl\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?propnode sh:path {propclass_iri.toRdf} .\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}} UNION {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}FILTER(?propnode = {propclass_iri.toRdf}Shape)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def __delete_property_ref_onto(self,
                                   owlclass_iri: Xsd_QName,
                                   propclass_iri: Xsd_QName,
                                   indent: int = 0,
                                   indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri.toRdf} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode owl:onProperty {propclass_iri.toRdf} .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def __update_shacl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        if not self._changeset:
            return ''
        blank = ''
        sparql_list = []


        #
        ############ NEW STRUCTURE ##########
        #

        #
        # we loop over all items in the changeset of the resource
        #
        for item, change in self._changeset.items():
            item: Union[Xsd_QName, HasProperty]
            if isinstance(item, ResClassAttribute):  # we have just an attribute or ResourceClass
                #
                # Do the changes to the ResourceClass attributes
                #
                sparql: str | None = None
                if item == ResClassAttribute.SUPERCLASS:
                    #
                    # Superclasses are only added to SHACL if they have been supplied as ResourceClass instance.
                    # Then the subclass inherits all property definitions!!
                    # Other superclasses where we do not have access to a SHACL definition are only added to
                    # OWL in order to allow reasoning.
                    #
                    if change.old_value:
                        old_set = {iri for iri, data in change.old_value.items() if data}
                    else:
                        old_set = set()
                    if self._attributes[item]:
                        new_set = {iri for iri, data in self._attributes[item].items() if data}
                    else:
                        new_set = set()
                    to_be_deleted = old_set - new_set
                    to_be_added = new_set - old_set
                    if to_be_deleted or to_be_added:
                        sparql = f'WITH {self._graph}:shacl\n'
                        if to_be_deleted:
                            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                            for ov in to_be_deleted:
                                sparql += f'{blank:{(indent + 1) * indent_inc}}?res sh:node {ov}Shape .\n'
                            sparql += f'{blank:{indent * indent_inc}}}}\n'
                        if to_be_added:
                            sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                            for nv in to_be_added:
                                sparql += f'{blank:{(indent + 1) * indent_inc}}?res sh:node {nv}Shape .\n'
                            sparql += f'{blank:{indent * indent_inc}}}}\n'
                        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri.toRdf}Shape as ?res)\n'
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
                        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
                        sparql += f'{blank:{indent * indent_inc}}}}'
                else:
                    sparql = RdfModifyRes.shacl(action=change.action,
                                                graph=self._graph,
                                                owlclass_iri=self._owlclass_iri,
                                                ele=RdfModifyItem(item.value,
                                                                  change.old_value,
                                                                  self._attributes.get(item)),
                                                last_modified=self._modified)
                if sparql:
                    sparql_list.append(sparql)
            elif isinstance(item, Xsd_QName): # noinspection PyUnreachableCode
                #
                # Something affected the self._properties
                #
                propiri = item
                match(change.action):
                    case Action.CREATE:
                        #
                        # We add a new HasPropertyClass instance with attached PropertyClass or reference
                        #
                        sparql: str | None = None
                        if isinstance(self._properties[propiri].prop, Xsd_QName):
                            # -> reference to an external, foreign property!
                            sparql = self.__add_new_property_ref_shacl(iri=self._properties[propiri].prop,
                                                                       hasprop=self._properties[propiri])
                        elif isinstance(self._properties[propiri].prop, PropertyClass):
                            # -> we have the PropertyClass available
                            if self._properties[propiri].prop.from_triplestore:
                                # --> the property is already existing...
                                if self._properties[propiri].prop.internal:
                                    raise OldapErrorInconsistency(
                                        f'Property "{propiri}" is defined as internal and cannot be reused!')
                                sparql = self.__add_new_property_ref_shacl(
                                    iri=self._properties[propiri].prop.property_class_iri,
                                    hasprop=self._properties[propiri])
                            else:  # -> it's a new property,  not yet in the triple store. First create it...
                                if self._properties[propiri].prop._force_external:
                                    # create a standalone property and the reference it!
                                    sparql2 = f'{blank:{indent * indent_inc}}INSERT DATA {{#C\n'
                                    sparql2 += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
                                    sparql2 += self._properties[propiri].prop.create_shacl(timestamp=timestamp,
                                                                                           indent=2)
                                    sparql2 += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                                    sparql_list.append(sparql2)
                                    sparql = self.__add_new_property_ref_shacl(
                                        iri=self._properties[propiri].prop.property_class_iri,
                                        hasprop=self._properties[propiri])
                                else:
                                    # Create an internal property (Bnode) and add minCount, maxCount
                                    sparql2 = f'{blank:{indent * indent_inc}}INSERT DATA {{#D\n'
                                    sparql2 += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
                                    sparql2 += self._properties[propiri].prop.create_shacl(timestamp=timestamp,
                                                                                           owlclass_iri=
                                                                                           self._properties[
                                                                                               propiri].prop.internal,
                                                                                           haspropdata=self._properties[
                                                                                               propiri].haspropdata,
                                                                                           indent=2)
                                    sparql2 += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                                    sparql2 += f'{blank:{indent * indent_inc}}}}\n'
                                    sparql_list.append(sparql2)
                        if sparql:
                            sparql_list.append(sparql)
                    case Action.DELETE:
                        #
                        # We delete a HasPropertyClass. If the property is internal, we delete it
                        # TODO: check if th PropertyClass is used ba a some data
                        #
                        if change.old_value.prop.internal:
                            sparql = change.old_value.prop.delete_shacl()
                        else:
                            sparql = self.__delete_property_ref_shacl(owlclass_iri=self._owlclass_iri,
                                                                      propclass_iri=change.old_value.prop.property_class_iri)
                        sparql_list.append(sparql)
                    case Action.REPLACE:
                        #
                        # We replace a property with a new one with same IRI – works only for internal if ever
                        # TODO: implement it sometime in the future; now throw an error
                        #
                        raise OldapErrorAlreadyExists(f'Property can not be replaced!')
                    case Action.MODIFY:
                        #
                        # Something happend within an existing HasPropertyClass instance
                        #
                        # the following method only updates attributes that have changed
                        sparql = self._properties[propiri].update_shacl(self._graph, self._owlclass_iri,
                                                                        propiri)
                        if sparql:
                            sparql_list.append(sparql)
                        #
                        # now update the attached props
                        #
                        for key, value in self._properties[item].changeset.items():
                            if isinstance(key, Xsd_QName):
                                #
                                # the attached PropertyClass instance has changed
                                #
                                sparql = self._properties[propiri].prop.update_shacl(owlclass_iri=self._owlclass_iri,
                                                                                     timestamp=timestamp)
                                if sparql:
                                    sparql_list.append(sparql)
            else:
                pass
        #
        #######################################
        #

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyRes.shacl(action=Action.REPLACE if self._contributor else Action.CREATE,
                                     graph=self._graph,
                                     owlclass_iri=self._owlclass_iri,
                                     ele=RdfModifyItem('dcterms:contributor', self._contributor, self._con.userIri),
                                     last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyRes.shacl(action=Action.REPLACE if self._modified else Action.CREATE,
                                     graph=self._graph,
                                     owlclass_iri=self._owlclass_iri,
                                     ele=RdfModifyItem('dcterms:modified', self._modified, timestamp),
                                     last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def __add_new_property_ref_onto(self, *,
                                    prop: PropertyClass | Xsd_QName,
                                    hasprop: HasProperty | None,
                                    indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'INSERT DATA {{#E\n'
        sparql += f'    GRAPH {self._graph}:onto {{\n'
        sparql += f'{blank:{indent * indent_inc}}{self._owlclass_iri} rdfs:subClassOf [\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:type owl:Restriction ;\n'
        if isinstance(prop, Xsd_QName):
            # sparql += prop.create_owl_part2(haspropdata=hasprop.haspropdata)
            sparql += f'{blank:{(indent + 1) * indent_inc}}owl:onProperty {prop.toRdf}'
            if hasprop.haspropdata.minCount and hasprop.haspropdata.maxCount and hasprop.haspropdata.minCount == hasprop.haspropdata.maxCount:
                tmp = Xsd_nonNegativeInteger(hasprop.haspropdata.minCount)
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:qualifiedCardinality {tmp.toRdf}'
            else:
                if hasprop.haspropdata.minCount:
                    tmp = Xsd_nonNegativeInteger(hasprop.haspropdata.minCount)
                    sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:minQualifiedCardinality {tmp.toRdf}'
                if hasprop.haspropdata.maxCount:
                    tmp = Xsd_nonNegativeInteger(hasprop.haspropdata.maxCount)
                    sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:maxQualifiedCardinality {tmp.toRdf}'
        elif isinstance(prop, PropertyClass):
            sparql += f'{blank:{(indent + 1) * indent_inc}}owl:onProperty {prop.property_class_iri.toRdf}'
            sparql += hasprop.create_owl(indent=1)
        else:
            raise OldapErrorInconsistency(f'Property can not be added!')
        sparql += f'{blank:{indent * indent_inc}}] .\n'
        sparql += f'    }}\n'
        sparql += f'}}\n'
        return sparql

    def __delete_property_ref_owl(self,
                                  owlclass_iri: Xsd_QName,
                                  propclass_iri: Xsd_QName,
                                  indent: int = 0,
                                  indent_inc: int = 4):
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri} sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:path {self.propclass_iri} .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def __update_owl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        if not self._changeset:
            return ''
        blank = ''
        sparql_list = []

        #
        ############ NEW STRUCTURE ##########
        #

        #
        # we loop over all items in the changeset of the resource
        #
        for item, change in self._changeset.items():
            item: Union[ResClassAttribute, Xsd_QName]
            if isinstance(item, ResClassAttribute):  # we have just an attribute or ResourceClass
                #
                # Do the changes to the ResourceClass attributes
                #
                if item == ResClassAttribute.LABEL:
                    sparql = RdfModifyRes.onto(action=change.action,
                                                graph=self._graph,
                                                owlclass_iri=self._owlclass_iri,
                                                ele=RdfModifyItem(item.value,
                                                                  change.old_value,
                                                                  self._attributes.get(ResClassAttribute.LABEL)),
                                                last_modified=self._modified)
                    sparql_list.append(sparql)
                if item == ResClassAttribute.COMMENT:
                    sparql = RdfModifyRes.onto(action=change.action,
                                                graph=self._graph,
                                                owlclass_iri=self._owlclass_iri,
                                                ele=RdfModifyItem(item.value,
                                                                  change.old_value,
                                                                  self._attributes.get(ResClassAttribute.COMMENT)),
                                                last_modified=self._modified)
                    sparql_list.append(sparql)

                #
                # we only need to add rdfs:subClassOf to the ontology – all other attributes are irrelevant
                #
                if item == ResClassAttribute.SUPERCLASS:
                    # sparql = f'#\n# OWL: Process attribute "{item.value}" with Action "{change.action.value}"\n#\n'
                    sparql = f'WITH {self._graph}:onto\n'
                    old_set = set(change.old_value) if change.old_value else set()
                    new_set = set(self._attributes[item]) if self._attributes[item] else set()
                    to_be_deleted = old_set - new_set
                    to_be_added = new_set - old_set
                    if to_be_deleted:
                        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                        for ov in to_be_deleted:
                            if isinstance(ov, ResourceClass):
                                sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {ov.owl_class_iri.toRdf} .\n'
                            else:
                                sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {ov.toRdf} .\n'
                        sparql += f'{blank:{indent * indent_inc}}}}\n'
                    if to_be_added:
                        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                        for nv in to_be_added:
                            if isinstance(nv, ResourceClass):
                                sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {nv.owl_class_iri.toRdf} .\n'
                            else:
                                sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {nv.toRdf} .\n'
                        sparql += f'{blank:{indent * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri.toRdf} as ?res)\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
                    sparql += f'{blank:{indent * indent_inc}}}}'
                    sparql_list.append(sparql)

            elif isinstance(item, Xsd_QName):  # Something affected the self._properties
                #
                # Something affected the self._properties
                #
                propiri = item
                match(change.action):
                    case Action.CREATE:
                        #
                        # We add a new HasPropertyClass instance with attached PropertyClass or reference
                        #
                        if isinstance(self._properties[propiri].prop, Xsd_QName):
                            # -> reference to an external, foreign property! prop is Iri!
                            sparql = self.__add_new_property_ref_onto(prop=self._properties[propiri].prop,  # is an Iri
                                                                      hasprop=self._properties[propiri])
                        elif isinstance(self._properties[propiri].prop, PropertyClass):
                            # -> we have the PropertyClass available
                            if self._properties[propiri].prop.from_triplestore:
                                # --> the property is already existing...
                                if self._properties[propiri].prop.internal:
                                    raise OldapErrorInconsistency(
                                        f'Property "{propiri}" is defined as internal and cannot be reused!')
                                sparql = self.__add_new_property_ref_onto(
                                    prop=self._properties[propiri].prop,  # is a PropertyClass already existing...
                                    hasprop=self._properties[propiri])
                            else:  # -> it's a new property,  not yet in the triple store. First create it...
                                # create a standalone property and the reference it!
                                sparql2 = f'{blank:{indent * indent_inc}}INSERT DATA {{#F\n'
                                sparql2 += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
                                sparql2 += self._properties[propiri].prop.create_owl_part1(timestamp=timestamp,
                                                                                           indent=2)
                                sparql2 += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                                sparql2 += f'{blank:{indent * indent_inc}}}}\n'
                                sparql_list.append(sparql2)
                                sparql = self.__add_new_property_ref_onto(
                                    prop=self._properties[propiri].prop,  # its a PropertyClass we just created
                                    hasprop=self._properties[propiri])
                            sparql_list.append(sparql)
                    case Action.REPLACE:
                        #
                        # NOT YET IMPLEMENTED
                        # TODO: check if th PropertyClass is used ba a some data
                        #
                        raise OldapErrorInconsistency(f'Property can not be replaced!')
                    case Action.DELETE:
                        #
                        # We delete a HasPropertyClass. If the property is internal, we delete it
                        # TODO: check if th PropertyClass is used ba a some data
                        #
                        if change.old_value.prop.internal:
                            # we delete everything
                            sparql = change.old_value.prop.delete_owl()
                            sparql_list.append(sparql)
                            sparql = change.old_value.prop.delete_owl_subclass_str(owlclass_iri=self._owlclass_iri)
                        else:
                            # delete only reference
                            sparql = change.old_value.prop.delete_owl_subclass_str(owlclass_iri=self._owlclass_iri)
                        sparql_list.append(sparql)

                    case Action.MODIFY:
                        #
                        # Something happend within an existing HasPropertyClass instance
                        #
                        for key, value in self._properties[item].changeset.items():
                            if isinstance(key, HasPropertyAttr):
                                #
                                # an attribute was added, deleted or has changed
                                #
                                sparql = self._properties[propiri].update_owl(self._graph, self._owlclass_iri, propiri)
                                sparql_list.append(sparql)
                            elif isinstance(key, Xsd_QName):
                                sparql = self._properties[propiri].prop.update_owl(owlclass_iri=self._owlclass_iri,
                                                                                   timestamp=timestamp)
                                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyRes.onto(action=Action.REPLACE if self._contributor else Action.CREATE,
                                    graph=self._graph,
                                    owlclass_iri=self._owlclass_iri,
                                    ele=RdfModifyItem('dcterms:contributor', self._contributor, self._con.userIri),
                                    last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyRes.onto(action=Action.REPLACE if self._modified else Action.CREATE,
                                    graph=self._graph,
                                    owlclass_iri=self._owlclass_iri,
                                    ele=RdfModifyItem('dcterms:modified', self._modified, timestamp),
                                    last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update(self) -> None:
        """
        Updates the current resource, ensuring all necessary permissions, conditions,
        and constraints are met before proceeding. This method primarily interacts with
        the context, SPARQL queries, and manages the update lifecycle, including
        transactional integrity. It finalizes the update process with cache synchronization.

        If any precondition is violated, corresponding errors are raised, such as lacking
        permissions, resource usage conflicts, or inconsistencies during the update process.

        Raises:
            OldapErrorNoPermission: If the actor does not have the required permissions to update.
            OldapErrorInUse: If the resource is in use and cannot be updated.
            OldapErrorUpdateFailed: If the update fails during the verification of timestamps.

        :raises OldapErrorNoPermission: When user lacks permissions to perform the update.
        :raises OldapErrorInUse: When the resource is already in active use and update cannot proceed.
        :raises OldapErrorUpdateFailed: When the update operation fails due to timestamp inconsistency.
        :return: None
        """
        #
        # First we check if the logged-in user ("actor") has the permission to update resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        #
        # we check if we have to cancel the update because the resource is in use
        #
        for item, change in self._changeset.items():
            if isinstance(item, ResClassAttribute):
                if item == ResClassAttribute.SUPERCLASS:
                    self._test_in_use = True
            else:
                if change.action != Action.CREATE:
                    self._test_in_use = True

        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)

        # sparql0 = ''
        # if check_use:
        #     sparql0 = self.in_use

        sparql1 = context.sparql_context
        sparql1 += self.__update_shacl(timestamp=timestamp)

        if not self._externalOntology:
            sparql2 = context.sparql_context
            sparql2 += self.__update_owl(timestamp=timestamp)

        self._con.transaction_start()

        if self._test_in_use:
            sparql0 = self.in_use
            result = self.safe_query(sparql0)
            if result['boolean']:
                self._con.transaction_abort()
                raise OldapErrorInUse(f'Cannot update: resource "{self._owlclass_iri}" is in use')

        self.safe_update(sparql1)
        if not self._externalOntology:
            self.safe_update(sparql2)

        if not self._externalOntology:
            try:
                modtime_shacl = self.read_modtime_shacl(context=context, graph=self._graph)
                modtime_owl = self.read_modtime_owl(context=context, graph=self._graph)
            except:
                self._con.transaction_abort()
                raise
            if modtime_shacl == timestamp and modtime_owl == timestamp:
                self._con.transaction_commit()
            else:
                self._con.transaction_abort()
                raise OldapErrorUpdateFailed(f'Update of {self._owlclass_iri} failed. {modtime_shacl} {modtime_owl} {timestamp}')
        else:
            self._con.transaction_commit()
        self.clear_changeset()
        self._modified = timestamp
        self._contributor = self._con.userIri
        self._test_in_use = False
        cache = CacheSingletonRedis()
        cache.set(self._owlclass_iri, self)


    def __delete_shacl(self) -> str:
        sparql = f'#\n# SHALC: Delete "{self._owlclass_iri}" completely\n#\n'
        sparql += f"""
        WITH {self._graph}:shacl
        DELETE {{
            {self._owlclass_iri}Shape ?rattr ?rvalue .
            ?rvalue ?pattr ?pval .
            ?z rdf:first ?head ;
            rdf:rest ?tail .
        }}
        WHERE {{
            {self._owlclass_iri}Shape ?rattr ?rvalue .
            OPTIONAL {{
                ?rvalue ?pattr ?pval .
                OPTIONAL {{
                    ?pval rdf:rest* ?z .
                    ?z rdf:first ?head ;
                    rdf:rest ?tail .
                }}
                FILTER(isBlank(?rvalue))
            }}
        }}
        """
        return sparql

    def __delete_owl(self) -> str:
        sparql = f'#\n# OWL: Delete "{self._owlclass_iri}" completely\n#\n'
        sparql += f"""
        WITH {self._graph}:onto
        DELETE {{
            ?prop ?p ?v
        }}
        WHERE {{
            ?prop rdfs:domain {self._owlclass_iri.toRdf} .
            ?prop ?p ?v
        }} ;
        WITH {self._graph}:onto
        DELETE {{
            ?res ?prop ?value .
            ?value ?pp ?vv .
        }}
        WHERE {{
            BIND({self._owlclass_iri.toRdf} AS ?res)
            ?res ?prop ?value
            OPTIONAL {{
                ?value ?pp ?vv
                FILTER(isBlank(?value))
            }}
        }}
        """
        return sparql

    def delete(self) -> None:
        """
        Deletes the specified resource class if it is not in use and the logged-in user has
        the necessary permissions. This operation involves ensuring that no SHACL or RDF resources
        associated with the class remain and performs validations before committing the transaction.

        :raises OldapErrorNoPermission: If the logged-in user lacks the necessary permissions.
        :raises OldapErrorInUse: If the resource class is currently in use.
        :raises OldapErrorUpdateFailed: If the deletion process fails due to residual SHACL or RDF resources.

        :return: None
        """
        #
        # First we check if the logged-in user ("actor") has the permission to create resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = datetime.now()
        context = Context(name=self._con.context_name)
        sparql0 = self.in_use
        sparql = context.sparql_context
        sparql += self.__delete_shacl()
        if not self._externalOntology:
            sparql += ' ;\n'
            sparql += self.__delete_owl()

        self._con.transaction_start()
        result = self.safe_query(sparql0)
        if result['boolean']:
            self._con.transaction_abort()
            raise OldapErrorInUse(f'Cannot delete: resource class {self._owlclass_iri} is in use!')
        self.safe_update(sparql)

        sparql = context.sparql_context
        sparql += f"SELECT * FROM {self._graph}:shacl WHERE {{ {self._owlclass_iri}Shape ?p ?v }}"
        jsonobj = self.safe_query(sparql)
        res_shacl = QueryProcessor(context, jsonobj)

        if not self._externalOntology:
            sparql = context.sparql_context
            sparql += f"SELECT * FROM {self._graph}:onto WHERE {{ {self._owlclass_iri.toRdf} ?p ?v }}"
            jsonobj = self.safe_query(sparql)
            res_onto = QueryProcessor(context, jsonobj)
        else:
            res_onto = []
        if len(res_shacl) > 0 or len(res_onto) > 0:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Could not delete "{self._owlclass_iri}".')
        else:
            self._con.transaction_commit()
        cache = CacheSingletonRedis()
        cache.delete(self._owlclass_iri)



