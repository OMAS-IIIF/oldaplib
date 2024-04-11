import json
import unittest

from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.serializer import serializer


class TestObservableSet(unittest.TestCase):

    _notified: str

    @classmethod
    def setUpClass(cls):
        cls._notified = ''

    def notifier_test(self, what: ObservableSet, data: str):
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

        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, 'gaga')
        self.assertEqual(obs, {'a', 'b', 'c'})

    def test_conversions(self):
        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, 'gaga')
        s = str(obs).strip('{}')
        s = s.split(", ")
        self.assertTrue("'a'" in s)
        self.assertTrue("'b'" in s)
        self.assertTrue("'c'" in s)

        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, 'gaga')
        s = repr(obs)
        s = s.split(", ")
        self.assertTrue("'a'" in s)
        self.assertTrue("'b'" in s)
        self.assertTrue("'c'" in s)

        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, 'gaga')
        s = obs.toRdf
        s = s.split(", ")
        self.assertTrue("a" in s)
        self.assertTrue("b" in s)
        self.assertTrue("c" in s)

    def test_logicals_or(self):
        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, 'gaga')
        res = obs | ObservableSet({'d', 'e', 'f'})
        self.assertEqual(res, {'a', 'b', 'c', 'd', 'e', 'f'})

        res = obs | {'d', 'e', 'f'}
        self.assertEqual(res, {'a', 'b', 'c', 'd', 'e', 'f'})

        with self.assertRaises(TypeError) as err:
            res = obs | ['a', 'b']

        self._notified = ''
        obs |= {'x', 'y'}
        self.assertEqual(obs, {'a', 'b', 'c', 'x', 'y'})
        self.assertEqual(self._notified, 'gaga')

    def test_logicals_and(self):
        obs = ObservableSet({'a', 'b', 'c'}, self.notifier_test, 'gaga')
        res = obs & ObservableSet({'b', 'c', 'd'})
        self.assertEqual(res, {'b', 'c'})

        res = obs & {'b', 'c', 'd'}
        self.assertEqual(res, {'b', 'c'})

        with self.assertRaises(TypeError) as err:
            res = obs & ['b', 'c', 'd']

        self._notified = ''
        obs &= {'b', 'c', 'd'}
        self.assertEqual(obs, {'b', 'c'})
        self.assertEqual(self._notified, 'gaga')

    def test_logical_sub(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        res = obs - ObservableSet({'b', 'd'})
        self.assertEqual(res, {'a', 'c'})

        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        res = obs - {'b', 'd'}
        self.assertEqual(res, {'a', 'c'})

        with self.assertRaises(TypeError) as err:
            res = obs - ['b', 'd']

        self._notified = ''
        obs -= {'b', 'd'}
        self.assertEqual(obs, {'a', 'c'})
        self.assertEqual(self._notified, 'gaga')

    def test_add(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        self._notified = ''
        obs.add('Z')
        self.assertEqual(obs, {'a', 'b', 'c', 'd', 'Z'})
        self.assertEqual(self._notified, 'gaga')

    def test_remove(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        self._notified = ''
        obs.remove('c')
        self.assertEqual(obs, {'a', 'b', 'd'})
        self.assertEqual(self._notified, 'gaga')

        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        with self.assertRaises(KeyError) as err:
            obs.remove('Z')

    def test_discard(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        self._notified = ''
        obs.discard('c')
        self.assertEqual(obs, {'a', 'b', 'd'})
        self.assertEqual(self._notified, 'gaga')

        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        self._notified = ''
        obs.discard('Z')
        self.assertEqual(obs, {'a', 'b', 'c', 'd'})
        self.assertEqual(self._notified, 'gaga')

    def test_pop(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        self._notified = ''
        len1 = len(obs)
        obs.pop()
        len2 = len(obs)
        self.assertEqual(len1, len2 + 1)
        self.assertEqual(self._notified, 'gaga')

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
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        self._notified = ''
        obs.clear()
        self.assertEqual(obs, {})
        self.assertEqual(len(obs), 0)
        self.assertEqual(self._notified, 'gaga')

    def test_copy(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        obs2 = obs.copy()
        obs.clear()
        self.assertEqual(obs, {})
        self.assertEqual(obs2, {'a', 'b', 'c', 'd'})

    def test_to_rdf(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        s = obs.toRdf
        s = s.split(', ')
        self.assertTrue('a' in s)
        self.assertTrue('b' in s)
        self.assertTrue('c' in s)
        self.assertTrue('d' in s)

    def test_json(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        jsonstr = json.dumps(obs, default=serializer.encoder_default)
        obs2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(obs2, {'a', 'b', 'c', 'd'})

    def test_type_conversion(self):
        obs = ObservableSet({'a', 'b', 'c', 'd'}, self.notifier_test, 'gaga')
        self.assertTrue(isinstance(obs.asSet(), set))


if __name__ == '__main__':
    unittest.main()
