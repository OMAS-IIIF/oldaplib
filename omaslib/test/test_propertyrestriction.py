import unittest

from omaslib.src.helpers.datatypes import QName
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
        shacl = r2.create_shacl()
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


