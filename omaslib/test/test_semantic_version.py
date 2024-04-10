import unittest

from omaslib.src.helpers.semantic_version import SemanticVersion


class TestSemanticVersion(unittest.TestCase):
    def test_constructor(self):
        sv = SemanticVersion()
        self.assertEqual(sv.major, 0)
        self.assertEqual(sv.minor, 1)
        self.assertEqual(sv.patch, 0)

        sv = SemanticVersion(1, 2,3)
        self.assertEqual(sv.major, 1)
        self.assertEqual(sv.minor, 2)
        self.assertEqual(sv.patch, 3)

        sv = SemanticVersion.fromString("1.2.3")
        self.assertEqual(sv.major, 1)
        self.assertEqual(sv.minor, 2)
        self.assertEqual(sv.patch, 3)

    def test_string_conversion(self):
        sv = SemanticVersion(1, 2,3)
        self.assertEqual(str(sv), '1.2.3')

    def test_repr_conversion(self):
        sv = SemanticVersion(1, 2,3)
        self.assertEqual(repr(sv), 'SemanticVersion(1, 2, 3)')

    def test_rdf_conversion(self):
        sv = SemanticVersion(1, 2, 3)
        self.assertEqual(sv.toRdf, '"1.2.3"^^xsd:string')

    def test_compare_ops(self):
        self.assertTrue(SemanticVersion(1, 2, 3) == SemanticVersion(1, 2, 3))
        self.assertTrue(SemanticVersion(1, 2, 3) >= SemanticVersion(1, 2, 3))
        self.assertTrue(SemanticVersion(1, 2, 3) <= SemanticVersion(1, 2, 3))
        self.assertFalse(SemanticVersion(1, 2, 3) != SemanticVersion(1, 2, 3))

        self.assertTrue(SemanticVersion(1, 2, 3) != SemanticVersion(1, 2, 4))
        self.assertTrue(SemanticVersion(1, 2, 3) != SemanticVersion(1, 3, 3))
        self.assertTrue(SemanticVersion(1, 2, 3) != SemanticVersion(2, 2, 3))

        self.assertTrue(SemanticVersion(1, 2, 3) < SemanticVersion(1, 2, 4))
        self.assertTrue(SemanticVersion(1, 2, 3) < SemanticVersion(1, 3, 3))
        self.assertTrue(SemanticVersion(1, 2, 3) < SemanticVersion(2, 2, 3))

        self.assertTrue(SemanticVersion(1, 2, 4) > SemanticVersion(1, 2, 3))
        self.assertTrue(SemanticVersion(1, 3, 3) > SemanticVersion(1, 2, 3))
        self.assertTrue(SemanticVersion(2, 2, 3) > SemanticVersion(1, 2, 3))

    def test_increment(self):
        sv = SemanticVersion(1, 2, 3)
        sv.increment_patch()
        self.assertEqual(sv.major, 1)
        self.assertEqual(sv.minor, 2)
        self.assertEqual(sv.patch, 4)


        sv = SemanticVersion(1, 2, 3)
        sv.increment_major()
        self.assertEqual(sv.major, 2)
        self.assertEqual(sv.minor, 0)
        self.assertEqual(sv.patch, 0)


if __name__ == '__main__':
    unittest.main()
