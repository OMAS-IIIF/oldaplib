from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple, Union

from omaslib.src.helpers.datatypes import Action, QName


def lprint(text: str):
    lines = text.split('\n')
    for i, line in enumerate(lines, start=1):
        print(f"{i}: {line}")

@dataclass
class RdfModifyItem:
    property: str
    old_value: Union[str, None]
    new_value: Union[str, None]


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
        sparql = ''
        blank = ' '
        if action != Action.CREATE:
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {ele.property} {ele.old_value} .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        if action != Action.DELETE:
            sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {ele.property} {ele.new_value} .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{\n'
        if owlclass_iri:
            if shacl:
                sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            else:
                sparql += f'{blank:{(indent + 2) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?prop .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop sh:path {pclass_iri} .\n'
        else:
            if shacl:
                sparql += f'{blank:{(indent + 2) * indent_inc}}BIND({pclass_iri}Shape as ?prop)\n'
            else:
                sparql += f'{blank:{(indent + 2) * indent_inc}}BIND({pclass_iri} as ?prop)\n'
        if action != Action.CREATE:
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop {ele.property} {ele.old_value} .\n'
        if ele.property != 'dcterms:modified':
            sparql += f'{blank:{(indent + 2) * indent_inc}}?prop dcterms:modified ?modified .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}FILTER(?modified = "{last_modified.isoformat()}"^^xsd:dateTime)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    @classmethod
    def shacl(cls, *,
              action: Action,
              owlclass_iri: Optional[QName] = None,
              pclass_iri: QName,
              graph: QName,
              ele: RdfModifyItem,
              last_modified: datetime,
              indent: int = 0, indent_inc: int = 4) -> str:
        return cls.__rdf_modify_property(shacl=True, action=action, owlclass_iri=owlclass_iri,
                                         pclass_iri=pclass_iri, graph=graph, ele=ele, last_modified=last_modified,
                                         indent=indent, indent_inc=indent_inc)

    @classmethod
    def onto(cls, *,
             action: Action,
             owlclass_iri: Optional[QName] = None,
             pclass_iri: QName,
             graph: QName,
             ele: RdfModifyItem,
             last_modified: datetime,
             indent: int = 0, indent_inc: int = 4) -> str:
        return cls.__rdf_modify_property(shacl=False, action=action, owlclass_iri=owlclass_iri,
                                         pclass_iri=pclass_iri, graph=graph, ele=ele, last_modified=last_modified,
                                         indent=indent, indent_inc=indent_inc)
