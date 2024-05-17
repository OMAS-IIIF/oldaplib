import unittest

from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapErrorType, OldapErrorKey


class TestLanguageIn(unittest.TestCase):

    def test_empty_constructor(self):
        lang = LanguageIn()
        self.assertIsInstance(lang, LanguageIn)
        self.assertEqual(len(lang), 0)

    def test_simple_constructor(self):
        lang = LanguageIn(Language.DE)
        self.assertIsInstance(lang, LanguageIn)
        self.assertEqual(len(lang), 1)
        self.assertTrue(Language.DE in lang)

        lang = LanguageIn(value=Language.DE)
        self.assertIsInstance(lang, LanguageIn)
        self.assertEqual(len(lang), 1)
        self.assertTrue(Language.DE in lang)


        lang = LanguageIn("de")
        self.assertIsInstance(lang, LanguageIn)
        self.assertEqual(len(lang), 1)
        self.assertTrue(Language.DE in lang)

        lang = LanguageIn(value="de")
        self.assertIsInstance(lang, LanguageIn)
        self.assertEqual(len(lang), 1)
        self.assertTrue(Language.DE in lang)


        lang2 = LanguageIn(lang)
        self.assertIsInstance(lang, LanguageIn)
        self.assertEqual(len(lang), 1)
        self.assertTrue(Language.DE in lang)

        lang2 = LanguageIn(value=lang)
        self.assertIsInstance(lang, LanguageIn)
        self.assertEqual(len(lang), 1)
        self.assertTrue(Language.DE in lang)


        with self.assertRaises(OldapErrorKey):
            lang = LanguageIn("xxx")

        with self.assertRaises(OldapErrorKey):
            lang = LanguageIn(value="xxx")


    def test_constructor_A(self):
        lang = LanguageIn(Language.DE, Language.EN, Language.FR)
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)

        lang = LanguageIn({Language.DE, Language.EN, Language.FR})
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)

        lang = LanguageIn(value={Language.DE, Language.EN, Language.FR})
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)

        t = (Language.DE, Language.EN, "fr")
        lang = LanguageIn(t)
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)

        lang = LanguageIn(value=t)
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)

        lang = LanguageIn([Language.DE, Language.EN, Language.FR])
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)

        lang = LanguageIn(value=[Language.DE, Language.EN, Language.FR])
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)


    def test_constructor_B(self):
        lang = LanguageIn("de", "en", Language.FR)
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)

        lang = LanguageIn(["de", "en", Language.FR])
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)

        lang = LanguageIn(value=["de", "en", Language.FR])
        self.assertEqual(len(lang), 3)
        self.assertTrue(Language.DE in lang)
        self.assertTrue(Language.EN in lang)
        self.assertTrue(Language.FR in lang)
        self.assertFalse(Language.RM in lang)


        with self.assertRaises(OldapErrorKey):
            lang = LanguageIn(["de", "en", "gaga", "it"])
        with self.assertRaises(OldapErrorKey):
            lang = LanguageIn(value=["de", "en", "gaga", "it"])


    def test_compare_ops(self):
        lang1 = LanguageIn(["de", "en", Language.FR])
        lang2 = LanguageIn("de", "en", Language.FR)
        self.assertTrue(lang1 == lang2)
        self.assertTrue(lang1 == {Language.DE, Language.EN, Language.FR})

        self.assertTrue(lang1 >= lang2)
        self.assertTrue(lang1 >= {Language.DE, Language.EN})

        self.assertTrue(lang1 <= lang2)
        self.assertFalse(lang1 <= {Language.DE, Language.EN})

        lang1 = LanguageIn(["de", "en", Language.FR])
        lang2 = LanguageIn("de", "en")
        self.assertTrue(lang1 > lang2)
        self.assertTrue(lang1 > {Language.DE, Language.EN})
        self.assertTrue(lang2 < lang1)
        self.assertFalse(lang2 < {Language.DE, Language.EN})
        self.assertTrue(lang1 != lang2)
        self.assertTrue(lang1 != {Language.DE, Language.EN})

    def test_conversions(self):
        li = LanguageIn({"en", "fr", "it"})
        s = str(li)
        s = s.strip('() ')
        s = s.split(', ')
        self.assertTrue("Language.EN" in s)
        self.assertTrue("Language.FR" in s)
        self.assertTrue("Language.IT" in s)

        s = repr(li)
        s = s.removeprefix('LanguageIn(')
        s = s.strip('()')
        s = s.split(', ')
        self.assertTrue("Language.EN" in s)
        self.assertTrue("Language.FR" in s)
        self.assertTrue("Language.IT" in s)

        s = li.toRdf
        s = s.strip('()')
        s = s.split(' ')
        self.assertTrue('"fr"^^xsd:string' in s)
        self.assertTrue('"en"^^xsd:string' in s)
        self.assertTrue('"it"^^xsd:string' in s)

        li = LanguageIn([Language.EN, "fr", "it"])

        li.add("el")
        self.assertTrue(Language.EL in li)

        li.add(Language.AB)
        self.assertTrue(Language.AB in li)

        li.discard("en")
        self.assertFalse(Language.EN in li)

        li.discard(Language.FR)
        self.assertFalse(Language.FR in li)

        with self.assertRaises(OldapErrorKey) as ex:
            li = li.add("xyz")


    def test_language_in(self):
        li = LanguageIn({"en", "fr", "it"})
        self.assertTrue(Language.EN in li)
        self.assertTrue(Language.FR in li)
        self.assertTrue(Language.IT in li)
        self.assertFalse(Language.DE in li)
        s = str(li)
        s = s.strip('() ')
        s = s.split(', ')
        self.assertTrue("Language.EN" in s)
        self.assertTrue("Language.FR" in s)
        self.assertTrue("Language.IT" in s)
        s = repr(li)
        s = s.removeprefix('LanguageIn(')
        s = s.strip('()')
        s = s.split(', ')
        self.assertTrue('Language.FR' in s)
        self.assertTrue('Language.EN' in s)
        self.assertTrue('Language.IT' in s)

        s = li.toRdf
        s = s.strip('()')
        s = s.split(' ')
        self.assertTrue('"fr"^^xsd:string' in s)
        self.assertTrue('"en"^^xsd:string' in s)
        self.assertTrue('"it"^^xsd:string' in s)

        li = LanguageIn("en", "fr", "it")
        self.assertTrue(Language.EN in li)
        self.assertTrue(Language.FR in li)
        self.assertTrue(Language.IT in li)
        self.assertFalse(Language.DE in li)

        li = LanguageIn(Language.EN, "fr", Language.IT)
        self.assertTrue(Language.EN in li)
        self.assertTrue(Language.FR in li)
        self.assertTrue(Language.IT in li)
        self.assertFalse(Language.DE in li)

        li = LanguageIn([Language.EN, "fr", "it"])
        self.assertTrue(Language.EN in li)
        self.assertTrue(Language.FR in li)
        self.assertTrue(Language.IT in li)
        self.assertFalse(Language.DE in li)

        li.add("el")
        self.assertTrue(Language.EL in li)

        li.add(Language.AB)
        self.assertTrue(Language.AB in li)

        li.discard("en")
        self.assertFalse(Language.EN in li)

        li.discard(Language.FR)
        self.assertFalse(Language.FR in li)

        with self.assertRaises(OldapErrorKey) as ex:
            li = LanguageIn([Language.EN, "fr", "xyz"])


if __name__ == '__main__':
    unittest.main()
