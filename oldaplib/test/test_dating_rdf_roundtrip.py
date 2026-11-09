"""RDF round trips preserve normalized intervals and original calendar metadata."""

import pytest
from rdflib import Graph

from oldaplib.src.helpers.construct_processor import ConstructProcessor
from oldaplib.src.helpers.context import Context
from oldaplib.src.objectfactory import (
    _dating_from_construct,
    _dating_insert_triples_for_item,
)
from oldaplib.src.xsd.dating import Dating, DatePrecision, OldapCalendar
from oldaplib.src.xsd.iri import Iri


@pytest.mark.parametrize(
    "calendar,precision,start,end",
    [
        *[
            (
                calendar,
                DatePrecision.DAY,
                (5690 if calendar == OldapCalendar.HEBREW else 1930, 2, 1),
                (5690 if calendar == OldapCalendar.HEBREW else 1930, 2, 1),
            )
            for calendar in OldapCalendar
        ],
        *[
            (calendar, precision, start, end)
            for calendar in [OldapCalendar.GREGORIAN, OldapCalendar.JULIAN]
            for precision, start, end in [
                (DatePrecision.MONTH, (1930, 2), (1930, 2)),
                (DatePrecision.YEAR, (1930,), (1930,)),
                (DatePrecision.DECADE, (1930,), (1939,)),
                (DatePrecision.CENTURY, (1900,), (1999,)),
            ]
        ],
    ],
)
def test_stored_normalized_dates_roundtrip(calendar, precision, start, end):
    """Writing and reading a valid Dating should preserve the represented interval."""
    iri = Iri("urn:dating-roundtrip:test")
    original = Dating(
        start,
        end,
        iri=iri,
        inCalendar=calendar,
        datePrecision=precision,
        verbatimDate="Original uncertain date",
    )
    context = Context(name="dating-roundtrip-test")
    graph = Graph().parse(
        data=context.turtle_context
        + "\n".join(_dating_insert_triples_for_item(original, set())),
        format="turtle",
    )
    values = ConstructProcessor.process(context, graph)
    restored = _dating_from_construct(iri, values, {})
    assert isinstance(restored, Dating)
    assert str(restored) == str(original)
    assert restored._as_dict() == original._as_dict()
