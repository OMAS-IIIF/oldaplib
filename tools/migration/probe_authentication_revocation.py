"""Authentication revocation acceptance cases for the owned Fuseki runner.

Uses the same query preparation as User.revoke_authentication, but exercises its
experimental receipt mode on synthetic users. Not an authenticated connection
adapter: permission decisions, cache and public User behavior are tested
separately. No URLs are accepted here; the owning runner supplies local I/O.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

from oldaplib.src.helpers.authentication_revocation import AuthenticationRevocation
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger

RECEIPTS = 'urn:oldap:jena-pilot:revocation-receipts'
NS = 'urn:oldap:jena-pilot:'


def run_revocation_checks(update, query, check):
    """Execute bounded mutation/replay cases; return a restart verification hook.

    A receipt is authoritative only after a successful read. An absent receipt
    after an acknowledged update is a conflict. After a transport failure,
    absence is UNKNOWN (the original request may still commit); retry the exact
    command or reconcile again. Never regenerate its timestamp or operation ID.
    """
    context = Context(name='JENA_REVOCATION_PROBE')
    old_time = Xsd_dateTime('2026-10-27T10:00:00Z')
    new_time = Xsd_dateTime('2026-10-27T10:01:00Z')

    def seed(name, *, version=0):
        user = Iri(f'https://example.org/jena-probe/{name}')
        version_triple = '' if version is None else f'; oldap:authVersion "{version}"^^xsd:nonNegativeInteger'
        update(context.sparql_context + f'''INSERT DATA {{ GRAPH oldap:admin {{
            {user.toRdf} a oldap:User ; dcterms:modified {old_time.toRdf}
            {version_triple} . }} }}''')
        return AuthenticationRevocation.prepare(context=context, user=user, actor=user,
            expected=Xsd_nonNegativeInteger(version or 0), previous_modified=old_time, modified=new_time)

    def receipt(command, operation):
        rows = query(f'''SELECT ?digest ?version WHERE {{ GRAPH <{RECEIPTS}> {{
            <{NS}revocation:{operation}> <{NS}digest> ?digest ; <{NS}version> ?version .
        }} }}''')['results']['bindings']
        if not rows:
            return 'absent'
        # Never report success for conflicting reuse, duplicate or malformed data.
        if len(rows) != 1 or rows[0]['digest']['value'] != command.digest:
            return 'mismatch'
        version = rows[0]['version']
        if version.get('datatype') != 'http://www.w3.org/2001/XMLSchema#nonNegativeInteger':
            return 'mismatch'
        persisted = Xsd_nonNegativeInteger(version['value'])
        return int(persisted) if persisted.toRdf == command.updated else 'mismatch'

    def state(command, version, timestamp):
        return query(context.sparql_context + f'''ASK {{ GRAPH oldap:admin {{
            {command.user} oldap:authVersion "{version}"^^xsd:nonNegativeInteger ;
                dcterms:modified {timestamp.toRdf} ; dcterms:contributor {command.actor} .
        }} }}''')['boolean']

    first = seed('legacy', version=None)
    operation = uuid4()
    update(first.sparql_update(receipt_id=operation))
    check('Revocation: legacy missing version becomes one with metadata and receipt',
          receipt(first, operation) == 1 and state(first, 1, new_time))
    update(first.sparql_update(receipt_id=operation))
    check('Revocation: exact replay does not increment twice',
          receipt(first, operation) == 1 and state(first, 1, new_time))

    stale_id = uuid4()
    update(first.sparql_update(receipt_id=stale_id))
    check('Revocation: stale model produces no receipt or mutation',
          receipt(first, stale_id) == 'absent' and state(first, 1, new_time))

    next_time = Xsd_dateTime('2026-10-27T10:02:00Z')
    next_command = replace(first, expected=Xsd_nonNegativeInteger(1).toRdf,
                           updated=Xsd_nonNegativeInteger(2).toRdf,
                           previous_modified=new_time.toRdf, modified=next_time.toRdf)
    # Both inputs now match the live user. Only the receipt guard stops reuse.
    update(next_command.sparql_update(receipt_id=operation))
    check('Revocation: reused operation ID rejects changed payload without effects',
          receipt(next_command, operation) == 'mismatch' and state(first, 1, new_time))
    other_actor = replace(first, actor=Iri('https://example.org/other-actor').toRdf)
    update(other_actor.sparql_update(receipt_id=operation))
    check('Revocation: receipt identity binds actor', receipt(other_actor, operation) == 'mismatch')

    next_id = uuid4()
    update(next_command.sparql_update(receipt_id=next_id))
    update(first.sparql_update(receipt_id=operation))
    check('Revocation: old replay returns its own result after later revocation',
          receipt(first, operation) == 1 and receipt(next_command, next_id) == 2
          and state(next_command, 2, next_time))

    timestamp_conflict = seed('timestamp-conflict', version=3)
    wrong_timestamp = replace(timestamp_conflict, previous_modified=next_time.toRdf)
    wrong_id = uuid4()
    update(wrong_timestamp.sparql_update(receipt_id=wrong_id))
    check('Revocation: matching version with stale timestamp changes nothing',
          receipt(wrong_timestamp, wrong_id) == 'absent' and query(context.sparql_context +
          f'ASK {{ GRAPH oldap:admin {{ {timestamp_conflict.user} oldap:authVersion  "3"^^xsd:nonNegativeInteger ; dcterms:modified {old_time.toRdf} }} }}')['boolean'])

    race = seed('race', version=4)
    ids = [uuid4(), uuid4()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(update, race.sparql_update(receipt_id=i)) for i in ids]
        for future in futures:
            future.result(timeout=20)
    check('Revocation: concurrent distinct commands have one winner',
          sorted(str(receipt(race, i)) for i in ids) == ['5', 'absent'] and state(race, 5, new_time))

    duplicate = seed('concurrent-retry', version=7)
    duplicate_id = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(update, duplicate.sparql_update(receipt_id=duplicate_id)) for _ in range(2)]
        for future in futures:
            future.result(timeout=20)
    check('Revocation: concurrent identical retries increment once',
          receipt(duplicate, duplicate_id) == 8 and state(duplicate, 8, new_time))

    lost = seed('lost-response', version=10)
    lost_id = uuid4()
    # Commit, then intentionally discard the acknowledgement at the caller.
    # This models lost-response reconciliation, not a socket/crash fault injector.
    def discard_response():
        update(lost.sparql_update(receipt_id=lost_id))
        raise TimeoutError('Simulated loss after successful server response')
    try:
        discard_response()
    except TimeoutError:
        pass
    check('Revocation: receipt reconciles simulated lost acknowledgement', receipt(lost, lost_id) == 11)
    update(lost.sparql_update(receipt_id=lost_id))
    check('Revocation: exact retry after lost acknowledgement is safe', state(lost, 11, new_time))

    missing = seed('never-sent', version=2)
    check('Revocation: missing receipt alone does not prove rollback', receipt(missing, uuid4()) == 'absent')

    def verify_restart():
        """Verify successful receipts remain usable after graceful TDB2 restart."""
        check('Revocation: receipt and user state survive restart',
              receipt(lost, lost_id) == 11 and state(lost, 11, new_time))
    return verify_restart
