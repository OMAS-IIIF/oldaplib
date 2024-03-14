import json
import math
import unittest
from base64 import b64encode

from omaslib.src.connection import token, Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import QName, AnyIRI, NamespaceIRI, NCName, Xsd_gYearMonth, Xsd_gYear, Xsd_hexBinary, \
    Xsd_gMonthDay, Xsd_gDay, Xsd_gMonth, Xsd_base64Binary, Xsd_anyURI, \
    Xsd_normalizedString, Xsd_token, Xsd_language, Xsd_NMTOKEN, Xsd, Xsd_ID, Xsd_IDREF, Xsd_integer, \
    Xsd_nonPositiveInteger, Xsd_int, Xsd_long, Xsd_short, Xsd_nonNegativeInteger, Xsd_unsignedLong, Xsd_unsignedInt, \
    Xsd_unsignedShort, Xsd_unsignedByte, \
    Xsd_positiveInteger, Xsd_decimal, Xsd_float, Xsd_double, Xsd_duration, Xsd_dateTime, Xsd_dateTimeStamp
from omaslib.src.helpers.omaserror import OmasErrorValue
from omaslib.src.helpers.query_processor import QueryProcessor, RowElementType
from omaslib.src.helpers.serializer import serializer


class TestXsdTypes(unittest.TestCase):

    _connection: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://testing.org/datatypes#")
        cls._context.use('test')
        cls._connection = Connection(server='http://localhost:7200',
                                     repo="omas",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._connection.clear_graph(QName('test:test'))

    @classmethod
    def tearDownClass(cls):
        pass

    def create_triple(self, name: NCName, value: Xsd):
        sparql = self._context.sparql_context
        sparql += f"""
        INSERT DATA {{
            GRAPH test:test {{
                test:{name} test:prop {repr(value)}
            }}
        }}"""
        self._connection.update_query(sparql)

    def get_triple(self, name: NCName) -> Xsd:
        sparql = self._context.sparql_context
        sparql += f"""
        SELECT ?value
        FROM test:test
        WHERE {{
            test:{name} test:prop ?value
        }}
        """
        result = self._connection.query(sparql)
        res = QueryProcessor(context=self._context, query_result=result)
        return res[0]['value']

    def delete_triple(self, name: NCName):
        sparql = self._context.sparql_context
        sparql += f"""
        DELETE FROM test:test {{
            test:{name} test:prop ?value
        }}
        """

    def test_xsd_decimal(self):
        val = Xsd_decimal(3.141592653589793)
        self.assertEqual(val, 3.141592653589793)
        self.assertEqual(str(val), '3.141592653589793')
        self.assertEqual(repr(val), '"3.141592653589793"^^xsd:decimal')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_decimal"), val)
        valx = self.get_triple(NCName("Xsd_decimal"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_decimal("-1. 0")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_decimal("abcd")

    def test_xsd_float(self):
        val = Xsd_float(6.62607015e-34)
        self.assertEqual(val, 6.62607015e-34)
        self.assertEqual(str(val), '6.62607015e-34')
        self.assertEqual(repr(val), '"6.62607015e-34"^^xsd:float')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_float"), val)
        valx = self.get_triple(NCName("Xsd_float"))
        self.assertEqual(val, valx)

        val = Xsd_float('NaN')
        self.assertTrue(math.isnan(val))

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isnan(val2))

        self.create_triple(NCName("Xsd_floatNaN"), val)
        valx = self.get_triple(NCName("Xsd_floatNaN"))
        self.assertTrue(math.isnan(valx))

        val = Xsd_float('inf')
        self.assertTrue(math.isinf(val) and val > 0.0)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isinf(val2) and val2 > 0.0)

        self.create_triple(NCName("Xsd_floatInf"), val)
        valx = self.get_triple(NCName("Xsd_floatInf"))
        self.assertTrue(math.isinf(valx) and valx > 0.0)

        val = Xsd_float('-inf')
        self.assertTrue(math.isinf(val) and val < 0.0)

        self.create_triple(NCName("Xsd_float_Inf"), val)
        valx = self.get_triple(NCName("Xsd_float_Inf"))
        self.assertTrue(math.isinf(valx) and valx < 0.0)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isinf(val2) and val2 < 0.0)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_float("-1. 0")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_float("abcd")

    def test_xsd_double(self):
        val = Xsd_double(6.62607015e-34)
        self.assertEqual(val, 6.62607015e-34)
        self.assertEqual(str(val), '6.62607015e-34')
        self.assertEqual(repr(val), '"6.62607015e-34"^^xsd:double')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_double"), val)
        valx = self.get_triple(NCName("Xsd_double"))
        self.assertEqual(val, valx)

        val = Xsd_double('NaN')
        self.assertTrue(math.isnan(val))

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isnan(val2))

        self.create_triple(NCName("Xsd_doubleNaN"), val)
        valx = self.get_triple(NCName("Xsd_doubleNaN"))
        self.assertTrue(math.isnan(valx))

        val = Xsd_double('inf')
        self.assertTrue(math.isinf(val) and val > 0.0)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isinf(val2) and val2 > 0.0)

        self.create_triple(NCName("Xsd_doubleInf"), val)
        valx = self.get_triple(NCName("Xsd_doubleInf"))
        self.assertTrue(math.isinf(valx) and valx > 0.0)

        val = Xsd_double('-inf')
        self.assertTrue(math.isinf(val) and val < 0.0)

        self.create_triple(NCName("Xsd_double_Inf"), val)
        valx = self.get_triple(NCName("Xsd_double_Inf"))
        self.assertTrue(math.isinf(valx) and valx < 0.0)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isinf(val2) and val2 < 0.0)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_double("-1. 0")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_double("abcd")

    def test_xsd_duration(self):
        val = Xsd_duration('PT2M10S')
        self.assertTrue(str(val), 'PT2M10S')
        self.assertTrue(repr(val), '"PT2M10S"^^xsd:duration')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_duration"), val)
        valx = self.get_triple(NCName("Xsd_duration"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_duration('P1M2Y')

    def test_xsd_datetime(self):
        val = Xsd_dateTime('2001-10-26T21:32:52')
        self.assertTrue(str(val), '2001-10-26T21:32:52')
        self.assertTrue(repr(val), '"2001-10-26T21:32:52"^^xsd:dateTime')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_dateTime"), val)
        valx = self.get_triple(NCName("Xsd_dateTime"))
        self.assertEqual(val, valx)

        val = Xsd_dateTime('2001-10-26T21:32:52+02:00')
        self.assertTrue(str(val), '2001-10-26T21:32:52+02:00')
        self.assertTrue(repr(val), '"2001-10-26T21:32:52+02:00"^^xsd:dateTime')

        val = Xsd_dateTime('2001-10-26T19:32:52Z')
        self.assertTrue(str(val), '2001-10-26T19:32:52Z')
        self.assertTrue(repr(val), '"2001-10-26T19:32:52Z"^^xsd:dateTime')

        val = Xsd_dateTime('2001-10-26T19:32:52+00:00')
        self.assertTrue(str(val), '2001-10-26T19:32:52+00:00')
        self.assertTrue(repr(val), '"2001-10-26T19:32:52+00:00"^^xsd:dateTime')

        val = Xsd_dateTime('2001-10-26T21:32:52.12679')
        self.assertTrue(str(val), '2001-10-26T21:32:52.12679')
        self.assertTrue(repr(val), '"2001-10-26T21:32:52.12679"^^xsd:dateTime')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTime('2001-10-26')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTime('2001-10-26T21:32')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTime('2001-10-26T25:32:52+02:00')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTime('01-10-26T21:32')

    def test_xsd_datetimeStamp(self):
        val = Xsd_dateTimeStamp('2001-10-26T21:32:52Z')
        self.assertTrue(str(val), '2001-10-26T21:32:52Z')
        self.assertTrue(repr(val), '"2001-10-26T21:32:52Z"^^xsd:dateTimeStamp')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_dateTimeStamp"), val)
        valx = self.get_triple(NCName("Xsd_dateTimeStamp"))
        self.assertEqual(val, valx)

        val = Xsd_dateTimeStamp('2001-10-26T21:32:52+02:00')
        self.assertTrue(str(val), '2001-10-26T21:32:52+02:00')
        self.assertTrue(repr(val), '"2001-10-26T21:32:52+02:00"^^xsd:dateTimeStamp')

        val = Xsd_dateTimeStamp('2001-10-26T19:32:52Z')
        self.assertTrue(str(val), '2001-10-26T19:32:52Z')
        self.assertTrue(repr(val), '"2001-10-26T19:32:52Z"^^xsd:dateTimeStamp')

        val = Xsd_dateTimeStamp('2001-10-26T19:32:52+00:00')
        self.assertTrue(str(val), '2001-10-26T19:32:52+00:00')
        self.assertTrue(repr(val), '"2001-10-26T19:32:52+00:00"^^xsd:dateTimeStamp')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTimeStamp('2001-10-26T21:32:52.12679')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTime('2001-10-26')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTime('2001-10-26T21:32')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTime('2001-10-26T25:32:52+02:00')

        with self.assertRaises(OmasErrorValue):
            val = Xsd_dateTime('01-10-26T21:32')


    def test_xsd_gYearMonth(self):
        val = Xsd_gYearMonth("2020-03")
        self.assertEqual(str(val), "2020-03")
        self.assertEqual(repr(val), '"2020-03"^^xsd:gYearMonth')

        val = Xsd_gYearMonth("1800-03Z")
        self.assertEqual(str(val), "1800-03Z")
        self.assertEqual(repr(val), '"1800-03Z"^^xsd:gYearMonth')

        val = Xsd_gYearMonth("1800-03-02:00")
        self.assertEqual(str(val), "1800-03-02:00")
        self.assertEqual(repr(val), '"1800-03-02:00"^^xsd:gYearMonth')

        val = Xsd_gYearMonth("-0003-03+02:00")
        self.assertEqual(str(val), "-0003-03+02:00")
        self.assertEqual(repr(val), '"-0003-03+02:00"^^xsd:gYearMonth')
        self.assertTrue(val == "-0003-03+02:00")

        val = Xsd_gYearMonth("1800-03-02:00")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_gYearMonth"), val)
        valx = self.get_triple(NCName("Xsd_gYearMonth"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gYearMonth("2023-13Z")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gYearMonth("2023-00Z")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gYearMonth("2000Z")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gYearMonth("2000-04\"\n SELECT * {?s ?p ?o } #")

    def test_xsd_gYear(self):
        val = Xsd_gYear("2020")
        self.assertEqual(str(val), "2020")
        self.assertEqual(repr(val), '"2020"^^xsd:gYear')

        val = Xsd_gYear("1800Z")
        self.assertEqual(str(val), "1800Z")
        self.assertEqual(repr(val), '"1800Z"^^xsd:gYear')

        val = Xsd_gYear("1800-02:00")
        self.assertEqual(str(val), "1800-02:00")
        self.assertEqual(repr(val), '"1800-02:00"^^xsd:gYear')

        val = Xsd_gYear("-0003+02:00")
        self.assertEqual(str(val), "-0003+02:00")
        self.assertEqual(repr(val), '"-0003+02:00"^^xsd:gYear')
        self.assertTrue(val == "-0003+02:00")

        val = Xsd_gYear("1800-02:00")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_gYear"), val)
        valx = self.get_triple(NCName("Xsd_gYear"))
        self.assertEqual(val, valx)

    def test_xsd_gMonthDay(self):
        val = Xsd_gMonthDay("--02-21")
        self.assertEqual(str(val), "--02-21")
        self.assertEqual(repr(val), '"--02-21"^^xsd:gMonthDay')

        val = Xsd_gMonthDay("--02-21+12:00")
        self.assertEqual(str(val), "--02-21+12:00")
        self.assertEqual(repr(val), '"--02-21+12:00"^^xsd:gMonthDay')

        val = Xsd_gMonthDay("--02-21Z")
        self.assertEqual(str(val), "--02-21Z")
        self.assertEqual(repr(val), '"--02-21Z"^^xsd:gMonthDay')
        self.assertTrue(val == "--02-21Z")

        val = Xsd_gMonthDay("--02-21Z")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_gMonthDay"), val)
        valx = self.get_triple(NCName("Xsd_gMonthDay"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gMonthDay("--02-32Z")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gMonthDay("--13-20")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gMonthDay("-13-20")

        val = Xsd_gMonthDay("--02-21Z")
        self.assertTrue(val == "--02-21Z")

    def test_xsd_gDay(self):
        val = Xsd_gDay("---01")
        self.assertEqual(str(val), "---01")
        self.assertEqual(repr(val), '"---01"^^xsd:gDay')

        val = Xsd_gDay("---01Z")
        self.assertEqual(str(val), "---01Z")
        self.assertEqual(repr(val), '"---01Z"^^xsd:gDay')

        val = Xsd_gDay("---01+01:00")
        self.assertEqual(str(val), "---01+01:00")
        self.assertEqual(repr(val), '"---01+01:00"^^xsd:gDay')

        val = Xsd_gDay("---21Z")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_gDay"), val)
        valx = self.get_triple(NCName("Xsd_gDay"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gDay("--01+01:00")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gDay("--01-")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gDay("---01+01:0")

    def test_xsd_gMonth(self):
        val = Xsd_gMonth("--10")
        self.assertEqual(str(val), "--10")
        self.assertEqual(repr(val), '"--10"^^xsd:gMonth')

        val = Xsd_gMonth("--05Z")
        self.assertEqual(str(val), "--05Z")
        self.assertEqual(repr(val), '"--05Z"^^xsd:gMonth')

        val = Xsd_gMonth("--01+01:00")
        self.assertEqual(str(val), "--01+01:00")
        self.assertEqual(repr(val), '"--01+01:00"^^xsd:gMonth')

        val = Xsd_gMonth("--12Z")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_gMonth"), val)
        valx = self.get_triple(NCName("Xsd_gMonth"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gMonth("---01+01:00")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gMonth("--01-")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gMonth("--01+01:0")

        with self.assertRaises(OmasErrorValue):
            val = Xsd_gMonth("--13Z")


    def test_xsd_hexBinary(self):
        val = Xsd_hexBinary("1fab17fa")
        self.assertEqual(str(val), "1fab17fa")
        self.assertEqual(repr(val), '"1fab17fa"^^xsd:hexBinary')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_hexBinary"), val)
        valx = self.get_triple(NCName("Xsd_hexBinary"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_hexBinary("1fab17fg")

    def test_xsd_base64Binary(self):
        data = b'Hello, World!12'
        base62string = b64encode(data)

        val = Xsd_base64Binary(base62string.decode('utf-8'))
        self.assertEqual(str(val), base62string.decode('utf-8'))
        self.assertEqual(repr(val), f'"{base62string.decode('utf-8')}"^^xsd:base64Binary')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_base64Binary"), val)
        valx = self.get_triple(NCName("Xsd_base64Binary"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_base64Binary("Was\nIst denn das$$\n\n")

    def test_xsd_anyURI(self):
        val = Xsd_anyURI("http://example.com")
        self.assertEqual(str(val), "http://example.com")
        self.assertEqual(repr(val), '"http://example.com"^^xsd:anyURI')

        val = Xsd_anyURI("http://example.com/gugus/nowas#anchor1")
        self.assertEqual(str(val), "http://example.com/gugus/nowas#anchor1")
        self.assertEqual(repr(val), '"http://example.com/gugus/nowas#anchor1"^^xsd:anyURI')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_anyURI"), val)
        valx = self.get_triple(NCName("Xsd_anyURI"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue) as ex:
            val = Xsd_anyURI("http://example.com/gugus/ test.dat")

    def test_xsd_normalizedString(self):
        val = Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen")
        self.assertEqual(str(val), "Dies ist ein string mit $onderzeichen\" und anderen Dingen")
        self.assertEqual(repr(val), '"Dies ist ein string mit $onderzeichen\\" und anderen Dingen"^^xsd:normalizedString')

        val = Xsd_normalizedString.fromRdf('Dies ist ein string mit $onderzeichen\\" und anderen Dingen')
        self.assertEqual(str(val), "Dies ist ein string mit $onderzeichen\" und anderen Dingen")
        self.assertEqual(repr(val), '"Dies ist ein string mit $onderzeichen\\" und anderen Dingen"^^xsd:normalizedString')

        val = Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen")
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_normalizedString"), val)
        valx = self.get_triple(NCName("Xsd_normalizedString"))
        self.assertEqual(val, valx)

    def test_xsd_token(self):
        val = Xsd_token("Dies ist ein string mit $onderzeichen und anderen Dingen")
        self.assertEqual(str(val), "Dies ist ein string mit $onderzeichen und anderen Dingen")
        self.assertEqual(repr(val), '"Dies ist ein string mit $onderzeichen und anderen Dingen"^^xsd:token')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_token"), val)
        valx = self.get_triple(NCName("Xsd_token"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_token("Dies ist ein string mit $onderzeichen\"\nund anderen Dingen")

    def test_xsd_language(self):
        val = Xsd_language("de")
        self.assertEqual(str(val), "de")
        self.assertEqual(repr(val), '"de"^^xsd:language')

        val = Xsd_language("de-CH")
        self.assertEqual(str(val), "de-CH")
        self.assertEqual(repr(val), '"de-CH"^^xsd:language')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_language"), val)
        valx = self.get_triple(NCName("Xsd_language"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_language("xxx")

    def test_xsd_NMTOKEN(self):
        val = Xsd_NMTOKEN(":ein.Test")
        self.assertEqual(str(val), ":ein.Test")
        self.assertEqual(repr(val), '":ein.Test"^^xsd:NMTOKEN')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_NMTOKEN"), val)
        valx = self.get_triple(NCName("Xsd_NMTOKEN"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_NMTOKEN("$EinTest;")

    def test_xsd_ID(self):
        val = Xsd_ID("unique")
        self.assertEqual(str(val), "unique")
        self.assertEqual(repr(val), '"unique"^^xsd:ID')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_ID"), val)
        valx = self.get_triple(NCName("Xsd_ID"))
        self.assertEqual(val, valx)

    def test_xsd_IDREF(self):
        val = Xsd_IDREF("uniqueref")
        self.assertEqual(str(val), "uniqueref")
        self.assertEqual(repr(val), '"uniqueref"^^xsd:IDREF')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_IDREF"), val)
        valx = self.get_triple(NCName("Xsd_IDREF"))
        self.assertEqual(val, valx)

    def test_xsd_integer(self):
        val = Xsd_integer(42)
        self.assertEqual(val, 42)
        self.assertEqual(str(val), '42')
        self.assertEqual(repr(val), '"42"^^xsd:integer')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_integer"), val)
        valx = self.get_triple(NCName("Xsd_integer"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_integer("was is 42")

    def test_xsd_nonPositiveInteger(self):
        val = Xsd_nonPositiveInteger(-22)
        self.assertEqual(val, -22)
        self.assertEqual(str(val), '-22')
        self.assertEqual(repr(val), '"-22"^^xsd:nonPositiveInteger')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)


        self.create_triple(NCName("Xsd_nonPositiveInteger"), val)
        valx = self.get_triple(NCName("Xsd_nonPositiveInteger"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_nonPositiveInteger(1)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_nonPositiveInteger('minusfortytwo')

    def test_xsd_int(self):
        val = Xsd_int(505_801)
        self.assertEqual(val, 505_801)
        self.assertEqual(str(val), '505801')
        self.assertEqual(repr(val), '"505801"^^xsd:int')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_int"), val)
        valx = self.get_triple(NCName("Xsd_int"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_int(2_147_483_648)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_int(-2_147_483_649)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_int("abcd")

    def test_xsd_long(self):
        val = Xsd_long(505_801)
        self.assertEqual(val, 505_801)
        self.assertEqual(str(val), '505801')
        self.assertEqual(repr(val), '"505801"^^xsd:long')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_long"), val)
        valx = self.get_triple(NCName("Xsd_long"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_long(9223372036854775808)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_long(-9223372036854775809)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_long("abcd")

    def test_xsd_short(self):
        val = Xsd_short(-2024)
        self.assertEqual(val, -2024)
        self.assertEqual(str(val), '-2024')
        self.assertEqual(repr(val), '"-2024"^^xsd:short')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_short"), val)
        valx = self.get_triple(NCName("Xsd_short"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_short(32768)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_short(-32769)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_short("abcd")

    def test_xsd_nonNegativeInteger(self):
        val = Xsd_nonNegativeInteger(202_203_204)
        self.assertEqual(val, 202_203_204)
        self.assertEqual(str(val), '202203204')
        self.assertEqual(repr(val), '"202203204"^^xsd:nonNegativeInteger')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_nonNegativeInteger"), val)
        valx = self.get_triple(NCName("Xsd_nonNegativeInteger"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_nonNegativeInteger(-5)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_nonNegativeInteger("abcd")

    def test_xsd_unsignedLong(self):
        val = Xsd_unsignedLong(202_203_204)
        self.assertEqual(val, 202_203_204)
        self.assertEqual(str(val), '202203204')
        self.assertEqual(repr(val), '"202203204"^^xsd:unsignedLong')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_unsignedLong"), val)
        valx = self.get_triple(NCName("Xsd_unsignedLong"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedLong(-1)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedLong(18446744073709551616)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedLong("abcd")

    def test_xsd_unsignedInt(self):
        val = Xsd_unsignedInt(20200)
        self.assertEqual(val, 20200)
        self.assertEqual(str(val), '20200')
        self.assertEqual(repr(val), '"20200"^^xsd:unsignedInt')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_unsignedInt"), val)
        valx = self.get_triple(NCName("Xsd_unsignedInt"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedInt(-1)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedInt(4294967296)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedInt("abcd")

    def test_xsd_unsignedShort(self):
        val = Xsd_unsignedShort(20200)
        self.assertEqual(val, 20200)
        self.assertEqual(str(val), '20200')
        self.assertEqual(repr(val), '"20200"^^xsd:unsignedShort')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_unsignedShort"), val)
        valx = self.get_triple(NCName("Xsd_unsignedShort"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedShort(-1)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedShort(65536)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedShort("abcd")

    def test_xsd_unsignedByte(self):
        val = Xsd_unsignedByte(202)
        self.assertEqual(val, 202)
        self.assertEqual(str(val), '202')
        self.assertEqual(repr(val), '"202"^^xsd:unsignedByte')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_unsignedByte"), val)
        valx = self.get_triple(NCName("Xsd_unsignedByte"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedByte(-1)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedByte(256)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_unsignedByte("abcd")

    def test_xsd_positiveInteger(self):
        val = Xsd_positiveInteger(202_303_404)
        self.assertEqual(val, 202_303_404)
        self.assertEqual(str(val), '202303404')
        self.assertEqual(repr(val), '"202303404"^^xsd:positiveInteger')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(NCName("Xsd_positiveInteger"), val)
        valx = self.get_triple(NCName("Xsd_positiveInteger"))
        self.assertEqual(val, valx)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_positiveInteger(0)

        with self.assertRaises(OmasErrorValue):
            val = Xsd_positiveInteger("abcd")


class TestQname(unittest.TestCase):

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
