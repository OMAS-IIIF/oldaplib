from copy import deepcopy
from datetime import datetime
from functools import partial
from typing import Any, Self

from elementpath.datatypes import NCName

from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.externalontologyattr import ExternalOntologyAttr
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@serializer
class ExternalOntology(Model):
    """Class representing external ontologies.

    This class provides methods for managing external ontologies.
    """
    __extonto_qname: Xsd_QName | None
    __graph: Xsd_NCName | None

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str |None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 graph: Xsd_NCName | str,
                 validate: bool = False,
                 **kwargs):
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified,
                         validate=validate)
        if isinstance(graph, Xsd_NCName):
            self.__graph = graph
        else:
            self.__graph = Xsd_NCName(graph, validate=validate)
        self.set_attributes(kwargs, ExternalOntologyAttr)
        self.__extonto_qname = Xsd_QName(self.__project.projectShortName, self._attributes[ExternalOntologyAttr.PREFIX])

        for attr in ExternalOntologyAttr:
            setattr(ExternalOntology, attr.value.fragment, property(
                partial(ExternalOntology._get_value, attr=attr),
                partial(ExternalOntology._set_value, attr=attr),
                partial(ExternalOntology._del_value, attr=attr)))
        self._changeset = {}

    def update_notifier(self):
        for attr, value in self._attributes.items():
            if getattr(value, 'set_notifier', None) is not None:
                value.set_notifier(self.notifier, attr)

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict() | {
            'graph': self.__graph
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
        # Copy internals of Model:
        instance._attributes = deepcopy(self._attributes, memo)
        instance._changset = deepcopy(self._changeset, memo)
        instance.__graph = deepcopy(self.__graph, memo)
        instance.__extonto_qname = deepcopy(self.__extonto_qname, memo)
        return instance

    def check_for_permissions(self) -> (bool, str):
        """
        Internal method to check if a user may modify the permission set.
        :return: a tuple with a boolean (True, False) and the error message (or "OK")
        """
        #
        # First we check if the logged-in user ("actor") has the ADMIN_PERMISSION_SETS permission for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK"
        else:
            if actor.inProject.get(self.__project.projectIri) is None:
                return False, f'Actor has no ADMIN_MODEL permission for project {self.__project.projectIri}'
            else:
                if AdminPermission.ADMIN_MODEL not in actor.inProject.get(self.__project.projectIri):
                    return False, f'Actor has no ADMIN_MODEL permission for project {self.__project.projectIri}'
            return True, "OK"

    def notifier(self, what: ExternalOntologyAttr, value: Any = None) -> None:
        self._changeset[what] = AttributeChange(None, Action.MODIFY)


    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self._con is None:
            raise OldapError("Cannot create: no connection")

        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime()

        context = Context(name=self._con.context_name)
        blank = ''
        sparql1 = context.sparql_context
        sparql1 += f"""
        SELECT ?onto
        FROM {self._project.projectShortName}:shacl
        WHERE {{
            ?onto a oldap:ExternalOntology .
            FILTER(?permset = {self.__extonto_qname.toRdf})       
        }}
        """

        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:shacl {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}} {self.__permset_iri.toRdf} a oldap:ExternalOntology'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._con.userIri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        for attr, value in self._attributes.items():
            if attr.value.prefix == 'virtual' or not value:
                continue
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}{attr.value.toRdf} {value.toRdf}'
        sparql += f'\n{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

