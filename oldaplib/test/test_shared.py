import json
import unittest
from copy import deepcopy
from pathlib import Path
from pprint import pprint
from time import sleep, time

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel, PropertyClassChange, ResourceClassChange
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.externalontology import ExternalOntology
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapError, OldapErrorAlreadyExists
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.resourceclassattr import ResClassAttribute
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.hasproperty import HasProperty

class TestDataModel(unittest.TestCase):
    _context: Context
    _connection: Connection
    _project: Project
    _dmproject: Project
    _sysproject: Project
    _sharedproject: Project

    @classmethod
    def setUp(cls):
        cache = CacheSingletonRedis()
        cache.clear()

        super().setUpClass()

        cls._context = Context(name="DEFAULT")

        cls._connection = Connection(userId="rosenth",
                                     credentials="RioGrande",
                                     context_name="DEFAULT")

        cls._sysproject = Project.read(cls._connection, "oldap", ignore_cache=True)
        cls._sharedproject = Project.read(cls._connection, "shared", ignore_cache=True)

    def test_read_shared(self):

        dm = DataModel.read(self._connection, self._sharedproject, ignore_cache=True)
        pass
