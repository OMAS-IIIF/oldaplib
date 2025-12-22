import json
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import Any

import yamale
import yaml

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.json_encoder import SpecialEncoder
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotImplemented, OldapErrorValue
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
    """
    Retrieve node indices from a given list structure in the ontology.

    This function constructs and executes a SPARQL query to retrieve
    the left and right indices of nodes belonging to the given list
    structure. The result is returned as a list of tuples containing
    the node IRI and its associated indices.

    :param con: An active connection to the ontology system.
    :param oldapList: Representation of a list within the ontology that
        contains contextual and project-specific information.
    :return: A list of tuples containing the node IRI, left index, and
        right index extracted from the ontology list.
    :rtype: list[tuple[Iri, Xsd_integer, Xsd_integer]]
    :raises OldapError: If the connection object is not an instance of IConnection.
    :raises TypeError: If the connection object is not an instance of IConnection.
    :raises ValueError: If the connection object is not an instance of IConnection.
    """
    context = Context(name=con.context_name)
    graph = oldapList.project.projectShortName

    query = context.sparql_context
    query += f"""
    SELECT ?node ?lindex ?rindex
    WHERE {{
        GRAPH {graph}:lists {{
            ?node skos:inScheme {oldapList.iri.toRdf} ;
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



def dump_list_to(con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 oldapListId: Xsd_NCName | str,
                 listformat: ListFormat=ListFormat.JSON,
                 ignore_cache=False) -> OldapList | str:
    """
    Dumps an OLDAP list into a specified format such as Python dictionary, JSON,
    or YAML. The function manages and consults a cache to improve performance,
    retrieving the necessary OLDAP list data from either the cache or directly
    from the database, based on user preferences.

    :param con: Connection object `con` used to interact with the database.
                Must provide necessary methods and properties for executing
                backend operations.
    :type con: IConnection

    :param project: Identifies the project to which the OLDAP list belongs.
                    Accepts project-related identifiers such as `Project`,
                    `Iri`, `Xsd_NCName`, or `str`.
    :type project: Project | Iri | Xsd_NCName | str

    :param oldapListId: The identifier for the OLDAP list to dump.
    :type oldapListId: Xsd_NCName | str

    :param listformat: Specifies the output format for the OLDAP list.
                       Supported formats include `ListFormat.JSON`,
                       `ListFormat.PYTHON`, and `ListFormat.YAML`.
                       Defaults to `ListFormat.JSON`.
    :type listformat: ListFormat

    :param ignore_cache: Whether to force fetching the list directly
                         from the database, bypassing any cached
                         value. Defaults to `False`.
    :type ignore_cache: bool

    :return: Depending on the specified `listformat`, returns the OLDAP list
             in one of the supported formats:
             - For `ListFormat.PYTHON`: Returns an `OldapList` instance.
             - For `ListFormat.JSON`: Returns a string representing the list
               as JSON.
             - For `ListFormat.YAML`: Returns a string representing the list
               as YAML.
    :rtype: OldapList | str

    :raises OldapError: If the connection object is not an instance of IConnection.
    :raises TypeError: If the connection object is not an instance of IConnection.
    :raises ValueError: If the connection object is not an instance of IConnection.
    :raises Exception: If an unexpected error occurs.
    """

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
    # We need to get the OldapList IRI for asking the cache...
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
            # if listnode.nodes:
            #     set_con(listnode.nodes)
            setattr(listnode, 'source', 'cache')
    if listnode is None:
        #
        # List was not in cache, read it from database
        #
        listnode = OldapList.read(con=con,
                                  project=project,
                                  oldapListId=oldapListId)
        nodes = listnode.nodes
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
            return yaml.dump(list_dict, indent=2, allow_unicode=True)

    return ''

def print_sublist(nodes: list[OldapListNode], level: int = 1) -> None:
    """
    Prints a nested list of OldapListNode objects in a structured format.

    This function recursively traverses through a list of OldapListNode objects,
    and its nested `nodes` attributes, to print their details. Node information
    is displayed with indentation proportional to their depth level in the
    hierarchy.

    :param nodes: A list of OldapListNode objects to be printed. Each node contains
        attributes such as `oldapListNodeId`, `leftIndex`, `rightIndex`,
        `prefLabel`, `iri`, and optionally nested `nodes`.
    :type nodes: list[OldapListNode]
    :param level: The current depth level of indentation. Defaults to 1.
    :type level: int
    :return: None
    """
    for node in nodes:
        print(f'{str(node.oldapListNodeId): >{level * 5}} ({node.leftIndex}, {node.rightIndex}) prefLabel={node.prefLabel} iri={node.iri}')
        if node.nodes:
            print_sublist(node.nodes, level + 1)


def load_list_from_yaml(con: Connection,
                        project: Project | Iri | Xsd_NCName | str,
                        filepath: Path) -> list[OldapList]:
    """
    Loads a list of OldapList objects from a YAML file, validates its structure
    using a predefined schema, and processes its content into objects in the
    system. Each list in the YAML file is mapped to an OldapList instance
    and its nodes recursively.

    :param con: A connection object to interact with the backend system.
    :param project: The project to which the created OldapLists will belong.
        It can be a Project object or identifications such as Iri, Xsd_NCName,
        or string.
    :param filepath: The path of the YAML file containing the lists and nodes
        to be loaded and processed.
    :return: A list of OldapList objects that were successfully created and
        populated based on the YAML input.

    :raises OldapError: If the connection object is not an instance of IConnection.
    :raises TypeError: If the connection object is not an instance of IConnection.
    :raises ValueError: If the connection object is not an instance of IConnection.
    :raises OldapErrorNotImplemented: If the YAML file contains nodes that are not implemented.
    """

    def process_nodes(nodes: dict[str, Any], oldaplist: OldapList, parent: OldapListNode | None):
        oldapnodes: list[OldapListNode] = []
        for nodeid, nodedata in nodes.items():
            if not hasattr(listdata, 'get'):
                raise OldapErrorValue(f'YAML has invalid content.')
            label = LangString(nodedata.get('label'))
            definition = LangString(nodedata.get('definition'))
            node = OldapListNode(con=con,
                                 **oldaplist.info,
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

    if not isinstance(project, Project):
        project = Project.read(con, project)

    oldaplists: list[OldapList] = []
    #
    # first we validate the YAML file using the following schema (using yamale)
    #
    with filepath.open() as f:
        schema = yamale.make_schema(content='''
map(include('node'))
---
node:
  label: list(str(matches='^.*@[ -~]{2}$'))
  definition: list(str(matches='^.*@[ -~]{2}$'), required=False)
  nodes: map(include('node'), required=False)
'''
                           )
        data = yamale.make_data(content=f.read())
        try:
            yamale.validate(schema=schema, data=data)
        except ValueError as e:
            raise OldapErrorValue(f"Error validating YAML file: {e}")
    #
    # now we read the YAML
    #
    with filepath.open() as f:
        try:
            lists = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise OldapErrorValue(f"Error loading YAML file: {e}")
        for listid, listdata in lists.items():
            if not hasattr(listdata, 'get'):
                raise OldapErrorValue(f'YAML has invalid content.')
            label = LangString(listdata.get('label'))
            definition = LangString(listdata.get('definition'))
            oldaplist = OldapList(con=con,
                                  project=project,
                                  oldapListId=Xsd_NCName(listid, validate=True),
                                  prefLabel=label or None,
                                  definition=definition or None,
                                  validate=True)
            oldaplist.create()
            oldaplists.append(oldaplist)
            if listdata.get('nodes'):
                oldaplist.nodes = process_nodes(listdata['nodes'], oldaplist, None)
    return oldaplists

def get_node_by_id(nodes: list[OldapListNode], id: Xsd_NCName) -> OldapListNode | None:
    """
    Retrieve a node from a nested list of OldapListNode objects that matches a given ID.

    This function searches recursively through the list of OldapListNode objects and their
    nested children to find a node with a matching oldapListNodeId. If a match is found,
    the node is returned. If no matching node is found in the entire structure, the function
    returns None.

    :param nodes: A list of OldapListNode objects within which the search is conducted.
    :type nodes: list[OldapListNode]
    :param id: The identifier to match against the oldapListNodeId of nodes.
    :type id: Xsd_NCName
    :return: Returns the matching OldapListNode object if found, or None if no match is located.
    :rtype: OldapListNode | None
    """
    for node in nodes:
        if node.oldapListNodeId == id:
            return node
        elif node.nodes:
            result = get_node_by_id(node.nodes, id)
            if result is not None:
                return result
    return None
