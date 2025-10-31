import json
import unittest
from enum import Enum

from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


class TestObservableDict(unittest.TestCase):

    _notified: Iri

    @classmethod
    def setUpClass(cls):
        cls._notified = ''

    def notifier_test(self, data: Iri) -> None:
        self._notified = data

    def test_constructor(self):
        obs = ObservableDict({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(obs.data, {'a': 1, 'b': 2, 'c': 3})

    def test_json(self):
        obs = ObservableDict({Iri('http://gaga.com/a'): 1, Iri('http://gaga.com/b'): 2, Iri('http://gaga.com/c'): 3, Iri('http://gaga.com/d'): 4})
        jsonstr = json.dumps(obs, default=serializer.encoder_default)
        obs2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        pass
        self.assertEqual(obs2, {Iri('http://gaga.com/a'): 1, Iri('http://gaga.com/b'): 2, Iri('http://gaga.com/c'): 3, Iri('http://gaga.com/d'): 4})

    def test_json2(self):
        obs = ObservableDict()
        jsonstr = json.dumps(obs, default=serializer.encoder_default)
        print(jsonstr)
        obs2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        print(obs2)
