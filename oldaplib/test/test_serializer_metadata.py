"""Offline regressions for constructor metadata reuse and caller isolation."""

from concurrent.futures import ThreadPoolExecutor
import inspect
import json
import unittest
from unittest.mock import Mock, patch

from oldaplib.src.helpers.serializer import serializer, _connection_parameters
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri


class SerializerMetadataTests(unittest.TestCase):
    def setUp(self):
        self.registered = dict(serializer._classes)
        _connection_parameters.cache_clear()
        self.addCleanup(_connection_parameters.cache_clear)
        self.addCleanup(self.restore_registry)

    def restore_registry(self):
        serializer._classes.clear()
        serializer._classes.update(self.registered)

    def test_both_connection_spellings_and_independent_objects(self):
        @serializer
        class MetadataPair:
            def __init__(self, values, connection=None, con=None):
                self.values, self.connection, self.con = values, connection, con

        encoded = '{"__class__":"MetadataPair","values":[1]}'
        first_connection, second_connection = object(), object()
        with patch("oldaplib.src.helpers.serializer.inspect.signature", wraps=inspect.signature) as signature:
            first = json.loads(encoded, object_hook=serializer.make_decoder_hook(first_connection))
            second = json.loads(encoded, object_hook=serializer.make_decoder_hook(second_connection))
            self.assertEqual(signature.call_count, 1)
        self.assertIs(first.connection, first_connection)
        self.assertIs(first.con, first_connection)
        self.assertIs(second.connection, second_connection)
        self.assertIs(second.con, second_connection)
        first.values.append(2)
        self.assertEqual(second.values, [1])

    def test_constructor_without_connection_does_not_receive_one(self):
        @serializer
        class MetadataValue:
            def __init__(self, value):
                self.value = value

        result = json.loads('{"__class__":"MetadataValue","value":7}',
                            object_hook=serializer.make_decoder_hook(object()))
        self.assertEqual(result.value, 7)

    def test_constructor_replacement_uses_new_keyword(self):
        @serializer
        class MetadataReplace:
            def __init__(self, connection=None):
                self.connection = connection

        encoded = '{"__class__":"MetadataReplace"}'
        first = object()
        self.assertIs(json.loads(encoded, object_hook=serializer.make_decoder_hook(first)).connection, first)

        def replacement(self, con=None):
            self.connection = con

        MetadataReplace.__init__ = replacement
        second = object()
        self.assertIs(json.loads(encoded, object_hook=serializer.make_decoder_hook(second)).connection, second)

    def test_class_reregistration_does_not_reuse_old_constructor(self):
        @serializer
        class MetadataRegistered:
            def __init__(self, connection=None):
                self.connection = connection

        encoded = '{"__class__":"MetadataRegistered"}'
        json.loads(encoded, object_hook=serializer.make_decoder_hook(object()))

        @serializer
        class MetadataRegistered:
            def __init__(self, con=None):
                self.connection = con

        connection = object()
        result = json.loads(encoded, object_hook=serializer.make_decoder_hook(connection))
        self.assertIsInstance(result, MetadataRegistered)
        self.assertIs(result.connection, connection)

    def test_threads_never_share_connection_or_mutable_payload(self):
        @serializer
        class MetadataThread:
            def __init__(self, values, con=None):
                self.values, self.connection = values, con

        connections = [object() for _ in range(64)]

        def decode(connection):
            return json.loads('{"__class__":"MetadataThread","values":[]}',
                              object_hook=serializer.make_decoder_hook(connection))

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(decode, connections))
        for result, connection in zip(results, connections):
            self.assertIs(result.connection, connection)
        self.assertEqual(len({id(r.values) for r in results}), len(results))

    def test_no_connection_retains_constructor_defaults(self):
        @serializer
        class MetadataDefault:
            def __init__(self, connection="default"):
                self.connection = connection

        result = json.loads('{"__class__":"MetadataDefault"}', object_hook=serializer.decoder_hook)
        self.assertEqual(result.connection, "default")
        self.assertEqual(_connection_parameters.cache_info().currsize, 0)

    def test_real_project_roundtrip_rebinds_connection_without_sharing_labels(self):
        connections = [Mock(spec=IConnection, context_name="SERIALIZER_METADATA_TEST",
                            userIri=Iri("urn:uuid:11111111-1111-1111-1111-111111111111"))
                       for _ in range(2)]
        original = Project(con=connections[0], projectIri="http://example.org/project",
                           projectShortName="example", namespaceIri="http://example.org/ns/",
                           label=LangString("Original@en"))
        encoded = json.dumps(original, default=serializer.encoder_default)
        first, second = [json.loads(encoded, object_hook=serializer.make_decoder_hook(con))
                         for con in connections]
        self.assertIs(first._con, connections[0])
        self.assertIs(second._con, connections[1])
        self.assertEqual(json.dumps(second, default=serializer.encoder_default), encoded)
        first.label["en"] = "Changed"
        self.assertEqual(str(second.label["en"]), "Original")
        self.assertEqual(str(original.label["en"]), "Original")

    def test_cache_is_bounded_for_dynamic_constructor_classes(self):
        for _ in range(300):
            def constructor(self, connection=None):
                pass
            self.assertEqual(_connection_parameters(constructor), ("connection",))
        self.assertEqual(_connection_parameters.cache_info().currsize, 256)


if __name__ == "__main__":
    unittest.main()
