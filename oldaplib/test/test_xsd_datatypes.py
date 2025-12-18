import base64
import json
import math
import unittest
from datetime import date, datetime, time

import isodate

from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.numeric import Numeric
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapError, OldapErrorType, OldapErrorIndex
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.floatingpoint import FloatingPoint
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_base64binary import Xsd_base64Binary
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_byte import Xsd_byte
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_double import Xsd_double
from oldaplib.src.xsd.xsd_duration import Xsd_duration
from oldaplib.src.xsd.xsd_float import Xsd_float
from oldaplib.src.xsd.xsd_gday import Xsd_gDay
from oldaplib.src.xsd.xsd_gmonth import Xsd_gMonth
from oldaplib.src.xsd.xsd_gmonthday import Xsd_gMonthDay
from oldaplib.src.xsd.xsd_gyear import Xsd_gYear
from oldaplib.src.xsd.xsd_gyearmonth import Xsd_gYearMonth
from oldaplib.src.xsd.xsd_hexbinary import Xsd_hexBinary
from oldaplib.src.xsd.xsd_id import Xsd_ID
from oldaplib.src.xsd.xsd_idref import Xsd_IDREF
from oldaplib.src.xsd.xsd_int import Xsd_int
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_language import Xsd_language
from oldaplib.src.xsd.xsd_long import Xsd_long
from oldaplib.src.xsd.xsd_name import Xsd_Name
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_negativeinteger import Xsd_negativeInteger
from oldaplib.src.xsd.xsd_nmtoken import Xsd_NMTOKEN
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from oldaplib.src.xsd.xsd_nonpositiveinteger import Xsd_nonPositiveInteger
from oldaplib.src.xsd.xsd_normalizedstring import Xsd_normalizedString
from oldaplib.src.xsd.xsd_positiveinteger import Xsd_positiveInteger
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_short import Xsd_short
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.xsd.xsd_time import Xsd_time
from oldaplib.src.xsd.xsd_token import Xsd_token
from oldaplib.src.xsd.xsd_unsignedbyte import Xsd_unsignedByte
from oldaplib.src.xsd.xsd_unsignedint import Xsd_unsignedInt
from oldaplib.src.xsd.xsd_unsignedlong import Xsd_unsignedLong
from oldaplib.src.xsd.xsd_unsignedshort import Xsd_unsignedShort



