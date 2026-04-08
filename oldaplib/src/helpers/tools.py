import re
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple, Union

from oldaplib.src.enums.action import Action
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


def lprint(text: str):
    lines = text.split('\n')
    for i, line in enumerate(lines, start=1):
        print(f"{i}: {line}")


def str2qname_anyiri(s: Xsd_QName | Xsd_anyURI | str) -> Xsd_QName | Xsd_anyURI:
    try:
        return Xsd_QName(s, validate=True)
    except:
        return Xsd_anyURI(s, validate=True)


@dataclass
class RdfModifyItem:
    property: str | Xsd_QName
    old_value: Xsd | None
    new_value: Xsd | None


class RdfModifyRes:

    @staticmethod
    def __rdf_modify_property(*,
                              shacl: bool,
                              action: Action,
                              owlclass_iri: Xsd_QName,
                              graph: Xsd_QName,
                              ele: RdfModifyItem,
                              last_modified: Xsd_dateTime,
                              indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'WITH {graph}\n'
        if action != Action.CREATE:
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            if ele.old_value is not None:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} {ele.old_value.toRdf} .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} ?value .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        if action != Action.DELETE:
            sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} {ele.new_value.toRdf} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        if shacl:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({owlclass_iri}Shape as ?resource)\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({owlclass_iri.toRdf} as ?resource)\n'
        if action != Action.CREATE:
            if ele.old_value is not None:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} {ele.old_value.toRdf} .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}?resource {ele.property} ?value .\n'
        if graph.fragment == 'shacl' and ele.property != 'dcterms:modified':
            sparql += f'{blank:{(indent + 1) * indent_inc}}?resource dcterms:modified ?modified .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {last_modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    @staticmethod
    def shacl(*,
              action: Action,
              graph: Xsd_NCName,
              owlclass_iri: Xsd_QName,
              ele: RdfModifyItem,
              last_modified: Xsd_dateTime,
              indent: int = 0, indent_inc: int = 4):
        graph = Xsd_QName(str(graph) + ':shacl')
        return RdfModifyRes.__rdf_modify_property(shacl=True, action=action, owlclass_iri=owlclass_iri,
                                         graph=graph, ele=ele, last_modified=last_modified,
                                         indent=indent, indent_inc=indent_inc)

    @staticmethod
    def onto(*,
             action: Action,
             graph: Xsd_NCName,
             owlclass_iri: Xsd_QName,
             ele: RdfModifyItem,
             last_modified: Xsd_dateTime,
             indent: int = 0, indent_inc: int = 4):
        graph = Xsd_QName(str(graph) + ':onto')
        return RdfModifyRes.__rdf_modify_property(shacl=False, action=action, owlclass_iri=owlclass_iri,
                                         graph=graph, ele=ele, last_modified=last_modified,
                                         indent=indent, indent_inc=indent_inc)

    @staticmethod
    def update_timestamp_contributors(*,
                                      contributor: Iri,
                                      timestamp: Xsd_dateTime,
                                      iri: Xsd_QName,
                                      graph: Xsd_QName,
                                      old_timestamp: Xsd_dateTime | None = None) -> str:
        #
        # The modified/contributor is on the level of the Shape only, the property itself does not carry
        # modified/contributor attributes
        #
        filter_part = (
            f'    FILTER(?m = {old_timestamp.toRdf})\n'
            if old_timestamp is not None else ''
        )

        sparql = textwrap.dedent(f"""\
        WITH {graph}
        DELETE {{
            {iri.toRdf}Shape dcterms:modified ?m .
            {iri.toRdf}Shape dcterms:contributor ?c .
        }}
        INSERT {{
            {iri.toRdf}Shape dcterms:modified {timestamp.toRdf} .
            {iri.toRdf}Shape dcterms:contributor {contributor.toRdf} .
        }}
        WHERE {{
            {iri.toRdf}Shape dcterms:modified ?m .
            {iri.toRdf}Shape dcterms:contributor ?c .
    {filter_part}\
        }}
        """)
        return sparql

