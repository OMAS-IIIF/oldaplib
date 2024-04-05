from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

from pystrict import strict

from omaslib.src.helpers.context import DEFAULT_CONTEXT
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.enums.sparql_result_format import SparqlResultFormat
from omaslib.src.user_dataclass import UserDataclass


@strict
class IConnection(ABC):
    _context_name: str
    _userdata: UserDataclass
    _token: str | None
    _transaction_url: Optional[str]

    @abstractmethod
    def __init__(self, context_name: Optional[str] = DEFAULT_CONTEXT):
        self._context_name = context_name
        self._userdata = UserDataclass()
        self._token = None
        self._transaction_url = None

    @property
    def userdata(self) -> UserDataclass:
        return self._userdata

    @property
    def userid(self) -> Xsd_NCName:
        return self._userdata.userId

    @property
    def userIri(self) -> Iri:
        return self._userdata.userIri

    @property
    def login(self) -> bool:
        return self._userIri is not None

    @property
    def context_name(self) -> str:
        """Getter for the context name"""
        return self._context_name

    @property
    def token(self) -> str:
        return self._token

    @abstractmethod
    def clear_graph(self, graph_iri: Xsd_QName) -> None:
        pass

    @abstractmethod
    def clear_repo(self) -> None:
        pass

    @abstractmethod
    def upload_turtle(self, filename: str, graphname: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def query(self, query: str, format: SparqlResultFormat = SparqlResultFormat.JSON) -> Any:
        pass

    @abstractmethod
    def update_query(self, query: str) -> Dict[str, str]:
        pass

    @abstractmethod
    def transaction_start(self) -> None:
        pass

    @abstractmethod
    def transaction_query(self, query: str, result_format: SparqlResultFormat = SparqlResultFormat.JSON) -> Any:
        pass

    @abstractmethod
    def transaction_update(self, query: str) -> None:
        pass

    @abstractmethod
    def transaction_commit(self) -> None:
        pass

    @abstractmethod
    def transaction_abort(self) -> None:
        pass

    @abstractmethod
    def in_transaction(self) -> bool:
        pass

