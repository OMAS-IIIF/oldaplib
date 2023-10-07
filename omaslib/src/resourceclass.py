from enum import Enum
from typing import Union, Optional, List, Set, Any, Tuple, Dict
from pystrict import strict
from rdflib import URIRef, Literal, BNode

from connection import Connection
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes, XsdValidator
from omaslib.src.helpers.datatypes import QName, Action
from omaslib.src.helpers.langstring import Languages, LangString
from omaslib.src.helpers.context import Context
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass
from omaslib.src.propertyrestriction import PropertyRestrictionType, PropertyRestrictions


class ResourceClassAttributes(Enum):
    SUBCLASS_OF = 'subclass_of'
    LABEL = 'label'
    COMMENT = 'comment'
    CLOSED = 'closed'
    PROPERTY = 'property'


@strict
class ResourceClass(Model):
    _owl_class: Union[QName, None]
    _subclass_of: Union[QName, None]
    _properties: Dict[QName, PropertyClass]
    _label: Union[LangString, None]
    _comment: Union[LangString, None]
    _closed: bool
    _changeset: Set[Tuple[ResourceClassAttributes, Action, Union[QName, None]]]

    def __init__(self,
                 con: Connection,
                 owl_cass: Optional[QName] = None,
                 subclass_of: Optional[QName] = None,
                 properties: Optional[Dict[QName, PropertyClass]] = None,
                 label: Optional[LangString] = None,
                 comment: Optional[LangString] = None,
                 closed: Optional[bool] = None) -> None:
        super().__init__(con)
        self._owl_class = owl_cass
        self._subclass_of = subclass_of
        self._properties = properties if properties else {}
        if label and not isinstance(label, LangString):
            raise OmasError(f'Parameter "label" must be a "LangString", but is "{type(label)}"!')
        self._label = label
        if comment and not isinstance(comment, LangString):
            raise OmasError(f'Parameter "comment" must be a "LangString", but is "{type(label)}"!')
        self._comment = comment
        self._closed = True if closed is None else closed
        self._changeset = set()

    def __getitem__(self, key: QName) -> PropertyClass:
        return self._properties[key]

    def __setitem__(self, key: QName, has_property: PropertyClass) -> None:
        if self._properties.get(key) is None:
            self._changeset.add((ResourceClassAttributes.PROPERTY, Action.CREATE, has_property.property_class_iri))
        else:
            self._changeset.add((ResourceClassAttributes.PROPERTY, Action.REPLACE, has_property.property_class_iri))
        self._properties[key] = has_property

    def __delitem__(self, key: QName):
        del self._properties[key]
        self._changeset.add((ResourceClassAttributes.PROPERTY, Action.DELETE, key))

    def get(self, key: QName) -> PropertyClass:
        self._properties.get(key)

    def items(self):
        return self._properties.items()

    def __str__(self):
        blank = ' '
        indent = 4
        s = f'Shape: {self._owl_class}Shape\n'
        if self._subclass_of:
            s += f'Subclass of "{self._subclass_of}"\n'
        if self._label:
            s += f'Label: "{self._label}"\n'
        if self._comment:
            s += f'Comment: "{self._comment}"\n'
        s += f'Closed: {self._closed}\n'
        s += 'Properties:\n'
        sorted_properties = sorted(self._properties.items(), key=lambda prop: prop[1].order if prop[1].order is not None else 9999)
        for tmp, p in sorted_properties:
            s += f'{blank:{indent}}{p}'
            s += '\n'
        return s

    def __attribute_setter(self, resclassattr: ResourceClassAttributes, value: Union[bool, int, float, str, QName, None]):
        ivarname = '_' + resclassattr.value
        if not hasattr(self, ivarname):
            raise OmasError(f'No attribute "{ivarname}" existing!')
        if value != getattr(self, ivarname):
            if getattr(self, ivarname) is None:
                self._changeset.add((resclassattr, Action.CREATE, None))
            else:
                if value is None:
                    self._changeset.add((resclassattr, Action.DELETE, None))
                else:
                    self._changeset.add((resclassattr, Action.REPLACE, None))
            setattr(self, ivarname, value)

    def __langstring_setter(self, resclassattr: ResourceClassAttributes, value: Union[LangString, None]) -> None:
        ivarname = '_' + resclassattr.value
        if not hasattr(self, ivarname):
            raise OmasError(f'No attribute "{resclassattr.value}" existing!')
        if value != getattr(self, ivarname):
            if getattr(self, ivarname) is None:
                setattr(self, ivarname, value)
                self._changeset.add((resclassattr, Action.CREATE, None))
            else:
                if value is None:
                    setattr(self, ivarname, None)
                    self._changeset.add((resclassattr, Action.DELETE, None))
                else:
                    setattr(self, ivarname, value)
                    self._changeset.add((resclassattr, Action.REPLACE, None))

    def __langstring_adder(self, resclassattr: ResourceClassAttributes, lang: Languages, value: Union[str, None]) -> None:
        ivarname = '_' + resclassattr.value
        if getattr(self, ivarname) is not None:
            if getattr(self, ivarname).langstring.get(lang) != value:
                tmp = getattr(self, ivarname)
                if value is None:
                    if tmp.get(lang) is not None:
                        del tmp[lang]
                        self._changeset.add((resclassattr, Action.DELETE, None))
                else:
                    tmp[lang] = value
                    if tmp.get(lang) is not None:
                        self._changeset.add((resclassattr, Action.REPLACE, None))
                    else:
                        self._changeset.add((resclassattr, Action.CREATE, None))
        else:
            setattr(self, ivarname, LangString({lang: value}))
            self._changeset.add((resclassattr, Action.CREATE, None))

    @property
    def owl_class(self) -> QName:
        return self._owl_class

    @owl_class.setter
    def owl_class(self, value: Any) -> None:
        OmasError(f'owl_class cannot be modified/set!')

    @property
    def subclass_of(self) -> Union[QName, None]:
        return self._subclass_of

    @subclass_of.setter
    def subclass_of(self, value: Union[QName, None]) -> None:
        self.__attribute_setter(ResourceClassAttributes.SUBCLASS_OF, value)

    @property
    def label(self) -> LangString:
        return self._label

    @label.setter
    def label(self, label: Union[LangString, None]) -> None:
        self.__langstring_setter(ResourceClassAttributes.LABEL, label)

    def label_add(self, lang: Languages, label: Union[str, None]):
        self.__langstring_adder(ResourceClassAttributes.LABEL, lang, label)

    @property
    def comment(self) -> LangString:
        return self._comment

    @comment.setter
    def comment(self, comment: Union[LangString, None]) -> None:
        self.__langstring_setter(ResourceClassAttributes.COMMENT, comment)

    def comment_add(self, lang: Languages, comment: Union[str, None]):
        self.__langstring_adder(ResourceClassAttributes.COMMENT, lang, comment)

    @property
    def closed(self) -> bool:
        return self._closed

    @closed.setter
    def closed(self, value: Union[bool, None]):
        self.__attribute_setter(ResourceClassAttributes.CLOSED, value)

    @property
    def in_use(self) -> bool:
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?resinstances) as ?nresinstances)
        WHERE {{
            ?resinstance rdf:type {self._owl_class} .
            FILTER(?resinstances != {self._owl_class}Shape)
        }} LIMIT 2
        """
        res = self._con.rdflib_query(query)
        if len(res) != 1:
            raise OmasError('Internal Error in "ResourceClass.in_use"')
        for r in res:
            if int(r.nresinstances) > 0:
                return True
            else:
                return False

    def to_sparql_insert(self, indent: int) -> str:
        blank = ' '
        sparql = f'{blank:{indent}}{self._shape} a sh:NodeShape, {self._owl_class} ;\n'
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
        """
        Read the shacl definition from the triple store and create the respective ResourceClass
        and PropertyClass instances which represent the Shape and OWL definitions in Python.

        :return: None
        """
        context = Context(name=self._con.context_name)
        if not self._owl_class:
            raise OmasError('ResourceClass must be created with "owl_class" given as parameter!')

        query1 = context.sparql_context
        query1 += f"""
        SELECT ?p ?o ?propiri ?propshape
        FROM {self._owl_class.prefix}:shacl
        WHERE {{
            BIND({str(self._owl_class)}Shape AS ?shape)
            ?shape ?p ?o
            OPTIONAL {{
                {{ ?o sh:path ?propiri . }} UNION {{ ?o sh:propertyShape ?propshape }}
            }}
        }}
         """
        res = con.rdflib_query(query1)
        self._subclass_of = None
        self._label = None
        self._comment = None
        self._closed = True
        propiris: List[QName] = []
        propshapes: List[QName] = []
        for r in res:
            p = context.iri2qname(r[0])
            if p == 'rdf:type':
                tmp_qname = context.iri2qname(r[1])
                if tmp_qname == QName('sh:NodeShape'):
                    continue
                if self._owl_class is None:
                    self._owl_class = tmp_qname
                else:
                    if tmp_qname != self._owl_class:
                        raise OmasError(f'Inconsistent Shape for "{self._owl_class}": rdf:type="{tmp_qname}"')
            elif p == 'rdfs:label':
                ll = Languages(r[1].language) if r[1].language else Languages.XX
                if self._label is None:
                    self._label = LangString({ll: r[1].toPython()})
                else:
                    self._label[ll] = r[1].toPython()
            elif p == 'rdfs:comment':
                ll = Languages(r[1].language) if r[1].language else Languages.XX
                if self._comment is None:
                    self._comment = LangString({ll: r[1].toPython()})
                else:
                    self._comment[ll] = r[1].toPython()
            elif p == 'rdfs:subClassOf':
                tmpstr = context.iri2qname(r[1])
                i = str(tmpstr).find('Shape')
                if i == -1:
                    raise OmasError('Shape not valid......')  # TODO: Correct error message
                self._subclass_of = QName(str(tmpstr)[:i])
            elif p == 'sh:targetClass':
                tmp_qname = context.iri2qname(r[1])
                if self._owl_class is None:
                    self._owl_class = tmp_qname
                else:
                    if tmp_qname != self._owl_class:
                        raise OmasError(f'Inconsistent Shape for "{self._owl_class}": sh:targetClass="{tmp_qname}"')
            elif p == 'sh:closed':
                self._closed = closed = r[1].value
            elif p == 'sh:property':
                if r[2] is not None:
                    propiris.append(context.iri2qname(r[2]))
                if r[3] is not None:
                    propshapes.append(context.iri2qname(r[3]))

        # TODO: read all propiris and propshapes. Move and adapt the code below to PropertClass.py !!!

        query2 = context.sparql_context
        query2 += f"""
        SELECT ?prop ?p ?o ?oo
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
            if not properties.get(r[0]):
                properties[r[0]] = {}
            p = context.iri2qname(r[1])
            if isinstance(r[2], URIRef):
                if properties[r[0]].get(p) is None:
                    properties[r[0]][p] = []
                properties[r[0]][p].append(context.iri2qname(r[2]))
            elif isinstance(r[2], Literal):
                if properties[r[0]].get(p) is None:
                    properties[r[0]][p] = []
                if r[2].language is None:
                    properties[r[0]][p].append(r[2].toPython())
                else:
                    properties[r[0]][p].append(r[2].toPython() + '@' + r[2].language)
            elif isinstance(r[2], BNode):
                pass
            else:
                if properties[r[0]].get(p) is None:
                    properties[r[0]][p] = []
                properties[r[0]][p].append(r[2])
            if r[1].fragment == 'languageIn':
                if not properties[r[0]].get(p):
                    properties[r[0]][p] = set()
                properties[r[0]][p].add(Languages(r[3].toPython()))
        for x, p in properties.items():
            p_iri = None
            p_datatype = None
            p_name = None
            p_description = None
            p_order = None
            p_to_class = None
            restrictions = PropertyRestrictions()
            exclusive_for_class: Optional[QName] = None
            # If "x" is a BNode, then the property is defined within a sh:NodeShape definition and thus is exclusive
            # for this sh:NodeShape. This implies that within the OWL ontology, we are able to define the rdfs:domain
            # property
            if isinstance(x, BNode):
                exclusive_for_class = self._owl_class
            elif isinstance(x, URIRef):
                pass
            else:
                raise OmasError(f'Inconsistency in SHACL: expected either "BNode" or "URIRef" buf got "{type(x)}"!')
            for key, val in p.items():
                if key == 'sh:path':
                    p_iri = val[0]
                elif key == 'sh:datatype':
                    p_datatype = XsdDatatypes(str(val[0]))
                elif key == 'sh:name':
                    p_name = LangString()
                    for ll in val:
                        p_name.add(ll)
                elif key == 'sh:description':
                    p_description = LangString()
                    for ll in val:
                        p_description.add(ll)
                elif key == 'sh:order':
                    p_order = val[0]
                elif key == 'sh:class':
                    p_to_class = val[0]
                else:
                    try:
                        restrictions[PropertyRestrictionType(key)] = val[0]
                    except (ValueError, TypeError) as err:
                        OmasError(f'Invalid shacl definition: "{key} {val}"')

            prop = PropertyClass(con=self._con,
                                 property_class_iri=p_iri,
                                 exclusive_for_class=exclusive_for_class,
                                 datatype=p_datatype,
                                 to_node_iri=p_to_class,
                                 restrictions=restrictions,
                                 name=p_name,
                                 description=p_description,
                                 order=p_order)

            self._properties[p_iri] = prop

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
            p = context.iri2qname(str(r[1]))
            pstr = str(p)
            if pstr == 'owl:onProperty':
                propdict[bnode_id]['property_iri'] = context.iri2qname(str(r[2]))
            elif pstr == 'owl:onClass':
                propdict[bnode_id]['to_node_iri'] = context.iri2qname(str(r[2]))
            elif pstr == 'owl:minQualifiedCardinality':
                propdict[bnode_id]['min_count'] = r[2].value
            elif pstr == 'owl:maxQualifiedCardinality':
                propdict[bnode_id]['max_count'] = r[2].value
            elif pstr == 'owl:qualifiedCardinality':
                propdict[bnode_id]['min_count'] = r[2].value
                propdict[bnode_id]['max_count'] = r[2].value
            elif pstr == 'owl:onDataRange':
                propdict[bnode_id]['datatype'] = context.iri2qname(str(r[2]))
            else:
                print(f'ERROR ERROR ERROR: Unknown restriction property: "{pstr}"')
        for bn, pp in propdict.items():
            if pp.get('property_iri') is None:
                OmasError('Invalid restriction node: No property_iri!')
            property_iri = pp['property_iri']
            prop = [x for x in self._properties if x == property_iri]
            if len(prop) != 1:
                OmasError(f'Property "{property_iri}" from OWL has no SHACL definition!')
            self._properties[prop[0]].prop.read_owl()

    def read(self) -> None:
        self.__read_shacl()
        self.__read_owl()

    def __create_shacl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent*indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'

        for iri, p in self._properties.items():
            if p.exclusive_for_class is None:
                sparql += "\n"
                sparql += f'{blank:{(indent + 2)*indent_inc}}{iri}Shape a sh:PropertyShape ;\n'
                sparql += p.property_node(4) + " .\n"
                sparql += "\n"

        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class}Shape a sh:NodeShape, {self._owl_class} ;\n'
        if self._subclass_of:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {self._subclass_of}Shape ;\n'
        sparql += f'{blank:{(indent + 3)*indent_inc}}sh:targetClass {self._owl_class} ;\n'
        if self._label:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:label {self._label} ;\n'
        if self._comment:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:comment {self._comment} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}sh:property\n'
        sparql += f'{blank:{(indent + 4) * indent_inc}}[\n'
        sparql += f'{blank:{(indent + 5) * indent_inc}}sh:path rdf:type ;\n'
        sparql += f'{blank:{(indent + 4) * indent_inc}}] ;\n'
        for iri, p in self._properties.items():
            if p.exclusive_for_class:
                sparql += f'{blank:{(indent + 3)*indent_inc}}sh:property [\n'
                sparql += p.property_node(4) + ' ;\n'
                sparql += f'{blank:{(indent + 3) * indent_inc}}] ;\n'
            else:
                sparql += f'{blank:{(indent + 3)*indent_inc}}sh:property {iri}Shape ;\n'
        sparql += f'{blank:{(indent + 2)*indent_inc}}sh:closed {"true" if self._closed else "false"} .\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        if as_string:
            return sparql
        else:
            #print(sparql)
            self._con.update_query(sparql)

    def __create_owl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False):
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent*indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:onto {{\n'
        for iri, p in self._properties.items():
            sparql += p.create_owl_part1(indent + 2) + '\n'
        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class} rdf:type owl:Class ;\n'
        if self._subclass_of:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {self._subclass_of} ,\n'
        else:
            sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf\n'
        i = 0
        for iri, p in self._properties.items():
            sparql += p.create_owl_part2(indent + 4)
            if i < len(self._properties) - 1:
                sparql += ' ,\n'
            else:
                sparql += ' .\n'
            i += 1
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        if as_string:
            return sparql
        else:
            #print(sparql)
            self._con.update_query(sparql)

    def create(self, as_string: bool = False) -> Union[str, None]:
        if as_string:
            rdfdata = self.__create_shacl(as_string=as_string)
            rdfdata += self.__create_owl(as_string=as_string)
            return rdfdata
        else:
            self.__create_shacl(as_string)
            self.__create_owl(as_string)

    def __update_shacl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        if not self._changeset:
            if as_string:
                return ''
            else:
                return
        sparql_switch1 = {
            ResourceClassAttributes.SUBCLASS_OF: '?shape rdfs:subClassOf ?subclass_of .',
            ResourceClassAttributes.CLOSED: '?shape sh:closed ?closed .',
            ResourceClassAttributes.LABEL: '?shape rdfs:label ?label .',
            ResourceClassAttributes.COMMENT: '?shape rdfs:comment ?comment .',
            ResourceClassAttributes.PROPERTY: '?shape sh:property ?propnode'
        }
        sparql_switch2 = {
            ResourceClassAttributes.SUBCLASS_OF: f'?shape rdfs:subClassOf {self._subclass_of}Shape .',
            ResourceClassAttributes.CLOSED: f'?shape sh:closed {"true" if self._closed else "false"} .',
            ResourceClassAttributes.LABEL: f'?shape rdfs:label {self._label} .',
            ResourceClassAttributes.COMMENT: f'?shape rdfs:comment {self._comment} .',
            ResourceClassAttributes.PROPERTY: ''
        }
        sparql_switch3 = {
            ResourceClassAttributes.SUBCLASS_OF: 'OPTIONAL { ?shape rdfs:subClassOf ?subclass_of }',
            ResourceClassAttributes.CLOSED: 'OPTIONAL { ?shape sh:closed ?closed }',
            ResourceClassAttributes.LABEL: 'OPTIONAL { ?shape rdfs:label ?label }',
            ResourceClassAttributes.COMMENT: 'OPTIONAL { ?shape rdfs:comment ?comment }',
            ResourceClassAttributes.PROPERTY: 'OPTIONAL { ?shape sh:property ?propnode }'
        }

        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        n = len(self._changeset)
        i = 1
        do_it = False
        for name, action, prop_iri in self._changeset:
            if name == ResourceClassAttributes.PROPERTY:
                print(self._properties)
                sparql_switch2[ResourceClassAttributes.PROPERTY] = '?shape sh:property [\n' + self._properties[prop_iri].property_node(indent + 1) + ' ; ]'
                if action == Action.DELETE:
                    sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch1[name]}\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                    sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
                    sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
                    sparql += f'{blank:{(indent + 2)*indent_inc}}?shape rdf:type sh:NodeShape .\n'
                    sparql += f'{blank:{(indent + 2)*indent_inc}}?shape sh:targetClass {self._owl_class} .\n'
                    sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch3[name]}\n'
                    sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
                    sparql += f'{blank:{indent*indent_inc}}}}{"" if i == n else " ;"}\n'

            sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch1[name]}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'

            if action != Action.DELETE:
                sparql += f'{blank:{indent*indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch2[name]}\n'
                sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
                sparql += f'{blank:{indent*indent_inc}}}}\n'

            sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}?shape rdf:type sh:NodeShape .\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}?shape sh:targetClass {self._owl_class} .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch3[name]}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}{"" if i == n else " ;"}\n'
            i += 1
            do_it = True
        if as_string:
            return sparql
        else:
            if do_it:
                self._con.update_query(sparql)

    def __update_owl(self, indent: int = 0, indent_inc: int = 4, as_string: bool = False) -> Union[str, None]:
        action = None
        if (ResourceClassAttributes.SUBCLASS_OF, Action.DELETE) in self._changeset:
            action = Action.DELETE
        elif (ResourceClassAttributes.SUBCLASS_OF, Action.REPLACE) in self._changeset:
            action = Action.REPLACE
        elif (ResourceClassAttributes.SUBCLASS_OF, Action.CREATE) in self._changeset:
            action = Action.CREATE

        if action:
            blank = ''
            context = Context(name=self._con.context_name)
            sparql = context.sparql_context
            sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:onto {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owl_class} rdfs:subClassOf ?subclass_of .\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'

            if action != Action.DELETE:
                sparql += f'{blank:{indent*indent_inc}}INSERT {{\n'
                sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owl_class} rdfs:subClassOf {self._subclass_of} .'
                sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
                sparql += f'{blank:{indent*indent_inc}}}}\n'

            sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class} rdf:type owl:Class .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}OPTIONAL {{\n'
            sparql += f'{blank:{(indent + 3)*indent_inc}}{self._owl_class} rdfs:subClassOf ?subclass_of .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}}}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'
            if as_string:
                return sparql
            else:
                self._con.update_query(sparql)
        else:
            if as_string:
                return ''
            else:
                return

    def update(self, as_string: bool = False) -> Union[str, None]:
        if as_string:
            tmp = self.__update_shacl(as_string=True)
            #print(tmp)
            tmp += self.__update_owl(as_string=True)
            return tmp
        else:
            self.__update_shacl()
            self.__update_owl()


if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    omas_project = ResourceClass(con, QName('omas:Project'))
    omas_project.read()
    #print(omas_project)
    #print(omas_project.create(as_string=True))
    #exit(0)
    #omas_project.label = LangString({Languages.EN: '*Omas Project*', Languages.DE: '*Omas-Projekt*'})
    #omas_project.comment_add(Languages.FR, 'Un project pour OMAS')
    #omas_project.closed = False
    #omas_project.subclass_of = QName('omas:Object')
    omas_project[QName('omas:projectEnd')].name = LangString({Languages.DE: "Projektende"})
    print(omas_project.update(as_string=True))
    # omas_project2 = ResourceClass(con, QName('omas:OmasProject'))
    # omas_project2.read()
    # print(omas_project2)
    # exit(0)
    #omas_project.closed = False
    #omas_project.update()
    #omas_project2 = ResourceClass(con, QName('omas:OmasProject'))
    #omas_project2.read()
    #print(omas_project2)
    #exit(0)
    #print(omas_project)
    #omas_project.create()
    #exit(-1)
    pdict = {
        QName('omas:commentstr'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:commentstr'),
                      datatype=XsdDatatypes.string,
                      exclusive_for_class=QName('omas:OmasComment'),
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          language_in={Languages.DE, Languages.EN},
                          unique_lang=True
                      ),
                      name=LangString({Languages.EN: "Comment"}),
                      description=LangString({Languages.EN: "A comment to anything"}),
                      order=1),
        QName('omas:creator'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:creator'),
                      to_node_iri=QName('omas:User'),
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          max_count=1
                      ),
                      order=2),
        QName('omas:createdAt'):
        PropertyClass(con=con,
                      property_class_iri=QName('omas:createdAt'),
                      datatype=XsdDatatypes.dateTime,
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          max_count=1
                      ),
                      order=3)
    }
    comment_class = ResourceClass(
        con=con,
        owl_cass=QName('omas:OmasComment'),
        subclass_of=QName('omas:OmasUser'),
        label=LangString({Languages.EN: 'Omas Comment', Languages.DE: 'Omas Kommentar'}),
        comment=LangString({Languages.EN: 'A class to comment something...'}),
        properties=pdict,
        closed=True
    )
    comment_class.create()
    comment_class = None
    comment_class2 = ResourceClass(con=con, owl_cass=QName('omas:OmasComment'))
    comment_class2.read()
    print(comment_class2)
