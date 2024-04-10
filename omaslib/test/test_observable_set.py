import unittest

from omaslib.src.helpers.observable_set import ObservableSet


class TestObservableSet(unittest.TestCase):

    def notifier_test(self, what: ObservableSet, data: str):
        pass

    def test_constructor(self):
        obs = ObservableSet()
        self.assertEqual(obs, set())
        self.assertEqual(len(obs), 0)

        data = {'a', 'b', 'c'}
        obs = ObservableSet(data)
        self.assertEqual(obs, data)

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


if __name__ == '__main__':
    unittest.main()
