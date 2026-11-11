"""Repair four reviewed legacy Place timestamps, retaining exact RDF terms.

Defaults to read-only inspection. Apply requires a private before-image file and
rechecks every subject inside the normal resource transaction/writer gate. Only
one explicitly reviewed old date per subject is removed. No business data,
lastModifiedBy, history or new timestamps are written. Credentials come from the
operator's environment; this script never prints them.
"""
import argparse
import json
import os
from pathlib import Path

from oldaplib.src.jena_connection import JenaConnection
from oldaplib.src.resource_transaction import resource_transaction

GRAPH = 'http://fasnacht.digital/ns/data'
OLDAP = 'http://oldap.org/base#'
# Proven present with these exact lexical values in the 2026-08-28 source dump.
REPAIRS = {
    'urn:uuid:77b2648b-7134-4d9e-ad36-42792cf09225': ('2026-05-27T23:39:55.712497+02:00', '2026-06-18T23:14:53.255254+00:00'),
    'urn:uuid:f16cf028-69e4-483c-adaf-337aada8bb57': ('2026-05-27T23:41:14.971251+02:00', '2026-06-18T23:14:39.971653+00:00'),
    'urn:uuid:5bc7d713-adfb-4e6d-a004-18939cc7e2e4': ('2026-05-27T23:38:53.075702+02:00', '2026-06-18T23:15:40.837020+00:00'),
    'urn:uuid:20d58f62-2cd6-4439-aa56-719e466b8841': ('2026-05-31T20:27:59.705563+00:00', '2026-06-18T23:15:17.243829+00:00'),
}
DATATYPE = 'http://www.w3.org/2001/XMLSchema#dateTimeStamp'


def snapshot(query):
    """Read all direct triples of the reviewed subjects in stable order."""
    subjects = ' '.join(f'<{iri}>' for iri in REPAIRS)
    rows = query(f'SELECT ?s ?p ?o WHERE {{ GRAPH <{GRAPH}> {{ VALUES ?s {{ {subjects} }} ?s ?p ?o }} }}')['results']['bindings']
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))


def old_date(row):
    """Identify only the exact reviewed obsolete RDF date triple."""
    return (row['p']['value'] == OLDAP + 'lastModificationDate'
            and row['o'] == {'type': 'literal', 'datatype': DATATYPE,
                             'value': REPAIRS[row['s']['value']][0]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if args.apply and args.backup is None:
        parser.error('--apply requires --backup')
    con = JenaConnection(userId=os.environ['OLDAP_AUTH_ADMIN_USER'],
                         credentials=os.environ['OLDAP_AUTH_ADMIN_PASSWORD'])
    before = snapshot(con.query)
    for iri, (obsolete, current) in REPAIRS.items():
        rows = [row for row in before if row['s']['value'] == iri]
        values = lambda predicate: [row['o'] for row in rows if row['p']['value'] == predicate]
        expected = [{'type': 'literal', 'datatype': DATATYPE, 'value': value} for value in (obsolete, current)]
        dates = values(OLDAP + 'lastModificationDate')
        if len(dates) != 2 or any(date not in dates for date in expected):
            raise RuntimeError(f'Unexpected dates for {iri}; no repair performed.')
        if values(OLDAP + 'creationDate') != [expected[0]] or len(values(OLDAP + 'lastModifiedBy')) != 1:
            raise RuntimeError(f'Unexpected audit metadata for {iri}; no repair performed.')
        if {'type': 'uri', 'value': 'http://fasnacht.digital/ns/Place'} not in values('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'):
            raise RuntimeError(f'Unexpected resource type for {iri}.')
    print('Verified four reviewed Place records; plan removes exactly four obsolete dates.')
    if not args.apply:
        return
    with open(args.backup, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
        json.dump({'graph': GRAPH, 'before': before, 'repair': REPAIRS}, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    with resource_transaction(con):
        if snapshot(con.transaction_query) != before:
            raise RuntimeError('Records changed after inspection; repair aborted.')
        triples = '\n'.join(f'<{iri}> <{OLDAP}lastModificationDate> "{dates[0]}"^^<{DATATYPE}> .' for iri, dates in REPAIRS.items())
        con.transaction_update(f'DELETE DATA {{ GRAPH <{GRAPH}> {{ {triples} }} }}')
        expected_after = [row for row in before if not old_date(row)]
        if len(before) - len(expected_after) != 4 or snapshot(con.transaction_query) != expected_after:
            raise RuntimeError('Unexpected repair delta; transaction aborted.')
    print('Committed: exactly four obsolete date triples removed; all other direct triples unchanged.')
    print(f'Private before-image: {args.backup}')


if __name__ == '__main__':
    main()
