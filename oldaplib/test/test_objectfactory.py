import base64
import unittest
from pathlib import Path
from time import sleep

from oldaplib.src.ObjectFactory import ResourceInstanceFactory
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
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


def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path

class TestObjectFactory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)
        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(server='http://localhost:7200',
                                     repo="oldap",
                                     userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")
        cls._unpriv = Connection(server='http://localhost:7200',
                                 repo="oldap",
                                 userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")
        cls._context['test'] = 'http://oldap.org/test#'
        cls._context.use('test')

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('oldap:admin'))

        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...

        file = project_root / 'oldaplib' / 'testdata' / 'objectfactory_test.trig'
        cls._connection.upload_turtle(file)

        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(Xsd_QName('oldaplib:admin'))
        #cls._connection.upload_turtle("oldaplib/ontologies/admin.trig")
        #sleep(1)  # upload may take a while...
        pass


    def test_constructor_A(self):
        project = Project.read(con=self._connection, projectIri_SName='test')
        factory = ResourceInstanceFactory(con=self._connection, project=project)
        Book = factory.createObjectInstance('Book')
        b = Book(title="Hitchhiker's Guide to the Galaxy",
                 author=Iri('test:DouglasAdams'),
                 pubDate="1995-09-27")
        self.assertEqual(b.title, "Hitchhiker's Guide to the Galaxy")
        self.assertEqual(b.author, Iri('test:DouglasAdams'))
        self.assertEqual(b.pubDate, "1995-09-27")
        b.create()

        Page = factory.createObjectInstance('Page')
        p1 = Page(pageDesignation="Cover",
                  pageNum=1,
                  pageDescription=LangString("Cover page of book@en", "Vorderseite des Bucheinschlags@de"),
                  pageInBook="test:Hitchhiker")
        self.assertEqual(p1.pageDesignation, "Cover")
        self.assertEqual(p1.pageNum, 1)
        self.assertEqual(p1.pageDescription, LangString("Cover page of book@en", "Vorderseite des Bucheinschlags@de"))
        self.assertEqual(p1.pageInBook, "test:Hitchhiker")

    def test_constructor_B(self):
        factory = ResourceInstanceFactory(con=self._connection, project='test')
        AllTypes = factory.createObjectInstance('AllTypes')
        at = AllTypes(stringProp=Xsd_string("A String Prop"),
                      langStringProp=LangString("A LangString@en", "Ein Sprachtext@de"),
                      booleanProp=Xsd_boolean(1),
                      decimalProp=Xsd_decimal(1.5),
                      floatProp= Xsd_float(1.5),
                      doubleProp=Xsd_double(1.5),
                      durationProp=Xsd_duration('PT2M10S'),
                      dateTimeProp=Xsd_dateTime('2001-10-26T21:32:52'),
                      dateTimeStampProp=Xsd_dateTimeStamp('2001-10-26T21:32:52Z'),
                      timeProp=Xsd_time('21:32:52+02:00'),
                      dateProp=Xsd_date(2025, 12, 31),
                      gYearMonthProp=Xsd_gYearMonth("2020-03"),
                      gYearProp=Xsd_gYear("2020"),
                      gMonthDayProp=Xsd_gMonthDay("--02-21"),
                      gDayProp=Xsd_gDay("---01"),
                      gMonthProp=Xsd_gMonth("--10"),
                      hexBinaryProp=Xsd_hexBinary("1fab17fa"),
                      base64BinaryProp=Xsd_base64Binary(base64.b64encode(b'Waseliwas soll den das sein?')),
                      anyURIProp=Xsd_anyURI('http://www.org/test'),
                      QNameProp=Xsd_QName('prefix:name'),
                      normalizedStringProp=Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen"),
                      tokenProp=Xsd_token("Dies ist ein string mit $onderzeichen und anderen Dingen"),
                      languageProp=Xsd_language("de"),
                      nCNameProp=Xsd_NCName("Xsd_NCName"),
                      nMTOKENProp=Xsd_NMTOKEN(":ein.Test"),
                      iDProp=Xsd_ID("anchor"),
                      iDREFProp=Xsd_IDREF("anchor"),
                      integerProp=Xsd_integer(1),
                      nonPositiveIntegerProp=Xsd_nonPositiveInteger(-22),
                      negativeIntegerProp=Xsd_negativeInteger(-22),
                      longProp=Xsd_long(505_801),
                      intProp=Xsd_int(505_801),
                      shortProp=Xsd_short(-2024),
                      byteProp=Xsd_byte(100),
                      nonNegativeIntegerProp=Xsd_nonNegativeInteger(202_203_204),
                      unsignedLongProp=Xsd_unsignedLong(202_203_204),
                      unsignedIntProp=Xsd_unsignedInt(20200),
                      unsignedShortProp=Xsd_unsignedShort(20200),
                      unsignedByteProp=Xsd_unsignedByte(202),
                      positiveIntegerProp=Xsd_unsignedByte(202))
        at.create()
        self.assertEqual(at.stringProp, Xsd_string("A String Prop"))
        self.assertEqual(at.langStringProp, LangString("A LangString@en", "Ein Sprachtext@de"))
        self.assertEqual(at.booleanProp, Xsd_boolean(1))
        self.assertEqual(at.decimalProp, Xsd_decimal(1.5))
        self.assertEqual(at.floatProp, Xsd_float(1.5))
        self.assertEqual(at.doubleProp, Xsd_double(1.5))
        self.assertEqual(at.durationProp, Xsd_duration('PT2M10S'))
        self.assertEqual(at.dateTimeProp, Xsd_dateTime('2001-10-26T21:32:52'))
        self.assertEqual(at.dateTimeStampProp, Xsd_dateTimeStamp('2001-10-26T21:32:52Z'))
        self.assertEqual(at.timeProp, Xsd_time('21:32:52+02:00'))
        self.assertEqual(at.dateProp, Xsd_date(2025, 12, 31))
        self.assertEqual(at.gYearMonthProp, Xsd_gYearMonth("2020-03"))
        self.assertEqual(at.gYearProp, Xsd_gYear("2020"))
        self.assertEqual(at.gMonthDayProp, Xsd_gMonthDay("--02-21"))
        self.assertEqual(at.gDayProp, Xsd_gDay("---01"))
        self.assertEqual(at.gMonthProp, Xsd_gMonth("--10"))
        self.assertEqual(at.hexBinaryProp, Xsd_hexBinary("1fab17fa"))
        self.assertEqual(at.base64BinaryProp, Xsd_base64Binary(base64.b64encode(b'Waseliwas soll den das sein?')))
        self.assertEqual(at.anyURIProp, Xsd_anyURI('http://www.org/test'))
        self.assertEqual(at.QNameProp, Xsd_QName('prefix:name'))
        self.assertEqual(at.normalizedStringProp, Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen"))
        self.assertEqual(at.tokenProp, Xsd_token("Dies ist ein string mit $onderzeichen und anderen Dingen"))
        self.assertEqual(at.languageProp, Xsd_language("de"))
        self.assertEqual(at.nCNameProp, Xsd_NCName("Xsd_NCName"))
        self.assertEqual(at.nMTOKENProp, Xsd_NMTOKEN(":ein.Test"))
        self.assertEqual(at.iDProp, Xsd_ID("anchor"))
        self.assertEqual(at.iDREFProp, Xsd_IDREF("anchor"))
        self.assertEqual(at.integerProp, Xsd_integer(1))
        self.assertEqual(at.nonPositiveIntegerProp, Xsd_nonPositiveInteger(-22))
        self.assertEqual(at.negativeIntegerProp, Xsd_negativeInteger(-22))
        self.assertEqual(at.longProp, Xsd_long(505_801))
        self.assertEqual(at.intProp, Xsd_int(505_801))
        self.assertEqual(at.shortProp, Xsd_short(-2024))
        self.assertEqual(at.byteProp, Xsd_byte(100))
        self.assertEqual(at.nonNegativeIntegerProp, Xsd_nonNegativeInteger(202_203_204))
        self.assertEqual(at.negativeIntegerProp, Xsd_negativeInteger(-22))
        self.assertEqual(at.longProp, Xsd_long(505_801))
        self.assertEqual(at.intProp, Xsd_int(505_801))
        self.assertEqual(at.shortProp, Xsd_short(-2024))
        self.assertEqual(at.byteProp, Xsd_byte(100))
        self.assertEqual(at.unsignedLongProp, Xsd_unsignedLong(202_203_204))
        self.assertEqual(at.unsignedIntProp, Xsd_unsignedInt(20200))
        self.assertEqual(at.unsignedShortProp, Xsd_unsignedShort(20200))
        self.assertEqual(at.unsignedByteProp, Xsd_unsignedByte(202))
        self.assertEqual(at.positiveIntegerProp, Xsd_positiveInteger(202))


    def test_constructor_C(self):
        factory = ResourceInstanceFactory(con=self._connection, project='test')
        AllTypes = factory.createObjectInstance('AllTypes')
        at = AllTypes(stringProp=Xsd_string("A String Prop"),
                      langStringProp=LangString("A LangString@en", "Ein Sprachtext@de"),
                      booleanProp=True,
                      decimalProp=1.5,
                      floatProp=1.5,
                      doubleProp=1.5,
                      durationProp='PT2M10S',
                      dateTimeProp='2001-10-26T21:32:52',
                      dateTimeStampProp='2001-10-26T21:32:52Z',
                      timeProp='21:32:52+02:00',
                      dateProp="2025-12-31",
                      gYearMonthProp="2020-03",
                      gYearProp="2020",
                      gMonthDayProp="--02-21",
                      gDayProp="---01",
                      gMonthProp="--10",
                      hexBinaryProp="1fab17fa",
                      base64BinaryProp=base64.b64encode(b'Waseliwas soll den das sein?'),
                      anyURIProp='http://www.org/test',
                      QNameProp='prefix:name',
                      normalizedStringProp="Dies ist ein string mit $onderzeichen\" und anderen Dingen",
                      tokenProp="Dies ist ein string mit $onderzeichen und anderen Dingen",
                      languageProp="de",
                      nCNameProp="Xsd_NCName",
                      nMTOKENProp=":ein.Test",
                      iDProp="anchor",
                      iDREFProp="anchor",
                      integerProp=1,
                      nonPositiveIntegerProp=-22,
                      negativeIntegerProp=-22,
                      longProp=505_801,
                      intProp=505_801,
                      shortProp=-2024,
                      byteProp=100,
                      nonNegativeIntegerProp=202_203_204,
                      unsignedLongProp=202_203_204,
                      unsignedIntProp=20200,
                      unsignedShortProp=20200,
                      unsignedByteProp=202,
                      positiveIntegerProp=202)
        self.assertEqual(at.stringProp, Xsd_string("A String Prop"))
        self.assertEqual(at.langStringProp, LangString("A LangString@en", "Ein Sprachtext@de"))
        self.assertEqual(at.booleanProp, Xsd_boolean(1))
        self.assertEqual(at.decimalProp, Xsd_decimal(1.5))
        self.assertEqual(at.floatProp, Xsd_float(1.5))
        self.assertEqual(at.doubleProp, Xsd_double(1.5))
        self.assertEqual(at.durationProp, Xsd_duration('PT2M10S'))
        self.assertEqual(at.dateTimeProp, Xsd_dateTime('2001-10-26T21:32:52'))
        self.assertEqual(at.dateTimeStampProp, Xsd_dateTimeStamp('2001-10-26T21:32:52Z'))
        self.assertEqual(at.timeProp, Xsd_time('21:32:52+02:00'))
        self.assertEqual(at.dateProp, Xsd_date(2025, 12, 31))
        self.assertEqual(at.gYearMonthProp, Xsd_gYearMonth("2020-03"))
        self.assertEqual(at.gYearProp, Xsd_gYear("2020"))
        self.assertEqual(at.gMonthDayProp, Xsd_gMonthDay("--02-21"))
        self.assertEqual(at.gDayProp, Xsd_gDay("---01"))
        self.assertEqual(at.gMonthProp, Xsd_gMonth("--10"))
        self.assertEqual(at.hexBinaryProp, Xsd_hexBinary("1fab17fa"))
        self.assertEqual(at.base64BinaryProp, Xsd_base64Binary(base64.b64encode(b'Waseliwas soll den das sein?')))
        self.assertEqual(at.anyURIProp, Xsd_anyURI('http://www.org/test'))
        self.assertEqual(at.QNameProp, Xsd_QName('prefix:name'))
        self.assertEqual(at.normalizedStringProp, Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen"))
        self.assertEqual(at.tokenProp, Xsd_token("Dies ist ein string mit $onderzeichen und anderen Dingen"))
        self.assertEqual(at.languageProp, Xsd_language("de"))
        self.assertEqual(at.nCNameProp, Xsd_NCName("Xsd_NCName"))
        self.assertEqual(at.nMTOKENProp, Xsd_NMTOKEN(":ein.Test"))
        self.assertEqual(at.iDProp, Xsd_ID("anchor"))
        self.assertEqual(at.iDREFProp, Xsd_IDREF("anchor"))
        self.assertEqual(at.integerProp, Xsd_integer(1))
        self.assertEqual(at.nonPositiveIntegerProp, Xsd_nonPositiveInteger(-22))
        self.assertEqual(at.negativeIntegerProp, Xsd_negativeInteger(-22))
        self.assertEqual(at.longProp, Xsd_long(505_801))
        self.assertEqual(at.intProp, Xsd_int(505_801))
        self.assertEqual(at.shortProp, Xsd_short(-2024))
        self.assertEqual(at.byteProp, Xsd_byte(100))
        self.assertEqual(at.nonNegativeIntegerProp, Xsd_nonNegativeInteger(202_203_204))
        self.assertEqual(at.negativeIntegerProp, Xsd_negativeInteger(-22))
        self.assertEqual(at.longProp, Xsd_long(505_801))
        self.assertEqual(at.intProp, Xsd_int(505_801))
        self.assertEqual(at.shortProp, Xsd_short(-2024))
        self.assertEqual(at.byteProp, Xsd_byte(100))
        self.assertEqual(at.unsignedLongProp, Xsd_unsignedLong(202_203_204))
        self.assertEqual(at.unsignedIntProp, Xsd_unsignedInt(20200))
        self.assertEqual(at.unsignedShortProp, Xsd_unsignedShort(20200))
        self.assertEqual(at.unsignedByteProp, Xsd_unsignedByte(202))
        self.assertEqual(at.positiveIntegerProp, Xsd_positiveInteger(202))

    def test_create_A(self):
        factory = ResourceInstanceFactory(con=self._connection, project='test')



if __name__ == '__main__':
    unittest.main()
