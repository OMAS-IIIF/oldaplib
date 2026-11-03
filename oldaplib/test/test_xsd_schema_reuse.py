"""Compiled schemas may be shared; input values and namespaces must remain fresh."""
from concurrent.futures import ThreadPoolExecutor

from oldaplib.src.enums.xsd_datatypes import XsdDatatypes, XsdValidator


def test_reused_validator_checks_each_new_value_and_qname_namespace():
    cases = [
        (XsdDatatypes.integer, '42', True),
        (XsdDatatypes.integer, '42.5', False),
        (XsdDatatypes.date, '2024-02-29', True),
        (XsdDatatypes.date, '2023-02-29', False),
        (XsdDatatypes.QName, 'first:field', True),
        (XsdDatatypes.QName, 'second:other', True),
        (XsdDatatypes.QName, 'first:bad name', False),
        (XsdDatatypes.NCName, 'Valid_Name', True),
        (XsdDatatypes.NCName, 'invalid:name', False),
        (XsdDatatypes.boolean, 'true', True),
        (XsdDatatypes.boolean, 'yes', False),
    ]
    for datatype, value, expected in cases * 3:
        assert XsdValidator.validate(datatype, value) is expected


def test_parallel_validation_has_independent_contexts():
    cases = [(XsdDatatypes.QName, f'namespace{i}:field', True) for i in range(40)]
    cases += [(XsdDatatypes.date, '2024-02-29', True),
              (XsdDatatypes.date, '2024-02-30', False),
              (XsdDatatypes.integer, '-100', True),
              (XsdDatatypes.integer, 'not-an-integer', False)] * 40
    def check(case):
        datatype, value, expected = case
        return XsdValidator.validate(datatype, value) is expected
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(pool.map(check, cases))


def test_trusted_rdf_skips_schema_validation_but_new_input_is_checked():
    """SELECT and CONSTRUCT must honor the same trusted-database boundary."""
    from unittest.mock import patch
    from rdflib import Graph, Literal, URIRef, XSD
    from oldaplib.src.helpers.context import Context
    from oldaplib.src.helpers.construct_processor import ConstructProcessor
    from oldaplib.src.helpers.query_processor import QueryProcessor
    from oldaplib.src.xsd.xsd_gmonthday import Xsd_gMonthDay
    from oldaplib.src.helpers.oldaperror import OldapErrorValue
    import pytest

    context = Context(name='TRUSTED_RDF_VALIDATION_TEST')
    with patch.object(XsdValidator, 'validate', side_effect=AssertionError('Unexpected RDF revalidation')):
        value = Xsd_gMonthDay.fromRdf('--02-29')
        assert str(value) == '--02-29'
        rows = QueryProcessor(context, {'head': {'vars': ['date']}, 'results': {'bindings': [
            {'date': {'type': 'literal', 'datatype': str(XSD.gMonthDay), 'value': '--02-29'}}
        ]}})
        assert str(next(iter(rows))['date']) == '--02-29'
        graph = Graph()
        graph.add((URIRef('urn:test:subject'), URIRef('urn:test:date'), Literal('--02-29', datatype=XSD.gMonthDay)))
        result = ConstructProcessor.process(context, graph)
        assert str(next(iter(next(iter(result.values())).values()))) == '--02-29'
    with pytest.raises(OldapErrorValue):
        Xsd_gMonthDay('--02-30', validate=True)
