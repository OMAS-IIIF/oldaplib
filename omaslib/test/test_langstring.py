import unittest

from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasError


class TestLangstring(unittest.TestCase):

    def test_langstring_constructor(self):
        ls1 = LangString("english@en")
        self.assertEqual(ls1['en'], 'english')
        ls2 = LangString('nolanguage')
        self.assertEqual(ls2['xx'], 'nolanguage')
        self.assertEqual(ls2[Language.XX], 'nolanguage')
        ls3 = LangString(ls1)
        self.assertEqual(ls3['en'], 'english')

        ls4 = LangString({
            'en': 'english',
            'de': 'deutsch',
            'fr': 'français',
            'xx': 'no language'
        })
        self.assertEqual(ls4['fr'], 'français')
        self.assertEqual(ls4[Language.FR], 'français')
        self.assertEqual(ls4['de'], 'deutsch')
        self.assertEqual(ls4[Language.DE], 'deutsch')
        self.assertEqual(ls4['en'], 'english')
        self.assertEqual(ls4['yi'], 'no language')
        with self.assertRaises(OmasError) as ex:
            impossible = ls4['rr']
        self.assertEqual(ex.exception.message, 'Language "rr" is invalid')

        ls5 = LangString(['english@en', 'deutsch@de', 'français@fr', 'no language'])
        self.assertEqual(ls5['fr'], 'français')
        self.assertEqual(ls5[Language.FR], 'français')
        self.assertEqual(ls5['de'], 'deutsch')
        self.assertEqual(ls5[Language.DE], 'deutsch')
        self.assertEqual(ls5['en'], 'english')
        self.assertEqual(ls5['yi'], 'no language')
        with self.assertRaises(OmasError) as ex:
            impossible = ls5['rr']
        self.assertEqual(ex.exception.message, 'Language "rr" is invalid')

        ls6 = LangString({
            Language.EN: 'english',
            Language.DE: 'deutsch',
            Language.FR: 'français',
            Language.XX: 'no language'
        })
        self.assertEqual(ls6['fr'], 'français')
        self.assertEqual(ls6[Language.FR], 'français')
        self.assertEqual(ls6['de'], 'deutsch')
        self.assertEqual(ls6[Language.DE], 'deutsch')
        self.assertEqual(ls6['en'], 'english')
        self.assertEqual(ls6['yi'], 'no language')
        with self.assertRaises(OmasError) as ex:
            impossible = ls6['rr']
        self.assertEqual(ex.exception.message, 'Language "rr" is invalid')

        ls7 = LangString("xyz@ur")
        self.assertEqual(ls7[Language.YI], '--no string--')

    def test_langstring_setitem(self):
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        ls1['fr'] = 'français'
        self.assertEqual(ls1[Language.FR], 'français')

        ls2 = LangString("english@en", "deutsch@de")
        ls2[Language.FR] = 'français'
        self.assertEqual(ls2[Language.FR], 'français')

        ls3 = LangString("english@en", "deutsch@de")
        with self.assertRaises(OmasError) as ex:
            ls3['rr'] = 'no way'
        self.assertEqual(ex.exception.message, 'Language "rr" is invalid')

    def test_langstring_delete(self):
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        del ls1['de']
        self.assertEqual(ls1['en'], 'english')
        self.assertEqual(ls1['xx'], 'unbekannt')
        self.assertEqual(ls1['de'], 'unbekannt')

        ls2 = LangString(["english@en", "deutsch@de", "unbekannt"])
        with self.assertRaises(OmasError) as ex:
            del ls2['it']
        self.assertEqual(ex.exception.message, 'No language string of language: "it"!')

        ls3 = LangString(["english@en", "deutsch@de", "unbekannt"])
        with self.assertRaises(OmasError) as ex:
            del ls2['rr']
        self.assertEqual(ex.exception.message, 'No language string of language: "rr"!')

    def test_langstring_str(self):
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        self.assertEqual(str(ls1),  '"english"@en, "deutsch"@de, "unbekannt"@xx')

    def test_langstring_eq(self):
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        ls2 = LangString(["english@en", "deutsch@de", "unbekannt"])
        self.assertTrue(ls1 == ls2)
        ls3 = LangString(["english@en", "français", "unbekannt"])
        self.assertFalse(ls1 == ls3)
        ls4 = LangString(["english@en", "unbekannt"])
        self.assertFalse(ls1 == ls4)
        ls5 = LangString(["english@en", "deutsch@de", "français@fr", "unbekannt"])
        self.assertFalse(ls1 == ls5)

    def test_langstring_items(self):
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        expected = {
            'English': 'english',
            'German': 'deutsch',
            'Undefined': 'unbekannt'
        }
        res = {}
        for lang, value in ls1.items():
            res[lang.value] = value
        self.assertDictEqual(res, expected)

    def test_langstring_langstring(self):
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        expected = {
            Language.EN: 'english',
            Language.DE: 'deutsch',
            Language.XX: 'unbekannt'
        }
        self.assertDictEqual(ls1.langstring, expected)

    def test_langstring_add(self):
        ls1 = LangString(["english@en", "deutsch@de"])
        ls1.add("français@fr")
        self.assertEqual(str(ls1), '"english"@en, "deutsch"@de, "français"@fr')

        ls2 = LangString(["english@en", "deutsch@de"])
        ls1.add(["français@fr", "undefined"])
        self.assertEqual(str(ls1), '"english"@en, "deutsch"@de, "français"@fr, "undefined@xx')




