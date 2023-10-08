import unittest

from omaslib.src.helpers.datatypes import QName, AnyIRI, NamespaceIRI, NCName
from omaslib.src.helpers.omaserror import OmasError


class TestQname(unittest.TestCase):

    def test_qname(self):
        qn = QName('prefix:name')
        self.assertEqual(qn.prefix, 'prefix')
        self.assertEqual(qn.fragment, 'name')
        self.assertEqual(str(qn), 'prefix:name')
        self.assertEqual(len(qn), 11)
        qn2 = qn + 'Shape'
        self.assertEqual(str(qn2), 'prefix:nameShape')
        qn3 = QName.build('prefix', 'name')
        self.assertTrue(qn == qn3)
        self.assertEqual(repr(qn3), 'QName(prefix:name)')
        self.assertTrue(qn != qn2)
        qn += 'Shape'
        self.assertEqual(str(qn), 'prefix:nameShape')
        with self.assertRaises(OmasError) as ex:
            qn4 = QName('2gaga')
        self.assertEqual(ex.exception.message, 'Invalid string "2gaga" for QName')

class TestAnyIRI(unittest.TestCase):

    def test_anyiri(self):
        iri1 = AnyIRI('http://www.org/test')
        self.assertEqual(str(iri1), 'http://www.org/test')
        self.assertEqual(len(iri1), 19)
        self.assertFalse(iri1.append_allowed)
        iri2 = AnyIRI('http://www.ch/tescht#')
        self.assertTrue(iri2.append_allowed)
        iri3 = iri2 + 'gaga'
        self.assertEqual(iri3, 'http://www.ch/tescht#gaga')
        self.assertFalse(iri1 == iri3)
        iri2 += 'gaga'
        self.assertTrue(iri2 == iri3)
        with self.assertRaises(OmasError) as ex:
            noiri = AnyIRI('waseliwas')
        self.assertEqual(ex.exception.message, 'Invalid string "waseliwas" for anyIRI')

    def test_namespace(self):
        ns1 = NamespaceIRI('http://www.org/test/')
        self.assertEqual(str(ns1), 'http://www.org/test/')
        ns2 = NamespaceIRI('http://www.org/test#')
        self.assertEqual(str(ns2), 'http://www.org/test#')
        with self.assertRaises(OmasError) as ex:
            nons = NamespaceIRI('http://www.org/test')
        self.assertEqual(ex.exception.message, "NamespaceIRI must end with '/' or '#'!")

class TestNCName(unittest.TestCase):

    def test_ncname(self):
        ncn1 = NCName('AnId0')
        self.assertEqual(str(ncn1), 'AnId0')
        self.assertEqual(repr(ncn1), 'NCName(AnId0)')
        ncn1a = ncn1 + 'X'
        self.assertEqual(str(ncn1a), 'AnId0X')
        ncn1a += 'Y'
        self.assertEqual(str(ncn1a), 'AnId0XY')
        ncn1b = ncn1 + 'XY'
        self.assertTrue(ncn1a == ncn1b)
        self.assertFalse(ncn1a != ncn1b)
        with self.assertRaises(OmasError) as ex:
            ncn2 = NCName('0AnId')
        self.assertEqual(ex.exception.message, "Invalid string for NCName")
        with self.assertRaises(OmasError) as ex:
            ncn3 = NCName('An$Id')
        self.assertEqual(ex.exception.message, "Invalid string for NCName")
        with self.assertRaises(OmasError) as ex:
            ncn4 = NCName('An:Id')
        self.assertEqual(ex.exception.message, "Invalid string for NCName")
        with self.assertRaises(OmasError) as ex:
            ncn5 = NCName('An@Id')
        self.assertEqual(ex.exception.message, "Invalid string for NCName")


