from typing import Union, Optional, List
from pystrict import strict
from rdflib import URIRef, Literal, BNode

from connection import Connection
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.helpers.datatypes import QName, Languages
from omaslib.src.helpers.context import Context, DEFAULT_CONTEXT
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass, PropertyRestrictions, PropertyRestrictionType


@strict
class ResourceClass(Model):
    #_shape: Union[QName, None]
    _owl_class: Union[QName, None]
    _subclass_of: Union[QName, None]
    _properties: List[PropertyClass]
    _closed: bool

    def __init__(self,
                 con: Connection,
                 owl_cass: Optional[QName] = None,
                 subclass_of: Optional[QName] = None,
                 properties: Optional[List[PropertyClass]] = None,
                 closed: Optional[bool] = None) -> None:
        super().__init__(con)
        self._owl_class = owl_cass
        self._subclass_of = subclass_of
        self._properties = properties if properties else set()
        self._closed = True if closed is None else closed

    def __str__(self):
        blank = ' '
        indent = 4
        s = f'Shape: {self._owl_class}Shape\nProperties:\n'
        for p in self._properties:
            s += f'{blank:{indent}}{str(p)}\n'
        return s

    def to_sparql_insert(self, indent: int) -> str:
        blank = ' '
        sparql = f'{blank:{indent}}{self._shape} a sh:nodeShape, {self._owl_class} ;\n'
        sparql += f'{blank:{indent + 4}}sh:targetClass {self._owl_class} ; \n'
        for p in self._properties:
            sparql += f'{blank:{indent + 4}}sh:property\n'
            sparql += f'{blank:{indent + 8}}[\n'
            sparql += f'{blank:{indent + 12}}sh:path rdf:type ;\n'
            sparql += f'{blank:{indent + 8}}] ;\n'
            sparql += f'{blank:{indent + 4}}sh:property\n'

            sparql += p.create_shacl(indent + 8)
        sparql += f'{blank:{indent}}sh:closed {"true" if self._closed else "false"} .\n'
        return sparql

    def __read_shacl(self) -> None:
        context = Context(name=self._con.context_name)
        if not self._owl_class:
            raise OmasError('ResourceClass mus be created with "owl_class" given as parameter!')
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o
        FROM {self._owl_class.prefix}:shacl
        WHERE {{
            BIND({str(self._owl_class)}Shape AS ?shape)
            ?shape ?p ?o
            FILTER(?p != sh:property)
        }}
        """
        res = con.rdflib_query(query1)
        self._subclass_of = None
        target_class = None
        self._closed = True
        prop_iris: List[QName] = []
        for r in res:
            p = context.iri2qname(r[0])
            if p == 'rdf:type':
                tmp_qname = context.iri2qname(r[1])
                if tmp_qname == f'{self._owl_class}' or tmp_qname == 'sh:nodeShape':
                    continue
                else:
                    raise OmasError(f'Inconsistent Shape for "{self._owl_class}": rdf:type="{context.iri2qname(r[1])}"')
            elif p == 'rdfs:subClassOf':
                tmpstr = context.iri2qname(r[1])
                i = tmpstr.find('Shape')
                if i == -1:
                    raise OmasError('Shape not valid......')  # TODO: Correct error message
                self._subclass_of = tmpstr[:i]
            elif p == 'sh:targetClass':
                target_class = context.iri2qname(r[1])
            elif p == 'sh:closed':
                self._closed = closed = r[1].value
        if target_class and self._owl_class and target_class != self._owl_class:
            raise OmasError(f'Inconsistent shape "{self._owl_class}Shape": sh:targetClass "{target_class}" != rdf:type "{self._owl_class}"')
        if not self._owl_class and target_class:
            self._owl_class = target_class

        query2 = context.sparql_context
        query2 += f"""
        SELECT ?prop ?p ?o ?pp ?oo
        FROM {self._owl_class.prefix}:shacl
        WHERE {{
            BIND({str(self._owl_class)}Shape AS ?shape)
            ?shape sh:property ?prop .
            ?prop ?p ?o .
            OPTIONAL {{
                ?o rdf:rest*/rdf:first ?oo
            }}
        }}
        """
        res = con.rdflib_query(query2)
        properties = {}
        for r in res:
            if r[2] == URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
                continue
            if not isinstance(r[1], URIRef):
                raise OmasError("INCONSISTENCY!")
            p = context.iri2qname(r[1])
            if not properties.get(r[0]):
                properties[r[0]] = {}
            if isinstance(r[2], URIRef):
                properties[r[0]][p] = context.iri2qname(r[2])
            elif isinstance(r[2], Literal):
                properties[r[0]][p] = r[2].toPython()
            elif isinstance(r[2], BNode):
                pass
            else:
                properties[r[0]][p] = r[2]
            if r[1].fragment == 'languageIn':
                if not properties[r[0]].get(p):
                    properties[r[0]][p] = set()
                properties[r[0]][p].add(Languages(r[4].toPython()))
        proplist: List[PropertyClass] = []
        for x, p in properties.items():
            p_iri = None
            p_datatype = None
            p_max_count = None
            p_min_count = None
            p_name = None
            p_description = None
            p_order = None
            p_to_class = None
            required = False
            multiple = True
            restrictions = PropertyRestrictions()
            for key, val in p.items():
                if key == 'sh:path':
                    p_iri = val
                elif key == 'sh:minCount':
                    p_min_count = val
                elif key == 'sh:maxCount':
                    p_max_count = val
                elif key == 'sh:datatype':
                    p_datatype = XsdDatatypes(str(val))
                elif key == 'sh:name':
                    p_name = val
                elif key == 'sh:description':
                    p_description = val
                elif key == 'sh:order':
                    p_order = val
                elif key == 'sh:class':
                    p_to_class = val
                else:
                    try:
                        restrictions[PropertyRestrictionType(key)] = val
                    except (ValueError, TypeError) as err:
                        OmasError(f'Invalid shacl definition: "{key} {val}"')

            if not p_min_count and not p_max_count:
                required = False
                multiple = True
            elif p_min_count == 1 and not p_max_count:
                required = True
                multiple = True
            elif not p_min_count and p_max_count == 1:
                required = False
                multiple = False
            elif p_min_count == 1 and p_max_count == 1:
                required = True
                multiple = False

            proplist.append(PropertyClass(con=self._con,
                                          property_class_iri=p_iri,
                                          datatype=p_datatype,
                                          to_node_iri=p_to_class,
                                          required=required,
                                          multiple=multiple,
                                          restrictions=restrictions,
                                          name=p_name,
                                          description=p_description,
                                          order=p_order))

        self._properties = proplist

    def __read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?prop ?p ?o
        FROM {self._owl_class.prefix}:onto
        WHERE {{
   	        omas:OmasProject rdfs:subClassOf ?prop .
            ?prop ?p ?o .
            FILTER(?o != owl:Restriction)
        }}
        """
        res = self._con.rdflib_query(query1)
        propdict = {}
        for r in res:
            bnode_id = str(r[0])
            if not propdict.get(bnode_id):
                propdict[bnode_id] = {}
                # Default is no restriction on cardinality
                propdict[bnode_id]['required'] = False
                propdict[bnode_id]['multiple'] = True
            p = context.iri2qname(str(r[1]))
            pstr = str(p)
            if pstr == 'owl:onProperty':
                propdict[bnode_id]['property_iri'] = context.iri2qname(str(r[2]))
            elif pstr == 'owl:onClass':
                propdict[bnode_id]['to_node_iri'] = context.iri2qname(str(r[2]))
            elif pstr == 'owl:minQualifiedCardinality':
                if r[2].value == 1:
                    propdict[bnode_id]['required'] = True
                elif r[2].value == 0:
                    propdict[bnode_id]['required'] = False
                else:
                    print(f'ERROR ERROR ERROR: owl:minQualifiedCardinality invalid: "{r[2].value}"')
            elif pstr == 'owl:maxQualifiedCardinality':
                if r[2].value == 1:
                    propdict[bnode_id]['multiple'] = False
            elif pstr == 'owl:qualifiedCardinality':
                if r[2].value != 1:
                    print(f'ERROR ERROR ERROR: QualifiedCardinality invalid: "{r[2].value}"')
                else:
                    propdict[bnode_id]['required'] = True
                    propdict[bnode_id]['mutiple'] = False
            elif pstr == 'owl:onDataRange':
                propdict[bnode_id]['datatype'] = context.iri2qname(str(r[2]))
            else:
                print(f'ERROR ERROR ERROR: Unknown restriction property: "{pstr}"')
        for bn, pp in propdict.items():
            if pp.get('property_iri') is None:
                OmasError('Invalid restriction node: No property_iri!')
            property_iri = pp['property_iri']
            prop = [x for x in self._properties if x.property_class_iri == property_iri]
            if len(prop) != 1:
                OmasError(f'Property "{property_iri}" from OWL has no SHACL definition!')
            prop[0].read_owl()

    def read(self) -> None:
        self.__read_shacl()
        self.__read_owl()

    def __create_shacl(self, indent: int = 0, indent_inc: int = 4):
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent*indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class}Shape a sh:nodeShape, {self._owl_class} ;\n'
        if self._subclass_of:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {self._subclass_of}Shape ; \n'
        sparql += f'{blank:{(indent + 3)*indent_inc}}sh:targetClass {self._owl_class} ; \n'
        for p in self._properties:
            sparql += f'{blank:{(indent + 3)*indent_inc}}sh:property\n'
            sparql += f'{blank:{(indent + 4)*indent_inc}}[\n'
            sparql += f'{blank:{(indent + 5)*indent_inc}}sh:path rdf:type ;\n'
            sparql += f'{blank:{(indent + 4)*indent_inc}}] ;\n'
            sparql += f'{blank:{(indent + 3)*indent_inc}}sh:property\n'
            sparql += p.create_shacl(4)
        sparql += f'{blank:{(indent + 2)*indent_inc}}sh:closed {"true" if self._closed else "false"} .\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        print(sparql)
        #return
        #self._con.update_query(sparql)

    def __create_owl(self, indent: int = 0, indent_inc: int = 4):
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent*indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:onto {{\n'
        for p in self._properties:
            sparql += p.create_owl_part1(indent + 2) + '\n'
        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class} rdf:type owl:Class ;\n'
        if self._subclass_of:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {self._subclass_of} ,\n'
        else:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf\n'
        for i, p in enumerate(self._properties):
            sparql += p.create_owl_part2(indent + 4)
            if i < len(self._properties) - 1:
                sparql += ' ,\n'
            else:
                sparql += ' .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        #print(sparql)
        #return
        #self._con.update_query(sparql)

    def create(self):
        self.__create_shacl()
        self.__create_owl()

if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    omas_project = ResourceClass(con, QName('omas:OmasProject'))
    omas_project.read()
    print(omas_project)
    omas_project.create()
    exit(-1)
    plist = [
        PropertyClass(con=con,
                      property_class_iri=QName('omas:commentstr'),
                      subproperty_of=QName('rdfs:comment'),
                      datatype=XsdDatatypes.string,
                      restrictions=PropertyRestrictions(
                          language_in={Languages.DE, Languages.EN},
                          unique_lang=True
                      ),
                      multiple=True,
                      required=True),
        PropertyClass(con=con,
                      property_class_iri=QName('omas:creator'),
                      to_node_iri=QName('omas:User'),
                      multiple=False,
                      required=True,
                      order=2),
        PropertyClass(con=con,
                      property_class_iri=QName('omas:createdAt'),
                      datatype=XsdDatatypes.dateTime,
                      multiple=False,
                      required=True,
                      order=1)
    ]
    comment_class = ResourceClass(
        con=con,
        owl_cass=QName('omas:OmasComment'),
        subclass_of=QName('omas:OmasUser'),
        properties=plist,
        closed=True
    )
    comment_class.create()
