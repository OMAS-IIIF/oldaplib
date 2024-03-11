import json
import unittest
from base64 import b64encode

from omaslib.src.helpers.datatypes import QName, AnyIRI, NamespaceIRI, NCName, gYearMonth, gYear, hexBinary, gMonthDay, gDay, gMonth, base64Binary, anyURI
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.serializer import serializer


class TestQname(unittest.TestCase):

    def test_gYearMonth(self):
        val = gYearMonth("2020-03")
        self.assertEqual(str(val), "2020-03")
        self.assertEqual(repr(val), '"2020-03"^^gYearMonth')

        val = gYearMonth("1800-03Z")
        self.assertEqual(str(val), "1800-03Z")
        self.assertEqual(repr(val), '"1800-03Z"^^gYearMonth')

        val = gYearMonth("1800-03-02:00")
        self.assertEqual(str(val), "1800-03-02:00")
        self.assertEqual(repr(val), '"1800-03-02:00"^^gYearMonth')

        val = gYearMonth("-0003-03+02:00")
        self.assertEqual(str(val), "-0003-03+02:00")
        self.assertEqual(repr(val), '"-0003-03+02:00"^^gYearMonth')
        self.assertTrue(val == "-0003-03+02:00")

        val = gYearMonth("1800-03-02:00")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        with self.assertRaises(OmasErrorValue):
            val = gYearMonth("2023-13Z")

        with self.assertRaises(OmasErrorValue):
            val = gYearMonth("2023-00Z")

        with self.assertRaises(OmasErrorValue):
            val = gYearMonth("2000Z")

        with self.assertRaises(OmasErrorValue):
            val = gYearMonth("2000-04\"\n SELECT * {?s ?p ?o } #")

    def test_gYear(self):
        val = gYear("2020")
        self.assertEqual(str(val), "2020")
        self.assertEqual(repr(val), '"2020"^^xsd:gYear')

        val = gYear("1800Z")
        self.assertEqual(str(val), "1800Z")
        self.assertEqual(repr(val), '"1800Z"^^xsd:gYear')

        val = gYear("1800-02:00")
        self.assertEqual(str(val), "1800-02:00")
        self.assertEqual(repr(val), '"1800-02:00"^^xsd:gYear')

        val = gYear("-0003+02:00")
        self.assertEqual(str(val), "-0003+02:00")
        self.assertEqual(repr(val), '"-0003+02:00"^^xsd:gYear')
        self.assertTrue(val == "-0003+02:00")

        val = gYear("1800-02:00")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

    def test_gMonthDay(self):
        val = gMonthDay("--02-21")
        self.assertEqual(str(val), "--02-21")
        self.assertEqual(repr(val), '"--02-21"^^xsd:gMonthDay')

        val = gMonthDay("--02-21+12:00")
        self.assertEqual(str(val), "--02-21+12:00")
        self.assertEqual(repr(val), '"--02-21+12:00"^^xsd:gMonthDay')

        val = gMonthDay("--02-21Z")
        self.assertEqual(str(val), "--02-21Z")
        self.assertEqual(repr(val), '"--02-21Z"^^xsd:gMonthDay')
        self.assertTrue(val == "--02-21Z")

        val = gMonthDay("--02-21Z")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        with self.assertRaises(OmasErrorValue):
            val = gMonthDay("--02-32Z")

        with self.assertRaises(OmasErrorValue):
            val = gMonthDay("--13-20")

        with self.assertRaises(OmasErrorValue):
            val = gMonthDay("-13-20")

        val = gMonthDay("--02-21Z")
        self.assertTrue(val == "--02-21Z")

    def test_gDay(self):
        val = gDay("---01")
        self.assertEqual(str(val), "---01")
        self.assertEqual(repr(val), '"---01"^^xsd:gDay')

        val = gDay("---01Z")
        self.assertEqual(str(val), "---01Z")
        self.assertEqual(repr(val), '"---01Z"^^xsd:gDay')

        val = gDay("---01+01:00")
        self.assertEqual(str(val), "---01+01:00")
        self.assertEqual(repr(val), '"---01+01:00"^^xsd:gDay')

        val = gDay("---21Z")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        with self.assertRaises(OmasErrorValue):
            val = gDay("--01+01:00")

        with self.assertRaises(OmasErrorValue):
            val = gDay("--01-")

        with self.assertRaises(OmasErrorValue):
            val = gDay("---01+01:0")

    def test_gMonth(self):
        val = gMonth("--10")
        self.assertEqual(str(val), "--10")
        self.assertEqual(repr(val), '"--10"^^xsd:gMonth')

        val = gMonth("--05Z")
        self.assertEqual(str(val), "--05Z")
        self.assertEqual(repr(val), '"--05Z"^^xsd:gMonth')

        val = gMonth("--01+01:00")
        self.assertEqual(str(val), "--01+01:00")
        self.assertEqual(repr(val), '"--01+01:00"^^xsd:gMonth')

        val = gMonth("--12Z")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        with self.assertRaises(OmasErrorValue):
            val = gMonth("---01+01:00")

        with self.assertRaises(OmasErrorValue):
            val = gMonth("--01-")

        with self.assertRaises(OmasErrorValue):
            val = gMonth("--01+01:0")

        with self.assertRaises(OmasErrorValue):
            val = gMonth("--13Z")


    def test_hexBinary(self):
        val = hexBinary("1fab17fa")
        self.assertEqual(str(val), "1fab17fa")
        self.assertEqual(repr(val), '"1fab17fa"^^xsd:hexBinary')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)


        with self.assertRaises(OmasErrorValue):
            val = hexBinary("1fab17fg")

    def test_base64Binary(self):
        data = b'Hello, World!12'
        base62string = b64encode(data)

        val = base64Binary(base62string.decode('utf-8'))
        self.assertEqual(str(val), base62string.decode('utf-8'))
        self.assertEqual(repr(val), f'"{base62string.decode('utf-8')}"^^xsd:base64Binary')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        with self.assertRaises(OmasErrorValue):
            val = base64Binary("Was\nIst denn das$$\n\n")

    def test_anyURI(self):
        val = anyURI("http://example.com")
        self.assertEqual(str(val), "http://example.com")
        self.assertEqual(repr(val), '"http://example.com"^^xsd:anyURI')

        val = anyURI("http://example.com/gugus/nowas#anchor1")
        self.assertEqual(str(val), "http://example.com/gugus/nowas#anchor1")
        self.assertEqual(repr(val), '"http://example.com/gugus/nowas#anchor1"^^xsd:anyURI')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)


        with self.assertRaises(OmasErrorValue) as ex:
            val = anyURI("http://example.com/gugus/ test.dat")

    def test_normalizedString(self):
        pass

    def test_qname(self):
        qn = QName('prefix:name')
        self.assertEqual(qn.prefix, 'prefix')
        self.assertEqual(qn.fragment, 'name')
        self.assertEqual(str(qn), 'prefix:name')
        self.assertEqual(len(qn), 11)
        qn2 = qn + 'Shape'
        self.assertEqual(str(qn2), 'prefix:nameShape')
        qn3 = QName('prefix', 'name')
        self.assertTrue(qn == qn3)
        self.assertEqual(hash(qn), hash(qn3))
        self.assertEqual(repr(qn3), "prefix:name")
        self.assertTrue(qn != qn2)
        qn += 'Shape'
        self.assertEqual(str(qn), 'prefix:nameShape')
        with self.assertRaises(OmasErrorValue) as ex:
            qn4 = QName('2gaga')
        self.assertEqual(str(ex.exception), 'Invalid string "2gaga" for QName')
        qn5 = QName('xml:double')
        self.assertEqual(str(qn5), 'xml:double')
        with self.assertRaises(OmasErrorValue) as ex:
            qn6 = QName('xml:2gaga')
        self.assertEqual(str(ex.exception), 'Invalid string "xml:2gaga" for QName. Error: Invalid string "2gaga" for NCName')


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
        self.assertEqual(hash(iri2), hash(iri3))
        with self.assertRaises(OmasErrorValue) as ex:
            noiri = AnyIRI('waseliwas')
        self.assertEqual(str(ex.exception), 'Invalid string "waseliwas" for anyIRI')

    def test_namespace(self):
        ns1 = NamespaceIRI('http://www.org/test/')
        self.assertEqual(str(ns1), 'http://www.org/test/')
        ns2 = NamespaceIRI('http://www.org/test#')
        self.assertEqual(str(ns2), 'http://www.org/test#')
        with self.assertRaises(OmasErrorValue) as ex:
            nons = NamespaceIRI('http://www.org/test')
        self.assertEqual(str(ex.exception), "NamespaceIRI must end with '/' or '#'!")


