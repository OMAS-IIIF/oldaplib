from datetime import datetime
from typing import List, Set, Dict, Tuple, Optional, Any, Union

from pystrict import strict

from omaslib.src.helpers.context import Context
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNotFound
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.tools import lprint
from omaslib.src.iconnection import IConnection


@strict
class Model:
    _con: IConnection
    _changed: Set[str]

    def __init__(self, connection: IConnection) -> None:
        # if not isinstance(connection, Connection):
        #     raise OmasError('"con"-parameter must be an instance of Connection')
        # if type(connection) != Connection:
        #     raise OmasError('"con"-parameter must be an instance of Connection')
        self._con = connection
        self._changed = set()

    def has_changed(self) -> bool:
        if self._changed:
            return True
        else:
            return False

    def get_modified_by_iri(self, graph: Xsd_QName, iri: Iri) -> Xsd_dateTime:
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
            print(sparql)
            raise OmasErrorNotFound(f'No resource found with iri "{iri}".')
        for r in res:
            return r['modified']

    def set_modified_by_iri(self,
                            graph: Xsd_QName,
                            iri: Iri,
                            old_timestamp: Xsd_dateTime,
                            timestamp: Xsd_dateTime) -> None:
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
        if self._con.in_transaction():
            self._con.transaction_update(sparql)
        else:
            self._con.query(sparql)
