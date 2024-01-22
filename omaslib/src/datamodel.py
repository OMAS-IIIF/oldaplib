from datetime import datetime
from pprint import pprint
from typing import Dict, List, Optional, Union

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NCName, QName, AnyIRI
from omaslib.src.helpers.omaserror import OmasErrorInconsistency, OmasError
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.helpers.tools import lprint
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass
from omaslib.src.resourceclass import ResourceClass


class DataModel(Model):
    __graph: NCName
    __context: Context
    __creator: Optional[AnyIRI]
    __created: Optional[datetime]
    __contributor: Optional[AnyIRI]
    __modified: Optional[datetime]
    __propclasses: Dict[QName, PropertyClass]
    __resclasses: Dict[QName, ResourceClass]

    def __init__(self, *,
                 con: Connection,
                 graph: NCName,
                 propclasses: Optional[List[PropertyClass]] = None,
                 resclasses: Optional[List[ResourceClass]] = None) -> None:
        super().__init__(con)
        self.__creator = None
        self.__created = None
        self.__contributor = None

        self.__graph = graph
        self.__propclasses = {}
        if propclasses is not None:
            for p in propclasses:
                self.__propclasses[p.property_class_iri] = p
        self.__resclasses = {}
        if resclasses is not None:
            for r in resclasses:
                self.__resclasses[r.owl_class_iri] = r

    def __getitem__(self, key: QName) -> Union[PropertyClass, ResourceClass]:
        if key in self.__resclasses:
            return self.__resclasses[key]
        if key in self.__propclasses:
            return self.__propclasses[key]
        else:
            raise KeyError(key)

    def get_propclasses(self) -> List[QName]:
        return [x for x in self.__propclasses]

    def get_propclass(self, propclass_iri: QName) -> Union[PropertyClass, None]:
        return self.__propclasses.get(propclass_iri)

    def get_resclasses(self) -> List[QName]:
        return [x for x in self.__resclasses]

    def get_resclass(self, resclass_iri: QName) -> Union[ResourceClass, None]:
        return self.__resclasses.get(resclass_iri)

    @classmethod
    def read(cls, con: Connection, graph: NCName):
        cls.__graph = graph
        cls.__context = Context(name=con.context_name)
        #
        # first we read the shapes metadata
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?creator ?created ?contributor ?modified
        FROM {cls.__graph}:shacl
        WHERE {{
           {cls.__graph}:shapes dcterms:creator ?creator .
           {cls.__graph}:shapes dcterms:created ?created .
           {cls.__graph}:shapes dcterms:contributor ?contributor .
           {cls.__graph}:shapes dcterms:modified ?modified .
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        cls.__created = res[0]['created']
        cls.__creator = res[0]['creator']
        cls.__modified = res[0]['modified']
        cls.__contributor = res[0]['contributor']
        #
        # now we read the OWL ontology metadata
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?creator ?created
        FROM {cls.__graph}:onto
        WHERE {{
           {cls.__graph}:ontology dcterms:creator ?creator .
           {cls.__graph}:ontology dcterms:created ?created .
           {cls.__graph}:ontology dcterms:contributor ?contributor .
           {cls.__graph}:ontology dcterms:modified ?modified .
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        #
        # now get the QNames of all standalone properties within the data model
        #
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
        propclasses = []
        for r in res:
            propnameshacl = str(r['prop'])
            propclassiri = propnameshacl.removesuffix("Shape")
            propclass = PropertyClass.read(con, graph, QName(propclassiri))
            propclasses.append(propclass)
        #
        # now get all resources defined in the data model
        #
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
        resclasses = []
        for r in res:
            resnameshacl = str(r['shape'])
            resclassiri = resnameshacl.removesuffix("Shape")
            resclass = ResourceClass.read(con, graph, QName(resclassiri))
            resclasses.append(resclass)
        return cls(graph=graph, con=con, propclasses=propclasses, resclasses=resclasses)

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        timestamp = datetime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:shacl {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:shapes dcterms:creator <{self._con.user_iri}> ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:contributor <{self._con.user_iri}> ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime .\n'
        sparql += '\n'

        for propiri, propclass in self.__propclasses.items():
            if propclass.internal:
                raise OmasErrorInconsistency(f"Property class {propclass.property_class_iri} is internal and cannot be used here.")
            sparql += propclass.create_shacl(timestamp=timestamp, indent=2)
            sparql += '\n'

        for resiri, resclass in self.__resclasses.items():
            sparql += resclass.create_shacl(timestamp=timestamp, indent=2)
            sparql += '\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += '\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:onto {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:ontology owl:type owl:Ontology ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}dcterms:creator <{self._con.user_iri}> ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}dcterms:created "{timestamp.isoformat()}"^^xsd:dateTime ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}dcterms:contributor <{self._con.user_iri}> ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime .\n'
        sparql += '\n'

        for propiri, propclass in self.__propclasses.items():
            sparql += propclass.create_owl_part1(timestamp=timestamp, indent=2)

        for resiri, resclass in self.__resclasses.items():
            sparql += resclass.create_owl(timestamp=timestamp, indent=2)

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        try:
            self._con.transaction_start()
            self._con.transaction_update(sparql)
            for propiri, propclass in self.__propclasses.items():
                propclass.set_creation_metadata(timestamp=timestamp)
            for resiri, resclass in self.__resclasses.items():
                resclass.set_creation_metadata(timestamp=timestamp)
            self._con.transaction_commit()
            self.__creator = self._con.user_iri
            self.__created = timestamp
            self.__contributor = self._con.user_iri
            self.__modified = timestamp
        except OmasError as err:
            self._con.transaction_abort()
            raise


