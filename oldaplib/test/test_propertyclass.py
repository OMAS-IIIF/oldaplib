import json
import unittest
from copy import deepcopy
from pathlib import Path
from pprint import pprint
from time import sleep

from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.dtypes.rdfset import RdfSet
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.action import Action
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString, LangStringChange
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists, OldapErrorValue, OldapErrorNoPermission, \
    OldapErrorInconsistency
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string


def find_project_root(current_path):
    # Climb up the directory hierarchy and check for a marker file
    path = Path(current_path).absolute()
    while not (path / 'pyproject.toml').exists():
        if path.parent == path:
            # Root of the filesystem, file not found
            raise RuntimeError('Project root not found')
        path = path.parent
    return path


class TestPropertyClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_root = find_project_root(__file__)

        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://oldap.org/test#")
        cls._context.use('test')

        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._unpriv = Connection(userId="fornaro",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")


        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)
        cls._project = Project.read(cls._connection, "test")
        cls._sysproject = Project.read(cls._connection, "oldap")


    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    def test_propertyclass_constructor(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:testprop'),
                          subPropertyOf=Xsd_QName('test:comment'),
                          datatype=XsdDatatypes.string,
                          name=LangString(["Test property@en", "Testprädikat@de"]),
                          description={"A property for testing...@en", "Property für Tests@de"})
        self.assertEqual(p.property_class_iri, Xsd_QName('test:testprop'))
        self.assertEqual(p.get(PropClassAttr.SUBPROPERTY_OF), Iri('test:comment'))
        self.assertEqual(p.get(PropClassAttr.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropClassAttr.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.get(PropClassAttr.DESCRIPTION), LangString("A property for testing...@en", "Property für Tests@de"))
        self.assertEqual(p.get(PropClassAttr.TYPE), {OwlPropertyType.OwlDataProperty})

    def test_star_propertyclass_constructor(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:testpropstar'),
                          type={OwlPropertyType.StatementProperty},
                          datatype=XsdDatatypes.string,
                          name=LangString(["Test property@en", "Testprädikat@de"]),
                          description={"A property for testing...@en", "Property für Tests@de"})
        self.assertEqual(p.property_class_iri, Xsd_QName('test:testpropstar'))
        self.assertTrue(OwlPropertyType.StatementProperty in p.type)
        self.assertEqual(p.get(PropClassAttr.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropClassAttr.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.get(PropClassAttr.DESCRIPTION), LangString("A property for testing...@en", "Property für Tests@de"))
        self.assertEqual(p[PropClassAttr.TYPE], {OwlPropertyType.StatementProperty, OwlPropertyType.OwlDataProperty})

    def test_propertyclass_constructor_owlprop(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isParent'),
                          toClass=Iri('test:Human'),
                          name=LangString(["Parent"]),
                          description={"Parent of the human"})
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChild'),
                          toClass=Iri('test:Human'),
                          inverseOf=Xsd_QName('test:isParent'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        self.assertEqual(i.inverseOf, Xsd_QName('test:isParent'))

    def test_propertyclass_inset_datatypes(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:inset'),
                          subPropertyOf=Xsd_QName('test:comment'),
                          datatype=XsdDatatypes.string,
                          inSet={"AAA", "BBB", "CCC"},
                          name=LangString(["Deepcopy@en", "Tiefekopie@de"]),
                          description=LangString("A test for deepcopy...@"))

    def test_propertyclass_jsonify(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:deepcopy'),
                          subPropertyOf=Xsd_QName('test:comment'),
                          datatype=XsdDatatypes.string,
                          inSet=XsdSet(Xsd_string("AAA"), Xsd_string("BBB"), Xsd_string("CCC")),
                          name=LangString(["Deepcopy@en", "Tiefekopie@de"]),
                          description=LangString("A test for deepcopy...@"))
        p.force_external()
        jsonstr = json.dumps(p, default=serializer.encoder_default, indent=3)
        p2 = json.loads(jsonstr, object_hook=serializer.make_decoder_hook(self._connection))
        self.assertEqual(p2, p)

    def test_propertyclass_deepcopy(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:deepcopy'),
                          subPropertyOf=Xsd_QName('test:comment'),
                          datatype=XsdDatatypes.string,
                          inSet=XsdSet(Xsd_string("AAA"), Xsd_string("BBB"), Xsd_string("CCC")),
                          name=LangString(["Deepcopy@en", "Tiefekopie@de"]),
                          description=LangString("A test for deepcopy...@"))
        p.force_external()
        p2 = deepcopy(p)
        p2.set_notifier(lambda x: x, Iri('test:gaga'))
        self.assertEqual(p._projectIri, p2._projectIri)
        self.assertFalse(p._projectIri is p2._projectIri)
        self.assertEqual(p._projectShortName, p2._projectShortName)
        self.assertFalse(p._projectShortName is p2._projectShortName)
        self.assertEqual(p._graph, p2._graph)
        self.assertFalse(p._graph is p2._graph)
        self.assertEqual(p._property_class_iri, p2._property_class_iri)
        self.assertFalse(p._property_class_iri is p2._property_class_iri)
        self.assertEqual(p._internal, p2._internal)
        self.assertIsNone(p2._internal)
        self.assertEqual(p._force_external, p2._force_external)
        self.assertIsNone(p2.notify(), Iri('test:gaga'))
        self.assertEqual(p.datatype, p2.datatype)
        self.assertEqual(p.name, p2.name)
        self.assertFalse(p.name is p2.name)
        self.assertEqual(p.description, p2.description)
        self.assertFalse(p.description is p2.description)
        self.assertEqual(p.inSet, p2.inSet)
        self.assertFalse(p.inSet is p2.inSet)

    def test_propertyclass_toclass_constructor(self):
        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           toClass=Xsd_QName('test:Person'))
        self.assertEqual(p2.get(PropClassAttr.CLASS), Xsd_QName('test:Person'))
        self.assertEqual(p2.get(PropClassAttr.TYPE), {OwlPropertyType.OwlObjectProperty})

    def test_propertyclass_toclass_constructor_invalid_A(self):
        with self.assertRaises(OldapErrorValue):
            p2 = PropertyClass(con=self._connection,
                               project=self._project,
                               toClass=Xsd_QName('rdf:Person'))

        with self.assertRaises(OldapErrorValue):
            p2 = PropertyClass(con=self._connection,
                               project=self._project,
                               toClass=Xsd_QName('xml:Person'))

    def test_propertyclass_toclass_constructor_invalid_B(self):
        with self.assertRaises(OldapErrorValue):
            p2 = PropertyClass(con=self._connection,
                               project=self._project,
                               toClass=Xsd_QName('gaga:Person'))


    def test_propertyclass_datatype_constructor(self):
        p3 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testprop3'),
                           datatype=XsdDatatypes.string,
                           inSet=RdfSet(Xsd_string('yes'), Xsd_string('may be'), Xsd_string('no')))
        self.assertEqual(p3.property_class_iri, Xsd_QName('test:testprop3'))
        self.assertEqual(p3.get(PropClassAttr.IN), {Xsd_string('yes'), Xsd_string('may be'), Xsd_string('no')})
        self.assertEqual(p3.get(PropClassAttr.DATATYPE), XsdDatatypes.string)

    def test_propertyclass_languagein_constructor(self):
        p4 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testprop4'),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p4.property_class_iri, Xsd_QName('test:testprop4'))
        self.assertEqual(p4.get(PropClassAttr.LANGUAGE_IN), LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p4.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)

        p4a = PropertyClass(con=self._connection,
                            project=self._project,
                            property_class_iri=Xsd_QName('test:testprop4a'),
                            languageIn={'en', 'fr'})
        self.assertEqual(p4a.property_class_iri, Xsd_QName('test:testprop4a'))
        self.assertEqual(p4a.get(PropClassAttr.LANGUAGE_IN), LanguageIn(Language.EN, Language.FR))
        self.assertEqual(p4a.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)

    def test_propertyclass_owltype_constructor(self):
        p4 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testprop4c'),
                           type={OwlPropertyType.SymmetricProperty},
                           datatype=XsdDatatypes.string)
        p4.create()
        self.assertEqual(p4.get(PropClassAttr.TYPE), {OwlPropertyType.SymmetricProperty, OwlPropertyType.OwlDataProperty})
        p4 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testprop4c'),
                                ignore_cache=True)
        self.assertEqual(p4.get(PropClassAttr.TYPE), {OwlPropertyType.SymmetricProperty, OwlPropertyType.OwlDataProperty})

        p4.type.add(OwlPropertyType.TransitiveProperty)
        p4.update()
        self.assertEqual(p4.get(PropClassAttr.TYPE), {OwlPropertyType.SymmetricProperty, OwlPropertyType.TransitiveProperty, OwlPropertyType.OwlDataProperty})

    def test_propertyclass_inconsistent_constructor_A(self):
        with self.assertRaises(OldapErrorValue):
            p5 = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Xsd_QName('test:testprop5a'),
                               datatype=XsdDatatypes.string,
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR))

    def test_propertyclass_inconsistent_constructor_B(self):
        with self.assertRaises(OldapErrorInconsistency):
            p5 = PropertyClass(con=self._connection,
                               project=self._project,
                               type={OwlPropertyType.SymmetricProperty, OwlPropertyType.OwlObjectProperty},
                               property_class_iri=Xsd_QName('test:testprop5b'),
                               datatype=XsdDatatypes.string)

    def test_propertyclass_inconsistent_constructor_C(self):
        with self.assertRaises(OldapErrorInconsistency):
            p5 = PropertyClass(con=self._connection,
                               project=self._project,
                               type={OwlPropertyType.SymmetricProperty, OwlPropertyType.OwlDataProperty},
                               property_class_iri=Xsd_QName('test:testprop5c'),
                               toClass=Xsd_QName('test:comment'))

    def test_propertyclass_invalid_constructor_A(self):
        with self.assertRaises(OldapErrorInconsistency):
            px = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Xsd_QName('test:testpropX'),
                               toClass=Xsd_QName('test:comment'),
                               minLength=42)

    def test_propertyclass_invalid_constructor_B(self):
        px = PropertyClass(con=self._connection,
                           project=self._project,
                           type={OwlPropertyType.SymmetricProperty, OwlPropertyType.FunctionalProperty},
                           property_class_iri=Xsd_QName('test:testpropBa'),
                           toClass=Xsd_QName('test:comment'))
        hp = HasProperty(con=self._connection, project=self._project, prop=px, maxCount=1)

        with self.assertRaises(OldapErrorInconsistency):
            px = PropertyClass(con=self._connection,
                               project=self._project,
                               type={OwlPropertyType.SymmetricProperty, OwlPropertyType.FunctionalProperty},
                               property_class_iri=Xsd_QName('test:testpropBb'),
                               toClass=Xsd_QName('test:comment'))
            hp = HasProperty(con=self._connection, project=self._project, prop=px)

    def test_propertyclass_invalid_constructor_C(self):
        px = PropertyClass(con=self._connection,
                           project=self._project,
                           type={OwlPropertyType.SymmetricProperty, OwlPropertyType.InverseFunctionalProperty},
                           property_class_iri=Xsd_QName('test:testpropC'),
                           toClass=Xsd_QName('test:comment'))
        hp = HasProperty(con=self._connection, project=self._project, prop=px, minCount=1, maxCount=1)

        with self.assertRaises(OldapErrorInconsistency):
            px = PropertyClass(con=self._connection,
                               project=self._project,
                               type={OwlPropertyType.SymmetricProperty, OwlPropertyType.InverseFunctionalProperty},
                               property_class_iri=Xsd_QName('test:testpropC'),
                               toClass=Xsd_QName('test:comment'))
            hp = HasProperty(con=self._connection, project=self._project, prop=px)

    def test_propertyclass_projectsn_constructor(self):
        p6 = PropertyClass(con=self._connection,
                           project="test",
                           property_class_iri=Xsd_QName('test:testprop6'),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p6.property_class_iri, Xsd_QName('test:testprop6'))
        self.assertEqual(p6.get(PropClassAttr.LANGUAGE_IN), LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p6.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)


    def test_propertyclass_read_projectshape(self):
        p = PropertyClass.read(con=self._connection,
                               project=self._sysproject,
                               property_class_iri=Xsd_QName('oldap:namespaceIri'),
                               ignore_cache=True)

    # @unittest.skip('Work in progress')
    def test_propertyclass_read_shacl(self):
        p1 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:comment'),
                                ignore_cache=True)
        self.assertEqual(p1.property_class_iri, Xsd_QName('test:comment'))
        self.assertEqual(p1.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)
        self.assertEqual(p1.datatype, XsdDatatypes.langString)
        self.assertTrue(p1.get(PropClassAttr.UNIQUE_LANG))
        self.assertTrue(p1.uniqueLang)
        self.assertEqual(p1.get(PropClassAttr.NAME), LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1.name, LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(p1.get(PropClassAttr.DESCRIPTION), LangString("This is a test property@de"))
        self.assertEqual(p1.description, LangString("This is a test property@de"))
        self.assertIsNone(p1.get(PropClassAttr.SUBPROPERTY_OF))
        self.assertIsNone(p1.subPropertyOf)
        self.assertEqual(p1.get(PropClassAttr.TYPE), {OwlPropertyType.OwlDataProperty})
        self.assertEqual(p1.type, {OwlPropertyType.OwlDataProperty})
        self.assertEqual(p1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(p1.created, Xsd_dateTime("2023-11-04T12:00:00Z"))

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:test'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:test'))
        self.assertEqual(p2[PropClassAttr.NAME], LangString("Test"))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.string)
        self.assertEqual(p2[PropClassAttr.TYPE], {OwlPropertyType.OwlDataProperty})

        p3 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:enum'),
                                ignore_cache=True)
        self.assertEqual(p3[PropClassAttr.IN],
                         {"very good", "good", "fair", "insufficient"})
        self.assertEqual(p3[PropClassAttr.IN],
                         RdfSet({Xsd_string("very good"), Xsd_string("good"), Xsd_string("fair"), Xsd_string("insufficient")}))

    # @unittest.skip('Work in progress')
    def test_propertyclass_create_A(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testWrite'),
            toClass=Xsd_QName('test:comment'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            inSet=RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"))
        )
        p1.create()
        p1 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testWrite'),
                                ignore_cache=True)
        self.assertEqual(p1.property_class_iri, Xsd_QName('test:testWrite'))
        self.assertEqual(p1[PropClassAttr.CLASS], Xsd_QName('test:comment'))
        self.assertEqual(p1[PropClassAttr.NAME], LangString("Annotations@en"))
        self.assertEqual(p1[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p1[PropClassAttr.IN],
                         RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2")))

    def test_propertyclass_create_B(self):
        p2 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testWrite2'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True)
        )
        p2.create()
        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testWrite2'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:testWrite2'))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.langString)
        self.assertEqual(p2[PropClassAttr.NAME], LangString("Annotations@en"))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropClassAttr.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

    def test_propertyclass_create_C(self):
        p3 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testWrite3'),
            datatype=XsdDatatypes.string,
            pattern=r"^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$"
        )
        p3.create()
        p3 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testWrite3'),
                                ignore_cache=True)
        self.assertEqual(p3.pattern, r"^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$")

    def test_propertyclass_create_D(self):
        pX = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testWriteABC'),
            datatype=XsdDatatypes.int
        )
        pX.create()
        pX = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testWriteABC'),
            datatype=XsdDatatypes.int
        )
        with self.assertRaises(OldapErrorAlreadyExists) as ex:
            pX.create()
        self.assertEqual(str(ex.exception), 'Property "test:testWriteABC" already exists.')

    def test_propertyclass_create_E(self):
        p = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testWriteStar'),
            type={OwlPropertyType.StatementProperty},
            datatype=XsdDatatypes.string,
        )
        p.create()
        p = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testWriteStar'),
                                ignore_cache=True)
        self.assertTrue(OwlPropertyType.StatementProperty in p.type)
        self.assertEqual(p.get(PropClassAttr.DATATYPE), XsdDatatypes.string)

    def test_propertyclass_create_F(self):
        p4 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testpropF'),
                           type={OwlPropertyType.SymmetricProperty},
                           datatype=XsdDatatypes.string)
        p4.create()
        p4 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testpropF'),
                                ignore_cache=True)
        self.assertEqual(p4.get(PropClassAttr.TYPE), {OwlPropertyType.SymmetricProperty, OwlPropertyType.OwlDataProperty})

    def test_propertyclass_create_G(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isParentG'),
                          toClass=Iri('test:Human'),
                          name=LangString(["Parent"]),
                          description={"Parent of the human"})
        p.create()
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChildG'),
                          toClass=Iri('test:Human'),
                          inverseOf=Xsd_QName('test:isParentG'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        self.assertEqual(i.inverseOf, Xsd_QName('test:isParentG'))
        i.create()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChildG'),
                                ignore_cache=True)
        self.assertEqual(i2.get(PropClassAttr.INVERSE_OF), Xsd_QName('test:isParentG'))


    def test_propertyclass_create_nopermission(self):
        p1 = PropertyClass(
            con=self._unpriv,
            project=self._project,
            property_class_iri=Xsd_QName('test:testCreateNoPerm'),
            toClass=Xsd_QName('test:comment'),
            name=LangString("NoPerm@en"),
            description=LangString("NoPerm@en")
        )
        with self.assertRaises(OldapErrorNoPermission) as ex:
            p1.create()
        self.assertEqual(str(ex.exception), 'Actor has no ADMIN_MODEL permission for project "oldap:Test"')

    def test_property_cache(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testCache'),
            toClass=Xsd_QName('test:comment'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            inSet=RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"))
        )
        p1.create()
        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testCache'))
        self.assertFalse(p1 is p2)
        self.assertEqual(p1.property_class_iri, p2.property_class_iri)
        self.assertEqual(p1.toClass, p2.toClass)
        self.assertEqual(p1.name, p2.name)
        self.assertEqual(p1.description, p2.description)
        self.assertEqual(p1.inSet, p2.inSet)

        p2.name.add("Annotation@de")
        self.assertEqual(p2.changeset, {PropClassAttr.NAME: AttributeChange(old_value=None, action=Action.MODIFY)})
        self.assertEqual(p2.name.changeset, {Language.DE: LangStringChange(old_value=None, action=Action.CREATE)})

    # @unittest.skip('Work in progress')
    def test_propertyclass_undo(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testUndo'),
            datatype=XsdDatatypes.langString,
            name=LangString(["Annotations@en", "Annotationen@de"]),
            languageIn=LanguageIn(Language.EN, Language.DE),
            uniqueLang=Xsd_boolean(True),
            pattern=Xsd_string('*.'),
        )
        self.assertEqual(p1.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE))
        self.assertTrue(p1[PropClassAttr.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.PATTERN], '*.')

        p1[PropClassAttr.NAME][Language.FR] = "Annotations en Français"
        del p1[PropClassAttr.NAME][Language.EN]
        p1[PropClassAttr.DESCRIPTION] = LangString("A description@en")
        p1[PropClassAttr.LANGUAGE_IN] = LanguageIn(Language.EN, Language.DE, Language.FR)

        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotationen@de", "Annotations en Français@fr"]))
        self.assertEqual(p1[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertTrue(p1[PropClassAttr.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.PATTERN], Xsd_string('*.'))
        p1.undo()
        self.assertEqual(p1[PropClassAttr.DATATYPE], XsdDatatypes.langString)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE))
        self.assertTrue(p1[PropClassAttr.UNIQUE_LANG])
        self.assertEqual(p1[PropClassAttr.PATTERN], Xsd_string('*.'))

        p1[PropClassAttr.NAME][Language.FR] = "Annotations en Français"
        del p1[PropClassAttr.NAME][Language.EN]
        p1[PropClassAttr.DESCRIPTION] = LangString("A description@en")
        p1[PropClassAttr.LANGUAGE_IN] = LanguageIn(Language.EN, Language.DE, Language.FR)

        p1.undo(PropClassAttr.NAME)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        p1.undo(PropClassAttr.DESCRIPTION)
        self.assertIsNone(p1.get(PropClassAttr.DESCRIPTION))
        p1.undo(PropClassAttr.LANGUAGE_IN)
        self.assertEqual(p1[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE))
        self.assertEqual(p1.changeset, {})

        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testUndo'),
            toClass=Xsd_QName('test:TestObject'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            inSet=XsdSet(Iri("http://www.test.org/comment1"),
                         Iri("http://www.test.org/comment2"),
                         Iri("http://www.test.org/comment3")))
        self.assertEqual(p1.get(PropClassAttr.CLASS), Xsd_QName('test:TestObject'))
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropClassAttr.IN],
                         XsdSet(Iri("http://www.test.org/comment1"),
                                Iri("http://www.test.org/comment2"),
                                Iri("http://www.test.org/comment3")))

        p1[PropClassAttr.NAME][Language.FR] = "Annotations en Français"
        del p1[PropClassAttr.NAME][Language.EN]
        p1[PropClassAttr.DESCRIPTION] = LangString("A description@en")
        p1[PropClassAttr.IN] = {"http://google.com", "https://google.com"}
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotationen@de", "Annotations en Français@fr"]))
        self.assertEqual(p1[PropClassAttr.IN], XsdSet(Iri("http://google.com"), Iri("https://google.com")))
        p1.undo()
        self.assertEqual(p1.get(PropClassAttr.CLASS), Xsd_QName('test:TestObject'))
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p1[PropClassAttr.IN],
                         XsdSet(Iri("http://www.test.org/comment1"),
                                Iri("http://www.test.org/comment2"),
                                Iri("http://www.test.org/comment3")))

        p1[PropClassAttr.NAME][Language.FR] = "Annotations en Français"
        del p1[PropClassAttr.NAME][Language.EN]
        p1[PropClassAttr.DESCRIPTION] = LangString("A description@en")
        p1[PropClassAttr.IN] = RdfSet(Iri("https://gaga.com"), Iri("https://gugus.com"))

        p1.undo(PropClassAttr.NAME)
        self.assertEqual(p1[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        p1.undo(PropClassAttr.DESCRIPTION)
        self.assertIsNone(p1.get(PropClassAttr.DESCRIPTION))
        p1.undo(PropClassAttr.IN)
        self.assertEqual(p1[PropClassAttr.IN], RdfSet(Iri("http://www.test.org/comment1"),
                                Iri("http://www.test.org/comment2"),
                                Iri("http://www.test.org/comment3")))
        self.assertEqual(p1.changeset, {})


        p1 = PropertyClass(
            con=self._connection,
            #graph=Xsd_NCName('test'),
            project=self._project,
            property_class_iri=Xsd_QName('test:testUndo'),
            toClass=Xsd_QName('test:testUndo42'),
            inSet={'test:testUndo42', 'test:UP4014'}
        )
        p1.toClass = Xsd_QName('test:UP4014')
        p1.inSet.add('test:RGW168')
        self.assertEqual(p1.toClass, Xsd_QName('test:UP4014'))
        self.assertEqual(p1.inSet, {'test:testUndo42', 'test:UP4014', 'test:RGW168'})
        p1.undo()
        self.assertEqual(p1.toClass, Xsd_QName('test:testUndo42'))
        self.assertEqual(p1.inSet, {'test:testUndo42', 'test:UP4014'})


    # @unittest.skip('Work in progress')
    def test_propertyclass_update_01(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testUpdate'),
            subPropertyOf=Xsd_QName('test:masterProp'),
            datatype=XsdDatatypes.langString,
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True)
        )
        p1.create()

        p1[PropClassAttr.SUBPROPERTY_OF] = Xsd_QName('test:masterProp2')
        p1[PropClassAttr.NAME][Language.DE] = 'Annotationen'
        p1[PropClassAttr.UNIQUE_LANG] = Xsd_boolean(False)
        p1[PropClassAttr.IN] = RdfSet(Xsd_string("gaga"), Xsd_string("is was"))
        self.maxDiff = None
        self.assertEqual(p1.changeset, {
            PropClassAttr.NAME: AttributeChange(None, Action.MODIFY),
            # PropClassAttr.LANGUAGE_IN: PropClassAttrChange(LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT), Action.REPLACE, True),
            PropClassAttr.SUBPROPERTY_OF: AttributeChange(Xsd_QName('test:masterProp'), Action.REPLACE),
            PropClassAttr.UNIQUE_LANG: AttributeChange(Xsd_boolean(True), Action.REPLACE),
            PropClassAttr.IN: AttributeChange(None, Action.CREATE),
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testUpdate'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:testUpdate'))
        self.assertEqual(p2.subPropertyOf, Xsd_QName('test:masterProp2'))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.langString)
        self.assertIsNone(p2.get(PropClassAttr.CLASS))
        self.assertEqual(p2[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(p2[PropClassAttr.IN], RdfSet(Xsd_string("gaga"), Xsd_string("is was")))
        self.assertFalse(p2[PropClassAttr.UNIQUE_LANG])

    # @unittest.skip('Work in progress')
    def test_propertyclass_update_02(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testUpdate2'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            datatype=XsdDatatypes.langString,
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True)
        )
        p1.create()
        p1.name[Language.DE] = 'Annotationen'
        p1.languageIn.add(Language.ZU)
        p1.uniqueLang = Xsd_boolean(False)
        p1.inSet = RdfSet(Xsd_string("gaga"), Xsd_string("is was"))
        self.maxDiff = None
        self.assertEqual(p1.changeset, {
            PropClassAttr.NAME: AttributeChange(None, Action.MODIFY),
            PropClassAttr.LANGUAGE_IN: AttributeChange(LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT), Action.REPLACE),
            PropClassAttr.UNIQUE_LANG: AttributeChange(Xsd_boolean(True), Action.REPLACE),
            PropClassAttr.IN: AttributeChange(None, Action.CREATE),
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                #graph=Xsd_NCName('test'),
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testUpdate2'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:testUpdate2'))
        self.assertEqual(p2.datatype, XsdDatatypes.langString)
        self.assertIsNone(p2.toClass)
        self.assertEqual(p2.name, LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2.description, LangString("An annotation@en"))
        self.assertEqual(p2.languageIn,
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT, Language.ZU))
        self.assertEqual(p2.inSet, RdfSet(Xsd_string("gaga"), Xsd_string("is was")))
        self.assertFalse(p2.uniqueLang)

    def test_propertyclass_update_03(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testUpdate3'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            datatype=XsdDatatypes.langString,
            minLength=Xsd_integer(2),
            maxLength=Xsd_integer(10),
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True)
        )
        p1.create()

        p1 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testUpdate3'),
                                ignore_cache=True)
        self.assertEqual(p1.property_class_iri, Xsd_QName('test:testUpdate3'))
        self.assertEqual(p1.datatype, XsdDatatypes.langString)
        self.assertEqual(p1.minLength, 2)
        self.assertEqual(p1.maxLength, 10)
        self.assertEqual(p1.languageIn, LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertTrue(p1.uniqueLang)
        self.assertIsNone(p1.toClass)
        self.assertEqual(p1.name, LangString(["Annotations@en"]))
        self.assertEqual(p1.description, LangString("An annotation@en"))

        p1.toClass = Iri('test:masterProp3')
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testUpdate3'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Xsd_QName('test:testUpdate3'))
        self.assertIsNone(p2.datatype)
        self.assertEqual(p2.toClass, Xsd_QName('test:masterProp3'))
        self.assertEqual(p2.name, LangString(["Annotations@en"]))
        self.assertEqual(p2.description, LangString("An annotation@en"))
        self.assertIsNone(p2.languageIn)
        self.assertIsNone(p2.uniqueLang)

    def test_propertyclass_update_04(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testUpdate4'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            toClass=Xsd_QName('test:masterProp4')
        )
        p1.create()

        p1 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testUpdate4'),
                                ignore_cache=True)
        p1.datatype = XsdDatatypes.string
        p1.maxLength = 100
        p1.pattern = '.*'
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testUpdate4'),
                                ignore_cache=True)
        self.assertEqual(p2.datatype, XsdDatatypes.string)
        self.assertEqual(p2.maxLength, 100)
        self.assertEqual(p2.pattern, '.*')
        self.assertIsNone(p2.toClass)
        self.assertEqual(p2.name, LangString(["Annotations@en"]))
        self.assertEqual(p2.description, LangString("An annotation@en"))


    def test_propertyclass_update_05(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testUpdate5'),
            datatype=XsdDatatypes.string,
            name=LangString(["name english@en", "nom français@fr"]),
            description=LangString("description english@en", "description français@fr"),
        )
        p1.create()

        p1 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testUpdate5'),
                                ignore_cache=True)
        p1.name[Language.DE] = "name deutsch"
        p1.description[Language.DE] = "description deutsch"
        p1.update()

        sparql = self._context.sparql_context
        sparql += """
        SELECT ?label
        FROM test:onto
        WHERE {{
            test:testUpdate5 rdfs:label ?label .
        }}
        """
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        for r in res:
            self.assertIn(r['label'], [Xsd_string("name english@en"),
                                       Xsd_string("nom français@fr"),
                                       Xsd_string("name deutsch@de")])

    def test_propertyclass_update_06(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testUpdate6'),
            datatype=XsdDatatypes.string,
            name=LangString(["name english@en", "nom français@fr"]),
        )
        p1.create()
        p1.description = LangString("description english@en", "description français@fr")
        del p1.name
        p1.update()

        p1 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testUpdate6'),
                                ignore_cache=True)

        #
        # test if all rdfs:label have been deleted!
        #
        sparql = self._context.sparql_context
        sparql += """
        SELECT ?label
        FROM test:onto
        WHERE {{
            test:testUpdate6 rdfs:label ?label .
        }}
        """
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

        #
        # test if the new rdfs:comments have been added
        #
        sparql = self._context.sparql_context
        sparql += """
        SELECT ?comment
        FROM test:onto
        WHERE {{
            test:testUpdate6 rdfs:comment ?comment .
        }}
        """
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 2)
        for r in res:
            self.assertIn(r['comment'], [Xsd_string("description english@en"), Xsd_string("description français@fr")])

    def test_propertyclass_update_07(self):
        p7 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testprop7'),
                           type={OwlPropertyType.SymmetricProperty},
                           datatype=XsdDatatypes.string)
        p7.create()
        p7 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testprop7'),
                                ignore_cache=True)
        p7.type.add(OwlPropertyType.TransitiveProperty)
        p7.update()
        p7 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testprop7'),
                                ignore_cache=True)
        self.assertEqual(p7.get(PropClassAttr.TYPE), {OwlPropertyType.SymmetricProperty, OwlPropertyType.TransitiveProperty, OwlPropertyType.OwlDataProperty})

    def test_propertyclass_update_08(self):
        p8 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Xsd_QName('test:testprop8'),
                           type={OwlPropertyType.SymmetricProperty, OwlPropertyType.TransitiveProperty},
                           datatype=XsdDatatypes.string)
        p8.create()
        p8 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testprop8'),
                                ignore_cache=True)
        p8.type.remove(OwlPropertyType.TransitiveProperty)
        p8.update()
        p8 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testprop8'),
                                ignore_cache=True)
        self.assertEqual(p8.get(PropClassAttr.TYPE), {OwlPropertyType.SymmetricProperty, OwlPropertyType.OwlDataProperty})

    def test_propertyclass_update_09(self):
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChild9'),
                          toClass=Iri('test:Human'),
                          inverseOf=Xsd_QName('test:isParent9'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        self.assertEqual(i.inverseOf, Xsd_QName('test:isParent9'))
        i.create()
        i.inverseOf = Xsd_QName('test:anotherParent')
        i.update()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChild9'),
                                ignore_cache=True)
        self.assertEqual(i2.get(PropClassAttr.INVERSE_OF), Xsd_QName('test:anotherParent'))

    def test_propertyclass_update_10(self):
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChild10'),
                          toClass=Iri('test:Human'),
                          inverseOf=Xsd_QName('test:isParent10'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        i.create()
        i.type = {OwlPropertyType.FunctionalProperty, OwlPropertyType.SymmetricProperty}
        i.update()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChild10'),
                                ignore_cache=True)
        self.assertTrue({OwlPropertyType.FunctionalProperty} <= set(i2.type))

    def test_propertyclass_update_11(self):
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChild11'),
                          type={OwlPropertyType.FunctionalProperty, OwlPropertyType.StatementProperty, OwlPropertyType.TransitiveProperty},
                          toClass=Iri('test:Human'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        i.create()
        i.type.discard(OwlPropertyType.FunctionalProperty)
        i.update()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChild11'),
                                ignore_cache=True)
        self.assertTrue({OwlPropertyType.StatementProperty, OwlPropertyType.TransitiveProperty} <= set(i2.type))
        self.assertTrue(OwlPropertyType.FunctionalProperty not in i2.type)

    def test_propertyclass_update_12(self):
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChild12'),
                          type={OwlPropertyType.FunctionalProperty, OwlPropertyType.TransitiveProperty},
                          toClass=Iri('test:Human'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        i.create()
        i.type.add(OwlPropertyType.StatementProperty)
        i.update()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChild12'),
                                ignore_cache=True)
        self.assertTrue({OwlPropertyType.StatementProperty, OwlPropertyType.FunctionalProperty, OwlPropertyType.TransitiveProperty} <= set(i2.type))

    def test_propertyclass_update_13(self):
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChild13'),
                          type={OwlPropertyType.StatementProperty},
                          toClass=Iri('test:Human'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        i.create()
        i.type.discard(OwlPropertyType.StatementProperty)
        i.update()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChild13'),
                                ignore_cache=True)
        self.assertTrue(OwlPropertyType.StatementProperty not in set(i2.type))

    def test_propertyclass_update_14(self):
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChild14'),
                          type={OwlPropertyType.StatementProperty},
                          toClass=Iri('test:Human'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        i.create()
        i.type = None
        i.update()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChild14'),
                                ignore_cache=True)
        self.assertTrue(OwlPropertyType.StatementProperty not in set(i2.type))

    def test_propertyclass_update_15(self):
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChild15'),
                          type={OwlPropertyType.StatementProperty},
                          toClass=Iri('test:Human'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        i.create()
        del i.type
        i.update()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChild15'),
                                ignore_cache=True)
        self.assertTrue(OwlPropertyType.StatementProperty not in set(i2.type))

    # @unittest.skip('Work in progress')
    def test_propertyclass_delete_attrs(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testDelete'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
            uniqueLang=Xsd_boolean(True),
            inSet=RdfSet(Xsd_string('A'), Xsd_string('B'), Xsd_string('C'))
        )
        p1.create()
        del p1[PropClassAttr.NAME]
        del p1[PropClassAttr.UNIQUE_LANG]
        del p1[PropClassAttr.LANGUAGE_IN]
        del p1[PropClassAttr.IN]
        p1.update()

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testDelete'),
                                ignore_cache=True)
        self.assertIsNone(p2.name)
        self.assertIsNone(p2.uniqueLang)
        self.assertIsNone(p2.languageIn)
        self.assertIsNone(p2.inSet)
        cstr = self._context.sparql_context
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "zu" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "cy" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "sv" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "rm" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "A" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

    def test_propertyclass_delete_owlattr(self):
        i = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Xsd_QName('test:isChildDel'),
                          toClass=Iri('test:Human'),
                          inverseOf=Xsd_QName('test:isParentDel'),
                          name=LangString(["Child"]),
                          description={"Child of the human"})
        i.create()
        i.inverseOf = None
        i.update()
        i2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:isChildDel'),
                                ignore_cache=True)
        self.assertIsNone(i2.get(PropClassAttr.INVERSE_OF))

    # @unittest.skip('Work in progress')
    def test_propertyclass_delete(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testDeleteIt'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
            uniqueLang=Xsd_boolean(True)
        )
        p1.create()

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testDeleteIt'),
                                ignore_cache=True)
        p2.delete()
        sparql = self._context.sparql_context
        sparql += 'SELECT ?p ?o WHERE { test:testDeleteIt ?p ?o }'
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

        cstr = self._context.sparql_context
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "zu" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "cy" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "sv" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "rm" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testDeleteIt2'),
            toClass=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            inSet=XsdSet(Iri('test:gaga1'), Iri('test:gaga2'), Iri('test:gaga3'))
        )
        p1.create()

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Xsd_QName('test:testDeleteIt2'),
                                ignore_cache=True)
        p2.delete()
        sparql = self._context.sparql_context
        sparql += 'SELECT ?p ?o WHERE { test:testDeleteIt2 ?p ?o }'
        jsonres = self._connection.query(sparql)
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        cstr = self._context.sparql_context
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p test:gaga1 . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p test:gaga2 . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p test:gaga3 . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)
        jsonres = self._connection.query(cstr + 'SELECT ?s ?p ?o WHERE { ?s ?p "rm" . ?s ?p ?o}')
        res = QueryProcessor(self._context, jsonres)
        self.assertEqual(len(res), 0)

    # @unittest.skip('Work in progress')
    def test_write_trig(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Xsd_QName('test:testWriteIt'),
            toClass=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
        )
        p1.write_as_trig('propclass_test.trig')


if __name__ == '__main__':
    unittest.main()
