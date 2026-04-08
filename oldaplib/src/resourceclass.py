import logging
import textwrap
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
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.construct_processor import ConstructResultDict, ConstructProcessor
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
from oldaplib.src.propertyclass import PropertyClass, Attributes, PropTypes
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
    _graph: Xsd_NCName
    _project: Project
    _sysproject: Project = None
    _sharedproject: Project = None
    _owlclass_iri: Xsd_QName | None
    _attributes: ResourceClassAttributesContainer
    _properties: dict[Xsd_QName, PropertyClass]
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
                    try:
                        sucla = ResourceClass.read(self._con, self._project, scval)
                    except OldapErrorNotFound as e:
                        sucla = None
                    except:
                        raise
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
                 properties: List[PropertyClass] | None = None,
                 notifier: Callable[[PropClassAttr], None] | None = None,
                 notify_data: PropClassAttr | None = None,
                 creator: Iri | None = None,  # DO NO USE! Only for jsonify!!
                 created: Xsd_dateTime | None = None,  # DO NO USE! Only for jsonify!!
                 contributor: Iri | None = None,  # DO NO USE! Only for jsonify!!
                 modified: Xsd_dateTime | None = None,  # DO NO USE! Only for jsonify!!
                 validate: bool = False,
                 **kwargs):
        Model.__init__(self,
                       connection=con,
                       creator=con.userIri,
                       created=created,
                       contributor=con.userIri,
                       modified=modified,
                       validate=validate)
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
        # now we add, if necessary, the mandatory superclass "oldap:Thing". Every ResourceClass in OLDAP must be
        # a subclass of "oldap:Thing"! We don't do it for system things with a prefix of "oldap".
        #
        if self._owlclass_iri.prefix != "oldap":
            thing_iri = Xsd_QName('oldap:Thing', validate=False)
            if self._owlclass_iri != thing_iri:
                if not new_kwargs.get(ResClassAttribute.SUPERCLASS.value.fragment):  # no superclass defined
                    thing = ResourceClass.read(self._con, self._sysproject, thing_iri)
                    new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment] = {thing_iri: thing}
                else:
                    if not thing_iri in new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment]:
                        thing = ResourceClass.read(self._con, self._sysproject, thing_iri)
                        new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment][thing_iri] = thing
        self.set_attributes(new_kwargs, ResClassAttribute)

        #
        # Check and assign properties
        #
        self._properties = {}
        if properties is not None:
            for prop in properties:
                if not isinstance(prop, PropertyClass):
                   raise TypeError('Property must be of type PropertyClass')
                prop.inResourceClass = owlclass_iri
                self._properties[prop.property_class_iri] = prop

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
            'properties': [x for x in self._properties.values()],
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

    def _change_setter(self, key: ResClassAttribute | Xsd_QName, value: AttributeParams | PropertyClass) -> None:
        if not isinstance(key, (ResClassAttribute, Xsd_QName)):
            raise ValueError(f'Invalid key type {type(key)} of key {key}')
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, key)

        if isinstance(key, ResClassAttribute):
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

        elif isinstance(key, Xsd_QName):  # Iri, we add a PropertyClass
            if self._properties.get(key) is None:  # Property not set -> CREATE action
                self._changeset[key] = ResourceClassPropertyChange(None, Action.CREATE, False)
                value.inResourceClass = self._owlclass_iri  # we need to access the private variable here
                value.property_class_iri = key  # we need to access the private variable here
                self._properties[key] = value
            else:  # REPLACE action
                if self._changeset.get(key) is None:
                    self._changeset[key] = ResourceClassPropertyChange(self._properties[key], Action.REPLACE, True)
                else:
                    self._changeset[key] = ResourceClassPropertyChange(self._changeset[key].old_value, Action.REPLACE, False)
                value.inResourceClass = self._owlclass_iri
                value.property_class_iri = key
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


    def __getitem__(self, key: ResClassAttribute | Xsd_QName) -> AttributeTypes | PropertyClass | Xsd_QName:
        if isinstance(key, ResClassAttribute):
            return super().__getitem__(key)
        elif isinstance(key, Xsd_QName):
            return self._properties.get(key)
        else:
            return None

    def get(self, key: ResClassAttribute | Xsd_QName) -> AttributeTypes | PropertyClass | Xsd_QName | None:
        if isinstance(key, ResClassAttribute):
            return self._attributes.get(key)
        elif isinstance(key, Xsd_QName):
            return self._properties.get(key)
        else:
            return None

    def __setitem__(self, key: ResClassAttribute | Xsd_QName, value: AttributeParams | PropertyClass) -> None:
        self._change_setter(key, value)

    def __delitem__(self, key: ResClassAttribute | Xsd_QName) -> None:
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
    def properties(self) -> dict[Xsd_QName, PropertyClass]:
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
        for qname, prop in sorted_properties:
            s += f'{blank:{indent*2}}{qname} = {prop} (minCount={prop.minCount}, maxCount={prop.maxCount}\n'
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
        query += textwrap.dedent(f"""
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
        """)
        return query

    @classmethod
    def read(cls,
             con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             owl_class_iri: Xsd_QName | str,  # no Shape-ending!
             ignore_cache: bool = False,
             validate: bool = False):
        project_inst = None
        if isinstance(project, Project):
            project_inst = project
        else:
            if not isinstance(project, (Iri, Xsd_NCName)):
                tmp = IriOrNCName(project, validate=validate)
                project_inst = Project.read(con=con, projectIri_SName=tmp, ignore_cache=ignore_cache)
        if not project_inst:
            raise OldapErrorInconsistency(f'Project invalid!')

        if not isinstance(owl_class_iri, Xsd_QName):
            resclass_iri = Xsd_QName(owl_class_iri, validate=True)
        else:
            resclass_iri = owl_class_iri

        cache = CacheSingletonRedis()
        if not ignore_cache:
            tmp = cache.get(owl_class_iri, connection=con)
            if tmp is not None:
                tmp.update_notifier()
                return tmp

        shape = Xsd_QName(resclass_iri) + 'Shape'
        obj = ConstructProcessor.query_shacl(con=con,
                                             project=project_inst,
                                             shape_iri=shape)
        shacl_resobj = obj.get(shape, None)
        if shacl_resobj is None:
            raise OldapErrorNotFound(f'Resource shape "{resclass_iri}" not found in "{project.projectShortName}:shacl"!')

        obj = ConstructProcessor.query_onto(con=con,
                                            project=project_inst,
                                            class_iri=resclass_iri)
        onto_resobj = obj.get(resclass_iri, None)
        if onto_resobj is None:
            raise OldapErrorInconsistency(f'Resource "{resclass_iri}" not found in "{project.projectShortName}:onto"!')

        superclass = None

        shacl_superclasses = set()
        onto_superclasses = set()
        if shacl_resobj.get(Xsd_QName('sh:node'), None) is not None:
            tmp = set(shacl_resobj[Xsd_QName('sh:node')]) if isinstance(shacl_resobj[Xsd_QName('sh:node')], list) else set([shacl_resobj[Xsd_QName('sh:node')]])
            shacl_superclasses = {Xsd_QName(x.prefix, str(x.fragment).removesuffix('Shape')) for x in tmp}
        if onto_resobj.get(Xsd_QName('rdfs:subClassOf'), None) is not None:
            onto_superclasses = set(onto_resobj[Xsd_QName('rdfs:subClassOf')]) if isinstance(onto_resobj[Xsd_QName('rdfs:subClassOf')], list) else set([onto_resobj[Xsd_QName('rdfs:subClassOf')]])
        if not shacl_superclasses.issubset(onto_superclasses):
            raise OldapErrorInconsistency(f'Superclasses inconsistent between SHACL and OWL! shacl: {shacl_superclasses} ≠ omto: {onto_superclasses}!')

        superclass = [x for x in onto_superclasses]

        creator = shacl_resobj.get('dcterms:creator')
        created = shacl_resobj.get('dcterms:created')
        modified = shacl_resobj.get('dcterms:modified')
        contributor = shacl_resobj.get('dcterms:contributor')

        properties: list[PropertyClass] = []
        tmp = shacl_resobj.get(Xsd_QName("sh:property"), [])
        if not isinstance(tmp, list):
            tmp = [tmp]
        for propobj in tmp:
            if propobj.get(Xsd_QName("sh:path"), None) is None:
                raise OldapErrorInconsistency(f'Resource shape "{shape}" has invalid property without "sh:path"!')
            prop_iri = Xsd_QName(propobj[Xsd_QName("sh:path")])
            kwargs = {k: v for k, v in propobj.items() if k not in {Xsd_QName("sh:path"),
                                                                  Xsd_QName("rdf:type"),
                                                                  Xsd_QName("sh:targetClass")}}
            tmp = {}
            for k, v in kwargs.items():
                if k == Xsd_QName("sh:class"):
                    tmp['toClass'] = v
                elif k == Xsd_QName("sh:in"):
                    tmp['inSet'] = v
                else:
                    tmp[k.fragment] = v
            kwargs = tmp
            property = PropertyClass(con=con,
                                     project=project,
                                     property_class_iri=prop_iri,
                                     creator=creator,
                                     created=created,
                                     modified=modified,
                                     contributor=contributor,
                                     _inResourceClass=resclass_iri,
                                     **kwargs)
            property.read_owl()
            properties.append(property)

        kwargs = {k.fragment: v for k, v in shacl_resobj.items() if k not in {Xsd_QName("sh:property"),  # it's a sh:property BNode
                                                                              Xsd_QName("sh:path"),  # corresponts to the prop_iri
                                                                              Xsd_QName("rdf:type"),  # TODO: No longer needed?
                                                                              Xsd_QName("sh:node"),  # Points to the superclass
                                                                              Xsd_QName("sh:targetClass")}}
        if superclass:
            kwargs['superclass'] = superclass
        resclass = cls(con=con,
                       project=project,
                       owlclass_iri=resclass_iri,
                       properties=properties,
                       **kwargs)
        cache.set(resclass_iri, resclass)

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

        for iri, prop in self._properties.items():
            sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property ['
            sparql += prop.property_node_shacl(indent=3, indent_inc=indent_inc)
            sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}]'
        sparql += ' .\n'
        return sparql

    def create_owl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owlclass_iri} rdf:type owl:Class'
        if self._attributes.get(ResClassAttribute.SUPERCLASS) is not None:
            sc = {x.toRdf for x in self._attributes[ResClassAttribute.SUPERCLASS].keys()}
            if Xsd_QName('oldap:Thing', validate=False).toRdf not in sc:
                sc.add(Xsd_QName('oldap:Thing', validate=False).toRdf)
        else:
            sc = {Xsd_QName('oldap:Thing', validate=False).toRdf}
        valstr = ", ".join(sc)
        if valstr:
            sparql += f' ;\n{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {valstr}'

        if self._properties:
            sparql += ' .\n\n'

        for iri, prop in self._properties.items():
            sparql += prop.create_owl(indent=2, indent_inc=indent_inc)
        return sparql

    def set_creation_metadata(self, timestamp: Xsd_dateTime) -> None:
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.__from_triplestore = True

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
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

        try:
            modtime_shacl = self.read_modtime_shacl(context=context, graph=self._graph)
        except:
            self._con.transaction_abort()
            raise
        if modtime_shacl == timestamp:
            self._con.transaction_commit()
            self.set_creation_metadata(timestamp=timestamp)
        else:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Creating resource "{self._owlclass_iri}" failed.')
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

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
            f.write(self.create_owl(timestamp=timestamp))
            f.write(f'{blank:{indent * indent_inc}}}}\n')


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
        # we loop over all items in the changeset of the resource
        #
        for item, change in self._changeset.items():
            item: Union[AttributeClass, Xsd_QName, PropertyClass]
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
                                                ele=RdfModifyItem(item.value, change.old_value, self._attributes.get(item)),
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
                        if isinstance(self._properties[propiri], PropertyClass):
                            sparql = f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
                            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
                            sparql += self._properties[propiri].create_shacl(timestamp=timestamp,
                                                                              owlclass_iri=self._owlclass_iri,
                                                                              indent=2)
                            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                            sparql += f'{blank:{indent * indent_inc}}}}\n'
                        if sparql:
                            sparql_list.append(sparql)
                    case Action.DELETE:
                        #
                        # We delete a HasPropertyClass. If the property is internal, we delete it
                        # TODO: check if th PropertyClass is used ba a some data
                        #
                        sparql = change.old_value.delete_shacl()
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
                        sparql = self._properties[propiri].update_shacl(owlclass_iri=self._owlclass_iri,
                                                                        timestamp=timestamp)
                        if sparql:
                            sparql_list.append(sparql)
            else:
                raise OldapErrorInconsistency('Impossible error!')
        #
        # Updating the timestamp and contributor ID
        #
        sparql = RdfModifyRes.update_timestamp_contributors(contributor=self._con.userIri,
                                                            timestamp=timestamp,
                                                            old_timestamp=self._modified,
                                                            iri=self._owlclass_iri,
                                                            graph=Xsd_QName(f'{self._graph}:shacl'))

        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def __add_new_property_ref_onto(self, *,
                                    prop: PropertyClass | Xsd_QName,
                                    indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}INSERT DATA {{#E\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
        sparql += self.create_owl(indent=2, indent_inc=indent_inc)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
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
        # we loop over all items in the changeset of the resource
        #
        for item, change in self._changeset.items():
            item: Union[ResClassAttribute, Xsd_QName]
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
                        if isinstance(self._properties[propiri], PropertyClass):
                            sparql = f'{blank:{indent * indent_inc}}INSERT DATA {{#F\n'
                            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
                            sparql += self._properties[propiri].create_owl(indent=2, indent_inc=indent_inc)
                            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                            sparql += f'{blank:{indent * indent_inc}}}}\n'
                            sparql_list.append(sparql)
                        else:
                            raise OldapErrorInconsistency(f'Something wrong with property "{propiri}"! Has type "{type(self._properties[propiri]).__name__}" ')
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
                        sparql = change.old_value.delete_owl()
                        sparql_list.append(sparql)
                        sparql = change.old_value.delete_owl_subclass_str(owlclass_iri=self._owlclass_iri)
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
                                sparql = self._properties[propiri].update_owl(owlclass_iri=self._owlclass_iri)
                                sparql_list.append(sparql)
                            elif isinstance(key, Xsd_QName):
                                sparql = self._properties[propiri].update_owl(owlclass_iri=self._owlclass_iri)
                                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = RdfModifyRes.update_timestamp_contributors(contributor=self._con.userIri,
                                                            timestamp=timestamp,
                                                            old_timestamp=self._modified,
                                                            iri=self._owlclass_iri,
                                                            graph=Xsd_QName(f'{self._graph}:onto'))
        sparql_list.append(sparql)

        #
        # now remove empty sparql statements (coming from changes that only affect SHACL but not OWL)!
        #
        sparql_list = [sparql for sparql in sparql_list if sparql.strip()]

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
        logger = logging.getLogger(__name__)

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
                if change.action != Action.CREATE and self._properties.get(item) is not None:
                    for i, c in self._properties[item].changeset.items():
                        match(i):
                            case HasPropertyAttr.MIN_COUNT:
                                if self._properties[item][HasPropertyAttr.MIN_COUNT] is None:
                                    continue
                                if self._properties[item].changeset[HasPropertyAttr.MIN_COUNT].old_value is None:
                                    self._test_in_use = True
                                    continue
                                if self._properties[item][HasPropertyAttr.MIN_COUNT] > self._properties[item].changeset[HasPropertyAttr.MIN_COUNT].old_value:
                                    self._test_in_use = True
                            case HasPropertyAttr.MAX_COUNT:
                                if self._properties[item][HasPropertyAttr.MAX_COUNT] is None:
                                    continue
                                if self._properties[item].changeset[HasPropertyAttr.MAX_COUNT].old_value is None:
                                    self._test_in_use = True
                                    continue
                                if self._properties[item][HasPropertyAttr.MAX_COUNT] < self._properties[item].changeset[HasPropertyAttr.MAX_COUNT].old_value:
                                    self._test_in_use = True


        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)

        # sparql0 = ''
        # if check_use:
        #     sparql0 = self.in_use

        sparql1 = context.sparql_context
        sparql1 += self.__update_shacl(timestamp=timestamp)

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
        self.safe_update(sparql2)

        try:
            modtime_shacl = self.read_modtime_shacl(context=context, graph=self._graph)
        except:
            self._con.transaction_abort()
            raise
        if modtime_shacl == timestamp:
            self._con.transaction_commit()
        else:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Update of {self._owlclass_iri} failed. {modtime_shacl} {timestamp}')
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

        sparql = context.sparql_context
        sparql += f"SELECT * FROM {self._graph}:onto WHERE {{ {self._owlclass_iri.toRdf} ?p ?v }}"
        jsonobj = self.safe_query(sparql)
        res_onto = QueryProcessor(context, jsonobj)
        if len(res_shacl) > 0 or len(res_onto) > 0:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Could not delete "{self._owlclass_iri}".')
        else:
            self._con.transaction_commit()
        cache = CacheSingletonRedis()
        cache.delete(self._owlclass_iri)



