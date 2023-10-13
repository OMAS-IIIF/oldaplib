import unittest
from pprint import pprint
from typing import Dict
from copy import deepcopy

from omaslib.src.helpers.datatypes import QName, Action
from omaslib.src.helpers.language import Language
from omaslib.src.propertyrestriction import PropertyRestrictions, PropertyRestrictionType

class TestPropertyRestriction(unittest.TestCase):

    test_restrictions = {
            PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT},
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
        self.assertEqual(len(r2), 13)
        self.assertEqual(r2[PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})
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
        r1 = PropertyRestrictions(restrictions=test2_restriction)
        r1[PropertyRestrictionType.LANGUAGE_IN] = {Language.EN, Language.DE}
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
        exp1a = {
            (PropertyRestrictionType.LANGUAGE_IN, Action.REPLACE),
            (PropertyRestrictionType.UNIQUE_LANG, Action.REPLACE),
            (PropertyRestrictionType.MIN_COUNT, Action.REPLACE),
            (PropertyRestrictionType.MAX_COUNT, Action.REPLACE),
            (PropertyRestrictionType.MIN_LENGTH, Action.REPLACE),
            (PropertyRestrictionType.MAX_LENGTH, Action.REPLACE),
            (PropertyRestrictionType.MIN_INCLUSIVE, Action.REPLACE),
            (PropertyRestrictionType.MIN_EXCLUSIVE, Action.REPLACE),
            (PropertyRestrictionType.MAX_INCLUSIVE, Action.REPLACE),
            (PropertyRestrictionType.MAX_EXCLUSIVE, Action.REPLACE),
            (PropertyRestrictionType.PATTERN, Action.REPLACE),
            (PropertyRestrictionType.LESS_THAN, Action.REPLACE),
            (PropertyRestrictionType.LESS_THAN_OR_EQUALS, Action.REPLACE),
        }
        exp1b = {
            PropertyRestrictionType.LANGUAGE_IN,
            PropertyRestrictionType.UNIQUE_LANG,
            PropertyRestrictionType.MIN_COUNT,
            PropertyRestrictionType.MAX_COUNT,
            PropertyRestrictionType.MIN_LENGTH,
            PropertyRestrictionType.MAX_LENGTH,
            PropertyRestrictionType.MIN_INCLUSIVE,
            PropertyRestrictionType.MIN_EXCLUSIVE,
            PropertyRestrictionType.MAX_INCLUSIVE,
            PropertyRestrictionType.MAX_EXCLUSIVE,
            PropertyRestrictionType.PATTERN,
            PropertyRestrictionType.LESS_THAN,
            PropertyRestrictionType.LESS_THAN_OR_EQUALS
        }
        self.assertEqual(r1.changeset, exp1a)
        self.assertEqual(r1.test_in_use, exp1b)

    def test_restriction_delete(self):
        test2_restrictions = deepcopy(TestPropertyRestriction.test_restrictions)
        r1 = PropertyRestrictions(restrictions=test2_restrictions)
        del r1[PropertyRestrictionType.MAX_LENGTH]
        self.assertIsNone(r1.get(PropertyRestrictionType.MAX_LENGTH))
        self.assertEqual(r1.changeset, {(PropertyRestrictionType.MAX_LENGTH, Action.DELETE)})

    def test_restriction_clear(self):
        test2_restrictions = deepcopy(TestPropertyRestriction.test_restrictions)
        r1 = PropertyRestrictions(restrictions=test2_restrictions)
        r1.clear()
        self.assertEqual(len(r1), 0)

    def test_restriction_shacl(self):
        r1 = PropertyRestrictions(restrictions=TestPropertyRestriction.test_restrictions)
        shacl = r1.create_shacl()
        tmplist = shacl.split(" ;")
        tmplist = [x.strip() for x in tmplist]
        expected = {
            PropertyRestrictionType.UNIQUE_LANG.value: {'value': 'true', 'done': False},
            PropertyRestrictionType.MIN_COUNT.value: {'value': '1', 'done': False},
            PropertyRestrictionType.MAX_COUNT.value: {'value': '4', 'done': False},
            PropertyRestrictionType.MIN_LENGTH.value: {'value': '8', 'done': False},
            PropertyRestrictionType.MAX_LENGTH.value: {'value': '64', 'done': False},
            PropertyRestrictionType.PATTERN.value: {'value': '.*', 'done': False},
            PropertyRestrictionType.MIN_EXCLUSIVE.value: {'value': '6.5', 'done': False},
            PropertyRestrictionType.MIN_INCLUSIVE.value: {'value': '8', 'done': False},
            PropertyRestrictionType.MAX_EXCLUSIVE.value: {'value': '6.5', 'done': False},
            PropertyRestrictionType.MAX_INCLUSIVE.value: {'value': '8', 'done': False},
            PropertyRestrictionType.LESS_THAN.value: {'value': QName('test:greater'), 'done': False},
            PropertyRestrictionType.LESS_THAN_OR_EQUALS.value: {'value': QName('test:gaga'), 'done': False},
        }
        for ele in tmplist:
            if not ele:
                continue
            if ele.startswith('sh:languageIn'):
                langs = ele[14:]
                langs = langs.strip("()")
                langslist = langs.split(" ")
                langsset = set(langslist)
                self.assertEqual(langsset, {'"fr"', '"en"', '"de"', '"it"'})
            else:
                name, value = ele.split(" ")
                if expected[name]['value'] == value:
                    expected[name]['done'] = True
        for x, y in expected.items():
            self.assertTrue(y['done'])

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

