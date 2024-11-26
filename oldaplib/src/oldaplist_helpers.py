import json
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import Any

import yaml

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.json_encoder import SpecialEncoder
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotImplemented
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

class ListFormat(Enum):
    PYTHON = 'python'
    JSON = 'json'
    YAML = 'yaml'


def get_node_indices(con: IConnection, oldapList: OldapList) -> list[tuple[Iri, Xsd_integer, Xsd_integer]]:
    context = Context(name=con.context_name)
    graph = oldapList.project.projectShortName

    query = context.sparql_context
    query += f"""
    SELECT ?node ?lindex ?rindex
    WHERE {{
        GRAPH {graph}:lists {{
            ?node skos:inScheme {oldapList.oldapList_iri.toRdf} ;
                oldap:leftIndex ?lindex ;
                oldap:rightIndex ?rindex .
        }}
    }}
    ORDER BY ?node
    """
    jsonobj = con.query(query)
    res = QueryProcessor(context, jsonobj)
    result: list[tuple[Iri, Xsd_integer, Xsd_integer]] = []
    for r in res:
        result.append((r['node'], r['lindex'], r['rindex']))
    return result

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
            if ln.definition:
                ln.definition.add(r['definition'])
            else:
                ln.definition = LangString(r['definition'])

        last_nodeiri = nodeiri
    return nodes


def dump_list_to(con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 oldapListId: Xsd_NCName | str,
                 listformat: ListFormat=ListFormat.JSON,
                 ignore_cache=False) -> OldapList | str:

    def set_con(nodes: list[OldapListNode]) -> None:
        for node in nodes:
            node._con = con
            if node.nodes:
                set_con(node.nodes)

    def make_dict(listnode: OldapList | OldapListNode, listdict: dict) -> None:
        if isinstance(listnode, OldapList):
            listdict[str(listnode.oldapListId)] =  {}
            if listnode.prefLabel:
                listdict[str(listnode.oldapListId)]['label'] = [str(x) for x in listnode.prefLabel]
            if listnode.definition:
                listdict[str(listnode.oldapListId)]['definition'] = [str(x) for x in listnode.definition]
            if listnode.nodes:
                listdict[str(listnode.oldapListId)]['nodes'] = {}
                for node in listnode.nodes:
                    make_dict(node, listdict[str(listnode.oldapListId)]['nodes'])
        else:
            listdict[str(listnode.oldapListNodeId)] =  {}
            if listnode.prefLabel:
                listdict[str(listnode.oldapListNodeId)]['label'] = [str(x) for x in listnode.prefLabel]
            if listnode.definition:
                listdict[str(listnode.oldapListNodeId)]['definition'] = [str(x) for x in listnode.definition]
            if listnode.nodes:
                listdict[str(listnode.oldapListNodeId)]['nodes'] = {}
                for node in listnode.nodes:
                    make_dict(node, listdict[str(listnode.oldapListNodeId)]['nodes'])

    #
    # We need to get the OldapList IRI for aksing the cache...
    #
    if not isinstance(project, Project):
        project = Project.read(con, project)
    oldapListIri = Iri.fromPrefixFragment(project.projectShortName, Xsd_NCName(oldapListId), validate=False)
    cache = CacheSingleton()
    listnode = None
    if not ignore_cache:
        listnode = cache.get(oldapListIri)
        if listnode is not None:
            # rectify the connection
            listnode._con = con
            if listnode.nodes:
                set_con(listnode.nodes)
            setattr(listnode, 'source', 'cache')
    if listnode is None:
        #
        # List was not in cache, read it from database
        #
        listnode = OldapList.read(con=con,
                                  project=project,
                                  oldapListId=oldapListId)
        nodes = get_nodes_from_list(con, listnode)
        listnode.nodes = nodes
        setattr(listnode, 'source', 'db')
        cache.set(oldapListIri, listnode)

    match listformat:
        case ListFormat.PYTHON:
            return listnode
        case ListFormat.JSON:
            return json.dumps(listnode, cls=SpecialEncoder, indent=3)
        case ListFormat.YAML:
            list_dict = {}
            make_dict(listnode, list_dict)
            return yaml.dump(list_dict, indent=3)


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
            if oldapnodes:
                node.insert_node_right_of(oldapnodes[-1])
            else:
                if parent is None:
                    node.create_root_node()
                else:
                    node.insert_node_below_of(parent)
            oldapnodes.append(node)
            if nodedata.get('nodes'):
                node.nodes = process_nodes(nodedata['nodes'], oldaplist, node)
        return oldapnodes

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
                oldaplist.nodes = process_nodes(listdata['nodes'], oldaplist, None)
    return oldaplists