class TestNCName(unittest.TestCase):

    def test_ncname(self):
        ncn1 = NCName('AnId0')
        self.assertEqual(str(ncn1), 'AnId0')
        self.assertEqual(repr(ncn1), '"AnId0"^^xsd:NCName')
        ncn1a = ncn1 + 'X'
        self.assertEqual(str(ncn1a), 'AnId0X')
        ncn1a += 'Y'
        self.assertEqual(str(ncn1a), 'AnId0XY')
        ncn1b = ncn1 + 'XY'
        self.assertTrue(ncn1a == ncn1b)
        self.assertEqual(hash(ncn1a), hash(ncn1b))
        self.assertFalse(ncn1a != ncn1b)
        with self.assertRaises(OmasErrorValue) as ex:
            ncn2 = NCName('0AnId')
        self.assertEqual(str(ex.exception), 'Invalid string "0AnId" for NCName')
        with self.assertRaises(OmasErrorValue) as ex:
            ncn3 = NCName('An$Id')
        self.assertEqual(str(ex.exception), 'Invalid string "An$Id" for NCName')
        with self.assertRaises(OmasErrorValue) as ex:
            ncn4 = NCName('An:Id')
        self.assertEqual(str(ex.exception), 'Invalid string "An:Id" for NCName')
        with self.assertRaises(OmasErrorValue) as ex:
            ncn5 = NCName('An@Id')
        self.assertEqual(str(ex.exception), 'Invalid string "An@Id" for NCName')
