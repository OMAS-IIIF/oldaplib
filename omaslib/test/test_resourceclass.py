import unittest
from datetime import datetime
from time import sleep
from typing import Dict, List, Union

from omaslib.src.connection import Connection
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.datatypes import NamespaceIRI, QName, NCName
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.language import Language
from omaslib.src.helpers.omaserror import OmasErrorNotFound
from omaslib.src.helpers.propertyclassattr import PropertyClassAttribute
from omaslib.src.helpers.semantic_version import SemanticVersion
from omaslib.src.helpers.tools import lprint
from omaslib.src.helpers.xsd_datatypes import XsdDatatypes
from omaslib.src.propertyclass import PropertyClassAttributesContainer, PropertyClass, OwlPropertyType
from omaslib.src.propertyrestrictions import PropertyRestrictions, PropertyRestrictionType
from omaslib.src.resourceclass import ResourceClassAttributesContainer, ResourceClass
from omaslib.src.helpers.resourceclassattr import ResourceClassAttribute


class TestResourceClass(unittest.TestCase):
    _context: Context
    _connection: Connection

    @classmethod
    def setUpClass(cls):
        cls._context = Context(name="DEFAULT")
        cls._context['test'] = NamespaceIRI("http://omas.org/test#")
        cls._context.use('test', 'dcterms')

        cls._connection = Connection(server='http://localhost:7200',
                                     userid="rosenth",
                                     credentials="RioGrande",
                                     repo="omas",
                                     context_name="DEFAULT")

        cls._connection.clear_graph(QName('test:shacl'))
        cls._connection.clear_graph(QName('test:onto'))
        cls._connection.clear_graph(QName('dcterms:shacl'))
        cls._connection.clear_graph(QName('dcterms:onto'))
        cls._connection.upload_turtle("omaslib/testdata/connection_test.trig")
        sleep(1)  # upload may take a while...

    @classmethod
    def tearDownClass(cls):
        #cls._connection.clear_graph(QName('test:shacl'))
        #cls._connection.clear_graph(QName('test:onto'))
        pass

    #@unittest.skip('Work in progress')
    def test_constructor(self):
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["Test resource@en", "Resource de test@fr"]),
            ResourceClassAttribute.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttribute.CLOSED: True
        }
        props: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 5
        }
        p = PropertyClass(con=self._connection,
                          graph=NCName('test'),
                          property_class_iri=QName('test:testprop'), attrs=props)

        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
            p
        ]

        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:TestResource"),
                           attrs=attrs,
                           properties=properties)
        self.assertEqual(r1[ResourceClassAttribute.LABEL], LangString(["Test resource@en", "Resource de test@fr"]))
        self.assertEqual(r1[ResourceClassAttribute.COMMENT], LangString("For testing purposes@en"))
        self.assertTrue(r1[ResourceClassAttribute.CLOSED])

        prop1 = r1[QName("test:comment")]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, QName("test:comment"))
        self.assertEqual(prop1[PropertyClassAttribute.DATATYPE], XsdDatatypes.string)
        self.assertEqual(prop1[PropertyClassAttribute.NAME], LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1[PropertyClassAttribute.DESCRIPTION], LangString("This is a test property@de"))
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG], True)

        prop2 = r1[QName("test:test")]
        self.assertIsNone(prop2.internal)
        self.assertEqual(prop2.property_class_iri, QName("test:test"))
        self.assertEqual(prop2.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:comment'))
        self.assertEqual(prop2.get(PropertyClassAttribute.DESCRIPTION), LangString("Property shape for testing purposes"))
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop2.get(PropertyClassAttribute.ORDER), 3)

        prop3 = r1[QName("test:testprop")]
        self.assertEqual(prop3.internal, QName('test:TestResource'))
        self.assertEqual(prop3.property_class_iri, QName("test:testprop"))
        self.assertEqual(prop3.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop3.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop3.get(PropertyClassAttribute.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.get(PropertyClassAttribute.ORDER), 5)
        self.assertEqual(prop3.get(PropertyClassAttribute.SUBPROPERTY_OF), QName("test:comment"))
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.UNIQUE_LANG], True)
        self.assertEqual(prop3[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})

    #@unittest.skip('Work in progress')
    def test_reading(self):
        r1 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName('test:testMyRes'))
        self.assertEqual(r1.owl_class_iri, QName('test:testMyRes'))
        self.assertEqual(r1.version, SemanticVersion(1, 0, 0))
        self.assertEqual(r1.creator, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(r1.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.contributor, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(r1.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(r1.get(ResourceClassAttribute.LABEL), LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr"]))
        self.assertEqual(r1.get(ResourceClassAttribute.COMMENT), LangString("Resource for testing..."))
        self.assertEqual(r1.get(ResourceClassAttribute.CLOSED), True)

        prop1 = r1[QName('test:test')]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, QName("test:test"))
        self.assertEqual(prop1.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop1.creator, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop1.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.contributor, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop1.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop1.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlObjectProperty)
        self.assertEqual(prop1.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:comment'))
        self.assertEqual(prop1.get(PropertyClassAttribute.DESCRIPTION), LangString("Property shape for testing purposes"))
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop1.get(PropertyClassAttribute.ORDER), 3)

        prop2 = r1[QName('test:hasText')]
        self.assertEqual(prop2.internal, QName('test:testMyRes'))
        self.assertEqual(prop2.property_class_iri, QName("test:hasText"))
        self.assertEqual(prop2.version, SemanticVersion(1, 0, 0))
        self.assertEqual(prop2.creator, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop2.created, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.contributor, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop2.modified, datetime.fromisoformat('2023-11-04T12:00:00Z'))
        self.assertEqual(prop2.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop2.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop2.get(PropertyClassAttribute.NAME), LangString(["A text", "Ein Text@de"]))
        self.assertEqual(prop2.get(PropertyClassAttribute.DESCRIPTION), LangString("A longer text..."))
        self.assertEqual(prop2.get(PropertyClassAttribute.ORDER), 1)
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MIN_COUNT), 1)
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)

    #@unittest.skip('Work in progress')
    def test_creating(self):
        props1: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 1
        }
        p1 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:testone'),
                           attrs=props1)

        props2: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:testMyRes'),
            PropertyClassAttribute.NAME: LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An exclusive property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 2
        }
        p2 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:testtwo'),
                           attrs=props2)

        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
            p1, p2
        ]
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["CreateResTest@en", "CréationResTeste@fr"]),
            ResourceClassAttribute.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttribute.CLOSED: True
        }
        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:TestResource"),
                           attrs=attrs,
                           properties=properties)

        r1.create()

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:TestResource"))
        self.assertEqual(r2.owl_class_iri, QName("test:TestResource"))
        self.assertEqual(r2[ResourceClassAttribute.LABEL], LangString(["CreateResTest@en", "CréationResTeste@fr"]))
        self.assertEqual(r2[ResourceClassAttribute.COMMENT], LangString("For testing purposes@en"))
        self.assertTrue(r2[ResourceClassAttribute.COMMENT])

        prop1 = r2[QName("test:comment")]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, QName('test:comment'))
        self.assertEqual(prop1.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertTrue(prop1.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(prop1.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(prop1.get(PropertyClassAttribute.NAME), LangString(["comment@en", "Kommentar@de"]))
        self.assertEqual(prop1.get(PropertyClassAttribute.DESCRIPTION), LangString("This is a test property@de"))
        self.assertIsNone(prop1.get(PropertyClassAttribute.SUBPROPERTY_OF))
        self.assertEqual(prop1[PropertyClassAttribute.ORDER], 2)
        self.assertEqual(prop1.get(PropertyClassAttribute.PROPERTY_TYPE), OwlPropertyType.OwlDataProperty)
        self.assertEqual(prop1.creator, QName('orcid:ORCID-0000-0003-1681-4036'))
        self.assertEqual(prop1.created, datetime.fromisoformat("2023-11-04T12:00:00Z"))

        prop2 = r2[QName("test:test")]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop2.property_class_iri, QName('test:test'))
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(prop2[PropertyClassAttribute.NAME], LangString("Test"))
        self.assertEqual(prop2[PropertyClassAttribute.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(prop2[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(prop2[PropertyClassAttribute.ORDER], 3)
        self.assertEqual(prop2[PropertyClassAttribute.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

        prop3 = r2[QName("test:testone")]
        self.assertEqual(prop3.internal, QName("test:TestResource"))
        self.assertEqual(prop3.property_class_iri, QName("test:testone"))
        self.assertEqual(prop3.get(PropertyClassAttribute.DATATYPE), XsdDatatypes.string)
        self.assertEqual(prop3.get(PropertyClassAttribute.NAME), LangString(["Test property@en", "Testprädikat@de"]))
        self.assertEqual(prop3.get(PropertyClassAttribute.DESCRIPTION), LangString("A property for testing...@en"))
        self.assertEqual(prop3.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(prop3.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(prop3.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertTrue(prop3.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(prop3.get(PropertyClassAttribute.ORDER), 1)

        prop4 = r2[QName("test:testtwo")]
        self.assertEqual(prop4.internal, QName("test:TestResource"))
        self.assertEqual(prop4.property_class_iri, QName("test:testtwo"))
        self.assertEqual(prop4.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:testMyRes'))
        self.assertEqual(prop4.get(PropertyClassAttribute.NAME), LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]))
        self.assertEqual(prop4.get(PropertyClassAttribute.DESCRIPTION), LangString("An exclusive property for testing...@en"))
        self.assertEqual(prop4.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(prop4.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE, Language.FR, Language.IT})
        self.assertTrue(prop4.get(PropertyClassAttribute.RESTRICTIONS)[PropertyRestrictionType.UNIQUE_LANG])
        self.assertEqual(prop4.get(PropertyClassAttribute.ORDER), 2)

    #@unittest.skip('Work in progress')
    def test_updating_add(self):
        r1 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:testMyResMinimal"))
        r1[ResourceClassAttribute.LABEL] = LangString(["Minimal Resource@en", "Kleinste Resource@de"])
        r1[ResourceClassAttribute.COMMENT] = LangString("Eine Beschreibung einer minimalen Ressource")
        r1[ResourceClassAttribute.SUBCLASS_OF] = QName('test:testMyRes')
        r1[ResourceClassAttribute.CLOSED] = True
        #
        # Add an external, shared property defined by its own sh:PropertyShape instance
        #
        r1[QName('test:test')] = None

        #
        # Adding an internal, private property
        #
        attrs: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:Person'),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={PropertyRestrictionType.MAX_COUNT: 1}),
        }
        p = PropertyClass(con=self._connection,
                          graph=NCName('test'),
                          attrs=attrs)
        r1[QName('dcterms:creator')] = p
        r1.update()

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:testMyResMinimal"))
        self.assertEqual(r2.get(ResourceClassAttribute.LABEL), LangString(["Minimal Resource@en", "Kleinste Resource@de"]))
        self.assertEqual(r2.get(ResourceClassAttribute.COMMENT), LangString("Eine Beschreibung einer minimalen Ressource"))
        self.assertEqual(r2.get(ResourceClassAttribute.SUBCLASS_OF), QName('test:testMyRes'))
        self.assertTrue(r2.get(ResourceClassAttribute.CLOSED))

        prop1 = r2[QName('test:test')]
        self.assertIsNone(prop1.internal)
        self.assertEqual(prop1.property_class_iri, QName('test:test'))
        self.assertEqual(prop1[PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(prop1[PropertyClassAttribute.NAME], LangString("Test"))
        self.assertEqual(prop1[PropertyClassAttribute.DESCRIPTION], LangString("Property shape for testing purposes"))
        self.assertEqual(prop1[PropertyClassAttribute.TO_NODE_IRI], QName('test:comment'))
        self.assertEqual(prop1[PropertyClassAttribute.ORDER], 3)
        self.assertEqual(prop1[PropertyClassAttribute.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

        prop2 = r2[QName('dcterms:creator')]
        self.assertEqual(prop2.internal, QName("test:testMyResMinimal"))
        self.assertEqual(prop2.get(PropertyClassAttribute.TO_NODE_IRI), QName('test:Person'))
        self.assertEqual(prop2[PropertyClassAttribute.RESTRICTIONS].get(PropertyRestrictionType.MAX_COUNT), 1)
        self.assertEqual(prop1[PropertyClassAttribute.PROPERTY_TYPE], OwlPropertyType.OwlObjectProperty)

    #@unittest.skip('Work in progress')
    def test_updating(self):
        r1 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:testMyRes"))
        self.assertEqual(r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 1)
        self.assertEqual(r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MIN_COUNT], 1)
        self.assertEqual(r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN], {Language.EN, Language.DE})
        r1[ResourceClassAttribute.LABEL][Language.IT] = "La mia risorsa"
        r1[ResourceClassAttribute.CLOSED] = False
        r1[ResourceClassAttribute.SUBCLASS_OF] = QName('test:TopGaga')
        r1[QName('test:hasText')][PropertyClassAttribute.NAME][Language.FR] = "Un Texte Français"
        r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT] = 12
        r1[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN] = {Language.DE, Language.FR, Language.IT}
        r1.update()

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:testMyRes"))
        self.assertEqual(r2.get(ResourceClassAttribute.LABEL), LangString(["My Resource@en", "Meine Ressource@de", "Ma Resource@fr", "La mia risorsa@it"]))
        self.assertFalse(r2.get(ResourceClassAttribute.CLOSED))
        self.assertEqual(r2.get(ResourceClassAttribute.SUBCLASS_OF), QName('test:TopGaga'))
        self.assertEqual(r2[QName('test:hasText')][PropertyClassAttribute.NAME], LangString(["A text", "Ein Text@de", "Un Texte Français@fr"]))
        self.assertEqual(r2[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.MAX_COUNT], 12)
        self.assertEqual(r2[QName('test:hasText')][PropertyClassAttribute.RESTRICTIONS][PropertyRestrictionType.LANGUAGE_IN], {Language.DE, Language.FR, Language.IT})

    #@unittest.skip('Work in progress')
    def test_delete_props(self):
        props1: PropertyClassAttributesContainer = {
            PropertyClassAttribute.SUBPROPERTY_OF: QName('test:comment'),
            PropertyClassAttribute.DATATYPE: XsdDatatypes.string,
            PropertyClassAttribute.NAME: LangString(["Test property@en", "Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("A property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MAX_COUNT: 1,
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 1
        }
        p1 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:propA'),
                           attrs=props1)

        props2: PropertyClassAttributesContainer = {
            PropertyClassAttribute.TO_NODE_IRI: QName('test:testMyRes'),
            PropertyClassAttribute.NAME: LangString(["Excl. Test property@en", "Exkl. Testprädikat@de"]),
            PropertyClassAttribute.DESCRIPTION: LangString("An exclusive property for testing...@en"),
            PropertyClassAttribute.RESTRICTIONS: PropertyRestrictions(
                restrictions={
                    PropertyRestrictionType.MIN_COUNT: 1,
                    PropertyRestrictionType.UNIQUE_LANG: True,
                    PropertyRestrictionType.LANGUAGE_IN: {Language.EN, Language.DE, Language.FR, Language.IT}
                }),
            PropertyClassAttribute.ORDER: 2
        }
        p2 = PropertyClass(con=self._connection,
                           graph=NCName('test'),
                           property_class_iri=QName('test:propB'),
                           attrs=props2)

        properties: List[Union[PropertyClass, QName]] = [
            QName("test:comment"),
            QName("test:test"),
            p1, p2
        ]
        attrs: ResourceClassAttributesContainer = {
            ResourceClassAttribute.LABEL: LangString(["CreateResTest@en", "CréationResTeste@fr"]),
            ResourceClassAttribute.COMMENT: LangString("For testing purposes@en"),
            ResourceClassAttribute.CLOSED: True
        }
        r1 = ResourceClass(con=self._connection,
                           graph=NCName('test'),
                           owlclass_iri=QName("test:TestResourceDelProps"),
                           attrs=attrs,
                           properties=properties)

        r1.create()

        r2 = ResourceClass.read(con=self._connection,
                                graph=NCName('test'),
                                owl_class_iri=QName("test:TestResourceDelProps"))
        print("\n========>", r2.modified)
        del r2[QName('test:propB')]
        r2.update()
