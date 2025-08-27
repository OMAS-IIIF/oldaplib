from pathlib import Path
from pprint import pprint

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import load_list_from_yaml, print_sublist
from oldaplib.src.permissionset import PermissionSet
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


def generate_a_datamodel(con: Connection, project: Project) -> DataModel:
    dm_name = project.projectShortName
    #
    # define an external standalone property
    #
    comment = PropertyClass(con=con,
                            project=project,
                            property_class_iri=Iri(f'{dm_name}:comment'),
                            datatype=XsdDatatypes.langString,
                            name=LangString(["Comment@en", "Kommentar@de"]),
                            uniqueLang=Xsd_boolean(True),
                            languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))
    comment.force_external()

    #
    # Define the properties for the "Book"
    #
    title = PropertyClass(con=con,
                          project=project,
                          property_class_iri=Iri(f'{dm_name}:title'),
                          datatype=XsdDatatypes.langString,
                          name=LangString(["Title@en", "Titel@de"]),
                          description=LangString(["Title of book@en", "Titel des Buches@de"]),
                          uniqueLang=Xsd_boolean(True),
                          languageIn=LanguageIn(Language.EN, Language.DE, Language.FR, Language.IT))

    authors = PropertyClass(con=con,
                            project=project,
                            property_class_iri=Iri(f'{dm_name}:authors'),
                            toClass=Iri('oldap:Person'),
                            name=LangString(["Author(s)@en", "Autor(en)@de"]),
                            description=LangString(["Writers of the Book@en", "Schreiber*innen des Buchs@de"]))

    catlist = OldapList(con=con,
                        project=project,
                        oldapListId='booktype')
    category = PropertyClass(con=con,
                             project=project,
                             property_class_iri=Iri(f'{dm_name}:category'),
                             toClass=catlist.node_classIri,
                             name=LangString(["Category@en", "Kategorie@de"]),
                             description=LangString(["Category of the Book@en", "Kategorie des Buchs@de"]))

    book = ResourceClass(con=con,
                         project=project,
                         owlclass_iri=Iri(f'{dm_name}:Book'),
                         label=LangString(["Book@en", "Buch@de"]),
                         comment=LangString("Ein Buch mit Seiten@en"),
                         closed=Xsd_boolean(True),
                         hasproperties=[
                             HasProperty(con=con, project=project, prop=title, minCount=Xsd_integer(1), order=1),
                             HasProperty(con=con, project=project, prop=authors, minCount=Xsd_integer(1), order=2),
                             HasProperty(con=con, project=project, prop=category, minCount=Xsd_integer(1), order=3),
                             HasProperty(con=con, project=project, prop=comment, order=4)])

    #
    # model for page
    #
    pagenum = PropertyClass(con=con,
                            project=project,
                            property_class_iri=Iri(f'{dm_name}:pagenum'),
                            datatype=XsdDatatypes.int,
                            name=LangString(["Pagenumber@en", "Seitennummer@de"]))

    inbook = PropertyClass(con=con,
                           project=project,
                           property_class_iri=Iri(f'{dm_name}:inbook'),
                           toClass=Iri(f'{dm_name}:Book'),
                           name=LangString(["In book@en", "Im Buch@de"]))

    page = ResourceClass(con=con,
                         project=project,
                         owlclass_iri=Iri(f'{dm_name}:Page'),
                         label=LangString(["Page@en", "Seite@de"]),
                         comment=LangString("Page of a book@en", "Seite eines Buches@de"),
                         closed=Xsd_boolean(True),
                         hasproperties=[
                             HasProperty(con=con, project=project, prop=pagenum, maxCount=Xsd_integer(1),
                                         minCount=Xsd_integer(1), order=1),
                             HasProperty(con=con, project=project, prop=inbook, maxCount=Xsd_integer(1),
                                         minCount=Xsd_integer(1), order=2),
                             HasProperty(con=con, project=project, prop=comment, order=3)])

    person = ResourceClass(con=con,
                           project=project,
                           owlclass_iri=Iri(f'{dm_name}:Person'),
                           label=LangString(["Person@en", "Person@de"]),
                           hasproperties=[
                               HasProperty(con=con, project=project, prop=Iri('schema:familyName'), minCount=Xsd_integer(1),
                                           maxCount=Xsd_integer(1), order=1),
                               HasProperty(con=con, project=project, prop=Iri('schema:givenName'), minCount=Xsd_integer(1),
                                           order=2)])

    dm = DataModel(con=con,
                   project=project,
                   propclasses=[comment],
                   resclasses=[book, page, person])
    return dm


