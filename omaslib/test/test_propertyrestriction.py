import unittest
from typing import Dict

from omaslib.src.helpers.datatypes import QName, Action
from omaslib.src.helpers.language import Language
from omaslib.src.propertyrestriction import PropertyRestrictions, PropertyRestrictionType


class TestPropertyRestriction(unittest.TestCase):

    def test_restriction_constructor(self):
        r1 = PropertyRestrictions()
        r2 = PropertyRestrictions(
            language_in={Language.EN, Language.DE, Language.FR, Language.IT},
            unique_lang=True,
            min_count=1,
            max_count=4,
            min_length=8,
            max_length=64,
            min_exclusive=6.5,
            min_inclusive=8,
            max_exclusive=6.5,
            max_inclusive=8,
            pattern='.*',
            less_than=QName('test:greater'),
            less_than_or_equals=QName('test:gaga')
        )
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
        r1 = PropertyRestrictions(
            language_in={Language.EN, Language.DE, Language.FR, Language.IT},
            unique_lang=True,
            min_count=1,
            max_count=4,
            min_length=8,
            max_length=64,
            min_exclusive=6.5,
            min_inclusive=8,
            max_exclusive=20,
            max_inclusive=21,
            pattern='.*',
            less_than=QName('test:greater'),
            less_than_or_equals=QName('test:gaga')
        )
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
        r1[PropertyRestrictionType.LESS_THAN] = 'gaga:gaga'
        r1[PropertyRestrictionType.LESS_THAN_OR_EQUALS] = 'gugus:gugus'
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

    def test_restriction_shacl(self):
        r1 = PropertyRestrictions(
            language_in={Language.EN, Language.DE, Language.FR, Language.IT},
            unique_lang=True,
            min_count=1,
            max_count=4,
            min_length=8,
            max_length=64,
            min_exclusive=6.5,
            min_inclusive=8,
            max_exclusive=6.5,
            max_inclusive=8,
            pattern='.*',
            less_than=QName('test:greater'),
            less_than_or_equals=QName('test:gaga')
        )
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
            PropertyRestrictionType.LESS_THAN.value: {'value': 'test:greater', 'done': False},
            PropertyRestrictionType.LESS_THAN_OR_EQUALS.value: {'value': 'test:gaga', 'done': False},
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

        r1 = PropertyRestrictions(
            language_in={Language.EN, Language.DE, Language.FR, Language.IT},
            unique_lang=True,
            min_count=1,
            max_count=4,
            min_length=8,
            max_length=64,
            min_exclusive=6.5,
            min_inclusive=8,
            max_exclusive=6.5,
            max_inclusive=8,
            pattern='.*',
            less_than=QName('test:greater'),
            less_than_or_equals=QName('test:gaga')
        )
        owl = r1.create_owl()
        check(owl, {'owl:minCardinality': '1', 'owl:maxCardinality': '4'})

        r2 = PropertyRestrictions(
            language_in={Language.EN, Language.DE, Language.FR, Language.IT},
            unique_lang=True,
            min_count=1,
            max_count=1,
            min_length=8,
            max_length=64,
            min_exclusive=6.5,
            min_inclusive=8,
            max_exclusive=6.5,
            max_inclusive=8,
            pattern='.*',
            less_than=QName('test:greater'),
            less_than_or_equals=QName('test:gaga')
        )
        owl = r2.create_owl()
        check(owl, {'owl:cardinality': '1'})

