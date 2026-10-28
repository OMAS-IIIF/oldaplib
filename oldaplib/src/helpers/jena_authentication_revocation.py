"""Internal, opt-in Fuseki revocation execution; no login/backend auto-selection.

Self and administrator revocation use atomic RDF 1.2 grant checks. The owner supplies protected update/query transport, preserves
receipt identity for recovery, and rejects joining an interactive transaction.
Receipts use the experimental pilot graph and must not be removed or modified.
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from oldaplib.src.helpers.authentication_revocation import AuthenticationRevocation
from oldaplib.src.helpers.oldaperror import (
    OldapError, OldapErrorInconsistency, OldapErrorNoPermission, OldapErrorUpdateFailed,
)
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger


@dataclass(frozen=True)
class RevocationAttempt:
    """Keep exact command/identity for internal reconciliation, never new inputs."""

    command: AuthenticationRevocation
    receipt_id: UUID

    @classmethod
    def prepare(cls, command: AuthenticationRevocation) -> 'RevocationAttempt':
        """Allocate one internal identity before the first transmission."""
        return cls(command, uuid4())

    def confirmed(self, query: Callable[[str], dict[str, Any]]) -> bool:
        """Read and strictly validate an immutable receipt.

        Returns:
            True for this exact committed command, False for no receipt.
            False alone never proves rollback after uncertain transmission.
        Raises:
            OldapErrorNoPermission: The atomic decision denied this command.
            OldapErrorInconsistency: Existing receipt is malformed or belongs
                to different inputs. Transport/read failures propagate.
        """
        result = query(f'''SELECT ?predicate ?value WHERE {{
            GRAPH <urn:oldap:jena-pilot:revocation-receipts> {{
                <urn:oldap:jena-pilot:revocation:{self.receipt_id}> ?predicate ?value .
            }}
        }}''')
        rows = result['results']['bindings']
        if not rows:
            return False
        statuses = [row['value'] for row in rows
                    if row['predicate'].get('value') == 'urn:oldap:jena-pilot:status']
        if len(statuses) != 1 or statuses[0].get('value') not in ('committed', 'denied'):
            raise OldapErrorInconsistency('Missing or invalid authentication revocation status.')
        outcome = statuses[0]['value']
        expected = {
            'urn:oldap:jena-pilot:digest': ('http://www.w3.org/2001/XMLSchema#string', self.command.digest),
            'urn:oldap:jena-pilot:status': ('http://www.w3.org/2001/XMLSchema#string', outcome),
        }
        if outcome == 'committed':
            expected['urn:oldap:jena-pilot:version'] = (
                'http://www.w3.org/2001/XMLSchema#nonNegativeInteger', self.command.updated)
        seen = set()
        for row in rows:
            predicate, value = row['predicate'], row['value']
            key = predicate['value']
            if predicate['type'] != 'uri' or key not in expected or key in seen:
                raise OldapErrorInconsistency('Invalid authentication revocation receipt.')
            datatype, wanted = expected[key]
            # SPARQL JSON may omit the datatype for a plain xsd:string literal.
            if (value['type'] not in ('literal', 'typed-literal') or 'xml:lang' in value
                    or value.get('datatype', 'http://www.w3.org/2001/XMLSchema#string') != datatype):
                raise OldapErrorInconsistency('Invalid authentication revocation receipt value.')
            actual = value['value']
            if key.endswith(':version'):
                actual = Xsd_nonNegativeInteger(actual).toRdf
            if actual != wanted:
                raise OldapErrorInconsistency('Authentication revocation receipt does not match the command.')
            seen.add(key)
        if seen != expected.keys():
            raise OldapErrorInconsistency('Incomplete authentication revocation receipt.')
        if outcome == 'denied':
            raise OldapErrorNoPermission('Actor may not revoke authentication for this user.')
        return True

    def execute(self, *, update: Callable[[str], Any],
                query: Callable[[str], dict[str, Any]]) -> None:
        """Send one mutation, then reconcile; never retry implicitly.

        ``update`` must return only for an acknowledged successful HTTP update
        and raise on non-success or uncertain delivery. On failure, a matching
        receipt can still establish success. Without one the outcome is unknown,
        not a revision conflict. Keep this attempt for later reconciliation.
        Success does not update a Python User or invalidate Redis; its owner does.
        """
        acknowledged = False
        send_error = None
        try:
            update(self.command.sparql_update(receipt_id=self.receipt_id))
            acknowledged = True
        except (OSError, OldapError) as error:
            send_error = error
        try:
            confirmed = self.confirmed(query)
        except (OldapErrorInconsistency, OldapErrorNoPermission):
            raise
        except (OSError, OldapError, ValueError, KeyError, TypeError) as error:
            raise OldapError(
                f'Authentication revocation outcome unknown; receipt {self.receipt_id}.') from error
        if confirmed:
            return
        if acknowledged:
            raise OldapErrorUpdateFailed('Authentication revocation conflicted with another update.')
        raise OldapError(
            f'Authentication revocation outcome unknown; receipt {self.receipt_id}.') from send_error
