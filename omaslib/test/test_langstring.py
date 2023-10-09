import unittest

from omaslib.src.helpers.langstring import LangString, Languages


class TestLangstring(unittest.TestCase):

    def test_langstring_constructor(self):
        ls1 = LangString("english@en")
        self.assertEqual(ls1['en'], 'english')
        ls2 = LangString('nolanguage')
        self.assertEqual(ls2['xx'], 'nolanguage')
        ls3 = LangString(ls1)
        self.assertEqual(ls3['en'], 'english')
        ls4 = LangString({
            'en': 'english',
            'de': 'deutsch',
            'fr': 'français'
        })
        self.assertEqual(ls4['fr'], 'français')
        self.assertEqual(ls4[Languages.FR], 'français')
        self.assertEqual(ls4['de'], 'deutsch')
        self.assertEqual(ls4[Languages.DE], 'deutsch')
        self.assertEqual(ls4['en'], 'english')
        self.assertEqual(ls4['it'], 'english')
        self.assertEqual(ls4['rr'], '--no string--')

