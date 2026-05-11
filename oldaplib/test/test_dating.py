import json
import unittest

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.dating import Dating, DatePrecision, OldapCalendar
from oldaplib.src.xsd.iri import Iri


class TestDating(unittest.TestCase):

    def test_constructor_day_month_year(self):
        day = Dating("2001-05-17")
        self.assertEqual(str(day), "2001-05-17 - 2001-05-17 (GREGORIAN, DAY)")

        day_range = Dating("2001-05-17", "2001-05-19")
        self.assertEqual(str(day_range), "2001-05-17 - 2001-05-19 (GREGORIAN, DAY)")

        month = Dating((2001, 5))
        self.assertEqual(str(month), "2001-05-01 - 2001-05-31 (GREGORIAN, MONTH)")

        month_range = Dating((1733, 9), (1734, 2))
        self.assertEqual(str(month_range), "1733-09-01 - 1734-02-28 (GREGORIAN, MONTH)")

        year = Dating((2001,))
        self.assertEqual(str(year), "2001-01-01 - 2001-12-31 (GREGORIAN, YEAR)")

        year_range = Dating((1922,), (1925,))
        self.assertEqual(str(year_range), "1922-01-01 - 1925-12-31 (GREGORIAN, YEAR)")

    def test_constructor_decade_century(self):
        decade = Dating((1660,), (1669,), datePrecision=DatePrecision.DECADE)
        self.assertEqual(str(decade), "1660-01-01 - 1669-12-31 (GREGORIAN, DECADE)")

        decade_single = Dating((1733,), datePrecision=DatePrecision.DECADE)
        self.assertEqual(str(decade_single), "1730-01-01 - 1739-12-31 (GREGORIAN, DECADE)")

        decade_marker_range = Dating((1720,), (1740,), datePrecision=DatePrecision.DECADE)
        self.assertEqual(str(decade_marker_range), "1720-01-01 - 1739-12-31 (GREGORIAN, DECADE)")

        decade_unaligned_marker_range = Dating((1723,), (1747,), datePrecision=DatePrecision.DECADE)
        self.assertEqual(str(decade_unaligned_marker_range), "1720-01-01 - 1739-12-31 (GREGORIAN, DECADE)")

        century = Dating((1900,), (1999,), datePrecision=DatePrecision.CENTURY)
        self.assertEqual(str(century), "1900-01-01 - 1999-12-31 (GREGORIAN, CENTURY)")

        century_single = Dating((1733,), datePrecision=DatePrecision.CENTURY)
        self.assertEqual(str(century_single), "1700-01-01 - 1799-12-31 (GREGORIAN, CENTURY)")

        century_marker_range = Dating((1700,), (1900,), datePrecision=DatePrecision.CENTURY)
        self.assertEqual(str(century_marker_range), "1700-01-01 - 1899-12-31 (GREGORIAN, CENTURY)")

        century_unaligned_marker_range = Dating((1654,), (1812,), datePrecision=DatePrecision.CENTURY)
        self.assertEqual(str(century_unaligned_marker_range), "1600-01-01 - 1799-12-31 (GREGORIAN, CENTURY)")

    def test_calendar_parsing(self):
        julian = Dating("1666-10-11:JULIAN")
        self.assertEqual(julian._inCalendar, OldapCalendar.JULIAN)
        self.assertEqual(julian._datePrecision, DatePrecision.DAY)

        persian = Dating((1400, 1, 1), inCalendar=OldapCalendar.PERSIAN)
        self.assertEqual(persian._inCalendar, OldapCalendar.PERSIAN)

    def test_invalid_precision(self):
        with self.assertRaises(OldapErrorValue):
            Dating((1660,), (1650,), datePrecision=DatePrecision.DECADE)

        with self.assertRaises(OldapErrorValue):
            Dating((1900,), (1800,), datePrecision=DatePrecision.CENTURY)

        with self.assertRaises(OldapErrorValue):
            Dating((2001, 5), datePrecision=DatePrecision.DAY)

    def test_comparisons(self):
        d1 = Dating((2001,))
        d2 = Dating((2002,))
        d3 = Dating((2000,), (2009,), datePrecision=DatePrecision.DECADE)

        self.assertTrue(d1 < d2)
        self.assertTrue(d2 > d1)
        self.assertTrue(d1.before(d2))
        self.assertTrue(d2.after(d1))
        self.assertTrue(d1.overlaps(d3))

    def test_before_relation(self):
        earlier = Dating((1999,))
        later = Dating((2001,), before={earlier})
        self.assertEqual(len(later._beforeDating), 1)
        self.assertIn(earlier, later._beforeDating)

    def test_json_roundtrip(self):
        earlier = Dating((1999,))
        dating = Dating((2000,), (2009,),
                        verbatimDate="between 2000 and 2009",
                        datePrecision=DatePrecision.DECADE,
                        before={earlier},
                        inCalendar=OldapCalendar.GREGORIAN,
                        iri=Iri("urn:uuid:test-dating", validate=False))
        jsonstr = json.dumps(dating, default=serializer.encoder_default)
        dating2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(dating, dating2)
        self.assertEqual(dating.iri, dating2.iri)
        self.assertEqual(dating._beforeDating, dating2._beforeDating)

    def test_rdf_serialization(self):
        dating = Dating((2000,), (2009,), datePrecision=DatePrecision.DECADE)
        rdf = dating.toRdf
        self.assertIn('oldap:normalizedStart "2000-01-01"^^xsd:date', rdf)
        self.assertIn('oldap:normalizedEnd "2009-12-31"^^xsd:date', rdf)
        self.assertIn('oldap:datePrecision oldap:DecadePrecision', rdf)
        self.assertIn('oldap:inCalendar oldap:GregorianCalendar', rdf)

    def test_normalized_input_rebuild(self):
        dating = Dating("2001-01-01", "2001-12-31", datePrecision=DatePrecision.YEAR)
        self.assertEqual(str(dating), "2001-01-01 - 2001-12-31 (GREGORIAN, YEAR)")

        year_range = Dating("1922-01-01", "1925-12-31", datePrecision=DatePrecision.YEAR)
        self.assertEqual(str(year_range), "1922-01-01 - 1925-12-31 (GREGORIAN, YEAR)")

        decade_range = Dating("1720-01-01", "1739-12-31", datePrecision=DatePrecision.DECADE)
        self.assertEqual(str(decade_range), "1720-01-01 - 1739-12-31 (GREGORIAN, DECADE)")

        century_range = Dating("1700-01-01", "1899-12-31", datePrecision=DatePrecision.CENTURY)
        self.assertEqual(str(century_range), "1700-01-01 - 1899-12-31 (GREGORIAN, CENTURY)")


if __name__ == '__main__':
    unittest.main()
