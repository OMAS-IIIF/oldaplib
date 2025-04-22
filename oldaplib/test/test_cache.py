import unittest

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


class MyTestCase(unittest.TestCase):

    def test_cache(self):
        cache = CacheSingleton()
        cache.set(Xsd_NCName('test'), "This is a test")

        cache2 = CacheSingleton()
        val = cache2.get(Xsd_NCName('test'))
        self.assertEqual(val, "This is a test")  # add assertion here

        cache3 = CacheSingleton()
        cache3.clear()
        val = cache2.get(Xsd_NCName('test'))
        self.assertEqual(val, None)


if __name__ == '__main__':
    unittest.main()