class RdfModifyProp:

    @staticmethod
    def __rdf_modify_property(*,
                              shacl: bool,
                              action: Action,
                              owlclass_iri: Xsd_QName | None = None,
                              pclass_iri: Xsd_QName,
                              graph: Xsd_QName,
                              ele: RdfModifyItem,
                              indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'# __rdf_modify_property of "{pclass_iri}"\n'
        sparql += f'WITH {graph}\n'
        if action != Action.CREATE:
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.old_value} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        if action != Action.DELETE:
            sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?property sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.new_value} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {pclass_iri} .\n'
        if owlclass_iri:
            if shacl:
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
        else:
            if shacl:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({pclass_iri}Shape as ?property)\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?property sh:property ?prop .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({pclass_iri} as ?property)\n'
        if action != Action.CREATE:
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.old_value} .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    @staticmethod
    def shacl(*,
              action: Action,
              graph: Xsd_NCName,
              owlclass_iri: Xsd_QName | None = None,
              pclass_iri: Xsd_QName,
              ele: RdfModifyItem,
              indent: int = 0, indent_inc: int = 4) -> str:
        graph = Xsd_QName(str(graph) + ':shacl')
        return RdfModifyProp.__rdf_modify_property(shacl=True, action=action, owlclass_iri=owlclass_iri,
                                         pclass_iri=pclass_iri, graph=graph, ele=ele,
                                         indent=indent, indent_inc=indent_inc)

    @staticmethod
    def onto(*,
             action: Action,
             graph: Xsd_NCName,
             owlclass_iri: Xsd_QName | None = None,
             pclass_iri: Xsd_QName,
             ele: RdfModifyItem,
             indent: int = 0, indent_inc: int = 4) -> str:
        graph = Xsd_QName(str(graph) + ':onto')
        # return cls.__rdf_modify_property(shacl=False, action=action, owlclass_iri=owlclass_iri,
        #                                  pclass_iri=pclass_iri, graph=graph, ele=ele,
        #                                  indent=indent, indent_inc=indent_inc)
        blank = ''
        sparql = f'WITH {graph}\n'
        if action != Action.CREATE:
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.old_value} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
        if action != Action.DELETE:
            sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.new_value} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({pclass_iri} as ?prop)\n'
        if action != Action.CREATE:
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.old_value} .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql


    @staticmethod
    def update_timestamp_contributors(*,
                                      contributor: Iri,
                                      timestamp: Xsd_dateTime,
                                      iri: Xsd_QName,
                                      graph: Xsd_QName):
        #
        # The modified/contributer is on the level of the Shape ony, the property itself does not carry
        # modified/contributor attributes
        #
        sparql = textwrap.dedent(f"""
        WITH {graph}
        DELETE {{
            {iri.toRdf}Shape dcterms:modified ?m .
            {iri.toRdf}Shape dcterms:contributor ?c .
        }}
        INSERT {{
            {iri.toRdf}Shape dcterms:modified {timestamp.toRdf} .
            {iri.toRdf}Shape dcterms:contributor {contributor.toRdf} .
        }}
        WHERE {{
            {iri.toRdf}Shape dcterms:modified ?m .
            {iri.toRdf}Shape dcterms:contributor ?c .
        }}
        """)
        return sparql

    @classmethod
    def replace_rdfset(cls, *,
                       action: Action,
                       owlclass_iri: Xsd_QName | None = None,
                       pclass_iri: Xsd_QName,
                       graph: Xsd_QName,
                       ele: RdfModifyItem,
                       last_modified: Xsd_dateTime,
                       indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql_list = []
        sparql = ''
        #
        # The SHACL RdfSet is implemented as a RDF List with blank nodes having
        # a rdf:first and rdf:rest property. This makes the manipulation a bit complicated. If
        # sh:languageIn is modified we delete the complete list and replace it by the new list.
        #
        if action != Action.CREATE:
            sparql += f'WITH {graph}:shacl\n'
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}rdf:rest ?tail .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
            sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {pclass_iri} .\n'
            if owlclass_iri:
                sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?property sh:property ?prop .\n'
            else:
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({pclass_iri}Shape as ?property)\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} ?bnode .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?bnode rdf:rest* ?z .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?z rdf:first ?head ;\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:rest ?tail .\n'
            sparql += f'{blank:{indent * indent_inc}}}}'
            sparql_list.append(sparql)

        sparql = f'WITH {graph}:shacl\n'
        if action != Action.CREATE:
            sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} ?rval .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
        if action != Action.DELETE:
            sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?property sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} {ele.new_value} .\n'
            sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?prop sh:path {pclass_iri} .\n'
        if owlclass_iri:
            sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?prop .\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}?property sh:property ?prop .\n'
        else:
            sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({pclass_iri}Shape as ?property)\n'
        if action != Action.CREATE:
            sparql += f'{blank:{(indent + 1) * indent_inc}}?prop {ele.property} ?rval .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?property dcterms:modified ?modified .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {last_modified.toRdf})\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        sparql_list.append(sparql)

        sparql = ";\n".join(sparql_list)
        return sparql


class DataModelModtime:

    @classmethod
    def __set_dm_modtime(cls, shacl: bool, graph: Xsd_NCName, timestamp: Xsd_dateTime, contributor: Xsd_QName | Xsd_anyURI) -> str:
        graphname = f"{graph}:shacl" if shacl else f"{graph}:onto"
        element = f"{graph}:shapes" if shacl else f"{graph}:ontology"
        return f"""
        DELETE {{
            GRAPH {graphname} {{ {element} dcterms:modified ?value . }}
        }}
        INSERT {{
            GRAPH {graphname} {{ {element} dcterms:modified {timestamp.toRdf} . }}
        }}
        WHERE {{
            GRAPH {graphname} {{ {element} dcterms:modified ?value . }}
        }} ;
        DELETE {{
            GRAPH {graphname} {{ {element} dcterms:contributor ?value . }}
        }}
        INSERT {{
            GRAPH {graphname} {{ {element} dcterms:contributor "{contributor.resUri}" . }}
        }}
        WHERE {{
            GRAPH {graphname} {{ {element} dcterms:contributor ?value . }}
        }}
        """

    @classmethod
    def set_dm_modtime_shacl(cls, graph: Xsd_NCName, timestamp: Xsd_dateTime, contributor: Xsd_QName | Xsd_anyURI) -> str:
        return cls.__set_dm_modtime(True, graph, timestamp, contributor)

    @classmethod
    def set_dm_modtime_onto(cls, graph: Xsd_NCName, timestamp: Xsd_dateTime, contributor: Xsd_QName | Xsd_anyURI) -> str:
        return cls.__set_dm_modtime(False, graph, timestamp, contributor)

