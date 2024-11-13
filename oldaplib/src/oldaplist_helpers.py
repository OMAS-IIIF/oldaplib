import json
from pathlib import Path
from typing import Any

import yaml

from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.json_encoder import SpecialEncoder
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


def get_nodes_from_list(con: IConnection, oldapList: OldapList) ->list[OldapListNode]:
    context = Context(name=con.context_name)
    graph = oldapList.project.projectShortName

    query = context.sparql_context
    query += f"""    
    SELECT ?node ?created ?creator ?modified ?contributor ?rindex ?lindex ?parent ?prefLabel ?definition
    WHERE {{
        GRAPH {graph}:lists {{
            ?node skos:inScheme {oldapList.oldapList_iri.toRdf} ;
                dcterms:created ?created ;
                dcterms:creator ?creator ;
                dcterms:modified ?modified ;
                dcterms:contributor ?contributor ;
                oldap:leftIndex ?lindex ;
                oldap:rightIndex ?rindex .
            OPTIONAL {{
                ?node skos:prefLabel ?prefLabel .
            }}
            OPTIONAL {{
                ?node skos:definition ?definition .
            }}
            OPTIONAL {{
                ?node skos:broaderTransitive ?parent .
            }}
        }}
    }}
    ORDER BY ?lindex
    """
    jsonobj = con.query(query)
    res = QueryProcessor(context, jsonobj)
    nodes: list[OldapListNode] = []
    all_nodes: list[OldapListNode] = []
    last_nodeiri = None
    for r in res:
        nodeiri = r['node']
        if last_nodeiri != nodeiri:
            prefix, id = str(nodeiri).split(':')
            ln = OldapListNode(con=con,
                               oldapList=oldapList,
                               oldapListNodeId=Xsd_NCName(id, validate=False),
                               created=r['created'],
                               creator=r['creator'],
                               modified=r['modified'],
                               contributor=r['contributor'],
                               leftIndex=r['lindex'],
                               rightIndex=r['rindex'])
            if r.get('parent') is not None:
                parent_prefix, parent_id = str(r['parent']).split(':')
                pnodes = [x for x in all_nodes if x.oldapListNodeId == parent_id]
                pnodes[0].add_node_to_nodes(ln)
            else:
                nodes.append(ln)
            all_nodes.append(ln)
        if r.get('prefLabel'):
            if ln.prefLabel:
                ln.prefLabel.add(r['prefLabel'])
            else:
                ln.prefLabel = LangString(r['prefLabel'])
        if r.get('definition'):
            if ln.prefLabel:
                ln.prefLabel.add(r['definition'])
            else:
                ln.prefLabel = LangString(r['definition'])

        last_nodeiri = nodeiri
    return nodes


def get_list(con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             oldapListId: Xsd_NCName | str):
    listnode = OldapList.read(con=con,
                              project=project,
                              oldapListId=oldapListId)
    nodes = get_nodes_from_list(con, listnode)
    setattr(listnode, 'nodes', nodes)
    jsonstr = json.dumps(listnode, cls=SpecialEncoder, indent=3)
    return jsonstr


def print_sublist(nodes: list[OldapListNode], level: int = 1) -> None:
    for node in nodes:
        print(f'{str(node.oldapListNodeId): >{level * 5}} ({node.leftIndex}, {node.rightIndex}) prefLabel={node.prefLabel}')
        if node.nodes:
            print_sublist(node.nodes, level + 1)


def load_list_from_yaml(con: Connection,
                        project: Project | Iri | Xsd_NCName | str,
                        filepath: Path) -> list[OldapList]:

    def process_nodes(nodes: dict[str, Any], oldaplist: OldapList, parent: OldapListNode | None):
        oldapnodes: list[OldapListNode] = []
        for nodeid, nodedata in nodes.items():
            label = LangString(nodedata.get('label'))
            definition = LangString(nodedata.get('definition'))
            node = OldapListNode(con=con,
                                 oldapList=oldaplist,
                                 oldapListNodeId=Xsd_NCName(nodeid),
                                 prefLabel=label or None,
                                 definition=definition or None)
            if parent is None:
                node.create_root_node()
            else:
                if oldapnodes:
                    node.insert_node_right_of(oldapnodes[-1])
                else:
                    node.insert_node_below_of(parent)
            oldapnodes.append(node)
            if nodedata.get('nodes'):
                process_nodes(nodedata['nodes'], oldaplist, node)

    oldaplists: list[OldapList] = []
    with filepath.open() as f:
        lists = yaml.safe_load(f)
        for listid, listdata in lists.items():
            label = LangString(listdata.get('label'))
            definition = LangString(listdata.get('definition'))
            oldaplist = OldapList(con=con,
                                  project=project,
                                  oldapListId=Xsd_NCName(listid),
                                  prefLabel=label or None,
                                  definition=definition or None)
            oldaplist.create()
            oldaplists.append(oldaplist)
            if listdata.get('nodes'):
                process_nodes(listdata['nodes'], oldaplist, None)
    return oldaplists
