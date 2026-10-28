"""Authorization parsing must not depend on an endpoint's SPARQL row order."""
import unittest
from itertools import permutations

from oldaplib.src.authentication import AuthorizationContext
from oldaplib.src.userdataclass import UserData
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class TestUserDataOrder(unittest.TestCase):
    def test_permissions_survive_every_membership_annotation_order(self):
        user = Iri('https://example.org/user')
        project = Iri('https://example.org/project')
        role = Xsd_QName('oldap:Editor')
        properties = [
            {'user': user, 'prop': Xsd_QName('dcterms:creator'), 'val': user},
            {'user': user, 'prop': Xsd_QName('oldap:userId'), 'val': Xsd_NCName('reader')},
        ]
        rows = [
            {'user': user, 'prop': Xsd_QName('oldap:inProject'), 'val': project},
            {'user': user, 'proj': project, 'rval': Xsd_QName('oldap:ADMIN_USERS')},
            {'user': user, 'prop': Xsd_QName('oldap:hasRole'), 'val': role},
            {'user': user, 'role': role, 'defdp': Xsd_QName('oldap:DATA_UPDATE')},
        ]
        for ordering in permutations(rows):
            context = AuthorizationContext.from_user_data(UserData.from_query(properties + list(ordering)))
            self.assertEqual(context.to_claims(), {
                'inProject': {str(project): ['oldap:ADMIN_USERS']},
                'hasRole': {'oldap:Editor': 'oldap:DATA_UPDATE'},
            })


if __name__ == '__main__':
    unittest.main()
