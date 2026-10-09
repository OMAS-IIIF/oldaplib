"""Offline regression tests for membership-only roles and explicit object grants."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.objectfactory import ResourceInstance, ResourceInstanceFactory
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class TestResourceDefaultRoles(unittest.TestCase):
    def factory(self, roles):
        """Exercise factory initialization without reading a live repository."""
        connection = SimpleNamespace(_userdata=SimpleNamespace(hasRole=roles))
        with patch('oldaplib.src.objectfactory.Project.read'), patch('oldaplib.src.objectfactory.DataModel.read'):
            return ResourceInstanceFactory(connection, 'test')

    def instance(self, defaults, **kwargs):
        """Construct a minimal modeled object through the real constructor."""
        cls = type('TestResource', (ResourceInstance,), {
            'project': SimpleNamespace(projectShortName='test'),
            'name': 'TestResource', 'superclass': {},
            'properties': {Xsd_QName('oldap:attachedToRole'): SimpleNamespace(minCount=None, maxCount=None)},
            'validate_value': lambda *args: None,
            'user_default_roles': defaults,
        })
        return cls(**kwargs)

    def test_memberships_without_default_grants_are_not_copied(self):
        viewer, member = Xsd_QName('test:Viewer'), Xsd_QName('test:Member')
        roles = {viewer: Xsd_QName('oldap:DATA_VIEW'), member: None}
        factory = self.factory(roles)
        image = self.instance(factory._user_default_roles)
        self.assertEqual(dict(image.attachedToRole), {viewer: DataPermission.DATA_VIEW})
        self.assertEqual(image.attachedToRole[viewer].toRdf, 'oldap:DATA_VIEW')
        self.assertIn(member, roles)
        self.assertIsNone(roles[member])

    def test_empty_default_maps_are_owned_per_factory(self):
        for roles in [None, {}, {Xsd_QName('test:Member'): None}]:
            factory = self.factory(roles)
            other = self.factory(roles)
            self.assertEqual(factory._user_default_roles, {})
            self.assertIsNot(factory._user_default_roles, other._user_default_roles)
            self.assertEqual(dict(self.instance(factory._user_default_roles).attachedToRole), {})

    def test_explicit_invalid_grants_raise_domain_error(self):
        for value in [None, [], {'test:Member': None}, {'test:Member': 2}, {'test:Member': 'bogus'}]:
            with self.subTest(value=value), self.assertRaises(OldapErrorValue):
                self.instance({}, attachedToRole=value)

    def test_explicit_grants_override_defaults_including_empty_map(self):
        defaults = {Xsd_QName('test:Default'): DataPermission.DATA_VIEW}
        for value in ['DATA_UPDATE', 'oldap:DATA_UPDATE', DataPermission.DATA_UPDATE]:
            image = self.instance(defaults, attachedToRole={'test:Editor': value})
            self.assertEqual(dict(image.attachedToRole), {Xsd_QName('test:Editor'): DataPermission.DATA_UPDATE})
        self.assertEqual(dict(self.instance(defaults, attachedToRole={}).attachedToRole), {})
