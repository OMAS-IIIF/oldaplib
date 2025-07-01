import unittest

from oldaplib.src.cachesingleton import CacheSingleton, CacheSingletonRedis
from oldaplib.src.iconnection import IConnection
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


class MyTestCase(unittest.TestCase):

    def test_cache(self):
        cache = CacheSingletonRedis()
        cache.set(Xsd_NCName('test'), "This is a test")

        cache2 = CacheSingletonRedis()
        val = cache2.get(Xsd_NCName('test'))

        self.assertEqual(val, "This is a test")  # add assertion here

        cache3 = CacheSingletonRedis()
        cache3.clear()
        val = cache2.get(Xsd_NCName('test'))
        self.assertEqual(val, None)


if __name__ == '__main__':
    unittest.main()
