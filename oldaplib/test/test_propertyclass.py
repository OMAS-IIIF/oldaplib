import unittest
from copy import deepcopy
from pathlib import Path
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
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists, OldapErrorValue, OldapErrorNoPermission
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
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


        cls._connection.clear_graph(Xsd_QName('test:shacl'))
        cls._connection.clear_graph(Xsd_QName('test:onto'))
        file = project_root / 'oldaplib' / 'testdata' / 'connection_test.trig'
        cls._connection.upload_turtle(file)
        sleep(1)  # upload may take a while...
        cls._project = Project.read(cls._connection, "test")

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    def test_propertyclass_constructor(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Iri('test:testprop'),
                          subPropertyOf=Iri('test:comment'),
                          datatype=XsdDatatypes.string,
                          name=LangString(["Test property@en", "Testprädikat@de"]),
                          description={"A property for testing...@en", "Property für Tests@de"})
        self.assertEqual(p.property_class_iri, Iri('test:testprop'))
        self.assertEqual(p.get(PropClassAttr.SUBPROPERTY_OF), Iri('test:comment'))
        self.assertEqual(p.get(PropClassAttr.DATATYPE), XsdDatatypes.string)
        self.assertEqual(p.get(PropClassAttr.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(p.get(PropClassAttr.DESCRIPTION), LangString("A property for testing...@en", "Property für Tests@de"))

    def test_propertyclass_inset_datatypes(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Iri('test:inset'),
                          subPropertyOf=Iri('test:comment'),
                          datatype=XsdDatatypes.string,
                          inSet={"AAA", "BBB", "CCC"},
                          name=LangString(["Deepcopy@en", "Tiefekopie@de"]),
                          description=LangString("A test for deepcopy...@"))


    def test_propertyclass_deepcopy(self):
        p = PropertyClass(con=self._connection,
                          project=self._project,
                          property_class_iri=Iri('test:deepcopy'),
                          subPropertyOf=Iri('test:comment'),
                          datatype=XsdDatatypes.string,
                          inSet=XsdSet(Xsd_string("AAA"), Xsd_string("BBB"), Xsd_string("CCC")),
                          name=LangString(["Deepcopy@en", "Tiefekopie@de"]),
                          description=LangString("A test for deepcopy...@"))
        p.force_external()
        p2 = deepcopy(p)
        p2.set_notifier(lambda x: x, Iri('test:gaga'))
        self.assertEqual(p._project.projectIri, p2._project.projectIri)
        self.assertFalse(p._project.projectIri is p2._project.projectIri)
        self.assertEqual(p._project.projectShortName, p2._project.projectShortName)
        self.assertFalse(p._project.projectShortName is p2._project.projectShortName)
        self.assertFalse(p._project is p2._project)
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

    def test_propertyclass_tonode_constructor(self):
        p2 = PropertyClass(con=self._connection,
                           project=self._project,
                           toClass=Iri('test:Person'))
        self.assertEqual(p2.get(PropClassAttr.CLASS), Xsd_QName('test:Person'))

    def test_propertyclass_datatype_constructor(self):
        p3 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:testprop3'),
                           datatype=XsdDatatypes.string,
                           inSet=RdfSet(Xsd_string('yes'), Xsd_string('may be'), Xsd_string('no')))
        self.assertEqual(p3.property_class_iri, Xsd_QName('test:testprop3'))
        self.assertEqual(p3.get(PropClassAttr.IN), {Xsd_string('yes'), Xsd_string('may be'), Xsd_string('no')})
        self.assertEqual(p3.get(PropClassAttr.DATATYPE), XsdDatatypes.string)

    def test_propertyclass_languagein_constructor(self):
        p4 = PropertyClass(con=self._connection,
                           project=self._project,
                           property_class_iri=Iri('test:testprop4'),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p4.property_class_iri, Xsd_QName('test:testprop4'))
        self.assertEqual(p4.get(PropClassAttr.LANGUAGE_IN), LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p4.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)

        p4a = PropertyClass(con=self._connection,
                            project=self._project,
                            property_class_iri=Iri('test:testprop4a'),
                            languageIn={'en', 'fr'})
        self.assertEqual(p4a.property_class_iri, Xsd_QName('test:testprop4a'))
        self.assertEqual(p4a.get(PropClassAttr.LANGUAGE_IN), LanguageIn(Language.EN, Language.FR))
        self.assertEqual(p4a.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)

    def test_propertyclass_inconsistent_constructor(self):
        with self.assertRaises(OldapErrorValue):
            p5 = PropertyClass(con=self._connection,
                               project=self._project,
                               property_class_iri=Iri('test:testprop5'),
                               datatype=XsdDatatypes.string,
                               languageIn=LanguageIn(Language.EN, Language.DE, Language.FR))

    def test_propertyclass_projectsn_constructor(self):
        p6 = PropertyClass(con=self._connection,
                           project="test",
                           property_class_iri=Iri('test:testprop6'),
                           languageIn=LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p6.property_class_iri, Xsd_QName('test:testprop6'))
        self.assertEqual(p6.get(PropClassAttr.LANGUAGE_IN), LanguageIn(Language.EN, Language.DE, Language.FR))
        self.assertEqual(p6.get(PropClassAttr.DATATYPE), XsdDatatypes.langString)


    # @unittest.skip('Work in progress')
    def test_propertyclass_read_shacl(self):
        p1 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:comment'),
                                ignore_cache=True)
        self.assertEqual(p1.property_class_iri, Iri('test:comment'))
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
        self.assertEqual(p1.get(PropClassAttr.TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(p1.type, OwlPropertyType.OwlDataProperty)
        self.assertEqual(p1.creator, Iri('https://orcid.org/0000-0003-1681-4036'))
        self.assertEqual(p1.created, Xsd_dateTime("2023-11-04T12:00:00Z"))

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:test'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Iri('test:test'))
        self.assertEqual(p2[PropClassAttr.NAME], LangString("Test"))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.string)
        self.assertEqual(p2[PropClassAttr.TYPE], OwlPropertyType.OwlDataProperty)

        p3 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:enum'),
                                ignore_cache=True)
        self.assertEqual(p3[PropClassAttr.IN],
                         {"very good", "good", "fair", "insufficient"})
        self.assertEqual(p3[PropClassAttr.IN],
                         RdfSet({Xsd_string("very good"), Xsd_string("good"), Xsd_string("fair"), Xsd_string("insufficient")}))

    # @unittest.skip('Work in progress')
    def test_propertyclass_create(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testWrite'),
            toClass=Iri('test:comment'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            inSet=RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"))
        )
        p1.create()
        p1 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:testWrite'),
                                ignore_cache=True)
        self.assertEqual(p1.property_class_iri, Iri('test:testWrite'))
        self.assertEqual(p1[PropClassAttr.CLASS], Iri('test:comment'))
        self.assertEqual(p1[PropClassAttr.NAME], LangString("Annotations@en"))
        self.assertEqual(p1[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p1[PropClassAttr.IN],
                         RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2")))

        p2 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testWrite2'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True)
        )
        p2.create()
        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:testWrite2'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Iri('test:testWrite2'))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.langString)
        self.assertEqual(p2[PropClassAttr.NAME], LangString("Annotations@en"))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropClassAttr.LANGUAGE_IN],
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

        p3 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testWrite3'),
            datatype=XsdDatatypes.string,
            pattern=r"^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$"
        )
        p3.create()
        p3 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:testWrite3'),
                                ignore_cache=True)
        self.assertEqual(p3.pattern, r"^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$")


        pX = PropertyClass(
            con=self._connection,
            #graph=Xsd_NCName('test'),
            project=self._project,
            property_class_iri=Iri('test:testWrite'),
            datatype=XsdDatatypes.int
        )
        with self.assertRaises(OldapErrorAlreadyExists) as ex:
            pX.create()
        self.assertEqual(str(ex.exception), 'Property "test:testWrite" already exists.')

    def test_propertyclass_create_nopermission(self):
        p1 = PropertyClass(
            con=self._unpriv,
            project=self._project,
            property_class_iri=Iri('test:testCreateNoPerm'),
            toClass=Iri('test:comment'),
            name=LangString("NoPerm@en"),
            description=LangString("NoPerm@en")
        )
        with self.assertRaises(OldapErrorNoPermission) as ex:
            p1.create()
        self.assertEqual(str(ex.exception), 'Actor has no ADMIN_MODEL permission for project "test"')

    def test_property_cache(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testCache'),
            toClass=Iri('test:comment'),
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            inSet=RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"))
        )
        p1.create()
        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:testCache'))
        self.assertFalse(p1 is p2)
        self.assertEqual(p1.property_class_iri, p2.property_class_iri)
        self.assertEqual(p1.toClass, p2.toClass)
        self.assertEqual(p1.name, p2.name)
        self.assertEqual(p1.description, p2.description)
        self.assertEqual(p1.inSet, p2.inSet)

    # @unittest.skip('Work in progress')
    def test_propertyclass_undo(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testUndo'),
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
            property_class_iri=Iri('test:testUndo'),
            toClass=Iri('http://www.test.org/TestObject'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            inSet=XsdSet(Iri("http://www.test.org/comment1"),
                         Iri("http://www.test.org/comment2"),
                         Iri("http://www.test.org/comment3")))
        self.assertEqual(p1.get(PropClassAttr.CLASS), Iri('http://www.test.org/TestObject'))
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
        self.assertEqual(p1.get(PropClassAttr.CLASS), Iri('http://www.test.org/TestObject'))
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
        self.assertEqual(p1[PropClassAttr.IN], RdfSet(Iri("http://www.test.org/comment1"), Iri("http://www.test.org/comment2"), Iri("http://www.test.org/comment3")))
        self.assertEqual(p1.changeset, {})


        p1 = PropertyClass(
            con=self._connection,
            #graph=Xsd_NCName('test'),
            project=self._project,
            property_class_iri=Iri('test:testUndo'),
            toClass=Iri('test:testUndo42'),
            inSet={'test:testUndo42', 'test:UP4014'}
        )
        p1.toClass = Iri('test:UP4014')
        p1.inSet.add('test:RGW168')
        self.assertEqual(p1.toClass, Iri('test:UP4014'))
        self.assertEqual(p1.inSet, {'test:testUndo42', 'test:UP4014', 'test:RGW168'})
        p1.undo()
        self.assertEqual(p1.toClass, Iri('test:testUndo42'))
        self.assertEqual(p1.inSet, {'test:testUndo42', 'test:UP4014'})


    # @unittest.skip('Work in progress')
    def test_propertyclass_update(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testUpdate'),
            subPropertyOf=Iri('test:masterProp'),
            datatype=XsdDatatypes.langString,
            name=LangString("Annotations@en"),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT),
            uniqueLang=Xsd_boolean(True)
        )
        p1.create()

        p1[PropClassAttr.SUBPROPERTY_OF] = Iri('test:masterProp2')
        p1[PropClassAttr.NAME][Language.DE] = 'Annotationen'
        p1[PropClassAttr.UNIQUE_LANG] = Xsd_boolean(False)
        p1[PropClassAttr.IN] = RdfSet(Xsd_string("gaga"), Xsd_string("is was"))
        self.maxDiff = None
        self.assertEqual(p1.changeset, {
            PropClassAttr.NAME: AttributeChange(None, Action.MODIFY),
            # PropClassAttr.LANGUAGE_IN: PropClassAttrChange(LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT), Action.REPLACE, True),
            PropClassAttr.SUBPROPERTY_OF: AttributeChange(Iri('test:masterProp'), Action.REPLACE),
            PropClassAttr.UNIQUE_LANG: AttributeChange(Xsd_boolean(True), Action.REPLACE),
            PropClassAttr.IN: AttributeChange(None, Action.CREATE),
        })
        p1.update()
        self.assertEqual(p1.changeset, {})

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:testUpdate'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Iri('test:testUpdate'))
        self.assertEqual(p2.subPropertyOf, Iri('test:masterProp2'))
        self.assertEqual(p2[PropClassAttr.DATATYPE], XsdDatatypes.langString)
        self.assertIsNone(p2.get(PropClassAttr.CLASS))
        self.assertEqual(p2[PropClassAttr.NAME], LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2[PropClassAttr.DESCRIPTION], LangString("An annotation@en"))
        self.assertEqual(p2[PropClassAttr.LANGUAGE_IN], LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
        self.assertEqual(p2[PropClassAttr.IN], RdfSet(Xsd_string("gaga"), Xsd_string("is was")))
        self.assertFalse(p2[PropClassAttr.UNIQUE_LANG])

    # @unittest.skip('Work in progress')
    def test_propertyclass_update2(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testUpdate2'),
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
                                property_class_iri=Iri('test:testUpdate2'),
                                ignore_cache=True)
        self.assertEqual(p2.property_class_iri, Iri('test:testUpdate2'))
        self.assertEqual(p2.datatype, XsdDatatypes.langString)
        self.assertIsNone(p2.toClass)
        self.assertEqual(p2.name, LangString(["Annotations@en", "Annotationen@de"]))
        self.assertEqual(p2.description, LangString("An annotation@en"))
        self.assertEqual(p2.languageIn,
                         LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT, Language.ZU))
        self.assertEqual(p2.inSet, RdfSet(Xsd_string("gaga"), Xsd_string("is was")))
        self.assertFalse(p2.uniqueLang)

    # @unittest.skip('Work in progress')
    def test_propertyclass_delete_attrs(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testDelete'),
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
                                property_class_iri=Iri('test:testDelete'),
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

    # @unittest.skip('Work in progress')
    def test_propertyclass_delete(self):
        p1 = PropertyClass(
            con=self._connection,
            project=self._project,
            property_class_iri=Iri('test:testDeleteIt'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            languageIn=LanguageIn(Language.ZU, Language.CY, Language.SV, Language.RM),
            uniqueLang=Xsd_boolean(True)
        )
        p1.create()

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:testDeleteIt'),
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
            property_class_iri=Iri('test:testDeleteIt2'),
            toClass=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
            inSet=XsdSet(Iri('test:gaga1'), Iri('test:gaga2'), Iri('test:gaga3'))
        )
        p1.create()

        p2 = PropertyClass.read(con=self._connection,
                                project=self._project,
                                property_class_iri=Iri('test:testDeleteIt2'),
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
            property_class_iri=Iri('test:testWriteIt'),
            toClass=Iri('test:comment'),
            name=LangString(["Annotations@en", "Annotationen@de"]),
            description=LangString("An annotation@en"),
        )
        p1.write_as_trig('propclass_test.trig')


if __name__ == '__main__':
    unittest.main()
