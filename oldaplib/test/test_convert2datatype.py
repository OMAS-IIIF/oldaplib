"""Unit tests for XML Schema datatype conversion dispatch."""

import unittest

from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.convert2datatype import convert2datatype
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.xsd.xsd_integer import Xsd_integer


class TestConvert2Datatype(unittest.TestCase):
    """Verify that closely related integer datatypes retain their XSD ranges."""

    def test_xsd_integer_supports_values_above_signed_32_bit(self) -> None:
        """Map unbounded ``xsd:integer`` values to ``Xsd_integer``."""
        value = convert2datatype(10_000_000_000, XsdDatatypes.integer)

        self.assertIs(type(value), Xsd_integer)
        self.assertEqual(int(value), 10_000_000_000)
        self.assertEqual(value.toRdf, '"10000000000"^^xsd:integer')

    def test_xsd_int_keeps_signed_32_bit_limit(self) -> None:
        """Keep the narrower ``xsd:int`` range check unchanged."""
        with self.assertRaises(OldapErrorValue):
            convert2datatype(10_000_000_000, XsdDatatypes.int)


if __name__ == "__main__":
    unittest.main()
