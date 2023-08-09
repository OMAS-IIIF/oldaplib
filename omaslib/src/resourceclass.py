from typing import Union, Optional, List, Set, Any, Dict, Tuple
from pystrict import strict
from rdflib import URIRef, Literal, BNode

from connection import Connection
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.helpers.datatypes import QName
from omaslib.src.helpers.langstring import Languages, LangString
from omaslib.src.helpers.context import Context, DEFAULT_CONTEXT
from omaslib.src.model import Model
from omaslib.src.propertyclass import PropertyClass
from omaslib.src.propertyrestriction import PropertyRestrictionType, PropertyRestrictions


@strict
class ResourceClass(Model):
    _owl_class: Union[QName, None]
    _subclass_of: Union[QName, None]
    _properties: List[PropertyClass]
    _label: Union[LangString, None]
    _comment: Union[LangString, None]
    _closed: bool

    _changeset: Set[str]

    def __init__(self,
                 con: Connection,
                 owl_cass: Optional[QName] = None,
                 subclass_of: Optional[QName] = None,
                 properties: Optional[List[PropertyClass]] = None,
                 label: Optional[LangString] = None,
                 comment: Optional[LangString] = None,
                 closed: Optional[bool] = None) -> None:
        super().__init__(con)
        self._owl_class = owl_cass
        self._subclass_of = subclass_of
        self._properties = properties if properties else set()
        if label and not isinstance(label, LangString):
            raise OmasError(f'Parameter "label" must be a "LangString", but is "{type(label)}"!')
        self._label = label
        if comment and not isinstance(comment, LangString):
            raise OmasError(f'Parameter "comment" must be a "LangString", but is "{type(label)}"!')
        self._comment = comment
        self._closed = True if closed is None else closed
        self._changeset = set()

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
        for p in self._properties:
            s += f'{blank:{indent}}{str(p)}\n'
        return s

    def __attribute_setter(self, varname: str, value: Union[bool, int, float, str, QName, None]):
        ivarname = '_' + varname
        if not hasattr(self, ivarname):
            raise OmasError(f'No attribute "{ivarname}" existing!')
        if value != getattr(self, ivarname):
            if getattr(self, ivarname) is None:
                self._changeset.add(f'{varname}:create')
            else:
                if value is None:
                    self._changeset.add(f'{varname}:delete')
                else:
                    self._changeset.add(f'{varname}:replace')
            setattr(self, ivarname, value)

    def __langstring_setter(self, varname: str, value: Union[LangString, None]) -> None:
        ivarname = '_' + varname
        if not hasattr(self, ivarname):
            raise OmasError(f'No attribute "{ivarname}" existing!')
        if value != getattr(self, ivarname):
            if getattr(self, ivarname) is None:
                setattr(self, ivarname, value)
                self._changeset.add(f'{varname}:create')
            else:
                if value is None:
                    setattr(self, ivarname, None)
                    self._changeset.add(f'{varname}:delete')
                else:
                    setattr(self, ivarname, value)
                    self._changeset.add(f'{varname}:replace')

    def __langstring_adder(self, varname: str, lang: Languages, value: Union[str, None]) -> None:
        ivarname = '_' + varname
        if getattr(self, ivarname) is not None:
            if getattr(self, ivarname).langstring.get(lang) != value:
                tmp = getattr(self, ivarname)
                if value is None:
                    if tmp.get(lang) is not None:
                        del tmp[lang]
                        self._changeset.add(f'{varname}:delete_lang')
                else:
                    tmp[lang] = value
                    if tmp.get(lang) is not None:
                        self._changeset.add(f'{varname}:replace_lang')
                    else:
                        self._changeset.add(f'{varname}:create_lang')
        else:
            setattr(self, ivarname, LangString({lang: value}))
            self._changeset.add(f'{varname}:create')

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
        self.__attribute_setter('subclass_of', value)

    @property
    def label(self) -> LangString:
        return self._label

    @label.setter
    def label(self, label: Union[LangString, None]) -> None:
        self.__langstring_setter('label', label)

    def label_add(self, lang: Languages, label: Union[str, None]):
        self.__langstring_adder('label', lang, label)

    @property
    def comment(self) -> LangString:
        return self._comment

    @comment.setter
    def comment(self, comment: Union[LangString, None]) -> None:
        self.__langstring_setter('comment', comment)

    def comment_add(self, lang: Languages, comment: Union[str, None]):
        self.__langstring_adder('comment', lang, comment)

    @property
    def closed(self) -> bool:
        return self._closed

    @closed.setter
    def closed(self, value: bool):
        self.__attribute_setter('closed', value)

    def get_property(self, property_class_iri: QName) -> PropertyClass:
        for p in self._properties:
            if p.property_class_iri == property_class_iri:
                return p
        raise OmasError(f'Property "{property_class_iri}" does not exist!')

    def add_property(self, property: PropertyClass):
        for p in self._properties:
            if p.property_class_iri == property.property_class_iri:
                raise OmasError(f'Property "{property.property_class_iri}" already exists!')
        property.set_new()
        self._properties.append(property)
        self._changeset.add("property")

    def delete_property(self, property_class_iri: QName):
        for p in self._properties:
            if p.property_class_iri == property_class_iri:
                pass

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
        """
        Read the shacl definition from the triple store and create the respective ResourceClass
        and PropertyClass instances which represent the Shape and OWL definitions in Python.

        :return: None
        """
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
        self._label = None
        self._comment = None
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
                self._subclass_of = str(tmpstr)[:i]
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
                properties[r[0]][p].add(Languages(r[4].toPython()))
        proplist: List[PropertyClass] = []
        for x, p in properties.items():
            p_iri = None
            p_datatype = None
            p_name = None
            p_description = None
            p_order = None
            p_to_class = None
            restrictions = PropertyRestrictions()
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


            proplist.append(PropertyClass(con=self._con,
                                          property_class_iri=p_iri,
                                          datatype=p_datatype,
                                          to_node_iri=p_to_class,
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
        for p in self._properties:
            sparql += f'{blank:{(indent + 3)*indent_inc}}sh:property\n'
            sparql += p.create_shacl(4)
        sparql += f'{blank:{(indent + 2)*indent_inc}}sh:closed {"true" if self._closed else "false"} .\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        print(sparql)
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
        print(sparql)
        #self._con.update_query(sparql)

    def create(self):
        self.__create_shacl()
        self.__create_owl()

    def __update_shacl(self, indent: int = 0, indent_inc: int = 4) -> None:
        if not self._changeset:
            return
        sparql_switch1 = {
            'subclass_of': '?shape rdfs:subClassOf ?subclass_of .',
            'closed': '?shape sh:closed ?closed .',
            'label': '?shape rdfs:label ?label .',
            'comment': '?shape rdfs:comment ?comment .'
        }
        sparql_switch2 = {
            'subclass_of': f'?shape rdfs:subClassOf {self._subclass_of}Shape .',
            'closed': f'?shape sh:closed {"true" if self._closed else "false"} .',
            'label': f'?shape rdfs:label {self._label} .',
            'comment': f'?shape rdfs:comment {self._comment} .'
        }
        sparql_switch3 = {
            'subclass_of': f'OPTIONAL {{ ?shape rdfs:subClassOf ?subclass_of }}',
            'closed': f'OPTIONAL {{ ?shape sh:closed ?closed }}',
            'label': f'OPTIONAL {{ ?shape rdfs:label ?label }}',
            'comment': f'OPTIONAL {{ ?shape rdfs:comment ?comment }}'
        }

        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        n = len(self._changeset)
        i = 1
        for cs in self._changeset:
            name, action = cs.split(':')
            if not name in sparql_switch1:
                pass  # TODO: Error handling
            sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch1[name]}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'

            sparql += f'{blank:{indent*indent_inc}}INSERT {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch2[name]}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}\n'

            sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}?shape rdf:type sh:nodeShape .\n'
            sparql += f'{blank:{(indent + 2)*indent_inc}}?shape sh:targetClass {self._owl_class} .\n'
            sparql += f'{blank:{(indent + 2) * indent_inc}}{sparql_switch3[name]}\n'
            sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
            sparql += f'{blank:{indent*indent_inc}}}}{"" if i == n else " ;"}\n'
            i += 1
        print(sparql)
        self._con.update_query(sparql)

    def __update_owl(self, indent: int = 0, indent_inc: int = 4):
        if not self._changeset:
            return
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent*indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:onto {{\n'
        for c in self._changeset:
            if c == 'subclass_of':
                sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owl_class} rdfs:subClassOf ?subclass_of .'
        sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'

        sparql += f'{blank:{indent*indent_inc}}INSERT {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
        for c in self._changeset:
            if c == 'subclass_of' and self._subclass_of:
                sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owl_class} rdfs:subClassOf {self._subclass_of} .'
        sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'

        sparql += f'{blank:{indent*indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}GRAPH {self._owl_class.prefix}:shacl {{\n'
        sparql += f'{blank:{(indent + 2)*indent_inc}}{self._owl_class} rdf:type owl:Class .\n'
        for c in self._changeset:
            if c == 'subclass_of':
                sparql += f'{blank:{(indent + 2) * indent_inc}}OPTIONAL {{\n'
                sparql += f'{blank:{(indent + 3)*indent_inc}}{self._owl_class} rdfs:subClassOf ?subclass_of .\n'
                sparql += f'{blank:{(indent + 2) * indent_inc}}}}\n'
        sparql += f'{blank:{(indent + 1)*indent_inc}}}}\n'
        sparql += f'{blank:{indent*indent_inc}}}}\n'
        print(sparql)
        #self._con.update_query(sparql)


    def update(self):
        self.__update_shacl()
        #self.__update_owl()