if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     userId="rosenth",
                     credentials="RioGrande",
                     repo="oldap",
                     context_name="DEFAULT")
    cache = CacheSingleton()
    cache.clear()
    con.clear_repo()
    con.upload_turtle("../oldaplib/ontologies/oldap.trig")
    con.upload_turtle("../oldaplib/ontologies/shared.trig")
    con.upload_turtle("../oldaplib/ontologies/admin.trig")

    #
    # Create project "playground"
    #
    project = Project(con=con,
                      projectShortName="playground",
                      namespaceIri=NamespaceIRI("http://playground.org/project/playground#"),
                      label=LangString(["Playground@en", "Playground@de"]),
                      comment=LangString(["Playground for App testing@en", "Playground zum Testen der App@de"]),
                      projectStart=Xsd_date(2024, 1, 1),
                      projectEnd=Xsd_date(2026, 12, 31)
                      )
    project.create()

    ps1 = PermissionSet(con=con,
                       permissionSetId="playgroundFull",
                       givesPermission=DataPermission.DATA_PERMISSIONS,
                       definedByProject=project.projectIri)
    ps1.create()

    ps2 = PermissionSet(con=con,
                       permissionSetId="playgroundView",
                       givesPermission=DataPermission.DATA_VIEW,
                       definedByProject=project.projectIri)
    ps2.create()


    #
    # Create two users
    #
    user1 = User(con=con,
                 userId=Xsd_NCName("p1"),
                 familyName="Playground",
                 givenName="One",
                 email="one.playground@playground.org",
                 credentials="RioGrande",
                 inProject={
                     project.projectIri: {
                         AdminPermission.ADMIN_USERS,
                         AdminPermission.ADMIN_RESOURCES,
                         AdminPermission.ADMIN_CREATE,
                         AdminPermission.ADMIN_PERMISSION_SETS,
                         AdminPermission.ADMIN_MODEL,
                         AdminPermission.ADMIN_LISTS,
                     }
                 },
                 hasPermissions={  # TODO: Conversion to Iri should be automatic...
                     Iri(f'{project.projectShortName}:playgroundFull'),
                     Iri('oldap:GenericView')
                 },
                 isActive=True)
    user1.create()

    user2 = User(con=con,
                 userId=Xsd_NCName("p2"),
                 familyName="Playground",
                 givenName="Two",
                 email="two.playground@playground.og",
                 credentials="RioGrande",
                 inProject={
                     project.projectIri: {
                         AdminPermission.ADMIN_CREATE,
                     }
                 },
                 hasPermissions={  # TODO: Conversion to Iri should be automatic...
                     Iri(f'{project.projectShortName}:playgroundFull')
                 },
                 isActive=True)
    user2.create()

    listnodes = load_list_from_yaml(con=con,
                                    project=project,
                                    filepath=Path('../oldaplib/testdata/playground_list.yaml'))

    listnodes = load_list_from_yaml(con=con,
                                    project=project,
                                    filepath=Path('../oldaplib/testdata/source_type.yaml'))

    collections_type = load_list_from_yaml(con=con,
                                           project=project,
                                           filepath=Path('../oldaplib/testdata/collections_type.yaml'))

    language_type = load_list_from_yaml(con=con,
                                        project=project,
                                        filepath=Path('../oldaplib/testdata/language.yaml'))

    location_type = load_list_from_yaml(con=con,
                                        project=project,
                                        filepath=Path('../oldaplib/testdata/location_type.yaml'))

    means_of_transportation = load_list_from_yaml(con=con,
                                                  project=project,
                                                  filepath=Path('../oldaplib/testdata/means_of_transportation.yaml'))

    role = load_list_from_yaml(con=con,
                               project=project,
                               filepath=Path('../oldaplib/testdata/role.yaml'))


    dm = generate_a_datamodel(con=con, project=project)
    dm.create()

    #
    # Filling in data
    #
    factory = ResourceInstanceFactory(con=con, project=project)
    Person = factory.createObjectInstance('Person')
    p1 = Person(familyName="Adams",givenName="Douglas")

    Book = factory.createObjectInstance('Book')
    b = Book(title="Hitchhiker's Guide to the Galaxy",
             authors=p1.iri,
             category=Iri(f'{listnodes[0].node_namespaceIri}:physics'),  # TODO: How to get the IRI programmatically?
             pubDate="1995-09-27",
             grantsPermission=ps1.iri)
    b.create()

    Page = factory.createObjectInstance('Page')
    for i in range(1, 10):
        p = Page(inbook=b.iri, pagenum=i)
        p.create()


