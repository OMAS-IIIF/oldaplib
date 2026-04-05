from pprint import pprint

from oldaplib.src.connection import Connection
import unittest

from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass


class TestKappa(unittest.TestCase):

    def test__read_shacl(self):
        connection = Connection(userId="rosenth",
                                credentials="RioGrande",
                                context_name="DEFAULT")

        shared = Project.read(connection, "shared")

        obj = ResourceClass.XX__read_shacl(connection,
                                     shared,
                                     'shared:MediaObject')
        pprint(obj)
