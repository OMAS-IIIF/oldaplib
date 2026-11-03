"""Public user serialization keeps GraphDB defaults and opts into RDF 1.2."""
from unittest.mock import Mock

from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.iconnection import IConnection
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime


def user(rdf12=False):
    """Build an offline user with one grant and one bare project membership."""
    con = Mock(spec=IConnection)
    con.context_name = 'USER_WRITE_UNIT'
    con._user_permissions_rdf12 = rdf12
    con.userIri = Iri('https://example.org/actor')
    return User(con=con, userIri=Iri('https://example.org/user'), userId='writer',
                familyName='Example', givenName='Writer', email='writer@example.org',
                credentials='$2b$synthetic-unused-test-hash',
                inProject={Iri('https://example.org/project'): {AdminPermission.ADMIN_USERS},
                           Iri('https://example.org/bare'): set()},
                hasRole={Xsd_QName('oldap:Reader'): DataPermission.DATA_VIEW})


def serialize(value):
    timestamp = Xsd_dateTime('2026-10-28T10:00:00Z')
    actor = Iri('https://example.org/actor')
    return value.trig_to_str(actor, timestamp, actor, timestamp)


def test_graphdb_serialization_retains_rdfstar_default():
    output = serialize(user())
    assert '<<' in output and 'rdf:reifies' not in output
    assert ('<<<https://example.org/user> oldap:inProject <https://example.org/project>>>'
            ' oldap:hasAdminPermission oldap:ADMIN_USERS .') in output
    assert ('<<<https://example.org/user> oldap:hasRole oldap:Reader>>'
            ' oldap:hasDefaultDataPermission oldap:DATA_VIEW .') in output


def test_jena_serialization_keeps_bare_membership_and_separate_grants():
    output = serialize(user(True))
    assert 'oldap:inProject <https://example.org/project>, <https://example.org/bare>' in output
    assert output.count('rdf:reifies') == 2
    assert '<<( <https://example.org/user> oldap:inProject <https://example.org/project> )>>' in output
    assert '<<( <https://example.org/user> oldap:hasRole oldap:Reader )>>' in output
    assert 'oldap:hasRole oldap:Reader' in output
    identifiers = [line.split()[0] for line in output.splitlines() if 'rdf:reifies' in line]
    assert len(set(identifiers)) == 2


def test_legacy_connection_without_capability_stays_graphdb():
    value = user()
    del value._con._user_permissions_rdf12
    assert 'rdf:reifies' not in serialize(value)