class TestXsdDatatypes(unittest.TestCase):

    _connection: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://testing.org/datatypes#")
        cls._context.use('test')
        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._connection.clear_graph(Xsd_QName('test:test'))

    @classmethod
    def tearDownClass(cls):
        pass

    def create_triple(self, name: Xsd_NCName | str, value: Xsd):
        if not isinstance(value, Xsd_NCName):
            name = Xsd_NCName(name)
        sparql = self._context.sparql_context
        sparql += f"""
        INSERT DATA {{
            GRAPH test:test {{
                test:{name} test:prop {value.toRdf}
            }}
        }}"""
        self._connection.update_query(sparql)

    def get_triple(self, name: Xsd_NCName) -> Xsd:
        if not isinstance(name, Xsd_NCName):
            name = Xsd_NCName(name)
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

    def delete_triple(self, name: Xsd_NCName):
        sparql = self._context.sparql_context
        sparql += f"""
        DELETE FROM test:test {{
            test:{name} test:prop ?value
        }}
        """

    def test_floating_point(self):
        val = FloatingPoint(3.14159, validate=True)
        fval = float(val)
        self.assertEqual(fval, 3.14159)
        self.assertEqual(str(val), "3.14159")
        self.assertEqual(repr(val), 'FloatingPoint(3.14159)')
        self.assertEqual(val.toRdf, '"3.14159"^^xsd:float')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        val = FloatingPoint("3.14159", validate=True)
        self.assertEqual(fval, 3.14159)

        val = FloatingPoint(3.14159, validate=True)
        valc = FloatingPoint(val)
        self.assertEqual(val2, 3.14159)

        self.assertTrue(val == 3.14159)
        self.assertTrue(val == "3.14159")
        self.assertTrue(val == valc)
        self.assertTrue(val == FloatingPoint(val))
        self.assertFalse(val == None)
        with self.assertRaises(OldapErrorValue):
            self.assertTrue(val == complex(0.0, 1.0))

        valc = FloatingPoint(4.0, validate=True)
        self.assertTrue(val != 4.0)
        self.assertTrue(val != "4.0")
        self.assertTrue(val != valc)
        self.assertTrue(val != FloatingPoint(valc))
        self.assertTrue(val != None)
        with self.assertRaises(OldapErrorValue):
            self.assertTrue(val != complex(0.0, 1.0))

        self.assertTrue(val < 4.0)
        self.assertTrue(val < "4.0")
        self.assertTrue(val < valc)
        self.assertTrue(val < FloatingPoint(valc))
        with self.assertRaises(OldapErrorValue):
            self.assertTrue(val < complex(0.0, 1.0))

        self.assertTrue(val <= 4.0)
        self.assertTrue(val <= "4.0")
        self.assertTrue(val <= valc)
        self.assertTrue(val <= FloatingPoint(valc))
        with self.assertRaises(OldapErrorValue):
            self.assertTrue(val <= complex(0.0, 1.0))

        valc = FloatingPoint(3.0, validate=True)
        self.assertTrue(val > 3.0)
        self.assertTrue(val > "3.0")
        self.assertTrue(val > valc)
        self.assertTrue(val > FloatingPoint(valc))
        with self.assertRaises(OldapErrorValue):
            self.assertTrue(val > complex(0.0, 1.0))

        self.assertTrue(val >= 3.0)
        self.assertTrue(val >= "3.0")
        self.assertTrue(val >= valc)
        self.assertTrue(val >= FloatingPoint(valc))
        with self.assertRaises(OldapErrorValue):
            self.assertTrue(val >= complex(0.0, 1.0))

        val = FloatingPoint('NaN', validate=True)
        self.assertTrue(math.isnan(float(val)))
        self.assertEqual(repr(val), 'FloatingPoint("NaN")')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isnan(val2))

        self.create_triple(Xsd_NCName("FloatingPoint_NaN"), val)
        valx = self.get_triple(Xsd_NCName("FloatingPoint_NaN"))
        self.assertTrue(math.isnan(float(valx)))

        val = FloatingPoint('inf', validate=True)
        self.assertTrue(math.isinf(float(val)) and val > 0.0)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isinf(val2) and val2 > 0.0)

        self.create_triple(Xsd_NCName("FloatingPoint_Inf"), val)
        valx = self.get_triple(Xsd_NCName("FloatingPoint_Inf"))
        self.assertTrue(math.isinf(float(valx)) and valx > 0.0)

        val = FloatingPoint('-inf', validate=True)
        self.assertTrue(math.isinf(float(val)) and val < 0.0)

        self.create_triple(Xsd_NCName("FloatingPoint_minusInf"), val)
        valx = self.get_triple(Xsd_NCName("FloatingPoint_minusInf"))
        self.assertTrue(math.isinf(float(valx)) and valx < 0.0)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(math.isinf(val2) and val2 < 0.0)

        with self.assertRaises(OldapErrorValue):
            val = FloatingPoint("-1. 0", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = FloatingPoint("abcd", validate=True)


    def test_iri(self):
        val = Iri("test:whatiri", validate=True)
        self.assertEqual(str(val), 'test:whatiri')
        self.assertEqual(repr(val), 'Iri("test:whatiri")')
        self.assertEqual(val.toRdf, "test:whatiri")

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple("Iri", val)
        valx = self.get_triple("Iri")
        self.assertEqual(val, valx)

        val = Iri("http://this.is.not/gaga", validate=True)
        self.assertEqual(str(val), 'http://this.is.not/gaga')
        self.assertEqual(repr(val), 'Iri("http://this.is.not/gaga")')
        self.assertEqual(val.toRdf, "<http://this.is.not/gaga>")

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple("Iri2", val)
        valx = self.get_triple("Iri2")
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Iri(25, validate=True)

        val = Iri()
        self.assertTrue(str(val).startswith("urn:"))



    def test_xsd_anyuri(self):
        val = Xsd_anyURI('http://www.org/test', validate=True)
        self.assertEqual(str(val), 'http://www.org/test')
        self.assertEqual(repr(val), 'Xsd_anyURI("http://www.org/test")')
        self.assertEqual(len(val), 19)
        self.assertFalse(val.append_allowed)
        self.assertEqual(val.toRdf, '"http://www.org/test"^^xsd:anyURI')
        self.assertEqual(val.value, 'http://www.org/test')
        nnn = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple("Xsd_anyURI", val)
        valx = self.get_triple("Xsd_anyURI")
        self.assertEqual(val, valx)

        val = Xsd_anyURI('http://www.ch/tescht#', validate=True)
        self.assertTrue(val.append_allowed)

        val1 = Xsd_anyURI('http://www.ch/tescht#', validate=True)
        val2 = Xsd_anyURI('http://www.ch/tescht#', validate=True)
        self.assertEqual(hash(val1), hash(val2))
        with self.assertRaises(OldapErrorValue) as ex:
            val = Xsd_anyURI('waseliwas', validate=True)
        self.assertEqual(str(ex.exception), 'Invalid string "waseliwas" for anyURI (no urn:/http:)')

    def test_xsd_base64binary(self):
        data = base64.b64encode(b'Waseliwas soll den das sein?')
        val = Xsd_base64Binary(data, validate=True)
        self.assertEqual(val.value, data)
        self.assertEqual(str(val), data.decode('utf-8'))
        self.assertEqual(repr(val), f'Xsd_base64Binary(b"{data.decode('utf-8')}")')
        nnn = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple("Xsd_base64Binary", val)
        valx = self.get_triple("Xsd_base64Binary")
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue) as ex:
            val = Xsd_base64Binary(b'Waseliwas soll den das sein?', validate=True)

    def test_xsd_boolean(self):
        val = Xsd_boolean(True, validate=True)
        self.assertTrue(val)
        self.assertEqual(str(val), "true")
        self.assertEqual(repr(val), "Xsd_boolean('true')")
        nnn = None
        self.assertFalse(val == nnn)

        valc = Xsd_boolean(val, validate=True)
        self.assertTrue(valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertTrue(val2)

        self.create_triple(Xsd_NCName("Xsd_booleanTrue"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_booleanTrue"))
        self.assertTrue(valx)

        val = Xsd_boolean('True', validate=True)
        self.assertTrue(val)

        val = Xsd_boolean('yes', validate=True)
        self.assertTrue(val)

        val = Xsd_boolean('t', validate=True)
        self.assertTrue(val)

        val = Xsd_boolean('y', validate=True)
        self.assertTrue(val)

        val = Xsd_boolean('1', validate=True)
        self.assertTrue(val)

        val = Xsd_boolean(1, validate=True)
        self.assertTrue(val)


        val = Xsd_boolean(False, validate=True)
        self.assertFalse(val)
        self.assertEqual(str(val), "false")
        self.assertEqual(repr(val), "Xsd_boolean('false')")

        valc = Xsd_boolean(val, validate=True)
        self.assertFalse(valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertFalse(val2)

        self.create_triple(Xsd_NCName("Xsd_booleanFalse"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_booleanFalse"))
        self.assertFalse(valx)

        val = Xsd_boolean('False', validate=True)
        self.assertFalse(val)

        val = Xsd_boolean('no', validate=True)
        self.assertFalse(val)

        val = Xsd_boolean('f', validate=True)
        self.assertFalse(val)

        val = Xsd_boolean('n', validate=True)
        self.assertFalse(val)

        val = Xsd_boolean('0', validate=True)
        self.assertFalse(val)

        val = Xsd_boolean(0, validate=True)
        self.assertFalse(val)

        with self.assertRaises(OldapError):
            val = Xsd_boolean("True\";SELECT * { ?s ?p ?o}")

    def test_xsd_byte(self):
        val = Xsd_byte(100, validate=True)
        self.assertEqual(str(val), '100')
        self.assertEqual(repr(val), 'Xsd_byte(100)')
        self.assertEqual(int(val), 100)
        nnn: Xsd_byte | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple("Xsd_byte", val)
        valx = self.get_triple("Xsd_byte")
        self.assertEqual(val, valx)

    def test_xsd_date(self):
        val = Xsd_date(2025, 12, 31, validate=True)
        self.assertEqual(str(val), '2025-12-31')
        self.assertEqual(repr(val), 'Xsd_date("2025-12-31")')
        nnn: Xsd_date | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_date(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_date"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_date"))
        self.assertEqual(val, valx)

        val = Xsd_date("2000-12-21", validate=True)
        self.assertEqual(str(val), '2000-12-21')

        val = Xsd_date(date(2000, 12, 21), validate=True)
        self.assertEqual(str(val), '2000-12-21')

        val1 = Xsd_date("2000-12-21", validate=True)
        val2 = Xsd_date("2000-12-24", validate=True)
        self.assertTrue(val1 < val2)
        self.assertTrue(val1 < "2000-12-24")
        self.assertTrue(val1 <= val2)
        self.assertTrue(val1 <= "2000-12-24")
        self.assertTrue(val2 > val1)
        self.assertTrue(val2 > "2000-12-21")
        self.assertTrue(val2 >= val1)
        self.assertTrue(val2 >= "2000-12-21")
        val2 = Xsd_date("2000-12-21", validate=True)
        self.assertTrue(val1 == val2)
        self.assertTrue(val1 == "2000-12-21")

        with self.assertRaises(OldapErrorValue):
            val1 = Xsd_date(42, validate=True)

        val1 = Xsd_date()
        self.assertTrue(val1 == date.today())

    def test_xsd_dateTime(self):
        val = Xsd_dateTime('2001-10-26T21:32:52', validate=True)
        self.assertTrue(str(val), '2001-10-26T21:32:52')
        self.assertTrue(repr(val), 'Xsd_dateTime("2001-10-26T21:32:52")')
        nnn: Xsd_dateTime | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_dateTime(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_dateTime"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_dateTime"))
        self.assertEqual(val, valx)

        val = Xsd_dateTime('2001-10-26T21:32:52+02:00', validate=True)
        self.assertTrue(str(val), '2001-10-26T21:32:52+02:00')
        self.assertTrue(repr(val), '"2001-10-26T21:32:52+02:00"^^xsd:dateTime')

        val = Xsd_dateTime('2001-10-26T19:32:52Z', validate=True)
        self.assertTrue(str(val), '2001-10-26T19:32:52Z')
        self.assertTrue(repr(val), '"2001-10-26T19:32:52Z"^^xsd:dateTime')

        val = Xsd_dateTime('2001-10-26T19:32:52+00:00', validate=True)
        self.assertTrue(str(val), '2001-10-26T19:32:52+00:00')
        self.assertTrue(repr(val), '"2001-10-26T19:32:52+00:00"^^xsd:dateTime')

        val = Xsd_dateTime('2001-10-26T21:32:52.12679', validate=True)
        self.assertTrue(str(val), '2001-10-26T21:32:52.12679')
        self.assertTrue(repr(val), '"2001-10-26T21:32:52.12679"^^xsd:dateTime')

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTime('2001-10-26', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTime('2001-10-26T21:32', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTime('2001-10-26T25:32:52+02:00', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTime('01-10-26T21:32', validate=True)

    def test_xsd_dateTimeStamp(self):
        val = Xsd_dateTimeStamp('2001-10-26T21:32:52Z', validate=True)
        self.assertTrue(str(val), '2001-10-26T21:32:52Z')
        self.assertTrue(repr(val), 'Xsd_dateTimeSTamp("2001-10-26T21:32:52Z")')
        nnn: Xsd_dateTimeStamp | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_dateTimeStamp(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_dateTimeStamp"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_dateTimeStamp"))
        self.assertEqual(val, valx)

        val = Xsd_dateTimeStamp('2001-10-26T21:32:52+02:00', validate=True)
        self.assertTrue(str(val), '2001-10-26T21:32:52+02:00')
        self.assertTrue(repr(val), '"2001-10-26T21:32:52+02:00"^^xsd:dateTimeStamp')

        val = Xsd_dateTimeStamp('2001-10-26T19:32:52Z', validate=True)
        self.assertTrue(str(val), '2001-10-26T19:32:52Z')
        self.assertTrue(repr(val), '"2001-10-26T19:32:52Z"^^xsd:dateTimeStamp')

        val = Xsd_dateTimeStamp('2001-10-26T19:32:52+00:00', validate=True)
        self.assertTrue(str(val), '2001-10-26T19:32:52+00:00')
        self.assertTrue(repr(val), '"2001-10-26T19:32:52+00:00"^^xsd:dateTimeStamp')

        dts = datetime.now()
        val = Xsd_dateTimeStamp(dts)
        self.assertEqual(val, dts)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTimeStamp('2001-10-26T21:32:52.12679', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTime('2001-10-26', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTime('2001-10-26T21:32', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTime('2001-10-26T25:32:52+02:00', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_dateTime('01-10-26T21:32', validate=True)

        with self.assertRaises(OldapErrorValue):
            b = Xsd_dateTimeStamp('2001-10-26T19:32:52+00:00', validate=True) == '2001-10-26T25:32:52+02:00'

    def test_xsd_decimal(self):
        val = Xsd_decimal(3.141592653589793, validate=True)
        self.assertEqual(float(val), 3.141592653589793)
        self.assertEqual(str(val), '3.141592653589793')
        self.assertEqual(repr(val), 'Xsd_decimal(3.141592653589793)')
        self.assertEqual(val.toRdf, '"3.141592653589793"^^xsd:decimal')

        valc = Xsd_decimal(val)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_decimal"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_decimal"))
        self.assertEqual(val, valx)

    def test_xsd_double(self):
        val = Xsd_double(6.62607015e-34, validate=True)
        self.assertEqual(float(val), 6.62607015e-34)
        self.assertEqual(str(val), '6.62607015e-34')
        self.assertEqual(repr(val), 'Xsd_double(6.62607015e-34)')
        nnn: Xsd_double | None = None
        self.assertFalse(val == nnn)

        val = Xsd_double("3.14159", validate=True)
        self.assertEqual(val, 3.14159)

        valc = Xsd_double(val)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_double"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_double"))
        self.assertEqual(val, valx)

    def test_xsd_duration(self):
        val = Xsd_duration('PT2M10S', validate=True)
        self.assertTrue(str(val), 'PT2M10S')
        self.assertTrue(repr(val), '"PT2M10S"^^xsd:duration')
        nnn: Xsd_duration | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_duration(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_duration"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_duration"))
        self.assertEqual(val, valx)

        dt = isodate.parse_duration('PT2M10S')
        val = Xsd_duration(dt, validate=True)
        self.assertEqual(val, dt)
        self.assertTrue(val == dt)

        h = hash(val)

        self.assertTrue(val == 'PT2M10S')

        with self.assertRaises(OldapErrorValue):
            b = val == 'P1M2Y'

        with self.assertRaises(OldapErrorValue):
            val = Xsd_duration('P1M2Y', validate=True)

    def test_xsd_float(self):
        val = Xsd_float(6.62607015e-34, validate=True)
        self.assertEqual(val, 6.62607015e-34)
        self.assertEqual(str(val), '6.62607015e-34')
        self.assertEqual(repr(val), 'Xsd_float(6.62607015e-34)')
        valc = Xsd_float(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_float"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_float"))
        self.assertEqual(val, valx)

    def test_xsd_gDay(self):
        val = Xsd_gDay("---01", validate=True)
        self.assertEqual(str(val), "---01")
        self.assertEqual(repr(val), 'Xsd_gDay("---01")')
        nnn: Xsd_gDay | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_gDay(val)
        self.assertEqual(val, valc)

        val = Xsd_gDay("---01Z", validate=True)
        self.assertEqual(str(val), "---01Z")
        self.assertEqual(repr(val), 'Xsd_gDay("---01Z")')

        val = Xsd_gDay("---01+01:00", validate=True)
        self.assertEqual(str(val), "---01+01:00")
        self.assertEqual(repr(val), 'Xsd_gDay("---01+01:00")')

        val = Xsd_gDay("---21Z", validate=True)
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_gDay"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_gDay"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gDay("--01+01:00", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gDay("--01-", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gDay("---01+01:0", validate=True)

    def test_xsd_gMonth(self):
        val = Xsd_gMonth("--10", validate=True)
        self.assertEqual(str(val), "--10")
        self.assertEqual(repr(val), 'Xsd_gMonth("--10")')
        nnn: Xsd_gMonth | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_gMonth(val)
        self.assertEqual(val, valc)

        val = Xsd_gMonth("--05Z", validate=True)
        self.assertEqual(str(val), "--05Z")
        self.assertEqual(repr(val), 'Xsd_gMonth("--05Z")')

        val = Xsd_gMonth("--01+01:00", validate=True)
        self.assertEqual(str(val), "--01+01:00")
        self.assertEqual(repr(val), 'Xsd_gMonth("--01+01:00")')

        val = Xsd_gMonth("--12Z", validate=True)
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_gMonth"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_gMonth"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gMonth("---01+01:00", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gMonth("--01-", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gMonth("--01+01:0", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gMonth("--13Z", validate=True)

    def test_xsd_gMonthDay(self):
        val = Xsd_gMonthDay("--02-21", validate=True)
        self.assertEqual(str(val), "--02-21")
        self.assertEqual(repr(val), 'Xsd_gMonthDay("--02-21")')
        nnn: Xsd_gMonthDay | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_gMonthDay(val)
        self.assertEqual(val, valc)

        val = Xsd_gMonthDay("--02-21+12:00", validate=True)
        self.assertEqual(str(val), "--02-21+12:00")
        self.assertEqual(repr(val), 'Xsd_gMonthDay("--02-21+12:00")')

        val = Xsd_gMonthDay("--02-21Z", validate=True)
        self.assertEqual(str(val), "--02-21Z")
        self.assertEqual(repr(val), 'Xsd_gMonthDay("--02-21Z")')
        self.assertTrue(val == "--02-21Z")

        val = Xsd_gMonthDay("--02-21Z", validate=True)
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_gMonthDay"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_gMonthDay"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gMonthDay("--02-32Z", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gMonthDay("--13-20", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gMonthDay("-13-20", validate=True)

        val = Xsd_gMonthDay("--02-21Z", validate=True)
        self.assertTrue(val == "--02-21Z")

    def test_xsd_gYear(self):
        val = Xsd_gYear("2020", validate=True)
        self.assertEqual(str(val), "2020")
        self.assertEqual(repr(val), 'Xsd_gYear("2020")')
        nnn: Xsd_gYear | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_gYear(val)
        self.assertEqual(val, valc)

        val = Xsd_gYear("1800Z", validate=True)
        self.assertEqual(str(val), "1800Z")
        self.assertEqual(repr(val), 'Xsd_gYear("1800Z")')

        val = Xsd_gYear("1800-02:00", validate=True)
        self.assertEqual(str(val), "1800-02:00")
        self.assertEqual(repr(val), 'Xsd_gYear("1800-02:00")')

        val = Xsd_gYear("-0003+02:00", validate=True)
        self.assertEqual(str(val), "-0003+02:00")
        self.assertEqual(repr(val), 'Xsd_gYear("-0003+02:00")')
        self.assertTrue(val == "-0003+02:00")

        val = Xsd_gYear("1800-02:00", validate=True)
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_gYear"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_gYear"))
        self.assertEqual(val, valx)

        val = Xsd_gYear(2022, validate=True)
        self.assertEqual(str(val), "2022Z")

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gYear("20-2-22222", validate=True)

    def test_xsd_gYearMonth(self):
        val = Xsd_gYearMonth("2020-03", validate=True)
        self.assertEqual(str(val), "2020-03")
        self.assertEqual(repr(val), 'Xsd_gYearMonth("2020-03")')
        nnn: Xsd_gYearMonth | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_gYearMonth(val)
        self.assertEqual(val, valc)

        val = Xsd_gYearMonth("1800-03Z", validate=True)
        self.assertEqual(str(val), "1800-03Z")
        self.assertEqual(repr(val), 'Xsd_gYearMonth("1800-03Z")')

        val = Xsd_gYearMonth("1800-03-02:00", validate=True)
        self.assertEqual(str(val), "1800-03-02:00")
        self.assertEqual(repr(val), 'Xsd_gYearMonth("1800-03-02:00")')

        val = Xsd_gYearMonth("-0003-03+02:00", validate=True)
        self.assertEqual(str(val), "-0003-03+02:00")
        self.assertEqual(repr(val), 'Xsd_gYearMonth("-0003-03+02:00")')
        self.assertTrue(val == "-0003-03+02:00")

        val = Xsd_gYearMonth("1800-03-02:00", validate=True)
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_gYearMonth"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_gYearMonth"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gYearMonth("2023-13Z", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gYearMonth("2023-00Z", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gYearMonth("2000Z", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_gYearMonth("2000-04\"\n SELECT * {?s ?p ?o } #", validate=True)

    def test_xsd_hexBinary(self):
        val = Xsd_hexBinary("1fab17fa", validate=True)
        self.assertEqual(str(val), "1fab17fa")
        self.assertEqual(repr(val), 'Xsd_hexBinary("1fab17fa")')
        nnn: Xsd_hexBinary | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_hexBinary(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_hexBinary"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_hexBinary"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_hexBinary("1fab17fg", validate=True)

    def test_xsd_ID(self):
        val = Xsd_ID("anchor", validate=True)
        self.assertEqual(str(val), "anchor")
        self.assertEqual(repr(val), 'Xsd_ID("anchor")')
        nnn: Xsd_ID | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_ID(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_ID"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_ID"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_ID("1fab17fg", validate=True)

    def test_xsd_IDREF(self):
        val = Xsd_IDREF("anchor", validate=True)
        self.assertEqual(str(val), "anchor")
        self.assertEqual(repr(val), 'Xsd_IDREF("anchor")')
        nnn: Xsd_IDREF | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_IDREF(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_IDREF"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_IDREF"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_IDREF("1fab17fg", validate=True)

    def test_xsd_int(self):
        val = Xsd_int(505_801, validate=True)
        self.assertEqual(val, 505_801)
        self.assertEqual(str(val), '505801')
        self.assertEqual(repr(val), 'Xsd_int(505801)')
        nnn: Xsd_int | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_int"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_int"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_int(25) == Xsd_int(25))
        self.assertTrue(Xsd_int(25) == 25)

        self.assertTrue(Xsd_int(26) > Xsd_int(25))
        self.assertTrue(Xsd_int(26) > 25)

        self.assertTrue(Xsd_int(25) >= Xsd_int(25))
        self.assertTrue(Xsd_int(25) >= 25)

        self.assertTrue(Xsd_int(25) != Xsd_int(24))
        self.assertTrue(Xsd_int(25) != 24)

        self.assertTrue(Xsd_int(24) < Xsd_int(25))
        self.assertTrue(Xsd_int(24) < 25)

        self.assertTrue(Xsd_int(25) <= Xsd_int(25))
        self.assertTrue(Xsd_int(24) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_int(2_147_483_648, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_int(-2_147_483_649, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_int("abcd", validate=True)

    def test_xsd_integer(self):
        val = Xsd_integer(42, validate=True)
        self.assertEqual(val, 42)
        self.assertEqual(str(val), '42')
        self.assertEqual(repr(val), 'Xsd_integer(42)')
        nnn: Xsd_integer | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_integer"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_integer"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_integer(25) == Xsd_integer(25))
        self.assertTrue(Xsd_integer(25) == 25)

        self.assertTrue(Xsd_integer(26) > Xsd_integer(25))
        self.assertTrue(Xsd_integer(26) > 25)

        self.assertTrue(Xsd_integer(25) >= Xsd_integer(25))
        self.assertTrue(Xsd_integer(25) >= 25)

        self.assertTrue(Xsd_integer(25) != Xsd_integer(24))
        self.assertTrue(Xsd_integer(25) != 24)

        self.assertTrue(Xsd_integer(24) < Xsd_integer(25))
        self.assertTrue(Xsd_integer(24) < 25)

        self.assertTrue(Xsd_integer(25) <= Xsd_integer(25))
        self.assertTrue(Xsd_integer(24) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_integer("was ist 42", validate=True)

    def test_xsd_language(self):
        val = Xsd_language("de", validate=True)
        self.assertEqual(str(val), "de")
        self.assertEqual(repr(val), 'Xsd_language("de")')
        nnn: Xsd_language | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_language(val)
        self.assertEqual(val, valc)

        val = Xsd_language("de-CH", validate=True)
        self.assertEqual(str(val), "de-CH")
        self.assertEqual(repr(val), 'Xsd_language("de-CH")')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_language"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_language"))
        self.assertEqual(val, valx)

        val = Xsd_language(Language.IT)
        self.assertEqual(str(val), "it")

        with self.assertRaises(OldapErrorValue):
            val = Xsd_language("xxx", validate=True)

    def test_xsd_long(self):
        val = Xsd_long(505_801, validate=True)
        self.assertEqual(val, 505_801)
        self.assertEqual(str(val), '505801')
        self.assertEqual(repr(val), 'Xsd_long(505801)')
        nnn: Xsd_long | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_long"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_long"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_long(25) == Xsd_long(25))
        self.assertTrue(Xsd_long(25) == 25)

        self.assertTrue(Xsd_long(26) > Xsd_long(25))
        self.assertTrue(Xsd_long(26) > 25)

        self.assertTrue(Xsd_long(25) >= Xsd_long(25))
        self.assertTrue(Xsd_long(25) >= 25)

        self.assertTrue(Xsd_long(25) != Xsd_long(24))
        self.assertTrue(Xsd_long(25) != 24)

        self.assertTrue(Xsd_long(24) < Xsd_long(25))
        self.assertTrue(Xsd_long(24) < 25)

        self.assertTrue(Xsd_long(25) <= Xsd_long(25))
        self.assertTrue(Xsd_long(24) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_long(9223372036854775808, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_long(-9223372036854775809, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_long("abcd", validate=True)

    def test_xsd_name(self):
        val = Xsd_Name("dies:ist:ein_name12", validate=True)
        self.assertEqual(str(val), "dies:ist:ein_name12")
        self.assertEqual(repr(val), 'Xsd_Name("dies:ist:ein_name12")')
        nnn: Xsd_Name | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_Name"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_Name"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_Name("kühn,dreist", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_Name("01234:56789", validate=True)

    def test_ncname(self):
        ncn1 = Xsd_NCName('AnId0', validate=True)
        self.assertEqual(str(ncn1), 'AnId0')
        self.assertEqual(repr(ncn1), 'Xsd_NCName("AnId0")')
        ncn1a = ncn1 + 'X'
        self.assertEqual(str(ncn1a), 'AnId0X')
        ncn1a += 'Y'
        self.assertEqual(str(ncn1a), 'AnId0XY')
        ncn1b = ncn1 + 'XY'
        self.assertTrue(ncn1a == ncn1b)
        self.assertEqual(hash(ncn1a), hash(ncn1b))
        self.assertFalse(ncn1a != ncn1b)
        with self.assertRaises(OldapErrorValue) as ex:
            ncn2 = Xsd_NCName('0AnId', validate=True)
        self.assertEqual(str(ex.exception), 'Invalid string "0AnId" for NCName')
        with self.assertRaises(OldapErrorValue) as ex:
            ncn3 = Xsd_NCName('An$Id', validate=True)
        self.assertEqual(str(ex.exception), 'Invalid string "An$Id" for NCName')
        with self.assertRaises(OldapErrorValue) as ex:
            ncn4 = Xsd_NCName('An:Id', validate=True)
        self.assertEqual(str(ex.exception), 'Invalid string "An:Id" for NCName')
        with self.assertRaises(OldapErrorValue) as ex:
            ncn5 = Xsd_NCName('An@Id', validate=True)
        self.assertEqual(str(ex.exception), 'Invalid string "An@Id" for NCName')
        nnn: Xsd_NCName | None = None
        self.assertFalse(ncn1 == nnn)

    def test_xsd_negativeInteger(self):
        val = Xsd_negativeInteger(-202_203_204, validate=True)
        self.assertEqual(int(val), -202_203_204)
        self.assertEqual(str(val), '-202203204')
        self.assertEqual(repr(val), 'Xsd_negativeInteger(-202203204)')
        nnn: Xsd_negativeInteger | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_negativeInteger"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_negativeInteger"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_negativeInteger(-25) == Xsd_negativeInteger(-25))
        self.assertTrue(Xsd_negativeInteger(-25) == -25)

        self.assertTrue(Xsd_negativeInteger(-24) > Xsd_negativeInteger(-25))
        self.assertTrue(Xsd_negativeInteger(-24) > -25)

        self.assertTrue(Xsd_negativeInteger(-25) >= Xsd_negativeInteger(-25))
        self.assertTrue(Xsd_negativeInteger(-25) >= -25)

        self.assertTrue(Xsd_negativeInteger(-25) != Xsd_negativeInteger(-24))
        self.assertTrue(Xsd_negativeInteger(-25) != -24)

        self.assertTrue(Xsd_negativeInteger(-25) < Xsd_negativeInteger(-24))
        self.assertTrue(Xsd_negativeInteger(-25) < -24)

        self.assertTrue(Xsd_negativeInteger(-25) <= Xsd_negativeInteger(-25))
        self.assertTrue(Xsd_negativeInteger(-25) <= -25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_negativeInteger(5, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_negativeInteger("abcd<-", validate=True)

    def test_xsd_NMTOKEN(self):
        val = Xsd_NMTOKEN(":ein.Test", validate=True)
        self.assertEqual(str(val), ":ein.Test")
        self.assertEqual(repr(val), 'Xsd_NMTOKEN(":ein.Test")')
        nnn: Xsd_NMTOKEN | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_NMTOKEN"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_NMTOKEN"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_NMTOKEN("$EinTest;", validate=True)

    def test_xsd_nonNegativeInteger(self):
        val = Xsd_nonNegativeInteger(202_203_204, validate=True)
        self.assertEqual(int(val), 202_203_204)
        self.assertEqual(str(val), '202203204')
        self.assertEqual(repr(val), 'Xsd_nonNegativeInteger(202203204)')
        nnn: Xsd_nonNegativeInteger | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_nonNegativeInteger"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_nonNegativeInteger"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_nonNegativeInteger(25) == Xsd_nonNegativeInteger(25))
        self.assertTrue(Xsd_nonNegativeInteger(25) == 25)

        self.assertTrue(Xsd_nonNegativeInteger(26) > Xsd_nonNegativeInteger(25))
        self.assertTrue(Xsd_nonNegativeInteger(26) > 25)

        self.assertTrue(Xsd_nonNegativeInteger(25) >= Xsd_nonNegativeInteger(25))
        self.assertTrue(Xsd_nonNegativeInteger(25) >= 25)

        self.assertTrue(Xsd_nonNegativeInteger(25) != Xsd_nonNegativeInteger(24))
        self.assertTrue(Xsd_nonNegativeInteger(25) != 24)

        self.assertTrue(Xsd_nonNegativeInteger(25) < Xsd_nonNegativeInteger(26))
        self.assertTrue(Xsd_nonNegativeInteger(25) < 26)

        self.assertTrue(Xsd_nonNegativeInteger(25) <= Xsd_nonNegativeInteger(25))
        self.assertTrue(Xsd_nonNegativeInteger(25) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_nonNegativeInteger(-5, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_nonNegativeInteger("abcd", validate=True)

    def test_xsd_nonPositiveInteger(self):
        val = Xsd_nonPositiveInteger(0, validate=True)
        self.assertEqual(int(val), 0)
        nnn: Xsd_nonPositiveInteger | None = None
        self.assertFalse(val == nnn)

        val = Xsd_nonPositiveInteger(-22, validate=True)
        self.assertEqual(int(val), -22)
        self.assertEqual(str(val), '-22')
        self.assertEqual(repr(val), 'Xsd_nonPositiveInteger(-22)')

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_nonPositiveInteger"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_nonPositiveInteger"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_nonPositiveInteger(-25) == Xsd_nonPositiveInteger(-25))
        self.assertTrue(Xsd_nonPositiveInteger(-25) == -25)

        self.assertTrue(Xsd_nonPositiveInteger(-24) > Xsd_nonPositiveInteger(-25))
        self.assertTrue(Xsd_nonPositiveInteger(-24) > -25)

        self.assertTrue(Xsd_nonPositiveInteger(-25) >= Xsd_nonPositiveInteger(-25))
        self.assertTrue(Xsd_nonPositiveInteger(-25) >= -25)

        self.assertTrue(Xsd_nonPositiveInteger(-25) != Xsd_nonPositiveInteger(-24))
        self.assertTrue(Xsd_nonPositiveInteger(-25) != -24)

        self.assertTrue(Xsd_nonPositiveInteger(-25) < Xsd_nonPositiveInteger(-24))
        self.assertTrue(Xsd_nonPositiveInteger(-25) < -24)

        self.assertTrue(Xsd_nonPositiveInteger(-25) <= Xsd_nonPositiveInteger(-25))
        self.assertTrue(Xsd_nonPositiveInteger(-25) <= -25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_nonPositiveInteger(1, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_nonPositiveInteger('minusfortytwo', validate=True)

    def test_xsd_normalizedString(self):
        val = Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen", validate=True)
        self.assertEqual(str(val), "Dies ist ein string mit $onderzeichen\" und anderen Dingen")
        self.assertEqual(repr(val), 'Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen")')
        nnn: Xsd_normalizedString | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_normalizedString(val, validate=True)
        self.assertEqual(val, valc)

        val = Xsd_normalizedString.fromRdf('Dies ist ein string mit $onderzeichen\\" und anderen Dingen')
        self.assertEqual(str(val), "Dies ist ein string mit $onderzeichen\" und anderen Dingen")
        self.assertEqual(repr(val), 'Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen")')

        val = Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen", validate=True)
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_normalizedString"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_normalizedString"))
        self.assertEqual(val, valx)

    def test_xsd_positiveInteger(self):
        val = Xsd_positiveInteger(202_303_404, validate=True)
        self.assertEqual(int(val), 202_303_404)
        self.assertEqual(str(val), '202303404')
        self.assertEqual(repr(val), 'Xsd_positiveInteger(202303404)')
        nnn: Xsd_positiveInteger | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_positiveInteger"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_positiveInteger"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_positiveInteger(25) == Xsd_positiveInteger(25))
        self.assertTrue(Xsd_positiveInteger(25) == 25)

        self.assertTrue(Xsd_positiveInteger(26) > Xsd_positiveInteger(25))
        self.assertTrue(Xsd_positiveInteger(26) > 25)

        self.assertTrue(Xsd_positiveInteger(25) >= Xsd_positiveInteger(25))
        self.assertTrue(Xsd_positiveInteger(25) >= 25)

        self.assertTrue(Xsd_positiveInteger(25) != Xsd_positiveInteger(24))
        self.assertTrue(Xsd_positiveInteger(25) != 24)

        self.assertTrue(Xsd_positiveInteger(25) < Xsd_positiveInteger(26))
        self.assertTrue(Xsd_positiveInteger(25) < 26)

        self.assertTrue(Xsd_positiveInteger(25) <= Xsd_positiveInteger(25))
        self.assertTrue(Xsd_positiveInteger(25) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_positiveInteger(0, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_positiveInteger("abcd", validate=True)

    def test_qname(self):
        qn = Xsd_QName('prefix:name', validate=True)
        self.assertEqual(qn.prefix, 'prefix')
        self.assertEqual(qn.fragment, 'name')
        self.assertEqual(str(qn), 'prefix:name')
        self.assertEqual(len(qn), 11)
        qn2 = qn + 'Shape'
        self.assertEqual(str(qn2), 'prefix:nameShape')
        qn3 = Xsd_QName('prefix', 'name', validate=True)
        self.assertTrue(qn == qn3)
        self.assertEqual(hash(qn), hash(qn3))
        self.assertEqual(repr(qn3), 'Xsd_QName("prefix:name")')
        self.assertTrue(qn != qn2)
        qn += 'Shape'
        self.assertEqual(str(qn), 'prefix:nameShape')
        with self.assertRaises(OldapErrorValue) as ex:
            qn4 = Xsd_QName('2gaga', validate=True)
        self.assertEqual(str(ex.exception), 'Invalid string "2gaga" for QName')
        qn5 = Xsd_QName('xml:double')
        self.assertEqual(str(qn5), 'xml:double')
        with self.assertRaises(OldapErrorValue) as ex:
            qn6 = Xsd_QName('xml:2gaga', validate=True)
        self.assertEqual(str(ex.exception), 'Invalid string "xml:2gaga" for QName. Error: Invalid string "2gaga" for NCName')
        nnn: Xsd_QName | None = None
        self.assertFalse(qn == nnn)

    def test_xsd_short(self):
        val = Xsd_short(-2024, validate=True)
        self.assertEqual(int(val), -2024)
        self.assertEqual(str(val), '-2024')
        self.assertEqual(repr(val), 'Xsd_short(-2024)')
        nnn: Xsd_short | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_short"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_short"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_positiveInteger(25) == Xsd_positiveInteger(25))
        self.assertTrue(Xsd_positiveInteger(25) == 25)

        self.assertTrue(Xsd_positiveInteger(26) > Xsd_positiveInteger(25))
        self.assertTrue(Xsd_positiveInteger(26) > 25)

        self.assertTrue(Xsd_positiveInteger(25) >= Xsd_positiveInteger(25))
        self.assertTrue(Xsd_positiveInteger(25) >= 25)

        self.assertTrue(Xsd_positiveInteger(25) != Xsd_positiveInteger(24))
        self.assertTrue(Xsd_positiveInteger(25) != 24)

        self.assertTrue(Xsd_positiveInteger(25) < Xsd_positiveInteger(26))
        self.assertTrue(Xsd_positiveInteger(25) < 26)

        self.assertTrue(Xsd_positiveInteger(25) <= Xsd_positiveInteger(25))
        self.assertTrue(Xsd_positiveInteger(25) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_short(32768, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_short(-32769, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_short("abcd", validate=True)

    def test_xsd_string(self):
        val = Xsd_string()
        self.assertFalse(val)
        self.assertEqual(len(val), 0)
        self.assertEqual(val, None)
        self.assertEqual(str(val), 'None')
        self.assertEqual(repr(val), 'None')
        self.assertTrue(val == None)
        self.assertFalse(val != None)
        self.assertEqual(hash(val), hash(None))
        with self.assertRaises(OldapErrorIndex):
            c = val[0]
        with self.assertRaises(OldapErrorValue):
            s = val.toRdf

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        val = Xsd_string("", validate=True)
        self.assertFalse(val)

        val = Xsd_string("@fr", validate=True)
        self.assertFalse(val)

        val = Xsd_string("Waseliwas\nsoll <denn> das\" sein?", validate=True)
        self.assertEqual(str(val), "Waseliwas\nsoll <denn> das\" sein?")
        self.assertEqual(repr(val), 'Xsd_string("Waseliwas\nsoll <denn> das\" sein?")')
        self.assertEqual(val.toRdf, '"Waseliwas\\nsoll <denn> das\\\" sein?"^^xsd:string')
        nnn: Xsd_string | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_string(val)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_string"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_string"))
        self.assertEqual(val, valx)

        val = Xsd_string("Waseliwas", "de", validate=True)
        self.assertEqual(str(val), "Waseliwas@de")
        self.assertEqual(repr(val), 'Xsd_string("Waseliwas", "de")')
        self.assertEqual(val.toRdf, '"Waseliwas"@de')
        self.assertEqual(len(val), 9)

        valc = Xsd_string(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_string2"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_string2"))
        self.assertEqual(val, valx)


        val = Xsd_string("Whateliwhat", Language.EN, validate=True)
        self.assertEqual(str(val), "Whateliwhat@en")
        self.assertEqual(repr(val), 'Xsd_string("Whateliwhat", "en")')
        self.assertEqual(val.toRdf, '"Whateliwhat"@en')

        valc = Xsd_string(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_string3"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_string3"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_string("sosdeli@xx", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_string("gaga", "xx", validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_string([], validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_string({}, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_string(set(), validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_string("gaga@xy", validate=True)


    def test_xsd_time(self):
        val = Xsd_time('21:32:52+02:00', validate=True)
        self.assertEqual(str(val), '21:32:52+02:00')
        self.assertEqual(repr(val), 'Xsd_time("21:32:52+02:00")')
        nnn: Xsd_time | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_time(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_time"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_time"))
        self.assertEqual(val, valx)

        val = Xsd_time('19:32:52Z', validate=True)
        self.assertEqual(str(val), '19:32:52+00:00')
        self.assertEqual(repr(val), 'Xsd_time("19:32:52+00:00")')

        val = Xsd_time('19:32:52+00:00', validate=True)
        self.assertEqual(str(val), '19:32:52+00:00')
        self.assertEqual(repr(val), 'Xsd_time("19:32:52+00:00")')

        val = Xsd_time('21:32:52', validate=True)
        self.assertEqual(str(val), '21:32:52')
        self.assertEqual(repr(val), 'Xsd_time("21:32:52")')

        val = Xsd_time('21:32:52.12679', validate=True)
        self.assertEqual(str(val), '21:32:52.126790')
        self.assertEqual(repr(val), 'Xsd_time("21:32:52.126790")')

        h = hash(val)

        t = time.fromisoformat('21:32:52.12679')
        val = Xsd_time(t)
        self.assertEqual(val.value, t)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_time('21:32', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_time('25:25:10', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_time('-10:00:00', validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_time('1:20:10', validate=True)

        with self.assertRaises(OldapErrorValue):
            s = Xsd_time('19:32:52+00:00', validate=True) == '1:20:10'

    def test_xsd_token(self):
        val = Xsd_token("Dies ist ein string mit $onderzeichen und anderen Dingen", validate=True)
        self.assertEqual(str(val), "Dies ist ein string mit $onderzeichen und anderen Dingen")
        self.assertEqual(repr(val), 'Xsd_token("Dies ist ein string mit $onderzeichen und anderen Dingen")')
        nnn: Xsd_token | None = None
        self.assertFalse(val == nnn)

        valc = Xsd_token(val, validate=True)
        self.assertEqual(val, valc)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_token"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_token"))
        self.assertEqual(val, valx)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_token("Dies ist ein string mit $onderzeichen\"\nund anderen Dingen", validate=True)

    def test_xsd_unsignedByte(self):
        val = Xsd_unsignedByte(202, validate=True)
        self.assertEqual(int(val), 202)
        self.assertEqual(str(val), '202')
        self.assertEqual(repr(val), 'Xsd_unsignedByte(202)')
        nnn: Xsd_unsignedByte | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_unsignedByte"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_unsignedByte"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_unsignedByte(25) == Xsd_unsignedByte(25))
        self.assertTrue(Xsd_unsignedByte(25) == 25)

        self.assertTrue(Xsd_unsignedByte(26) > Xsd_unsignedByte(25))
        self.assertTrue(Xsd_unsignedByte(26) > 25)

        self.assertTrue(Xsd_unsignedByte(25) >= Xsd_unsignedByte(25))
        self.assertTrue(Xsd_unsignedByte(25) >= 25)

        self.assertTrue(Xsd_unsignedByte(25) != Xsd_unsignedByte(24))
        self.assertTrue(Xsd_unsignedByte(25) != 24)

        self.assertTrue(Xsd_unsignedByte(25) < Xsd_unsignedByte(26))
        self.assertTrue(Xsd_unsignedByte(25) < 26)

        self.assertTrue(Xsd_unsignedByte(25) <= Xsd_unsignedByte(25))
        self.assertTrue(Xsd_unsignedByte(25) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedByte(-1, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedByte(256, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedByte("abcd", validate=True)

    def test_xsd_unsignedInt(self):
        val = Xsd_unsignedInt(20200, validate=True)
        self.assertEqual(int(val), 20200)
        self.assertEqual(str(val), '20200')
        self.assertEqual(repr(val), 'Xsd_unsignedInt(20200)')
        nnn: Xsd_unsignedInt | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_unsignedInt"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_unsignedInt"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_unsignedInt(25) == Xsd_unsignedInt(25))
        self.assertTrue(Xsd_unsignedInt(25) == 25)

        self.assertTrue(Xsd_unsignedInt(26) > Xsd_unsignedInt(25))
        self.assertTrue(Xsd_unsignedInt(26) > 25)

        self.assertTrue(Xsd_unsignedInt(25) >= Xsd_unsignedInt(25))
        self.assertTrue(Xsd_unsignedInt(25) >= 25)

        self.assertTrue(Xsd_unsignedInt(25) != Xsd_unsignedInt(24))
        self.assertTrue(Xsd_unsignedInt(25) != 24)

        self.assertTrue(Xsd_unsignedInt(25) < Xsd_unsignedInt(26))
        self.assertTrue(Xsd_unsignedInt(25) < 26)

        self.assertTrue(Xsd_unsignedInt(25) <= Xsd_unsignedInt(25))
        self.assertTrue(Xsd_unsignedInt(25) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedInt(-1, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedInt(4294967296, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedInt("abcd", validate=True)

    def test_xsd_unsignedLong(self):
        val = Xsd_unsignedLong(202_203_204, validate=True)
        self.assertEqual(int(val), 202_203_204)
        self.assertEqual(str(val), '202203204')
        self.assertEqual(repr(val), 'Xsd_unsignedLong(202203204)')
        nnn: Xsd_unsignedLong | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_unsignedLong"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_unsignedLong"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_unsignedLong(25) == Xsd_unsignedLong(25))
        self.assertTrue(Xsd_unsignedLong(25) == 25)

        self.assertTrue(Xsd_unsignedLong(26) > Xsd_unsignedLong(25))
        self.assertTrue(Xsd_unsignedLong(26) > 25)

        self.assertTrue(Xsd_unsignedLong(25) >= Xsd_unsignedLong(25))
        self.assertTrue(Xsd_unsignedLong(25) >= 25)

        self.assertTrue(Xsd_unsignedLong(25) != Xsd_unsignedLong(24))
        self.assertTrue(Xsd_unsignedLong(25) != 24)

        self.assertTrue(Xsd_unsignedLong(25) < Xsd_unsignedLong(26))
        self.assertTrue(Xsd_unsignedLong(25) < 26)

        self.assertTrue(Xsd_unsignedInt(25) <= Xsd_unsignedInt(25))
        self.assertTrue(Xsd_unsignedInt(25) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedLong(-1, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedLong(18446744073709551616, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedLong("abcd", validate=True)

    def test_xsd_unsignedShort(self):
        val = Xsd_unsignedShort(20200, validate=True)
        self.assertEqual(int(val), 20200)
        self.assertEqual(str(val), '20200')
        self.assertEqual(repr(val), 'Xsd_unsignedShort(20200)')
        nnn: Xsd_unsignedShort | None = None
        self.assertFalse(val == nnn)

        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

        self.create_triple(Xsd_NCName("Xsd_unsignedShort"), val)
        valx = self.get_triple(Xsd_NCName("Xsd_unsignedShort"))
        self.assertEqual(val, valx)

        self.assertTrue(Xsd_unsignedShort(25) == Xsd_unsignedShort(25))
        self.assertTrue(Xsd_unsignedShort(25) == 25)

        self.assertTrue(Xsd_unsignedShort(26) > Xsd_unsignedShort(25))
        self.assertTrue(Xsd_unsignedShort(26) > 25)

        self.assertTrue(Xsd_unsignedShort(25) >= Xsd_unsignedShort(25))
        self.assertTrue(Xsd_unsignedShort(25) >= 25)

        self.assertTrue(Xsd_unsignedShort(25) != Xsd_unsignedShort(24))
        self.assertTrue(Xsd_unsignedShort(25) != 24)

        self.assertTrue(Xsd_unsignedShort(25) < Xsd_unsignedShort(26))
        self.assertTrue(Xsd_unsignedShort(25) < 26)

        self.assertTrue(Xsd_unsignedShort(25) <= Xsd_unsignedShort(25))
        self.assertTrue(Xsd_unsignedShort(25) <= 25)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedShort(-1, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedShort(65536, validate=True)

        with self.assertRaises(OldapErrorValue):
            val = Xsd_unsignedShort("abcd", validate=True)

    def test_numeric(self):
        n = Numeric(3.14159)
        self.assertTrue(isinstance(n, FloatingPoint))

        n = Numeric("3.14159")
        self.assertTrue(isinstance(n, FloatingPoint))

        n = Numeric(42)
        self.assertTrue(isinstance(n, Xsd_integer))

        n = Numeric("42")
        self.assertTrue(isinstance(n, Xsd_integer))




if __name__ == '__main__':
    unittest.main()
