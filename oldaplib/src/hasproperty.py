from copy import deepcopy
from enum import Enum
from functools import partial
from typing import Callable, Self, Any

from oldaplib.src.enums.action import Action
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.enums.haspropertyattr import HasPropertyAttr
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorInconsistency
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass, HasPropertyData
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@serializer
class PropType(Enum):
    INTERNAL = 1
    STANDALONE = 2
    EXTERNAL = 3


@serializer
class HasProperty(Model, Notify):
    """
    Represents a `HasProperty` model that integrates functionalities from both the `Model`
    and `Notify` classes. It provides extensive management for property attributes,
    notifications, and serialization.

    This class serves the purpose of managing `PropertyClass` objects or equivalent IRIs
    within the context of a given project. It offers capabilities such as notifying
    changes, serializing properties into dictionaries, and generating SHACL and OWL
    annotations for validation and reasoning purposes. The class also helps track
    updates to attributes or changes made to properties associated with a project.

    :ivar prop: The associated `PropertyClass` object or IRI of this property.
    :type prop: PropertyClass | Iri | None
    :ivar haspropdata: Represents combined data attributes (minCount, maxCount, order, group)
                      as a single `HasPropertyData` object.
    :type haspropdata: HasPropertyData
    """


    _prop: PropertyClass | Xsd_QName | None
    _project: Project | None
    _type: PropType | None

    def __init__(self, *,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 prop: PropertyClass | Xsd_QName | None = None,
                 notifier: Callable[[Xsd_QName], None] | None = None,
                 notify_data: Xsd_QName | None = None,
                 creator: Iri | None = None,  # DO NO USE! Only for jsonify!!
                 created: Xsd_dateTime | None = None,  # DO NO USE! Only for jsonify!!
                 contributor: Iri | None = None,  # DO NO USE! Only for jsonify!!
                 modified: Xsd_dateTime | None = None,  # DO NO USE! Only for jsonify!!
                 validate: bool = False,
                 _type: PropType | None = None,
                 **kwargs):
        """
        Initializes the class with the given parameters and configurations.

        This constructor sets up the internal properties and state, and handles specific
        initialization logic related to `PropertyClass`, notification handlers, and attributes.
        It also prepares the object to track changes and attributes defined in `HasPropertyAttr`.

        :param con: The connection interface used to interact with the related resources.
        :type con: IConnection
        :param project: The project instance associated with this object.
        :type project: Project
        :param prop: Optional; the property class or IRI associated with this object, or None.
        :param notifier: Optional; the callable function used for notification.
        :type notifier: Callable[[Iri], None] | None
        :param notify_data: Optional; additional data in the form of an IRI for notification.
        :type notify_data: Iri | None
        :param kwargs: Additional attributes to configure specific behaviors, passed as key-value pairs.

        :raises OldapErrorNotFound: If the given property class is not found.
        """
        Model.__init__(self, connection=con,
                       creator=creator,
                       created=created,
                       contributor=contributor,
                       modified=modified)
        Notify.__init__(self, notifier, notify_data)
        self._type = _type
        if isinstance(project, Project):
            self._project = project
        else:
            if not isinstance(project, (Iri, Xsd_NCName)):
                project = IriOrNCName(project, validate=validate)
            self._project = Project.read(self._con, project)
        if isinstance(prop, Xsd_QName):
            fixed_prop = Xsd_QName(str(prop).removesuffix("Shape"))
            try:
                self._prop = PropertyClass.read(self._con, self._project, fixed_prop)
                self._type = PropType.STANDALONE
            except OldapErrorNotFound as err:
                self._prop = fixed_prop
                self._type = PropType.EXTERNAL
        else:
            self._prop = prop
            if self._type is None:
                if prop.externalOntology:
                    self._type = PropType.EXTERNAL
                else:
                    self._type = PropType.INTERNAL
        self.set_attributes(kwargs, HasPropertyAttr)

        #
        # Check consistency for owl:FunctionalProperty. It must have a maxCount=1
        #
        if isinstance(self._prop, PropertyClass) and OwlPropertyType.FunctionalProperty in self._prop.type:
            if not self._attributes.get(HasPropertyAttr.MAX_COUNT):
                raise OldapErrorInconsistency(f'FunctionalProperty {self._prop.property_class_iri} must have maxCount=1')
            if self._attributes[HasPropertyAttr.MAX_COUNT] != 1:
                raise OldapErrorInconsistency(f'FunctionalProperty {self._prop.property_class_iri} must have maxCount=1')

        #
        # Check consistency for owl:InverseFunctionalProperty. It must have a cardinality of 1..1
        #
        if isinstance(self._prop, PropertyClass) and OwlPropertyType.InverseFunctionalProperty in self._prop.type:
            if not self._attributes.get(HasPropertyAttr.MIN_COUNT) or not self._attributes.get(HasPropertyAttr.MAX_COUNT):
                raise OldapErrorInconsistency(f'InverseFunctionalProperty {self._prop.property_class_iri} must have cardinality=1..1')
            if self._attributes[HasPropertyAttr.MIN_COUNT] != 1 or self._attributes[HasPropertyAttr.MAX_COUNT] != 1:
                raise OldapErrorInconsistency(f'InverseFunctionalProperty {self._prop.property_class_iri} must have cardinality=1..1')


        for attr in HasPropertyAttr:
            setattr(HasProperty, attr.value.fragment, property(
                partial(HasProperty._get_value, attr=attr),
                partial(HasProperty._set_value, attr=attr),
                partial(HasProperty._del_value, attr=attr)))
        self.update_notifier(notifier, notify_data)
        self._changeset = {}

    def update_notifier(self,
                        notifier: Callable[[AttributeClass | Xsd_QName], None] | None = None,
                        notify_data: HasPropertyAttr | Xsd_QName | None = None):
        self.set_notifier(notifier, notify_data)
        if isinstance(self._prop, PropertyClass):
            self._prop.set_notifier(self.notifier, self._prop.property_class_iri)
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict() | {
            'project': self._project.projectShortName,
            '_type': self._type,
            'prop': self._prop
        }

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
        instance._changset = deepcopy(self._changeset, memo)
        instance._prop = deepcopy(self._prop)  # no deepcopy here (????)
        return instance

    def __str__(self) -> str:
        iri = self._prop.property_class_iri if isinstance(self._prop, PropertyClass) else self._prop
        s = f'HasProperty: {iri}\n'
        s += Model.__str__(self)
        return s

    @property
    def type(self) -> PropType:
        return self._type

    @property
    def prop(self) -> PropertyClass | Xsd_QName | None:
        return self._prop

    @prop.setter
    def prop(self, prop: PropertyClass | Xsd_QName) -> None:
        self._prop = prop

    @property
    def haspropdata(self) -> HasPropertyData:
        return HasPropertyData(minCount=self._attributes.get(HasPropertyAttr.MIN_COUNT, None),
                               maxCount=self._attributes.get(HasPropertyAttr.MAX_COUNT, None),
                               order=self._attributes.get(HasPropertyAttr.ORDER, None),
                               group=self._attributes.get(HasPropertyAttr.GROUP, None))

    def clear_changeset(self) -> None:
        if hasattr(self._prop, 'clear_changeset'):
            self._prop.clear_changeset()
        super().clear_changeset()

    def notifier(self, attr: HasPropertyAttr | Iri | Xsd_QName) -> None:
        #if attr == HasPropertyAttr.PROP:
        #    return
        if isinstance(attr, HasPropertyAttr):
            self._changeset[attr] = AttributeChange(self._attributes[attr], Action.MODIFY)
        elif isinstance(attr, Xsd_QName):
            self._changeset[attr] = AttributeChange(None, Action.MODIFY)
        self.notify()

    def create_shacl(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        if self._attributes.get(HasPropertyAttr.MIN_COUNT, None) is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:minCount {self._attributes[HasPropertyAttr.MIN_COUNT].toRdf}'
        if self._attributes.get(HasPropertyAttr.MAX_COUNT, None) is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:maxCount {self._attributes[HasPropertyAttr.MAX_COUNT].toRdf}'
        if self._attributes.get(HasPropertyAttr.ORDER, None) is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:order {self._attributes[HasPropertyAttr.ORDER].toRdf}'
        if self._attributes.get(HasPropertyAttr.GROUP, None) is not None:
            sparql += f' ;\n{blank:{indent * indent_inc}}sh:group {self._attributes[HasPropertyAttr.GROUP].toRdf}'
        return sparql

    def create_owl(self, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        min_count = Xsd_nonNegativeInteger(int(self._attributes[HasPropertyAttr.MIN_COUNT])) if self._attributes.get(HasPropertyAttr.MIN_COUNT) else None
        max_count = Xsd_nonNegativeInteger(int(self._attributes[HasPropertyAttr.MAX_COUNT])) if self._attributes.get(HasPropertyAttr.MAX_COUNT) else None

        if min_count and max_count and min_count == max_count:
            tmp = Xsd_nonNegativeInteger(min_count)
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:qualifiedCardinality {tmp.toRdf}'
        else:
            if min_count:
                tmp = Xsd_nonNegativeInteger(min_count)
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:minQualifiedCardinality {tmp.toRdf}'
            if max_count:
                tmp = Xsd_nonNegativeInteger(max_count)
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:maxQualifiedCardinality {tmp.toRdf}'
        return sparql

    def update_shacl(self,
                     graph: Xsd_NCName,
                     resclass_iri: Xsd_QName,
                     propclass_iri: Xsd_QName,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for attr, change in self._changeset.items():
            if isinstance(attr, Xsd_QName):  # if it's an IRI, the attached PropertyClass has changed. We don't process this here
                continue
            sparql = f'WITH {graph}:shacl\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {attr.value} {change.old_value.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            if change.action != Action.DELETE:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {attr.value} {self._attributes[attr].toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}{resclass_iri}Shape sh:property ?prop .\n'
            if isinstance(self._prop, Xsd_QName) or self._prop.internal is None:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:node {propclass_iri}Shape.\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {propclass_iri} .\n'
            if change.action != Action.CREATE:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {attr.value} {change.old_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)
        sparql = " ;\n".join(sparql_list)
        return sparql

    def update_owl(self,
                     graph: Xsd_NCName,
                     resclass_iri: Xsd_QName,
                     propclass_iri: Xsd_QName,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        if HasPropertyAttr.MIN_COUNT in self._changeset or HasPropertyAttr.MAX_COUNT in self._changeset:
            sparql = f'WITH {graph}:onto\n'
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:qualifiedCardinality ?val_qualified .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:minQualifiedCardinality ?val_min .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:maxQualifiedCardinality ?val .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

            #
            # Convert to xsd:nonNegativeInteger or None
            #
            min_count = Xsd_nonNegativeInteger(int(self._attributes[HasPropertyAttr.MIN_COUNT])) if self._attributes.get(HasPropertyAttr.MIN_COUNT) else None
            max_count = Xsd_nonNegativeInteger(int(self._attributes[HasPropertyAttr.MAX_COUNT])) if self._attributes.get(HasPropertyAttr.MAX_COUNT) else None

            if min_count or max_count:
                sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                if min_count and max_count and min_count == max_count:
                    tmp = Xsd_nonNegativeInteger(min_count)
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:qualifiedCardinality {tmp.toRdf} .\n'
                else:
                    if min_count:
                        tmp = Xsd_nonNegativeInteger(min_count)
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:minQualifiedCardinality {tmp.toRdf} .\n'
                    if max_count:
                        tmp = Xsd_nonNegativeInteger(max_count)
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:maxQualifiedCardinality {tmp.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}{resclass_iri} rdfs:subClassOf ?prop .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:onProperty {propclass_iri} .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}OPTIONAL {{ ?prop owl:qualifiedCardinality ?val_qualified . }}\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}OPTIONAL {{ ?prop owl:minQualifiedCardinality ?val_min . }}\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}OPTIONAL {{ ?prop owl:maxQualifiedCardinality ?val_max . }}\n'
            sparql += f'{blank:{indent * indent_inc}}}}'

            return sparql
        else:
            return ''
