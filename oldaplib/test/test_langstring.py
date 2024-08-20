import json
import unittest
from datetime import datetime

from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.action import Action
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.langstring import LangString, LangStringChange
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorValue
from oldaplib.src.xsd.xsd_string import Xsd_string


class TestLangstring(unittest.TestCase):

    def test_simple_things(self):
        ls = LangString()
        self.assertFalse(ls)

        ls = LangString(Xsd_string())
        self.assertFalse(ls)

        ls = LangString("a@en", Xsd_string(), "b@fr")
        self.assertEqual(LangString("a@en", "b@fr"), ls)

        ls = LangString({Language.EN: "aaa", Language.FR: ""})
        self.assertEqual(LangString("aaa@en"), ls)

        ls = LangString({Language.EN: "aaa", Language.FR: Xsd_string()})
        self.assertEqual(LangString("aaa@en"), ls)

        ls = LangString(Xsd_string('hallo', "en"))
        self.assertEqual(LangString("hallo@en"), ls)
        self.assertIsNone(ls.get('zu'))
        self.assertIsNone(ls.get(Language.ZA))

        with self.assertRaises(OldapError):
            ls = LangString(3.1515)

    def test_langstring_constructor(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString("english@en")
        self.assertEqual(ls1['en'], 'english')
        ls2 = LangString('nolanguage')
        self.assertEqual(ls2['zu'], 'nolanguage')
        self.assertEqual(ls2[Language.ZU], 'nolanguage')
        ls3 = LangString(ls1)
        self.assertEqual(ls3['en'], 'english')

        ls4 = LangString({
            'en': 'english',
            'de': 'deutsch',
            'fr': 'français'
        })
        self.assertEqual(ls4['fr'], 'français')
        self.assertEqual(ls4[Language.FR], 'français')
        self.assertEqual(ls4['de'], 'deutsch')
        self.assertEqual(ls4[Language.DE], 'deutsch')
        self.assertEqual(ls4['en'], 'english')
        with self.assertRaises(OldapError) as ex:
            impossible = ls4['rr']
        self.assertEqual(str(ex.exception), 'Language "rr" is invalid')

        ls5 = LangString(['english@en', 'deutsch@de', 'français@fr', 'no language'])
        self.assertEqual(ls5['fr'], 'français')
        self.assertEqual(ls5[Language.FR], 'français')
        self.assertEqual(ls5['de'], 'deutsch')
        self.assertEqual(ls5[Language.DE], 'deutsch')
        self.assertEqual(ls5['en'], 'english')
        self.assertEqual(ls5['yi'], 'english')
        with self.assertRaises(OldapError) as ex:
            impossible = ls5['rr']
        self.assertEqual(str(ex.exception), 'Language "rr" is invalid')

        ls6 = LangString({
            Language.EN: 'english',
            Language.DE: 'deutsch',
            Language.FR: 'français',
        })
        self.assertEqual(ls6['fr'], 'français')
        self.assertEqual(ls6[Language.FR], 'français')
        self.assertEqual(ls6['de'], 'deutsch')
        self.assertEqual(ls6[Language.DE], 'deutsch')
        self.assertEqual(ls6['en'], 'english')
        self.assertEqual(ls6['yi'], 'english')
        with self.assertRaises(OldapError) as ex:
            impossible = ls6['rr']
        self.assertEqual(str(ex.exception), 'Language "rr" is invalid')

        ls7 = LangString("xyz@ur")
        self.assertEqual(ls7[Language.YI], '--no string--')

        ls8 = LangString("lukas.rosenthaler@unibas.ch@en")
        ls8[Language.DE] = 'lukas.rosenthaler@gmail.com'
        self.assertEqual(ls8['en'], 'lukas.rosenthaler@unibas.ch')
        self.assertEqual(ls8['de'], 'lukas.rosenthaler@gmail.com')

        with self.assertRaises(OldapErrorValue) as ex:
            ls9 = LangString(255)

        ls10 = LangString("lukas.rosenthaler@gmail.com")
        self.assertEqual(str(ls10), '"lukas.rosenthaler@gmail.com@zu"')

    def test_langstring_empty(self):
        ls1 = LangString()
        self.assertFalse(ls1)
        self.assertEqual(ls1[Language.EN], '--no string--')

        ls2 = LangString("wasistdas@en", "", "soso@fr")
        self.assertEqual(len(ls2), 2)

        ls3 = LangString("soso@fr", "gaga@fr", "")
        self.assertEqual(len(ls3), 1)
        self.assertEqual(ls3["fr"], "gaga")

        ls4 = LangString()
        self.assertFalse(ls4)

    def test_langstring_setitem(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        ls1['fr'] = 'français'
        self.assertEqual(ls1[Language.FR], 'français')

        ls2 = LangString("english@en", "deutsch@de")
        ls2[Language.FR] = 'français'
        self.assertEqual(ls2[Language.FR], 'français')

        ls3 = LangString("english@en", "deutsch@de")
        with self.assertRaises(OldapError) as ex:
            ls3['rr'] = 'no way'

        with self.assertRaises(OldapError) as ex:
            ls3[42] = 'no way'

    def test_langstring_undo(self):
        LangString.setDefaultLang(Language.ZU)
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        ls1['fr'] = 'français'
        del ls1[Language.DE]
        self.assertIsNone(ls1.get(Language.DE))
        self.assertEqual(ls1[Language.FR], 'français')
        self.assertEqual(ls1[Language.EN], 'english')
        self.assertEqual(ls1[Language.ZU], 'unbekannt')
        ls1.undo()
        self.assertIsNone(ls1.get(Language.FR))
        self.assertEqual(ls1[Language.EN], 'english')
        self.assertEqual(ls1[Language.DE], 'deutsch')
        self.assertEqual(ls1[Language.ZU], 'unbekannt')

    def test_langstring_delete(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        del ls1['de']
        self.assertEqual(ls1.changeset, {Language.DE: LangStringChange("deutsch", Action.DELETE)})
        self.assertEqual(ls1['en'], 'english')
        self.assertEqual(ls1['zu'], 'unbekannt')
        self.assertEqual(ls1['de'], 'english')

        ls2 = LangString(["english@en", "deutsch@de", "unbekannt"])
        with self.assertRaises(OldapError) as ex:
            del ls2['it']
        self.assertEqual(str(ex.exception), 'No language string of language: "it"!')

        ls3 = LangString(["english@en", "deutsch@de", "unbekannt"])
        with self.assertRaises(OldapError) as ex:
            del ls3['rr']
        self.assertEqual(str(ex.exception), 'No language string of language: "rr"!')

        with self.assertRaises(OldapError) as ex:
            del ls3[42]

    def test_langstring_str(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        s = str(ls1)
        s = set(s.split(", "))
        self.assertTrue('"english@en"' in s)
        self.assertTrue('"deutsch@de"' in s)
        self.assertTrue('"unbekannt@zu"' in s)

    def test_langstring_repr(self):
        ls1 = LangString(["english@en"])
        s = repr(ls1)
        self.assertEqual('LangString("english@en")', s)

    def test_langstring_jsonify(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        jsonstr = json.dumps(ls1, default=serializer.encoder_default)
        ls2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(ls1, ls2)


    def test_langstring_eq_ne(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        ls2 = LangString(["english@en", "deutsch@de", "unbekannt"])
        self.assertTrue(ls1 == ls2)
        self.assertFalse(ls1 != ls2)
        ls3 = LangString(["english@en", "français", "unbekannt"])
        self.assertFalse(ls1 == ls3)
        self.assertTrue(ls1 != ls3)
        ls4 = LangString(["english@en", "unbekannt"])
        self.assertFalse(ls1 == ls4)
        self.assertTrue(ls1 != ls4)
        ls5 = LangString(["english@en", "deutsch@de", "français@fr", "unbekannt"])
        self.assertFalse(ls1 == ls5)
        self.assertTrue(ls1 != ls5)

        lsa = LangString('aaaa@en')
        lsb = LangString('aaaa@de')
        self.assertFalse(lsa == lsb)
        self.assertTrue(lsa != lsb)

    def test_langstring_items(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        expected = {
            'English': 'english',
            'German': 'deutsch',
            'Zulu': 'unbekannt'
        }
        res = {}
        for lang, value in ls1.items():
            res[lang.value] = value
        self.assertDictEqual(res, expected)

    def test_langstring_langstring(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de", "unbekannt"])
        expected = {
            Language.EN: 'english',
            Language.DE: 'deutsch',
            Language.ZU: 'unbekannt'
        }
        self.assertDictEqual(ls1.langstring, expected)

    def test_langstring_add(self):
        LangString.defaultLanguage = Language.ZU

        ls0 = LangString(["english@en", "deutsch@de"])
        ls0.add()
        self.assertEqual(LangString(["english@en", "deutsch@de"]), ls0)

        ls1 = LangString(["english@en", "deutsch@de"])
        ls1.add("français@fr")
        self.assertEqual(ls1, LangString("english@en", "deutsch@de", "français@fr"))
        self.assertEqual(ls1.changeset, {Language.FR: LangStringChange(None, Action.CREATE)})

        ls2 = LangString(["english@en", "deutsch@de"])
        ls2.add(["français@fr", "undefined"])
        self.assertEqual(ls2, LangString("english@en", "deutsch@de", "français@fr", "undefined@zu"))
        self.assertEqual(ls2.changeset, {Language.FR: LangStringChange(None, Action.CREATE),
                                         Language.ZU: LangStringChange(None, Action.CREATE)})

        ls3 = LangString(["english@en", "deutsch@de"])
        ls3.add({Language.FR: "français", Language.ZU: "undefined"})
        self.assertEqual(ls3, LangString("english@en", "deutsch@de", "français@fr", "undefined@zu"))
        self.assertEqual(ls2.changeset, {Language.FR: LangStringChange(None, Action.CREATE),
                                         Language.ZU: LangStringChange(None, Action.CREATE)})

        ls4 = LangString(["english@en", "deutsch@de", "französisch@fr"])
        ls4.add({Language.FR: "français", Language.ZU: "undefined"})
        self.assertEqual(ls4, LangString("english@en", "deutsch@de", "français@fr", "undefined@zu"))
        self.assertEqual(ls4.changeset, {Language.FR: LangStringChange("französisch", Action.REPLACE),
                                         Language.ZU: LangStringChange(None, Action.CREATE)})

        ls5 = LangString(["english@en", "deutsch@de"])
        ls5.add("italiano@it", "espagnol@es")
        self.assertEqual(LangString(["english@en", "deutsch@de", "italiano@it", "espagnol@es"]), ls5)

        ls6 = LangString(["english@en", "deutsch@de"])
        ls5.add(Xsd_string("italiano","it"), Xsd_string("espagnol", Language.ES))
        self.assertEqual(LangString(["english@en", "deutsch@de", "italiano@it", "espagnol@es"]), ls5)

        ls7 = LangString(["english@en", "deutsch@de"])
        with self.assertRaises(OldapErrorValue):
            ls7.add(77)


    def test_langstring_undo(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de"])
        ls1.add({Language.FR: "français", Language.ZU: "undefined"})
        self.assertEqual(ls1, LangString("english@en", "deutsch@de", "français@fr", "undefined@zu"))
        ls1.undo()
        self.assertEqual(ls1, LangString("english@en", "deutsch@de"))

    def test_langstring_update(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de"])
        ls1.add({Language.FR: "français", Language.ZU: "undefined"})
        del ls1[Language.EN]
        qlist = ls1.update(graph=Xsd_QName("oldaplib:test"),
                           subject=Iri("oldaplib:subj"),
                           field=Xsd_QName("oldaplib:prop"))
        qstr = " ;\n".join(qlist)
        expected = """INSERT DATA {
    GRAPH oldaplib:test {
        oldaplib:subj oldaplib:prop "français"@fr .
    }
}
 ;
INSERT DATA {
    GRAPH oldaplib:test {
        oldaplib:subj oldaplib:prop "undefined"@zu .
    }
}
 ;
DELETE DATA {
    GRAPH oldaplib:test {
        oldaplib:subj oldaplib:prop "english"@en .
    }
}
"""
        self.assertEqual(qstr, expected)

        sstr = ls1.update_shacl(graph=Xsd_NCName("test"),
                                prop_iri=Iri('oldaplib:prop'),
                                attr=PropClassAttr.NAME,
                                modified=Xsd_dateTime("2023-11-04T12:00:00Z"))
        expected = """# LangString: Process "FR" with Action "create"
WITH test:shacl
INSERT {
    ?prop sh:name "français"@fr .
}
WHERE {
    BIND(oldaplib:propShape as ?prop) .
    ?prop dcterms:modified ?modified .
    FILTER(?modified = "2023-11-04T12:00:00+00:00"^^xsd:dateTime)
};
# LangString: Process "ZU" with Action "create"
WITH test:shacl
INSERT {
    ?prop sh:name "undefined"@zu .
}
WHERE {
    BIND(oldaplib:propShape as ?prop) .
    ?prop dcterms:modified ?modified .
    FILTER(?modified = "2023-11-04T12:00:00+00:00"^^xsd:dateTime)
};
# LangString: Process "EN" with Action "delete"
WITH test:shacl
DELETE {
    ?prop sh:name "english"@en .
}
WHERE {
    BIND(oldaplib:propShape as ?prop) .
    ?prop sh:name "english"@en .
    ?prop dcterms:modified ?modified .
    FILTER(?modified = "2023-11-04T12:00:00+00:00"^^xsd:dateTime)
}"""
        self.assertEqual(sstr, expected)

    def test_langstring_delete_shacl(self):
        LangString.defaultLanguage = Language.ZU
        ls1 = LangString(["english@en", "deutsch@de"])
        sparql = ls1.delete_shacl(graph=Xsd_NCName("test"),
                                  prop_iri=Iri('oldaplib:prop'),
                                  attr=PropClassAttr.NAME,
                                  modified=Xsd_dateTime("2023-11-04T12:00:00Z"))
        expected = """#
# Deleting the complete LangString data for oldaplib:prop sh:name
#
WITH test:shacl
DELETE {
    ?prop sh:name ?langval
}
WHERE {
    BIND(oldaplib:propShape as ?prop)
    ?prop sh:name ?langval
}
"""
        self.assertEqual(expected, sparql)