if __name__ == '__main__':
    con = Connection('http://localhost:7200', 'omas')
    omas_project = ResourceClass(con, QName('omas:OmasProject'))
    omas_project.read()
    print(omas_project)
    omas_project.label = LangString({Languages.EN: '*Omas Project*', Languages.DE: '*Omas-Projekt*'})
    omas_project.comment_add(Languages.FR, 'Un project pour OMAS')
    omas_project.closed = False
    omas_project.subclass_of = QName('omas:Object')
    omas_project.update()
    omas_project2 = ResourceClass(con, QName('omas:OmasProject'))
    omas_project2.read()
    print(omas_project2)
    exit(0)
    #omas_project.closed = False
    #omas_project.update()
    #omas_project2 = ResourceClass(con, QName('omas:OmasProject'))
    #omas_project2.read()
    #print(omas_project2)
    #exit(0)
    #print(omas_project)
    #omas_project.create()
    #exit(-1)
    plist = [
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
        PropertyClass(con=con,
                      property_class_iri=QName('omas:creator'),
                      to_node_iri=QName('omas:User'),
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          max_count=1
                      ),
                      order=2),
        PropertyClass(con=con,
                      property_class_iri=QName('omas:createdAt'),
                      datatype=XsdDatatypes.dateTime,
                      restrictions=PropertyRestrictions(
                          min_count=1,
                          max_count=1
                      ),
                      order=3)
    ]
    comment_class = ResourceClass(
        con=con,
        owl_cass=QName('omas:OmasComment'),
        subclass_of=QName('omas:OmasUser'),
        label=LangString({Languages.EN: 'Omas Comment', Languages.DE: 'Omas Kommentar'}),
        comment=LangString({Languages.EN: 'A class to comment something...'}),
        properties=plist,
        closed=True
    )
    comment_class.create()
