from dataclasses import dataclass
import unittest
from datetime import datetime
from pprint import pprint
from typing import Dict, Tuple, Union
from copy import deepcopy
from rdflib import Graph, Namespace, ConjunctiveGraph
from rdflib.namespace import NamespaceManager

from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, Action, NCName
from omaslib.src.helpers.language import Language
from omaslib.src.propertyrestrictions import PropertyRestrictions, PropertyRestrictionType, PropertyRestrictionChange

@dataclass
class ExpectationValue:
    value: [bool, int, float, str, QName, set]
    done: bool


TurtleExpectation = Dict[PropertyRestrictionType, ExpectationValue]


def check_turtle_expectation(turtle: str, expectation: TurtleExpectation, cl: unittest.TestCase) -> None:
    tmplist = turtle.split(" ;")
    tmplist = [x.strip() for x in tmplist]
    for ele in tmplist:
        if not ele:
            continue
        name, value = ele.split(" ", maxsplit=1)
        try:
            ptype = PropertyRestrictionType(name)
        except ValueError:
            continue
        if ptype == PropertyRestrictionType.LANGUAGE_IN:
            langs = value.strip("( )")
            langslist = langs.split(" ")
            langslist = [Language[x.strip('"').upper()] for x in langslist]
            langsset = set(langslist)
            if langsset >= expectation[ptype].value and langsset <= expectation[ptype].value:
                expectation[ptype].done = True
        elif ptype == PropertyRestrictionType.IN:
            items = value.strip("( )")
            itemlist = items.split(" ")
            itemlist = [x.strip('"') for x in itemlist]
            itemset = set(itemlist)
            if itemset >= expectation[ptype].value and itemset <= expectation[ptype].value:
                expectation[ptype].done = True

        else:
            value = value.strip(" .")
            tvalue: Union[bool, int, float, str, QName, None] = None
            if bool in PropertyRestrictions.datatypes[ptype] and tvalue is None:
                tvalue = True if value == 'true' else False
            if int in PropertyRestrictions.datatypes[ptype] and tvalue is None:
                try:
                    tvalue = int(value)
                except ValueError:
                    tvalue = None
            if float in PropertyRestrictions.datatypes[ptype] and tvalue is None:
                tvalue = float(value)
            if str in PropertyRestrictions.datatypes[ptype] and tvalue is None:
                tvalue = value.strip('"')
            if QName in PropertyRestrictions.datatypes[ptype] and tvalue is None:
                tvalue = QName(value)
            if tvalue is None:
                tvalue = value
            if expectation[ptype].value == tvalue:
                expectation[ptype].done = True
    for x, y in expectation.items():
        cl.assertTrue(y.done, f'Restriction: {x.value}, expected value: {y.value}')


