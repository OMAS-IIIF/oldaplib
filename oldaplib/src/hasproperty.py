from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Callable, Self, Any

from oldaplib.src.enums.action import Action
from oldaplib.src.enums.haspropertyattr import HasPropertyAttr
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.propertyclass import PropertyClass, HasPropertyData
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger


class HasProperty(Model, Notify):
    _prop: PropertyClass | Iri | None

    def __init__(self, *,
                 con: IConnection,
                 prop: PropertyClass | Iri | None = None,
                 notifier: Callable[[Iri], None] | None = None,
                 notify_data: Iri | None = None,
                 **kwargs):
        Model.__init__(self, connection=con)
        Notify.__init__(self, notifier, notify_data)
        self._prop = prop
        self.set_attributes(kwargs, HasPropertyAttr)

        for attr in HasPropertyAttr:
            setattr(HasProperty, attr.value.fragment, property(
                partial(HasProperty._get_value, attr=attr),
                partial(HasProperty._set_value, attr=attr),
                partial(HasProperty._del_value, attr=attr)))
        self._changeset = {}

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
    def prop(self) -> PropertyClass:
        return self._prop

    @prop.setter
    def prop(self, prop: PropertyClass) -> None:
        self._prop = prop

    @property
    def haspropdata(self) -> HasPropertyData:
        return HasPropertyData(minCount=self._attributes.get(HasPropertyAttr.MIN_COUNT, None),
                               maxCount=self._attributes.get(HasPropertyAttr.MAX_COUNT, None),
                               order=self._attributes.get(HasPropertyAttr.ORDER, None),
                               group=self._attributes.get(HasPropertyAttr.GROUP, None))

    def notifier(self, attr: HasPropertyAttr) -> None:
        if attr == HasPropertyAttr.PROP:
            return
        self._changeset[attr] = AttributeChange(self._attributes[attr], Action.MODIFY)
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

    def create_owl(self, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        min_count = Xsd_nonNegativeInteger(int(self._attributes[HasPropertyAttr.MIN_COUNT])) if self._attributes.get(HasPropertyAttr.MIN_COUNT) else None
        max_count = Xsd_nonNegativeInteger(int(self._attributes[HasPropertyAttr.MAX_COUNT])) if self._attributes.get(HasPropertyAttr.MAX_COUNT) else None

        if min_count and max_count and min_count == max_count:
            sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:qualifiedCardinality {min_count.toRdf}'
        else:
            if min_count:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:minQualifiedCardinality {min_count.toRdf}'
            if max_count:
                sparql += f' ;\n{blank:{(indent + 1) * indent_inc}}owl:maxQualifiedCardinality {max_count.toRdf}'
        return sparql

    def update_shacl(self,
                     graph: Xsd_NCName,
                     resclass_iri: Iri,
                     propclass_iri: Iri,
                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        for attr, change in self._changeset.items():
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
            if isinstance(self._prop, Iri) or self._prop.internal is None:
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
                     resclass_iri: Iri,
                     propclass_iri: Iri,
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
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:qualifiedCardinality {min_count.toRdf} .\n'
                else:
                    if min_count:
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:minQualifiedCardinality {min_count.toRdf} .\n'
                    if max_count:
                        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:maxQualifiedCardinality {max_count.toRdf} .\n'
                sparql += f'{blank:{indent * indent_inc}}}}\n'

            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}{resclass_iri} rdfs:subClassOf ?prop .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop owl:onProperty {propclass_iri} .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}OPTIONAL {{ ?prop owl:qualifiedCardinality ?val_qualified . }}\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}OPTIONAL {{ ?prop owl:minQualifiedCardinality ?val_min . }}\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}OPTIONAL {{ ?prop owl:maxQualifiedCardinality ?val_max . }}\n'
            sparql += f'{blank:{indent * indent_inc}}}}'

            return sparql
