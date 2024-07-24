import json
import unittest
from enum import Enum

from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.iri import Iri


class TestObservableSet(unittest.TestCase):

    _notified: Iri

    @classmethod
    def setUpClass(cls):
        cls._notified = ''

    def notifier_test(self, data: Iri) -> None:
        self._notified = data

    def test_constructor(self):
        obs = ObservableSet()
        self.assertEqual(obs, set())
        self.assertEqual(len(obs), 0)

        data = {'a', 'b', 'c'}
        obs = ObservableSet(data)
        self.assertEqual(obs, data)

        obs2 = ObservableSet(obs)
        self.assertEqual(obs2, data)

        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, Iri('gaga:gaga'))
        self.assertEqual(obs, {'a', 'b', 'c'})

    def test_conversions(self):
        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, Iri('gaga:gaga'))
        s = str(obs).strip('{}')
        s = s.split(", ")
        self.assertTrue("'a'" in s)
        self.assertTrue("'b'" in s)
        self.assertTrue("'c'" in s)

        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, Iri('gaga:gaga'))
        s = repr(obs)
        s = s.split(", ")
        self.assertTrue("'a'" in s)
        self.assertTrue("'b'" in s)
        self.assertTrue("'c'" in s)

        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, Iri('gaga:gaga'))
        s = obs.toRdf
        s = s.split(", ")
        self.assertTrue("a" in s)
        self.assertTrue("b" in s)
        self.assertTrue("c" in s)

    def test_logicals_or(self):
        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, Iri('gaga:gaga'))
        res = obs | ObservableSet({'d', 'e', 'f'})
        self.assertEqual(res, {'a', 'b', 'c', 'd', 'e', 'f'})

        res = obs | {'d', 'e', 'f'}
        self.assertEqual(res, {'a', 'b', 'c', 'd', 'e', 'f'})

        self._notified = ''
        obs |= {'x', 'y'}
        self.assertEqual(obs, {'a', 'b', 'c', 'x', 'y'})
        self.assertEqual(self._notified, Iri('gaga:gaga'))

    def test_logicals_and(self):
        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, Iri('gaga:gaga'))
        res = obs & ObservableSet({'b', 'c', 'd'})
        self.assertEqual(res, {'b', 'c'})

        res = obs & {'b', 'c', 'd'}
        self.assertEqual(res, {'b', 'c'})

        self._notified = ''
        obs &= {'b', 'c', 'd'}
        self.assertEqual(obs, {'b', 'c'})
        self.assertEqual(self._notified, Iri('gaga:gaga'))

    def test_logical_sub(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        res = obs - ObservableSet({'b', 'd'})
        self.assertEqual(res, {'a', 'c'})

        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        res = obs - {'b', 'd'}
        self.assertEqual(res, {'a', 'c'})

        self._notified = ''
        obs -= {'b', 'd'}
        self.assertEqual(obs, {'a', 'c'})
        self.assertEqual(self._notified, Iri('gaga:gaga'))

    def test_add(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        self._notified = ''
        obs.add('Z')
        self.assertEqual(obs, {'a', 'b', 'c', 'd', 'Z'})
        self.assertEqual(self._notified, Iri('gaga:gaga'))

    def test_remove(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        self._notified = ''
        obs.remove('c')
        self.assertEqual(obs, {'a', 'b', 'd'})
        self.assertEqual(self._notified, Iri('gaga:gaga'))

        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        with self.assertRaises(KeyError) as err:
            obs.remove('Z')

    def test_discard(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        self._notified = ''
        obs.discard('c')
        self.assertEqual(obs, {'a', 'b', 'd'})
        self.assertEqual(self._notified, 'gaga:gaga')

        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        self._notified = ''
        obs.discard('Z')
        self.assertEqual(obs, {'a', 'b', 'c', 'd'})
        self.assertEqual(self._notified, Iri('gaga:gaga'))

    def test_pop(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        self._notified = ''
        len1 = len(obs)
        obs.pop()
        len2 = len(obs)
        self.assertEqual(len1, len2 + 1)
        self.assertEqual(self._notified, Iri('gaga:gaga'))

        obs = ObservableSet()
        self._notified = ''
        len1 = len(obs)
        self.assertEqual(len1, 0)
        with self.assertRaises(KeyError):
            obs.pop()
        len2 = len(obs)
        self.assertEqual(len2, 0)
        self.assertEqual(self._notified, '')

    def test_clear(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        self._notified = ''
        obs.clear()
        self.assertEqual(obs, set())
        self.assertEqual(len(obs), 0)
        self.assertEqual(self._notified, Iri('gaga:gaga'))

    def test_copy(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        obs2 = obs.copy()
        obs.clear()
        self.assertEqual(obs, set())
        self.assertEqual(obs2, {'a', 'b', 'c', 'd'})

    def test_to_rdf(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        s = obs.toRdf
        s = s.split(', ')
        self.assertTrue('a' in s)
        self.assertTrue('b' in s)
        self.assertTrue('c' in s)
        self.assertTrue('d' in s)

    def test_json(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        jsonstr = json.dumps(obs, default=serializer.encoder_default)
        obs2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(obs2, {'a', 'b', 'c', 'd'})

    def test_type_conversion(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, Iri('gaga:gaga'))
        self.assertTrue(isinstance(obs.asSet(), set))


if __name__ == '__main__':
    unittest.main()
