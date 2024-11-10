import base64
import unittest
from pathlib import Path
from pprint import pprint
from time import sleep

from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.connection import Connection
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorValue, OldapErrorNoPermission, OldapErrorInUse
from oldaplib.src.permissionset import PermissionSet
from oldaplib.src.project import Project
from oldaplib.src.user import User
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
                                 userId="unknown",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")
        cls._context['test'] = 'http://oldap.org/test#'
        cls._context.use('test')

        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        cls._connection.clear_graph(Xsd_QName('test:data'))
        cls._connection.clear_graph(Xsd_QName('oldap:admin'))

        file = project_root / 'oldaplib' / 'ontologies' / 'admin.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...

        file = project_root / 'oldaplib' / 'testdata' / 'objectfactory_test.trig'
        cls._connection.upload_turtle(file)

        sleep(1)  # upload may take a while...

        user = User.read(cls._connection, "rosenth")
        user.hasPermissions.add(Iri('oldap:GenericUpdate'))
        user.update()

        ps = PermissionSet(con=cls._connection,
                           permissionSetId="testNoUpdate",
                           label=LangString("testNoUpdate@en"),
                           comment=LangString("Testing PermissionSet@en"),
                           givesPermission=DataPermission.DATA_VIEW,
                           definedByProject="test")
        ps.create()
        cls._tps = ps.read(cls._connection, "testNoUpdate", "test")

        user = User(con=cls._connection,
                    userId=Xsd_NCName("factorytestuser"),
                    familyName="FactoryTest",
                    givenName="FactoryTest",
                    credentials="Waseliwas",
                    inProject={'oldap:Test': {}},
                    hasPermissions={ps.iri.as_qname},
                    isActive=True)
        user.create()
        cls._tuser = User.read(cls._connection, "factorytestuser")


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
                 author=Iri('test:DouglasAdams', validate=False),
                 pubDate="1995-09-27",
                 grantsPermission=Iri('oldap:GenericView'))
        self.assertEqual(b.title, {Xsd_string("Hitchhiker's Guide to the Galaxy")})
        self.assertEqual(b.author, {Iri('test:DouglasAdams')})
        self.assertEqual(b.pubDate, {Xsd_date("1995-09-27")})
        self.assertIsNotNone(b.creationDate)
        self.assertEqual(b.createdBy, Iri('https://orcid.org/0000-0003-1681-4036', validate=False))
        self.assertIsNotNone(b.lastModificationDate)
        self.assertEqual(b.lastModifiedBy, Iri('https://orcid.org/0000-0003-1681-4036', validate=False))
        b.create()
        b2 = Book.read(con=self._connection,
                       project='test',
                       iri=b.iri)
        self.assertEqual(b2.title, b.title)
        self.assertEqual(b2.author, b.author)
        self.assertEqual(b2.pubDate, b.pubDate)
        self.assertEqual(b2.createdBy, b.createdBy)
        self.assertEqual(b2.creationDate, b.creationDate)
        self.assertEqual(b2.lastModifiedBy, b.lastModifiedBy)
        self.assertEqual(b2.lastModificationDate, b.lastModificationDate)

        #
        # test unprivileged access. Should return "not found"-Error!
        #
        with self.assertRaises(OldapErrorNotFound):
            b3 = Book.read(con=self._unpriv, project='test', iri=b.iri)

        Page = factory.createObjectInstance('Page')
        p1 = Page(pageDesignation="Cover",
                  pageNum=1,
                  pageDescription=LangString("Cover page of book@en", "Vorderseite des Bucheinschlags@de"),
                  pageInBook="test:Hitchhiker",
                  grantsPermission=Iri('oldap:GenericView'))
        self.assertEqual(p1.pageDesignation, {"Cover"})
        self.assertEqual(p1.pageNum, {1})
        self.assertEqual(p1.pageDescription, LangString("Cover page of book@en", "Vorderseite des Bucheinschlags@de"))
        self.assertEqual(p1.pageInBook, {"test:Hitchhiker"})
        p1.create()
        p2 = Page.read(con=self._connection, project='test', iri=p1.iri)
        self.assertEqual(p2.pageDesignation, p1.pageDesignation)
        self.assertEqual(p2.pageNum, p1.pageNum)
        self.assertEqual(p2.pageInBook, p1.pageInBook)
        self.assertEqual(p2.createdBy, p1.createdBy)
        self.assertEqual(p2.creationDate, p1.creationDate)
        self.assertEqual(p2.lastModifiedBy, p1.lastModifiedBy)
        self.assertEqual(p2.lastModificationDate, p1.lastModificationDate)

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
                      positiveIntegerProp=Xsd_unsignedByte(202),
                      grantsPermission=Iri('oldap:GenericView'))
        self.assertEqual(at.stringProp, {Xsd_string("A String Prop")})
        self.assertEqual(at.langStringProp, LangString("A LangString@en", "Ein Sprachtext@de"))
        self.assertEqual(at.booleanProp, Xsd_boolean(1))
        self.assertEqual(at.decimalProp, {Xsd_decimal(1.5)})
        self.assertEqual(at.floatProp, {Xsd_float(1.5)})
        self.assertEqual(at.doubleProp, {Xsd_double(1.5)})
        self.assertEqual(at.durationProp, {Xsd_duration('PT2M10S')})
        self.assertEqual(at.dateTimeProp, {Xsd_dateTime('2001-10-26T21:32:52')})
        self.assertEqual(at.dateTimeStampProp, {Xsd_dateTimeStamp('2001-10-26T21:32:52Z')})
        self.assertEqual(at.timeProp, {Xsd_time('21:32:52+02:00')})
        self.assertEqual(at.dateProp, {Xsd_date(2025, 12, 31)})
        self.assertEqual(at.gYearMonthProp, {Xsd_gYearMonth("2020-03")})
        self.assertEqual(at.gYearProp, {Xsd_gYear("2020")})
        self.assertEqual(at.gMonthDayProp, {Xsd_gMonthDay("--02-21")})
        self.assertEqual(at.gDayProp, {Xsd_gDay("---01")})
        self.assertEqual(at.gMonthProp, {Xsd_gMonth("--10")})
        self.assertEqual(at.hexBinaryProp, {Xsd_hexBinary("1fab17fa")})
        self.assertEqual(at.base64BinaryProp, {Xsd_base64Binary(base64.b64encode(b'Waseliwas soll den das sein?'))})
        self.assertEqual(at.anyURIProp, {Xsd_anyURI('http://www.org/test')})
        self.assertEqual(at.QNameProp, {Xsd_QName('prefix:name')})
        self.assertEqual(at.normalizedStringProp,
                         {Xsd_normalizedString("Dies ist ein string mit $onderzeichen\" und anderen Dingen")})
        self.assertEqual(at.tokenProp, {Xsd_token("Dies ist ein string mit $onderzeichen und anderen Dingen")})
        self.assertEqual(at.languageProp, {Xsd_language("de")})
        self.assertEqual(at.nCNameProp, {Xsd_NCName("Xsd_NCName")})
        self.assertEqual(at.nMTOKENProp, {Xsd_NMTOKEN(":ein.Test")})
        self.assertEqual(at.iDProp, {Xsd_ID("anchor")})
        self.assertEqual(at.iDREFProp, {Xsd_IDREF("anchor")})
        self.assertEqual(at.integerProp, {Xsd_integer(1)})
        self.assertEqual(at.nonPositiveIntegerProp, {Xsd_nonPositiveInteger(-22)})
        self.assertEqual(at.negativeIntegerProp, {Xsd_negativeInteger(-22)})
        self.assertEqual(at.longProp, {Xsd_long(505_801)})
        self.assertEqual(at.intProp, {Xsd_int(505_801)})
        self.assertEqual(at.shortProp, {Xsd_short(-2024)})
        self.assertEqual(at.byteProp, {Xsd_byte(100)})
        self.assertEqual(at.nonNegativeIntegerProp, {Xsd_nonNegativeInteger(202_203_204)})
        self.assertEqual(at.negativeIntegerProp, {Xsd_negativeInteger(-22)})
        self.assertEqual(at.longProp, {Xsd_long(505_801)})
        self.assertEqual(at.intProp, {Xsd_int(505_801)})
        self.assertEqual(at.shortProp, {Xsd_short(-2024)})
        self.assertEqual(at.byteProp, {Xsd_byte(100)})
        self.assertEqual(at.unsignedLongProp, {Xsd_unsignedLong(202_203_204)})
        self.assertEqual(at.unsignedIntProp, {Xsd_unsignedInt(20200)})
        self.assertEqual(at.unsignedShortProp, {Xsd_unsignedShort(20200)})
        self.assertEqual(at.unsignedByteProp, {Xsd_unsignedByte(202)})
        self.assertEqual(at.positiveIntegerProp, {Xsd_positiveInteger(202)})
        at.create()
        at2 = AllTypes.read(con=self._connection, project='test', iri=at.iri)
        self.assertEqual(at.stringProp, at2.stringProp)
        self.assertEqual(at.langStringProp, at2.langStringProp)
        self.assertEqual(at.booleanProp, at2.booleanProp)
        self.assertEqual(at.decimalProp, at2.decimalProp)
        self.assertEqual(at.floatProp, at2.floatProp)
        self.assertEqual(at.doubleProp, at2.doubleProp)
        self.assertEqual(at.durationProp, at2.durationProp)
        self.assertEqual(at.dateTimeProp, at2.dateTimeProp)
        self.assertEqual(at.dateTimeStampProp, at2.dateTimeStampProp)
        self.assertEqual(at.timeProp, at2.timeProp)
        self.assertEqual(at.dateProp, at2.dateProp)
        self.assertEqual(at.gYearMonthProp, at2.gYearMonthProp)
        self.assertEqual(at.gYearProp, at2.gYearProp)
        self.assertEqual(at.gMonthDayProp, at2.gMonthDayProp)
        self.assertEqual(at.gDayProp, at2.gDayProp)
        self.assertEqual(at.gMonthProp, at2.gMonthProp)
        self.assertEqual(at.hexBinaryProp, at2.hexBinaryProp)
        self.assertEqual(at.base64BinaryProp, at2.base64BinaryProp)
        self.assertEqual(at.anyURIProp, at2.anyURIProp)
        self.assertEqual(at.QNameProp, at2.QNameProp)
        self.assertEqual(at.normalizedStringProp, at2.normalizedStringProp)
        self.assertEqual(at.languageProp, at2.languageProp)
        self.assertEqual(at.nCNameProp, at2.nCNameProp)
        self.assertEqual(at.nMTOKENProp, at2.nMTOKENProp)
        self.assertEqual(at.iDProp, at2.iDProp)
        self.assertEqual(at.iDREFProp, at2.iDREFProp)
        self.assertEqual(at.integerProp, at2.integerProp)
        self.assertEqual(at.nonPositiveIntegerProp, at2.nonPositiveIntegerProp)
        self.assertEqual(at.negativeIntegerProp, at2.negativeIntegerProp)
        self.assertEqual(at.longProp, at2.longProp)
        self.assertEqual(at.intProp, at2.intProp)
        self.assertEqual(at.shortProp, at2.shortProp)
        self.assertEqual(at.byteProp, at2.byteProp)
        self.assertEqual(at.nonNegativeIntegerProp, at2.nonNegativeIntegerProp)
        self.assertEqual(at.negativeIntegerProp, at2.negativeIntegerProp)
        self.assertEqual(at.longProp, at2.longProp)
        self.assertEqual(at.intProp, at2.intProp)
        self.assertEqual(at.shortProp, at2.shortProp)
        self.assertEqual(at.byteProp, at2.byteProp)
        self.assertEqual(at.unsignedLongProp, at2.unsignedLongProp)
        self.assertEqual(at.unsignedIntProp, at2.unsignedIntProp)
        self.assertEqual(at.unsignedShortProp, at2.unsignedShortProp)
        self.assertEqual(at.unsignedByteProp, at2.unsignedByteProp)
        self.assertEqual(at.positiveIntegerProp, at2.positiveIntegerProp)

    def test_value_setter(self):
        factory = ResourceInstanceFactory(con=self._connection, project='test')
        SetterTester = factory.createObjectInstance('SetterTester')
        obj1 = SetterTester(stringSetter="This is a test string",
                            langStringSetter=LangString("This is a test string@de"),
                            decimalSetter=Xsd_decimal(3.14),
                            integerSetter={20200, 30300},
                            grantsPermission={Iri('oldap:GenericView'), Iri('oldap:GenericUpdate')})
        obj1.create()
        obj2 = SetterTester.read(con=self._connection, project='test', iri=obj1.iri)
        self.assertEqual(obj1.stringSetter, obj2.stringSetter)
        self.assertEqual(obj1.langStringSetter, obj2.langStringSetter)
        self.assertIsNone(obj2.booleanSetter)
        self.assertEqual(obj1.decimalSetter, obj2.decimalSetter)
        self.assertEqual(obj1.integerSetter, obj2.integerSetter)

        #obj3 = SetterTester.read(con=self._connection, project='test', iri=obj1.iri)
        with self.assertRaises(OldapErrorValue):
            obj2.stringSetter = {"This is not a statement!", "One value too much"}
        with self.assertRaises(OldapErrorValue):
            obj2.langStringSetter = LangString("In Deutsch@de", "In Italiano@it")
        with self.assertRaises(OldapErrorValue):
            obj2.decimalSetter = {Xsd_decimal(3.14159), Xsd_decimal(2.71828), Xsd_decimal(1.61803), Xsd_decimal(1.0)}
        with self.assertRaises(OldapErrorValue):
            obj2.decimalSetter = None

        obj2.stringSetter = "This is not a statement!"
        obj2.langStringSetter = LangString("In Deutsch@de", "En Français@fr")
        obj2.booleanSetter = True
        obj2.decimalSetter = {Xsd_decimal(3.14159), Xsd_decimal(2.71828), Xsd_decimal(1.61803)}
        obj2.integerSetter = None
        self.assertEqual(obj2.stringSetter, {"This is not a statement!"})
        self.assertEqual(obj2.langStringSetter, LangString("In Deutsch@de", "En Français@fr"))
        self.assertTrue(obj2.booleanSetter)
        self.assertEqual(obj2.decimalSetter, {Xsd_decimal(3.14159), Xsd_decimal(2.71828), Xsd_decimal(1.61803)})
        self.assertFalse(obj2.integerSetter)

        expected_cs = {
            Iri("test:stringSetter"): AttributeChange(old_value={Xsd_string("This is a test string")}, action=Action.REPLACE),
            Iri("test:decimalSetter"): AttributeChange(old_value={Xsd_decimal(3.14)}, action=Action.REPLACE),
            Iri("test:langStringSetter"): AttributeChange(old_value=LangString("This is a test string@de"), action=Action.REPLACE),
            Iri("test:booleanSetter"): AttributeChange(old_value=None, action=Action.CREATE),
            Iri("test:integerSetter"): AttributeChange(old_value={20200, 30300}, action=Action.DELETE)}
        self.assertEqual(obj2.changeset, expected_cs)

        obj2.update()
        obj2 = SetterTester.read(con=self._connection, project='test', iri=obj1.iri)
        self.assertEqual(obj2.stringSetter, {"This is not a statement!"})
        self.assertEqual(obj2.langStringSetter, LangString("In Deutsch@de", "En Français@fr"))
        self.assertTrue(obj2.booleanSetter)
        self.assertEqual(obj2.decimalSetter, {Xsd_decimal(3.14159), Xsd_decimal(2.71828), Xsd_decimal(1.61803)})
        self.assertFalse(obj2.integerSetter)

    def test_value_modifier(self):
        factory = ResourceInstanceFactory(con=self._connection, project='test')
        SetterTester = factory.createObjectInstance('SetterTester')
        obj1 = SetterTester(stringSetter="This is a test string",
                            langStringSetter=LangString("C'est un teste@fr", "Dies ist eine Test-Zeichenkette@de"),
                            decimalSetter=Xsd_decimal(3.14),
                            integerSetter={-10, 20},
                            booleanSetter=True,
                            grantsPermission={Iri('oldap:GenericView'), Iri('oldap:GenericUpdate')})
        obj1.create()
        obj1 = SetterTester.read(con=self._connection, project='test', iri=obj1.iri)
        obj1.langStringSetter[Language.FR] = "Qu'est-ce que c'est?"
        obj1.integerSetter.add(42)
        obj1.integerSetter.discard(-10)
        obj1.booleanSetter = False
        with self.assertRaises(OldapErrorValue):
            obj1.stringSetter.pop()
        with self.assertRaises(OldapErrorValue):
            del obj1.stringSetter
        obj1.update()
        obj1 = SetterTester.read(con=self._connection, project='test', iri=obj1.iri)
        self.assertEqual(obj1.stringSetter, {"This is a test string"})
        self.assertEqual(obj1.langStringSetter, LangString("Dies ist eine Test-Zeichenkette@de", "Qu'est-ce que c'est?@fr"))
        self.assertEqual(obj1.integerSetter, {Xsd_int(20), Xsd_int(42)})
        self.assertFalse(obj1.booleanSetter)

    def test_value_modifier_norights(self):
        # ps = PermissionSet(con=self._connection,
        #                    permissionSetId="testNoUpdate",
        #                    label=LangString("testNoUpdate@en"),
        #                    comment=LangString("Testing PermissionSet@en"),
        #                    givesPermission=DataPermission.DATA_VIEW,
        #                    definedByProject="test")
        # ps.create()
        #
        # user = User(con=self._connection,
        #             userId=Xsd_NCName("factorytestuser"),
        #             familyName="FactoryTest",
        #             givenName="FactoryTest",
        #             credentials="Waseliwas",
        #             inProject={'oldap:Test': {}},
        #             hasPermissions={ps.iri.as_qname},
        #             isActive=True)
        # user.create()

        factory = ResourceInstanceFactory(con=self._connection, project='test')
        SetterTester = factory.createObjectInstance('SetterTester')
        obj1 = SetterTester(stringSetter="This is a test string",
                            langStringSetter=LangString("C'est un teste@fr", "Dies ist eine Test-Zeichenkette@de"),
                            decimalSetter={Xsd_decimal(3.14159), Xsd_decimal(2.71828), Xsd_decimal(1.61803)},
                            integerSetter={-10, 20},
                            booleanSetter=True,
                            grantsPermission={Iri('oldap:GenericView'), Iri('oldap:GenericUpdate'), self._tps.iri})
        obj1.create()

        unpriv = Connection(server='http://localhost:7200',
                            repo="oldap",
                            userId="factorytestuser",
                            credentials="Waseliwas",
                            context_name="DEFAULT")
        factory = ResourceInstanceFactory(con=unpriv, project='test')
        SetterTester = factory.createObjectInstance('SetterTester')
        obj = SetterTester.read(con=unpriv, project='test', iri=obj1.iri)
        self.assertEqual(obj.stringSetter, {"This is a test string"})
        self.assertEqual(obj.langStringSetter, LangString("C'est un teste@fr", "Dies ist eine Test-Zeichenkette@de"))
        self.assertTrue(obj.booleanSetter)
        self.assertEqual(obj.decimalSetter, {Xsd_decimal(3.14159), Xsd_decimal(2.71828), Xsd_decimal(1.61803)})
        self.assertEqual(obj.integerSetter, {-10, 20})

        obj.decimalSetter.discard(Xsd_decimal(3.14159))
        with self.assertRaises(OldapErrorNoPermission):
            obj.update()

    def test_delete_resource(self):
        project = Project.read(con=self._connection, projectIri_SName='test')
        factory = ResourceInstanceFactory(con=self._connection, project=project)
        Book = factory.createObjectInstance('Book')
        b = Book(title="Hitchhiker's Guide to the Galaxy",
                 author=Iri('test:DouglasAdams', validate=False),
                 pubDate="1995-09-27",
                 grantsPermission=Iri('oldap:GenericView'))
        b.create()
        b = Book.read(con=self._connection,
                       project='test',
                       iri=b.iri)
        Page = factory.createObjectInstance('Page')
        p1 = Page(pageDesignation="Cover",
                  pageNum=1,
                  pageDescription=LangString("Cover page of book@en", "Vorderseite des Bucheinschlags@de"),
                  pageInBook=b.iri,
                  grantsPermission=Iri('oldap:GenericView'))
        p1.create()

        with self.assertRaises(OldapErrorInUse):
            b.delete()

        p1.delete()
        with self.assertRaises(OldapErrorNotFound):
            Page.read(con=self._connection,
                    project='test',
                    iri=p1.iri)
        b.delete()
        with self.assertRaises(OldapErrorNotFound):
            b = Book.read(con=self._connection,
                          project='test',
                          iri=b.iri)

    def test_change_permissions(self):
        project = Project.read(con=self._connection, projectIri_SName='test')

        ps = PermissionSet(con=self._connection,
                           permissionSetId="testChangePermission",
                           label=LangString("testChangePermission@en"),
                           comment=LangString("Testing PermissionSet@en"),
                           givesPermission=DataPermission.DATA_PERMISSIONS,
                           definedByProject="test")
        ps.create()

        factory = ResourceInstanceFactory(con=self._connection, project=project)
        Book = factory.createObjectInstance('Book')

        b = Book(title="Hitchhiker's Guide to the Galaxy",
                 author=Iri('test:DouglasAdams', validate=False),
                 pubDate="1995-09-27",
                 grantsPermission=Iri('oldap:GenericView'))
        b.create()
        b = Book.read(con=self._connection,
                      project='test',
                      iri=b.iri)
        b.grantsPermission.add('hyha:HyperHamletMember')
        b.update()

        unpriv = Connection(server='http://localhost:7200',
                            repo="oldap",
                            userId="factorytestuser",
                            credentials="Waseliwas",
                            context_name="DEFAULT")
        factory = ResourceInstanceFactory(con=unpriv, project=project)
        Book = factory.createObjectInstance('Book')
        b = Book.read(con=self._connection,
                      project='test',
                      iri=b.iri)
        b.grantsPermission.add('oldap:GenericUpdate')
        with self.assertRaises(OldapErrorNoPermission):
            b.update()


if __name__ == '__main__':
    unittest.main()
