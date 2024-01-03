from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple, Union

from omaslib.src.helpers.datatypes import Action, QName, NCName


def lprint(text: str):
    lines = text.split('\n')
    for i, line in enumerate(lines, start=1):
        print(f"{i}: {line}")


@dataclass
class RdfModifyItem:
    property: str
    old_value: Union[str, None]
    new_value: Union[str, None]


class RdfModifyRes:

    @classmethod
    def __rdf_modify_property(cls, *,
                              shacl: bool,
                              action: Action,
                              owlclass_iri: QName,
                              graph: QName,
                              ele: RdfModifyItem,
                              last_modified: datetime,
                              indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'WITH {graph}\n'
        if action != Action.CREATE:
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            if ele.old_value is not None:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} {ele.old_value} .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} ?value .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        if action != Action.DELETE:
            sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} {ele.new_value} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        if shacl:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({owlclass_iri}Shape as ?resource)\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({owlclass_iri} as ?resource)\n'
        if action != Action.CREATE:
            if ele.old_value is not None:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} {ele.old_value} .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} ?value .\n'
        if ele.property != 'dcterms:modified':
            sparql += f'{blank:{(indent + 1) * indent_inc}}?resource dcterms:modified ?modified .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = "{last_modified.isoformat()}"^^xsd:dateTime)\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    @classmethod
    def shacl(cls, *,
              action: Action,
              graph: NCName,
              owlclass_iri: QName,
              ele: RdfModifyItem,
              last_modified: datetime,
              indent: int = 0, indent_inc: int = 4):
        graph = QName(str(graph) + ':shacl')
        return cls.__rdf_modify_property(shacl=True, action=action, owlclass_iri=owlclass_iri,
                                         graph=graph, ele=ele, last_modified=last_modified,
                                         indent=indent, indent_inc=indent_inc)

    @classmethod
    def onto(cls, *,
             action: Action,
             graph: NCName,
             owlclass_iri: QName,
             ele: RdfModifyItem,
             last_modified: datetime,
             indent: int = 0, indent_inc: int = 4):
        graph = QName(str(graph) + ':onto')
        return cls.__rdf_modify_property(shacl=False, action=action, owlclass_iri=owlclass_iri,
                                         graph=graph, ele=ele, last_modified=last_modified,
                                         indent=indent, indent_inc=indent_inc)


class RdfModifyProp:

    @classmethod
    def __rdf_modify_property(cls, *,
                              shacl: bool,
                              action: Action,
                              owlclass_iri: Optional[QName] = None,
                              pclass_iri: QName,
                              graph: QName,
                              ele: RdfModifyItem,
                              last_modified: datetime,
                              indent: int = 0, indent_inc: int = 4) -> str:
        sparql = f'WITH {graph}\n'
        blank = ' '
        if action != Action.CREATE:
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.old_value} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        if action != Action.DELETE:
            sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.new_value} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        if owlclass_iri:
            if shacl:
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?prop .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {pclass_iri} .\n'
        else:
            if shacl:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({pclass_iri}Shape as ?prop)\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({pclass_iri} as ?prop)\n'
        if action != Action.CREATE:
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.old_value} .\n'
        if ele.property != 'dcterms:modified':
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop dcterms:modified ?modified .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = "{last_modified.isoformat()}"^^xsd:dateTime)\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    @classmethod
    def shacl(cls, *,
              action: Action,
              graph: NCName,
              owlclass_iri: Optional[QName] = None,
              pclass_iri: QName,
              ele: RdfModifyItem,
              last_modified: datetime,
              indent: int = 0, indent_inc: int = 4) -> str:
        graph = QName(str(graph) + ':shacl')
        return cls.__rdf_modify_property(shacl=True, action=action, owlclass_iri=owlclass_iri,
                                         pclass_iri=pclass_iri, graph=graph, ele=ele, last_modified=last_modified,
                                         indent=indent, indent_inc=indent_inc)

    @classmethod
    def onto(cls, *,
             action: Action,
             graph: NCName,
             owlclass_iri: Optional[QName] = None,
             pclass_iri: QName,
             ele: RdfModifyItem,
             last_modified: datetime,
             indent: int = 0, indent_inc: int = 4) -> str:
        graph = QName(str(graph) + ':onto')
        return cls.__rdf_modify_property(shacl=False, action=action, owlclass_iri=owlclass_iri,
                                         pclass_iri=pclass_iri, graph=graph, ele=ele, last_modified=last_modified,
                                         indent=indent, indent_inc=indent_inc)


class DataModelModtime:

    @classmethod
    def __set_dm_modtime(cls, shacl: bool, graph: NCName, timestamp: datetime, contributor: str) -> str:
        graphname = f"{graph}:shacl" if shacl else f"{graph}:onto"
        element = f"{graph}:shapes" if shacl else f"{graph}:ontology"
        return f"""
        DELETE {{
            GRAPH {graphname} {{ {element} dcterms:modified ?value . }}
        }}
        INSERT {{
            GRAPH {graphname} {{ {element} dcterms:modified "{timestamp.isoformat()}"^^xsd:dateTime . }}
        }}
        WHERE {{
            GRAPH {graphname} {{ {element} dcterms:modified ?value . }}
        }} ;
        DELETE {{
            GRAPH {graphname} {{ {element} dcterms:contributor ?value . }}
        }}
        INSERT {{
            GRAPH {graphname} {{ {element} dcterms:contributor "{contributor}" . }}
        }}
        WHERE {{
            GRAPH {graphname} {{ {element} dcterms:contributor ?value . }}
        }}
        """

    @classmethod
    def set_dm_modtime_shacl(cls, graph: NCName, timestamp: datetime, contributor: str) -> str:
        return cls.__set_dm_modtime(True, graph, timestamp, contributor)

    @classmethod
    def set_dm_modtime_onto(cls, graph: NCName, timestamp: datetime, contributor: str) -> str:
        return cls.__set_dm_modtime(False, graph, timestamp, contributor)

