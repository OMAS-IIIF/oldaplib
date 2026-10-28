"""Internal SPARQL preparation for authentication revocation.

The normal User path still owns a GraphDB transaction and verifies its writes.
The optional receipt is for the isolated Jena pilot only: it couples the mutation
and an immutable outcome in one guarded update. Receipt mode rechecks administrative grants atomically using RDF 1.2 reifiers.
The caller still authenticates the actor; this module performs no I/O, cache
invalidation or automatic retries.
"""
from dataclasses import dataclass
import hashlib
import json
from uuid import UUID

from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger


@dataclass(frozen=True)
class AuthenticationRevocation:
    """Snapshot the serialized inputs of one revocation before sending it.

    Construct with ``prepare`` so RDF values are escaped by OLDAP's serializers.
    Reuse this exact snapshot, including timestamp and receipt ID, for retries.
    Receipt graphs must be private and protected from unrelated writers.
    """

    prefixes: str
    user: str
    actor: str
    expected: str
    previous_modified: str
    modified: str
    updated: str

    @classmethod
    def prepare(cls, *, context: Context, user: Iri, actor: Iri,
                expected: Xsd_nonNegativeInteger, previous_modified: Xsd_dateTime,
                modified: Xsd_dateTime) -> 'AuthenticationRevocation':
        """Copy typed inputs to immutable RDF strings; do not mutate the user."""
        return cls(context.sparql_context, user.toRdf, actor.toRdf, expected.toRdf,
                   previous_modified.toRdf, modified.toRdf,
                   Xsd_nonNegativeInteger(int(expected) + 1).toRdf)

    @property
    def digest(self) -> str:
        """Bind the operation kind, context, actor, target and all mutation inputs."""
        payload = json.dumps(
            ['oldap-authentication-revocation-v2', self.prefixes, self.user,
             self.actor, self.expected, self.previous_modified, self.modified, self.updated],
            ensure_ascii=True, separators=(',', ':'),
        )
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def sparql_update(self, *, receipt_id: UUID | None = None) -> str:
        """Build the existing guarded update, optionally with a pilot receipt.

        Args:
            receipt_id: Internal UUID reused for an exact retry, never a new
                public User argument. None preserves the GraphDB update path.

        Returns:
            Complete SPARQL UPDATE. A successful HTTP status alone does not
            establish whether its WHERE matched. The owner must verify it.
        """
        receipt_insert = ''
        receipt_guard = ''
        write_user = '?user'
        if receipt_id is not None:
            write_user = '?writeUser'
            # Keep experimental receipt vocabulary out of the OLDAP ontology.
            receipt = f'<urn:oldap:jena-pilot:revocation:{UUID(str(receipt_id))}>'
            receipt_insert = f'''
            GRAPH <urn:oldap:jena-pilot:revocation-receipts> {{
                {receipt} <urn:oldap:jena-pilot:digest> "{self.digest}" ;
                    <urn:oldap:jena-pilot:status> ?outcome ;
                    <urn:oldap:jena-pilot:version> ?resultVersion .
            }}'''
            receipt_guard = f'''
            FILTER NOT EXISTS {{ GRAPH <urn:oldap:jena-pilot:revocation-receipts> {{
                {receipt} ?receiptPredicate ?receiptValue .
            }} }}
            BIND((
                {self.actor} = ?user ||
                EXISTS {{ GRAPH oldap:admin {{
                    {self.actor} oldap:inProject oldap:SystemProject .
                    ?rootGrant rdf:reifies <<( {self.actor} oldap:inProject oldap:SystemProject )>> ;
                        oldap:hasAdminPermission oldap:ADMIN_OLDAP .
                }} }} ||
                (EXISTS {{ GRAPH oldap:admin {{ ?user oldap:inProject ?someProject }} }} &&
                 NOT EXISTS {{ GRAPH oldap:admin {{
                    ?user oldap:inProject ?targetProject .
                    FILTER NOT EXISTS {{
                        {self.actor} oldap:inProject ?targetProject .
                        ?projectGrant rdf:reifies <<( {self.actor} oldap:inProject ?targetProject )>> ;
                            oldap:hasAdminPermission oldap:ADMIN_USERS .
                    }}
                 }} }})
            ) AS ?authorized)
            BIND(IF(?authorized, "committed", "denied") AS ?outcome)
            BIND(IF(?authorized, ?user, ?unboundOnDenial) AS ?writeUser)
            BIND(IF(?authorized, {self.updated}, ?unboundOnDenial) AS ?resultVersion)
            '''
            # Unbound template variables omit user mutations/version on denial;
            # the denial receipt still commits under the same snapshot/guard.
        return self.prefixes + f'''
        WITH oldap:admin
        DELETE {{
            {write_user} oldap:authVersion ?storedVersion .
            {write_user} dcterms:contributor ?oldContributor .
            {write_user} dcterms:modified {self.previous_modified} .
        }}
        INSERT {{
            {write_user} oldap:authVersion {self.updated} .
            {write_user} dcterms:contributor {self.actor} .
            {write_user} dcterms:modified {self.modified} .
            {receipt_insert}
        }}
        WHERE {{
            BIND({self.user} AS ?user)
            ?user a oldap:User .
            ?user dcterms:modified {self.previous_modified} .
            OPTIONAL {{ ?user dcterms:contributor ?oldContributor . }}
            OPTIONAL {{ ?user oldap:authVersion ?storedVersion . }}
            FILTER(COALESCE(?storedVersion, "0"^^xsd:nonNegativeInteger) = {self.expected})
            {receipt_guard}
        }}
        '''
