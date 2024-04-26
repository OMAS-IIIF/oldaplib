import json
import unittest

from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorKey
from omaslib.src.helpers.serializer import serializer
from omaslib.src.in_project import InProjectClass
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_string import Xsd_string


class TestInproject(unittest.TestCase):
    def test_creation(self):
        ip = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                             'https://gaga.com/test': {'ADMIN_MODEL'},
                             Xsd_QName('gaga:gugus'): set()})

        with self.assertRaises(OmasErrorValue) as ex:
            ip = InProjectClass({'test': {'ADMIN_MODEL'}})

        with self.assertRaises(OmasErrorValue) as ex:
            ip = InProjectClass({'test:proj': {'MODEL_T'}})

    def test_get_item(self):
        ip = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                             'https://gaga.com/test': {'ADMIN_MODEL'},
                             Iri('gaga:gugus'): set()})
        self.assertEqual(ip['test:proj'], {AdminPermission.ADMIN_PERMISSION_SETS, AdminPermission.ADMIN_RESOURCES})
        self.assertEqual(ip['https://gaga.com/test'], {AdminPermission.ADMIN_MODEL})
        self.assertEqual(ip[Iri('gaga:gugus')], set())

        with self.assertRaises(OmasErrorValue) as ex:
            tmp = ip['gaga']
        with self.assertRaises(OmasErrorValue) as ex:
            tmp = ip['$<>12']
        with self.assertRaises(OmasErrorValue) as ex:
            tmp = ip[Xsd_string('test:proj')]

    def test_set_item(self):
        ip = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                             'https://gaga.com/test': {'ADMIN_MODEL'},
                             Xsd_QName('gaga:gugus'): set()})
        ip['test:proj'] = {AdminPermission.ADMIN_OLDAP}
        self.assertEqual(ip['test:proj'], {AdminPermission.ADMIN_OLDAP})
        ip['https://gaga.com/test'] = {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'}
        self.assertEqual(ip['https://gaga.com/test'], {AdminPermission.ADMIN_PERMISSION_SETS, AdminPermission.ADMIN_RESOURCES})
        ip[Xsd_QName('gaga:gugus')] = {'ADMIN_MODEL'}
        self.assertEqual(ip[Xsd_QName('gaga:gugus')], {AdminPermission.ADMIN_MODEL})

        with self.assertRaises(OmasErrorValue) as ex:
            ip[Xsd_QName('gaga:gugus')] = {'GAGA'}
        with self.assertRaises(OmasErrorValue) as ex:
            ip[Xsd_QName('XYZ')] = {'ADMIN_MODEL'}

    def test_del_item(self):
        ip = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                             'https://gaga.com/test': {'ADMIN_MODEL'},
                             Xsd_QName('gaga:gugus'): set()})
        del ip['test:proj']
        with self.assertRaises(OmasErrorKey) as ex:
            tmp = ip['test:proj']

        with self.assertRaises(OmasErrorKey) as ex:
            del ip[Xsd_QName('gaga:blabla')]

    def test_str(self):
        ip = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                             'https://gaga.com/test': {'ADMIN_MODEL'},
                             Xsd_QName('gaga:gugus'): set()})
        projs = str(ip).strip().split('\n')
        projs = [x.strip() for x in projs]
        for projstr in projs:
            proj, permset = projstr.split(' : ')
            match proj:
                case 'test:proj':
                    self.assertEqual(permset, "['omas:ADMIN_PERMISSION_SETS', 'omas:ADMIN_RESOURCES']")
                case 'https://gaga.com/test':
                    self.assertEqual(permset, "['omas:ADMIN_MODEL']")
                case 'gaga:gugus':
                    self.assertEqual(permset, "[]")
                case _:
                    raise Exception("Unexpected project")

    def test_bool(self):
        ip = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                             'https://gaga.com/test': {'ADMIN_MODEL'},
                             Xsd_QName('gaga:gugus'): set()})
        self.assertTrue(bool(ip))

    def test_serialization(self):
        val = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                              'https://gaga.com/test': {'ADMIN_MODEL'},
                              Xsd_QName('gaga:gugus'): set()})
        jsonstr = json.dumps(val, default=serializer.encoder_default)
        val2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
        self.assertEqual(val, val2)

    def test_copy_eq_ne(self):
        val = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                              'https://gaga.com/test': {'ADMIN_MODEL'},
                              Xsd_QName('gaga:gugus'): set()})
        val2 = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                              'https://gaga.com/test': {'ADMIN_MODEL'},
                              Xsd_QName('gaga:gugus'): set()})
        self.assertTrue(val == val2)
        self.assertFalse(val != val2)

        val = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                              'https://gaga.com/test': {'ADMIN_MODEL'},
                              Xsd_QName('gaga:gugus'): set()})
        val2 = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                              'https://gaga.com/test': {'ADMIN_MODEL'},
                              Xsd_QName('gaga:gaga'): set()})
        self.assertFalse(val == val2)
        self.assertTrue(val != val2)

        val = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                              'https://gaga.com/test': {'ADMIN_MODEL'},
                              Xsd_QName('gaga:gugus'): {AdminPermission.ADMIN_RESOURCES}})
        val2 = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                              'https://gaga.com/test': {'ADMIN_MODEL'},
                              Xsd_QName('gaga:gugus'): {AdminPermission.ADMIN_RESOURCES, AdminPermission.ADMIN_PERMISSION_SETS}})
        self.assertFalse(val == val2)
        self.assertTrue(val != val2)


    def test_items(self):
        ip = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                             'https://gaga.com/test': {'ADMIN_MODEL'},
                             Xsd_QName('gaga:gugus'): set()})
        for proj, perms in ip.items():
            self.assertTrue(proj in ['test:proj', 'https://gaga.com/test', Iri('gaga:gugus')])

    def test_keys(self):
        ip = InProjectClass({'test:proj': {AdminPermission.ADMIN_PERMISSION_SETS, 'omas:ADMIN_RESOURCES'},
                             'https://gaga.com/test': {'ADMIN_MODEL'},
                             Iri('gaga:gugus'): set()})
        keys = set(ip.keys())
        self.assertEqual(keys, {'test:proj', 'https://gaga.com/test', Iri('gaga:gugus')})


if __name__ == '__main__':
    unittest.main()
