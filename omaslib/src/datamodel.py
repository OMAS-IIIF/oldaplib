from typing import Dict, List, Optional

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, QName
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass
from omaslib.src.resourceclass import ResourceClass


class DataModel(Model):
    __graph: NCName
    __context: Context
    __propclasses: Dict[QName, PropertyClass]
    __resclasses: Dict[QName, ResourceClass]

    def __init__(self, *,
                 con: Connection,
                 graph: NCName,
                 propclasses: Optional[List[PropertyClass]] = None,
                 resclasses: Optional[List[ResourceClass]] = None) -> None:
        super().__init__(con)
        self.__graph = graph
        self.__propclasses = {}
        if propclasses is not None:
            for p in propclasses:
                self.__propclasses[p.property_class_iri] = p
        self.__resclasses = {}
        if resclasses is not None:
            for r in resclasses:
                self.__resclasses[r.owl_class_iri] = r

    @classmethod
    def read(cls, con: Connection, graph: NCName):
        cls.__graph = graph
        cls.__context = Context(name=cls.__graph)
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?prop
        FROM {cls.__graph}:shacl
        WHERE {{
            ?prop a sh:PropertyShape
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        cls.__propclasses = {}
        for r in res:
            propnameshacl = str(r['prop'])
            propclassiri = propnameshacl.removesuffix("Shape")
            propclass = PropertyClass.read(con, graph, QName(propclassiri))
            cls.__propclasses[propclass.property_class_iri] = propclass

        query = cls.__context.sparql_context
        query += f"""
        SELECT ?shape
        FROM {cls.__graph}:shacl
        WHERE {{
            ?shape a sh:NodeShape
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        for r in res:
            print('::-->>', r['shape'])

        return cls



