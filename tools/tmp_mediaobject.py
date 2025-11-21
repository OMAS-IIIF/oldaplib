from oldaplib.src.connection import Connection
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_qname import Xsd_QName

if __name__ == '__main__':
    con = Connection(server='http://localhost:7200',
                     userId="rosenth",
                     credentials="RioGrande",
                     repo="oldap",
                     context_name="DEFAULT")
    project = Project.read(con, "shared")

    origname = PropertyClass(con=con,
                            project=project,
                            property_class_iri=Xsd_QName(f'shared:originalName'),
                            datatype=XsdDatatypes.string,
                            name=LangString(["Original Filename@en",
                                             "Originaler Dateiname@de",
                                             "Nom orignal du fichier@fr",
                                             "Nome documento originale@it"]))

    mimetype = PropertyClass(con=con,
                            project=project,
                            property_class_iri=Xsd_QName(f'shared:originalMimeType'),
                            datatype=XsdDatatypes.string,
                            name=LangString(["Original mimetype@en",
                                             "Originaler Mimetype@de",
                                             "Mimetype original@fr",
                                             "Mimetype originale@it"]))
    server = PropertyClass(con=con,
                           project=project,
                           property_class_iri=Xsd_QName(f'shared:serverUrl'),
                           datatype=XsdDatatypes.anyURI,
                           name=LangString(["Server URL@en",
                                            "URL des servers@de",
                                            "Server URL@fr",
                                            "Server URL@it"]))
    imageid = PropertyClass(con=con,
                           project=project,
                           property_class_iri=Xsd_QName(f'shared:imageId'),
                           datatype=XsdDatatypes.string,
                           name=LangString(["Image ID@en",
                                            "ID des Bilder@de",
                                            "ID de l'image@fr",
                                            "ID de l'immagine@it"]))
    mediaobj = ResourceClass(con=con,
                             project=project,
                             owlclass_iri=Xsd_QName(f'shared:MediaObject'),
                             label=LangString(
                                 ["MediaObject@en", "Medienobjekt@de", "MediaObject@fr", "MediaObject@it"]),
                             comment=LangString("Page of a book@en", "Seite eines Buches@de"),
                             closed=Xsd_boolean(True),
                             hasproperties=[
                                 HasProperty(con=con, project=project, prop=origname, maxCount=Xsd_integer(1),
                                             minCount=Xsd_integer(1), order=1),
                                 HasProperty(con=con, project=project, prop=mimetype, maxCount=Xsd_integer(1),
                                             minCount=Xsd_integer(1), order=2),
                                 HasProperty(con=con, project=project, prop=server, maxCount=Xsd_integer(1),
                                             minCount=Xsd_integer(1), order=3),
                                 HasProperty(con=con, project=project, prop=imageid, maxCount=Xsd_integer(1),
                                             minCount=Xsd_integer(1), order=3)])
    mediaobj.write_as_trig('mediaobj.trig')