class TestPropertyRestriction(unittest.TestCase):
    test_restrictions = {
        PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
        PropertyRestrictionType.IN: {'A', 'B', 'C'},
        PropertyRestrictionType.UNIQUE_LANG: True,
        PropertyRestrictionType.MIN_COUNT: 1,
        PropertyRestrictionType.MAX_COUNT: 4,
        PropertyRestrictionType.MIN_LENGTH: 8,
        PropertyRestrictionType.MAX_LENGTH: 64,
        PropertyRestrictionType.MIN_EXCLUSIVE: 6.5,
        PropertyRestrictionType.MIN_INCLUSIVE: 8,
        PropertyRestrictionType.MAX_EXCLUSIVE: 6.5,
        PropertyRestrictionType.MAX_INCLUSIVE: 8,
        PropertyRestrictionType.PATTERN: '.*',
        PropertyRestrictionType.LESS_THAN: QName('test:greater'),
        PropertyRestrictionType.LESS_THAN_OR_EQUALS: QName('test:gaga')
    }

    def test_restriction_constructor(self):
        r1 = PropertyRestrictions()
        r2 = PropertyRestrictions(restrictions=TestPropertyRestriction.test_restrictions)
        self.assertEqual(len(r2), 14)
        self.assertEqual(r2[PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(r2[PropertyRestrictionType.IN], {'A', 'B', 'C'})
        self.assertTrue(r2[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(r2[PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(r2[PropertyRestrictionType.MAX_COUNT], 4)
        self.assertEqual(r2[PropertyRestrictionType.MIN_LENGTH], 8)
        self.assertEqual(r2[PropertyRestrictionType.MAX_LENGTH], 64)
        self.assertEqual(r2[PropertyRestrictionType.PATTERN], '.*')
        self.assertEqual(r2[PropertyRestrictionType.MIN_EXCLUSIVE], 6.5)
        self.assertEqual(r2[PropertyRestrictionType.MIN_INCLUSIVE], 8)
        self.assertEqual(r2[PropertyRestrictionType.MAX_EXCLUSIVE], 6.5)
        self.assertEqual(r2[PropertyRestrictionType.MAX_INCLUSIVE], 8)
        self.assertEqual(r2[PropertyRestrictionType.LESS_THAN], QName('test:greater'))
        self.assertEqual(r2[PropertyRestrictionType.LESS_THAN_OR_EQUALS], QName('test:gaga'))
        s = str(r2)

    def test_restriction_setitem(self):
        test2_restriction = deepcopy(TestPropertyRestriction.test_restrictions)
        test2_restriction[PropertyRestrictionType.MAX_EXCLUSIVE] = 20
        test2_restriction[PropertyRestrictionType.MAX_INCLUSIVE] = 21
        test3_restriction = deepcopy(test2_restriction)
        r1 = PropertyRestrictions(restrictions=test2_restriction)
        r1[PropertyRestrictionType.LANGUAGE_IN] = {Language.EN, Language.DE}
        r1[PropertyRestrictionType.IN] = {'X', 'Y'}
        r1[PropertyRestrictionType.UNIQUE_LANG] = False
        r1[PropertyRestrictionType.MIN_COUNT] = 2
        r1[PropertyRestrictionType.MAX_COUNT] = 2
        r1[PropertyRestrictionType.MIN_LENGTH] = 16
        r1[PropertyRestrictionType.MAX_LENGTH] = 48
        r1[PropertyRestrictionType.MIN_INCLUSIVE] = 10.2
        r1[PropertyRestrictionType.MIN_EXCLUSIVE] = 10.2
        r1[PropertyRestrictionType.MAX_INCLUSIVE] = 16
        r1[PropertyRestrictionType.MAX_EXCLUSIVE] = 18
        r1[PropertyRestrictionType.PATTERN] = '[a..zA..Z]'
        r1[PropertyRestrictionType.LESS_THAN] = QName('gaga:gaga')
        r1[PropertyRestrictionType.LESS_THAN_OR_EQUALS] = QName('gugus:gugus')
        expected: Dict[PropertyRestrictionType, PropertyRestrictionChange] = {
            PropertyRestrictionType.LANGUAGE_IN:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.LANGUAGE_IN], Action.REPLACE, True),
            PropertyRestrictionType.IN:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.IN], Action.REPLACE, True),
            PropertyRestrictionType.UNIQUE_LANG:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.UNIQUE_LANG], Action.REPLACE, False),
            PropertyRestrictionType.MIN_COUNT:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.MIN_COUNT], Action.REPLACE, True),
            PropertyRestrictionType.MAX_COUNT:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.MAX_COUNT], Action.REPLACE, True),
            PropertyRestrictionType.MIN_LENGTH:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.MIN_LENGTH], Action.REPLACE, True),
            PropertyRestrictionType.MAX_LENGTH:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.MAX_LENGTH], Action.REPLACE, True),
            PropertyRestrictionType.MIN_INCLUSIVE:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.MIN_INCLUSIVE], Action.REPLACE, True),
            PropertyRestrictionType.MIN_EXCLUSIVE:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.MIN_EXCLUSIVE], Action.REPLACE, True),
            PropertyRestrictionType.MAX_INCLUSIVE:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.MAX_INCLUSIVE], Action.REPLACE, True),
            PropertyRestrictionType.MAX_EXCLUSIVE:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.MAX_EXCLUSIVE], Action.REPLACE, True),
            PropertyRestrictionType.PATTERN:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.PATTERN], Action.REPLACE, True),
            PropertyRestrictionType.LESS_THAN:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.LESS_THAN], Action.REPLACE, True),
            PropertyRestrictionType.LESS_THAN_OR_EQUALS:
                PropertyRestrictionChange(test3_restriction[PropertyRestrictionType.LESS_THAN_OR_EQUALS], Action.REPLACE, True)
        }
        self.maxDiff = None
        self.assertEqual(r1.changeset, expected)

    def test_restriction_undo(self):
        undo_restrictions = deepcopy(TestPropertyRestriction.test_restrictions)
        r1 = PropertyRestrictions(restrictions=undo_restrictions)
        r1[PropertyRestrictionType.LANGUAGE_IN] = {Language.EN, Language.DE}
        r1[PropertyRestrictionType.IN] = {'X', 'Y'}
        r1[PropertyRestrictionType.UNIQUE_LANG] = False
        r1[PropertyRestrictionType.MIN_COUNT] = 3
        r1[PropertyRestrictionType.MAX_COUNT] = 10
        r1[PropertyRestrictionType.MIN_LENGTH] = 3
        r1[PropertyRestrictionType.MAX_LENGTH] = 100
        r1[PropertyRestrictionType.PATTERN] = '[a-zA-Z0-9]*'
        r1[PropertyRestrictionType.MIN_EXCLUSIVE] = 20
        r1[PropertyRestrictionType.MIN_INCLUSIVE] = 20
        r1[PropertyRestrictionType.MAX_EXCLUSIVE] = 25
        r1[PropertyRestrictionType.MAX_INCLUSIVE] = 25
        r1[PropertyRestrictionType.LESS_THAN] = QName('test:waseliwas')
        r1[PropertyRestrictionType.LESS_THAN_OR_EQUALS] = QName('test:soso')
        self.assertEqual(r1[PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE})
        self.assertEqual(r1[PropertyRestrictionType.IN], {'X', 'Y'})
        self.assertFalse(r1[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(r1[PropertyRestrictionType.MIN_COUNT], 3)
        self.assertEqual(r1[PropertyRestrictionType.MAX_COUNT], 10)
        self.assertEqual(r1[PropertyRestrictionType.MIN_LENGTH], 3)
        self.assertEqual(r1[PropertyRestrictionType.MAX_LENGTH], 100)
        self.assertEqual(r1[PropertyRestrictionType.PATTERN], '[a-zA-Z0-9]*')
        self.assertEqual(r1[PropertyRestrictionType.MIN_EXCLUSIVE], 20)
        self.assertEqual(r1[PropertyRestrictionType.MIN_INCLUSIVE], 20)
        self.assertEqual(r1[PropertyRestrictionType.MAX_EXCLUSIVE], 25)
        self.assertEqual(r1[PropertyRestrictionType.MAX_INCLUSIVE], 25)
        self.assertEqual(r1[PropertyRestrictionType.LESS_THAN], QName('test:waseliwas'))
        self.assertEqual(r1[PropertyRestrictionType.LESS_THAN_OR_EQUALS], QName('test:soso'))

        r1.undo(PropertyRestrictionType.LANGUAGE_IN)
        r1.undo(PropertyRestrictionType.IN)
        r1.undo(PropertyRestrictionType.UNIQUE_LANG)
        r1.undo(PropertyRestrictionType.MIN_COUNT)
        r1.undo(PropertyRestrictionType.MAX_COUNT)
        r1.undo(PropertyRestrictionType.MIN_LENGTH)
        r1.undo(PropertyRestrictionType.MAX_LENGTH)
        r1.undo(PropertyRestrictionType.PATTERN)
        r1.undo(PropertyRestrictionType.MIN_EXCLUSIVE)
        r1.undo(PropertyRestrictionType.MIN_INCLUSIVE)
        r1.undo(PropertyRestrictionType.MAX_EXCLUSIVE)
        r1.undo(PropertyRestrictionType.MAX_INCLUSIVE)
        r1.undo(PropertyRestrictionType.LESS_THAN)
        r1.undo(PropertyRestrictionType.LESS_THAN_OR_EQUALS)

        self.assertEqual(len(r1), 14)
        self.assertEqual(r1[PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertEqual(r1[PropertyRestrictionType.IN], {'A', 'B', 'C'})
        self.assertTrue(r1[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(r1[PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(r1[PropertyRestrictionType.MAX_COUNT], 4)
        self.assertEqual(r1[PropertyRestrictionType.MIN_LENGTH], 8)
        self.assertEqual(r1[PropertyRestrictionType.MAX_LENGTH], 64)
        self.assertEqual(r1[PropertyRestrictionType.PATTERN], '.*')
        self.assertEqual(r1[PropertyRestrictionType.MIN_EXCLUSIVE], 6.5)
        self.assertEqual(r1[PropertyRestrictionType.MIN_INCLUSIVE], 8)
        self.assertEqual(r1[PropertyRestrictionType.MAX_EXCLUSIVE], 6.5)
        self.assertEqual(r1[PropertyRestrictionType.MAX_INCLUSIVE], 8)
        self.assertEqual(r1[PropertyRestrictionType.LESS_THAN], QName('test:greater'))
        self.assertEqual(r1[PropertyRestrictionType.LESS_THAN_OR_EQUALS], QName('test:gaga'))

    def test_restriction_update_shacl(self):
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"

        test2_restrictions = deepcopy(TestPropertyRestriction.test_restrictions)
        r1 = PropertyRestrictions(restrictions=test2_restrictions)

        #
        # put a dummy property shape into a rdflib triple store
        #
        modified = datetime.now()
        data = context.sparql_context
        data += f'''test:shacl {{
          test:testShape a sh:PropertyShape ;
            sh:path test:test{r1.create_shacl(indent=2, indent_inc=2)} ;
            dcterms:creator <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:created "{modified.isoformat()}"^^xsd:dateTime ;
            dcterms:contributor <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:modified "{modified.isoformat()}"^^xsd:dateTime ;
        }} 
        '''
        g1 = ConjunctiveGraph()
        g1.parse(data=data, format='trig')

        #
        # now modify PropertyRestrictioninstance and test the modifications in the instance
        #
        del r1[PropertyRestrictionType.MAX_LENGTH]
        r1[PropertyRestrictionType.LESS_THAN] = QName('test:mustbemore')
        r1[PropertyRestrictionType.LANGUAGE_IN] = {Language.EN, Language.DE, Language.FR, Language.IT, Language.ES}
        r1[PropertyRestrictionType.IN] = {'X', 'Y'}
        self.assertIsNone(r1.get(PropertyRestrictionType.MAX_LENGTH))
        expected: Dict[PropertyRestrictionType, PropertyRestrictionChange] = {
            PropertyRestrictionType.MAX_LENGTH:
                PropertyRestrictionChange(TestPropertyRestriction.test_restrictions[PropertyRestrictionType.MAX_LENGTH], Action.DELETE, False),
            PropertyRestrictionType.LESS_THAN:
                PropertyRestrictionChange(TestPropertyRestriction.test_restrictions[PropertyRestrictionType.LESS_THAN], Action.REPLACE, True),
            PropertyRestrictionType.LANGUAGE_IN:
                PropertyRestrictionChange(TestPropertyRestriction.test_restrictions[PropertyRestrictionType.LANGUAGE_IN], Action.REPLACE, False),
            PropertyRestrictionType.IN:
                PropertyRestrictionChange(TestPropertyRestriction.test_restrictions[PropertyRestrictionType.IN], Action.REPLACE, True),
        }
        self.maxDiff = None
        self.assertEqual(r1.changeset, expected)

        #
        # now apply the update to the rdflib triple store
        #
        querystr = context.sparql_context
        querystr += r1.update_shacl(graph=NCName('test'), prop_iri=QName('test:test'), modified=modified)
        g1.update(querystr)
        expected: TurtleExpectation = {
            PropertyRestrictionType.UNIQUE_LANG: ExpectationValue(True, False),
            PropertyRestrictionType.LANGUAGE_IN: ExpectationValue({
                Language.FR, Language.EN, Language.DE, Language.IT, Language.ES}, False),
            PropertyRestrictionType.IN: ExpectationValue({'X', 'Y'}, False),
            PropertyRestrictionType.MIN_COUNT: ExpectationValue(1, False),
            PropertyRestrictionType.MAX_COUNT: ExpectationValue(4, False),
            PropertyRestrictionType.MIN_LENGTH: ExpectationValue(8, False),
            PropertyRestrictionType.PATTERN: ExpectationValue(".*", False),
            PropertyRestrictionType.MIN_EXCLUSIVE: ExpectationValue(6.5, False),
            PropertyRestrictionType.MIN_INCLUSIVE: ExpectationValue(8, False),
            PropertyRestrictionType.MAX_EXCLUSIVE: ExpectationValue(6.5, False),
            PropertyRestrictionType.MAX_INCLUSIVE: ExpectationValue(8, False),
            PropertyRestrictionType.LESS_THAN: ExpectationValue(QName('test:mustbemore'), False),
            PropertyRestrictionType.LESS_THAN_OR_EQUALS: ExpectationValue(QName('test:gaga'), False),
        }
        check_turtle_expectation(g1.serialize(format="n3"), expected, self)

    def test_restriction_update_onto(self):
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"

        test2_restrictions = deepcopy(TestPropertyRestriction.test_restrictions)
        r1 = PropertyRestrictions(restrictions=test2_restrictions)

        #
        # put a dummy property shape into a rdflib triple store
        #
        modified = datetime.now()
        data1 = context.sparql_context
        data1 += f'''test:onto {{
          test:test a owl:DatatypeProperty ;
            dcterms:creator <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:created "{modified.isoformat()}"^^xsd:dateTime ;
            dcterms:contributor <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:modified "{modified.isoformat()}"^^xsd:dateTime ;
            owl:minCardinality 1 ;
            owl:maxCardinality 4 ;
        }} 
        '''
        g1 = ConjunctiveGraph()
        g1.parse(data=data1, format='trig')
        #
        # now modify PropertyRestrictioninstance and test the modifications in the instance
        #
        r1[PropertyRestrictionType.MAX_COUNT] = 1
        expected: Dict[PropertyRestrictionType, PropertyRestrictionChange] = {
            PropertyRestrictionType.MAX_COUNT:
                PropertyRestrictionChange(TestPropertyRestriction.test_restrictions[PropertyRestrictionType.MAX_COUNT], Action.REPLACE, True),
        }
        self.assertEqual(r1.changeset, expected)

        querystr = context.sparql_context
        querystr += r1.update_owl(graph=NCName('test'), prop_iri=QName('test:test'), modified=modified)
        g1.update(querystr)
        expected = context.sparql_context
        expected += f'''test:onto {{
          test:test a owl:DatatypeProperty ;
            dcterms:creator <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:created "{modified.isoformat()}"^^xsd:dateTime ;
            dcterms:contributor <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:modified "{modified.isoformat()}"^^xsd:dateTime ;
            owl:cardinality 1 ;
        }} 
        '''
        g2 = ConjunctiveGraph()
        g2.parse(data=expected, format='trig')
        self.assertEqual(set(g1), set(g2))
        r1.changeset_clear()

        r1[PropertyRestrictionType.MIN_COUNT] = 0
        querystr = context.sparql_context
        querystr += r1.update_owl(graph=NCName('test'), prop_iri=QName('test:test'), modified=modified)
        g1.update(querystr)
        expected = context.sparql_context
        expected += f'''test:onto {{
          test:test a owl:DatatypeProperty ;
            dcterms:creator <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:created "{modified.isoformat()}"^^xsd:dateTime ;
            dcterms:contributor <https://orcid.org/0000-0003-1681-4036> ;
            dcterms:modified "{modified.isoformat()}"^^xsd:dateTime ;
            owl:maxCardinality 1 ;
        }} 
        '''
        g2 = ConjunctiveGraph()
        g2.parse(data=expected, format='trig')
        self.assertEqual(set(g1), set(g2))
        r1.changeset_clear()

    def test_restriction_clear(self):
        test2_restrictions = deepcopy(TestPropertyRestriction.test_restrictions)
        r1 = PropertyRestrictions(restrictions=test2_restrictions)
        r1.clear()
        self.assertEqual(len(r1), 0)

    def test_restriction_shacl(self):
        r1 = PropertyRestrictions(restrictions=TestPropertyRestriction.test_restrictions)
        shacl = r1.create_shacl()
        expected: TurtleExpectation = {
            PropertyRestrictionType.UNIQUE_LANG: ExpectationValue(True, False),
            PropertyRestrictionType.LANGUAGE_IN: ExpectationValue({
                Language.FR, Language.EN, Language.DE, Language.IT}, False),
            PropertyRestrictionType.IN: ExpectationValue({'A', 'B', 'C'}, False),
            PropertyRestrictionType.MIN_COUNT: ExpectationValue(1, False),
            PropertyRestrictionType.MAX_COUNT: ExpectationValue(4, False),
            PropertyRestrictionType.MIN_LENGTH: ExpectationValue(8, False),
            PropertyRestrictionType.MAX_LENGTH: ExpectationValue(64, False),
            PropertyRestrictionType.PATTERN: ExpectationValue(".*", False),
            PropertyRestrictionType.MIN_EXCLUSIVE: ExpectationValue(6.5, False),
            PropertyRestrictionType.MIN_INCLUSIVE: ExpectationValue(8, False),
            PropertyRestrictionType.MAX_EXCLUSIVE: ExpectationValue(6.5, False),
            PropertyRestrictionType.MAX_INCLUSIVE: ExpectationValue(8, False),
            PropertyRestrictionType.LESS_THAN: ExpectationValue(QName('test:greater'), False),
            PropertyRestrictionType.LESS_THAN_OR_EQUALS: ExpectationValue(QName('test:gaga'), False),
        }
        check_turtle_expectation(shacl, expected, self)

    def test_restriction_owl(self):

        def check(owl: str, expect: Dict[str, str]):
            owllist = owl.split(';')
            owllist = [x.strip() for x in owllist]
            for ele in owllist:
                if not ele:
                    continue
                qname, value = ele.split(' ')
                self.assertEqual(value, expect[qname])

        r1 = PropertyRestrictions(restrictions=TestPropertyRestriction.test_restrictions)
        owl = r1.create_owl()
        check(owl, {'owl:minCardinality': '1', 'owl:maxCardinality': '4'})

        test2_restrictions = deepcopy(TestPropertyRestriction.test_restrictions)
        test2_restrictions[PropertyRestrictionType.MIN_COUNT] = 1
        test2_restrictions[PropertyRestrictionType.MAX_COUNT] = 1
        r2 = PropertyRestrictions(restrictions=test2_restrictions)
        owl = r2.create_owl()
        check(owl, {'owl:cardinality': '1'})


