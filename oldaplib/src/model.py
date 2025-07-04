import json
from copy import deepcopy
from datetime import datetime
from enum import Enum
from pprint import pprint
from typing import Set, Dict, Any, Self

from oldaplib.src.connection import Connection
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.numeric import Numeric
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorType, OldapErrorImmutable, OldapErrorValue
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection


#@strict
@serializer
class Model:
    _con: IConnection
    _changed: Set[str]
    _creator: Iri | None
    _created: Xsd_dateTime | None
    _contributor: Iri | None
    _modified: Xsd_dateTime | None
    _attributes: dict[Enum, Any]
    _changeset: dict[AttributeClass | Iri, AttributeChange]
    _validate: bool

    def __init__(self, *,
                 connection: IConnection,
                 creator: Iri | str | None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | str | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 validate: bool = False) -> None:
        if not isinstance(connection, IConnection):
            raise OldapError('"connection"-parameter must be an instance of IConnection')
        self._validate = validate
        self._con = connection
        if not creator:
            creator = self._con.userIri
        if not contributor:
            contributor = self._con.userIri

        self._creator = Iri(creator, validate=validate)
        self._created = Xsd_dateTime(created, validate=validate)
        self._contributor = Iri(contributor, validate=validate)
        self._modified = Xsd_dateTime(modified, validate=validate)
        self._attributes = {}
        self._changeset = {}

    def _as_dict(self) -> dict[str, Any]:
        return {
            **({"creator": self._creator} if self._creator is not None else {}),
            **({"created": self._created} if self._created is not None else {}),
            **({"contributor": self._contributor} if self._contributor is not None else {}),
            **({"modified": self._modified} if self._modified is not None else {}),
        }

    def __deepcopy__(self, memo: Dict[int, Any]) -> 'Model':
        cls = self.__class__
        instance = cls.__new__(cls)
        memo[id(self)] = instance
        instance._creator = deepcopy(self._creator, memo=memo)
        instance._created = deepcopy(self._created, memo=memo)
        instance._contributor = deepcopy(self._contributor, memo=memo)
        instance._modified = deepcopy(self._modified, memo=memo)
        instance._attributes = deepcopy(self._attributes, memo=memo)
        instance._changeset = {}

        return instance

    def check_consistency(self, attr: AttributeClass, value: Any) -> None:
        pass

    def pre_transform(self, attr: AttributeClass, value: Any, validate: bool = False) -> Any:
        return value

    def cleanup_setter(self, attr: AttributeClass, value: Any) -> None:
        pass

    def notifier(self, attr: AttributeClass, value: Any) -> None:
        pass

    def __str__(self) -> str:
        res = f'Creation: {self._created} by {self._creator}\n'
        res += f'Modified: {self._modified} by {self._contributor}\n'
        for attr, value in self._attributes.items():
            res += f'{attr} ({attr.value}): {value}\n'
        return res

    def __getitem__(self, attr: AttributeClass) -> Any:
        return self._attributes.get(attr)

    def get(self, attr: AttributeClass) -> Any:
        return self._attributes.get(attr)

    def __setitem__(self, attr: AttributeClass, value: Any) -> None:
        self._change_setter(attr, value)

    def __delitem__(self, attr: AttributeClass) -> None:
        if self._attributes.get(attr) is not None:
            self._changeset[attr] = AttributeChange(self._attributes[attr], Action.DELETE)
            del self._attributes[attr]

    # def __delattr__(self, attrstr: str) -> None:
    #     try:
    #         attr = AttributeClass.from_name(attrstr)
    #     except ValueError:
    #         raise OldapErrorValue(f'Nonexisting attribute: "{attrstr}"')
    #     if self._attributes.get(attr) is not None:
    #         self._changeset[attr] = AttributeChange(self._attributes[attr], Action.DELETE)
    #         del self._attributes[attr]

    def set_attributes(self, arguments: dict[str, Any], Attributes: type[Enum]) -> None:
        for name, value in arguments.items():
            if not isinstance(value, (bool, Xsd_boolean)) and not value:
                continue
            attr = Attributes.from_name(name)
            try:
                self._attributes[attr] = value if isinstance(value, attr.datatype) else attr.datatype(value, validate=self._validate)
            except ValueError as err:
                raise OldapErrorValue(err)
            if hasattr(self._attributes[attr], 'set_notifier'):
                self._attributes[attr].set_notifier(self.notifier, attr)
        for attr in Attributes:
            if attr.mandatory and not self._attributes.get(attr):
                raise OldapErrorType(f'Mandatory parameter {attr.name} is missing.')

    def _get_value(self: Self, attr: AttributeClass) -> Any | None:
        tmp = self._attributes.get(attr)
        if attr.datatype != Xsd_boolean and not tmp:
            return None
        return tmp

    def _set_value(self: Self, value: Any, attr: AttributeClass) -> None:
        self._change_setter(attr, value)

    def _del_value(self: Self, attr: AttributeClass) -> None:
        self._changeset[attr] = AttributeChange(self._attributes[attr], Action.DELETE)
        del self._attributes[attr]
        if hasattr(self, "notify"):
            self.notify()
        self.cleanup_setter(attr, None)

    def _change_setter(self, attr: AttributeClass, value: Any) -> None:
        if value is not None:
            if self._attributes.get(attr) == value:
                return
            if attr.immutable:
                raise OldapErrorImmutable(f'Attribute {attr.value} is immutable.')
            self.check_consistency(attr, value)
            value = self.pre_transform(attr, value, validate=self._validate)
        if self._attributes.get(attr) is None:
            if self._changeset.get(attr) is None:
                self._changeset[attr] = AttributeChange(None, Action.CREATE)
        else:
            if value is None:
                if self._changeset.get(attr) is None:
                    self._changeset[attr] = AttributeChange(deepcopy(self._attributes[attr]), Action.DELETE)
            else:
                if self._changeset.get(attr) is None:
                    self._changeset[attr] = AttributeChange(deepcopy(self._attributes[attr]), Action.REPLACE)
        if value is None:
            del self._attributes[attr]
        else:
            if not isinstance(value, attr.datatype):
                self._attributes[attr] = attr.datatype(value, validate=True)
            else:
                self._attributes[attr] = value
            if hasattr(self._attributes[attr], 'set_notifier') and hasattr(self, 'notifier'):
                self._attributes[attr].set_notifier(self.notifier, attr)
        if hasattr(self, "notify"):
            self.notify()
        self.cleanup_setter(attr, value)

    @property
    def changeset(self) -> Dict[AttributeClass, AttributeChange]:
        """
        Return the changeset, that is dicst with information about all properties that have benn changed.
        This method is only for internal use or debugging...
        :return: A dictionary of all changes
        :rtype: Dict[ProjectAttr, ProjectAttrChange]
        """
        return self._changeset

    def clear_changeset(self) -> None:
        """
        Clear the changeset. This method is only for internal use or debugging...
        :return: None
        """
        for item in self._attributes:
            if hasattr(self._attributes[item], 'clear_changeset'):
                self._attributes[item].clear_changeset()
        self._changeset = {}

    @property
    def creator(self) -> Iri | None:
        """
        The creator of the project.
        :return: Iri of the creator of the project.
        :rtype: Iri | None
        """
        return self._creator

    @property
    def created(self) -> Xsd_dateTime | None:
        """
        The creation date of the project.
        :return: Creation date of the project.
        :rtype: Xsd_dateTime | None
        """
        return self._created

    @property
    def contributor(self) -> Iri | None:
        """
        The contributor of the project as Iri.
        :return: Iri of the contributor of the project.
        :rtype: Iri | None
        """
        return self._contributor

    @property
    def modified(self) -> Xsd_dateTime | None:
        """
        Modification date of the project.
        :return: Modification date of the project.
        :rtype: Xsd_dateTime | None
        """
        return self._modified


    def get_modified_by_iri(self, graph: Xsd_QName | str, iri: Iri | str) -> Xsd_dateTime:
        if not isinstance(graph, Xsd_QName):
            graph = Xsd_QName(graph, validate=True)
        if not isinstance(iri, Iri):
            iri = Iri(iri, validate=True)
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f"""
        SELECT ?modified
        FROM {graph}
        WHERE {{
            {iri.toRdf} dcterms:modified ?modified
        }}
        """
        jsonobj = None
        if self._con.in_transaction():
            jsonobj = self._con.transaction_query(sparql)
        else:
            jsonobj = self._con.query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            raise OldapErrorNotFound(f'No resource found with iri "{iri}".')
        for r in res:
            return r['modified']

    def set_modified_by_iri(self,
                            graph: Xsd_QName | str,
                            iri: Iri | str,
                            old_timestamp: Xsd_dateTime | datetime | str,
                            timestamp: Xsd_dateTime | datetime | str) -> None:
        if not isinstance(graph, Xsd_QName):
            graph = Xsd_QName(graph, validate=True)
        if not isinstance(iri, Iri):
            iri = Iri(iri, validate=True)
        if not isinstance(old_timestamp, Xsd_dateTime):
            old_timestamp = Xsd_dateTime(old_timestamp, validate=True)
        if not isinstance(timestamp, Xsd_dateTime):
            timestamp = Xsd_dateTime(timestamp, validate=True)
        try:
            context = Context(name=self._con.context_name)
            sparql = context.sparql_context
            sparql += f"""
            WITH {graph}
            DELETE {{
                ?res dcterms:modified {old_timestamp.toRdf} .
                ?res dcterms:contributor ?contributor .
            }}
            INSERT {{
                ?res dcterms:modified {timestamp.toRdf} .
                ?res dcterms:contributor {self._con.userIri.toRdf} .
            }}
            WHERE {{
                BIND({iri.toRdf} as ?res)
                ?res dcterms:modified {old_timestamp.toRdf} .
                ?res dcterms:contributor ?contributor .
            }}
            """
        except Exception as e:
            raise OldapError(e)
        if self._con.in_transaction():
            self._con.transaction_update(sparql)
        else:
            self._con.update_query(sparql)

    def safe_query(self, query: str) -> Any:
        try:
            return self._con.transaction_query(query)
        except OldapError:
            self._con.transaction_abort()
            raise

    def safe_update(self, update_query: str) -> None:
        try:
            self._con.transaction_update(update_query)
        except OldapError:
            self._con.transaction_abort()
            raise

    def safe_commit(self) -> None:
        try:
            self._con.transaction_commit()
        except OldapError:
            self._con.transaction_abort()
            raise

