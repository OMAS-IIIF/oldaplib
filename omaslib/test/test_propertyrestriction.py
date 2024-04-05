import json
import unittest
from copy import deepcopy
from typing import Dict

from rdflib import ConjunctiveGraph

from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.enums.propertyrestrictiontype import PropertyRestrictionType
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.query_processor import QueryProcessor
from omaslib.src.propertyrestrictions import PropertyRestrictions
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd import Xsd
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_float import Xsd_float
from omaslib.src.xsd.xsd_integer import Xsd_integer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_string import Xsd_string




class TestPropertyRestrictions(unittest.TestCase):

    test_restrictions = {
        PropertyRestrictionType.LANGUAGE_IN: LanguageIn('de', 'fr', 'it', 'en'),
        PropertyRestrictionType.IN: RdfSet({Xsd_string('A'), Xsd_string('B'), Xsd_string('C')}),
        PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
        PropertyRestrictionType.MIN_COUNT: Xsd_integer(1),
        PropertyRestrictionType.MAX_COUNT: Xsd_integer(4),
        PropertyRestrictionType.MIN_LENGTH: Xsd_integer(8),
        PropertyRestrictionType.MAX_LENGTH: Xsd_integer(64),
        PropertyRestrictionType.MIN_EXCLUSIVE: Xsd_float(6.5),
        PropertyRestrictionType.MIN_INCLUSIVE: Xsd_integer(8),
        PropertyRestrictionType.MAX_EXCLUSIVE: Xsd_float(6.5),
        PropertyRestrictionType.MAX_INCLUSIVE: Xsd_integer(8),
        PropertyRestrictionType.PATTERN: Xsd_string('.*'),
        PropertyRestrictionType.LESS_THAN: Iri('test:greater'),
        PropertyRestrictionType.LESS_THAN_OR_EQUALS: Iri('test:gaga')
    }
    test_restrictions2 = {
        PropertyRestrictionType.LANGUAGE_IN: LanguageIn('el', 'he'),
        PropertyRestrictionType.IN: RdfSet({Xsd_string('X'), Xsd_string('Y'), Xsd_string('Z')}),
        PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(False),
        PropertyRestrictionType.MIN_COUNT: Xsd_integer(0),
        PropertyRestrictionType.MAX_COUNT: Xsd_integer(10),
        PropertyRestrictionType.MIN_LENGTH: Xsd_integer(3),
        PropertyRestrictionType.MAX_LENGTH: Xsd_integer(12),
        PropertyRestrictionType.MIN_EXCLUSIVE: Xsd_float(10),
        PropertyRestrictionType.MIN_INCLUSIVE: Xsd_integer(80),
        PropertyRestrictionType.MAX_EXCLUSIVE: Xsd_float(65),
        PropertyRestrictionType.MAX_INCLUSIVE: Xsd_integer(80),
        PropertyRestrictionType.PATTERN: Xsd_string('^.*$'),
        PropertyRestrictionType.LESS_THAN: Iri('test:less_than'),
        PropertyRestrictionType.LESS_THAN_OR_EQUALS: Iri('test:gugus')
    }

    def check_shacl_expectation(self,
                                context: Context,
                                expected: dict[PropertyRestrictionType, Xsd | LanguageIn | RdfSet],
                                rdfgraph: ConjunctiveGraph):
        query = context.sparql_context
        query += '''SELECT ?prop ?val ?oo
        WHERE {
          test:testShape a sh:PropertyShape .
          test:testShape ?prop ?val .
                    OPTIONAL {{
                        ?val rdf:rest*/rdf:first ?oo
                    }}
        }
        '''
        results = rdfgraph.query(query)
        jsonobj = json.loads(results.serialize(format='json'))
        res = QueryProcessor(context, jsonobj)
        lang_in = LanguageIn()
        set_in = RdfSet()
        for r in res:
            if str(r['prop']) in {"rdf:type", "sh:path", "dcterms:creator", "dcterms:created", "dcterms:modified", "dcterms:contributor"}:
                continue
            key = PropertyRestrictionType(str(r['prop']))
            if key == PropertyRestrictionType.LANGUAGE_IN:
                lang_in.add(str(r['oo']))
            elif key == PropertyRestrictionType.IN:
                set_in.add(r['oo'])
            else:
                self.assertEqual(expected[key], r['val'])
        if expected.get(PropertyRestrictionType.LANGUAGE_IN) is not None:
            self.assertEqual(expected[PropertyRestrictionType.LANGUAGE_IN], lang_in)
        if expected.get(PropertyRestrictionType.IN) is not None:
            self.assertEqual(expected[PropertyRestrictionType.IN], set_in)

    def check_onto_expectation(self, context: Context, expected: dict[Iri, Xsd], rdfgraph: ConjunctiveGraph):
        query = context.sparql_context
        query += '''SELECT ?prop ?val
        WHERE {
            test:test ?prop ?val .
        }
        '''
        results = rdfgraph.query(query)
        jsonobj = json.loads(results.serialize(format='json'))
        res = QueryProcessor(context, jsonobj)
        for r in res:
            if str(r['prop']) in {"rdf:type", "dcterms:creator", "dcterms:created", "dcterms:modified", "dcterms:contributor"}:
                continue
            self.assertEqual(expected[r['prop']], r['val'])

    def create_shacl_restriction(self, context: Context, restrictions: PropertyRestrictions) -> tuple[ConjunctiveGraph, Xsd_dateTime]:
        modified = Xsd_dateTime()
        data = context.sparql_context
        data += f'''test:shacl {{
          test:testShape a sh:PropertyShape ;
            sh:path test:test {restrictions.create_shacl(indent=2, indent_inc=2)} ;
            dcterms:creator <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:created {modified.toRdf} ;
            dcterms:contributor <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:modified {modified.toRdf} ;
        }} 
        '''
        g1 = ConjunctiveGraph()
        g1.parse(data=data, format='trig')
        return g1, modified

    def create_onto_restriction(self, context: Context, restrictions: PropertyRestrictions) -> tuple[ConjunctiveGraph, Xsd_dateTime]:
        modified = Xsd_dateTime()
        data = context.sparql_context
        data += f'''test:onto {{
          test:test a owl:DatatypeProperty {restrictions.create_owl(indent=2, indent_inc=2)} ;
            dcterms:creator <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:created {modified.toRdf} ;
            dcterms:contributor <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:modified {modified.toRdf} ;
        }}
        '''
        g1 = ConjunctiveGraph()
        g1.parse(data=data, format='trig')
        return g1, modified

    def test_constructor(self):
        val = PropertyRestrictions()
        val = PropertyRestrictions(restrictions=self.test_restrictions)
        self.assertEqual(len(val), 14)

        for key, expected_val in self.test_restrictions.items():
            self.assertEqual(val[key], expected_val)
        s = str(val)

    def test_restriction_create_shacl(self):
        restrictions = deepcopy(self.test_restrictions)
        val = PropertyRestrictions(restrictions=restrictions)
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"
        g1, modified = self.create_shacl_restriction(context, val)
        self.check_shacl_expectation(context, self.test_restrictions, g1)

    def test_restriction_create_onto(self):
        restrictions = deepcopy(self.test_restrictions)
        val = PropertyRestrictions(restrictions=restrictions)
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"
        g1, modified = self.create_onto_restriction(context, val)
        self.check_onto_expectation(context, {Iri('owl:minCardinality'): Xsd_nonNegativeInteger(1),
                                              Iri('owl:maxCardinality'): Xsd_nonNegativeInteger(4)}, g1)

        restrictions = deepcopy(self.test_restrictions)
        restrictions[PropertyRestrictionType.MIN_COUNT] = Xsd_integer(1)
        restrictions[PropertyRestrictionType.MAX_COUNT] = Xsd_integer(1)
        val = PropertyRestrictions(restrictions=restrictions)
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"
        g1, modified = self.create_onto_restriction(context, val)
        self.check_onto_expectation(context, {Iri('owl:cardinality'): Xsd_nonNegativeInteger(1)}, g1)


    def test_restriction_setitem_on_empty(self):
        val = PropertyRestrictions()
        for key, newval in self.test_restrictions.items():
            val[key] = newval
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"
        g1, modified = self.create_shacl_restriction(context, val)
        self.check_shacl_expectation(context, self.test_restrictions, g1)

    def test_restriction_setitem(self):
        restrictions = deepcopy(self.test_restrictions)
        val = PropertyRestrictions(restrictions=restrictions)
        for key, newval in self.test_restrictions2.items():
            val[key] = newval
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"
        g1, modified = self.create_shacl_restriction(context, val)
        self.check_shacl_expectation(context, self.test_restrictions2, g1)

    def test_restriction_undo(self):
        restrictions = deepcopy(self.test_restrictions)
        val = PropertyRestrictions(restrictions=restrictions)
        for key, newval in self.test_restrictions2.items():
            val[key] = newval
        for key in self.test_restrictions2.keys():
            val.undo(key)
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"
        g1, modified = self.create_shacl_restriction(context, val)
        self.check_shacl_expectation(context, self.test_restrictions, g1)

    def test_restriction_update_shacl(self):
        restrictions = deepcopy(self.test_restrictions)
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"

        val = PropertyRestrictions(restrictions=restrictions)
        g1, modified = self.create_shacl_restriction(context, val)

        for key, newval in self.test_restrictions2.items():
            val[key] = newval

        querystr = context.sparql_context
        querystr += val.update_shacl(graph=Xsd_NCName('test'), prop_iri=Xsd_QName('test:test'), modified=modified)
        g1.update(querystr)

        self.check_shacl_expectation(context, self.test_restrictions2, g1)

    def test_restriction_update_onto(self):
        restrictions = deepcopy(self.test_restrictions)
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"

        val = PropertyRestrictions(restrictions=restrictions)
        g1, modified = self.create_onto_restriction(context, val)

        for key, newval in self.test_restrictions2.items():
            val[key] = newval

        querystr = context.sparql_context
        querystr += val.update_owl(graph=Xsd_NCName('test'), prop_iri=Iri('test:test'), modified=modified)
        g1.update(querystr)
        self.check_onto_expectation(context, { Iri("owl:maxCardinality"): Xsd_nonNegativeInteger(10)}, g1)

        restrictions = deepcopy(self.test_restrictions)
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"

        val = PropertyRestrictions(restrictions=restrictions)
        g1, modified = self.create_onto_restriction(context, val)

        val[PropertyRestrictionType.MAX_COUNT] = Xsd_integer(1)
        val[PropertyRestrictionType.MIN_COUNT] = Xsd_integer(1)

        querystr = context.sparql_context
        querystr += val.update_owl(graph=Xsd_NCName('test'), prop_iri=Iri('test:test'), modified=modified)
        g1.update(querystr)
        self.check_onto_expectation(context, { Iri("owl:cardinality"): Xsd_nonNegativeInteger(1)}, g1)

    def test_restriction_clear(self):
        test_restrictions2 = deepcopy(self.test_restrictions)
        r1 = PropertyRestrictions(restrictions=test_restrictions2)
        r1.clear()
        self.assertEqual(len(r1), 0)



if __name__ == '__main__':
    unittest.main()
