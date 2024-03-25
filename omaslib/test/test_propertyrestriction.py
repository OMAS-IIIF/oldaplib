import unittest
from copy import deepcopy

from rdflib import ConjunctiveGraph

from omaslib.src.dtypes.languagein import LanguageIn
from omaslib.src.dtypes.rdfset import RdfSet
from omaslib.src.enums.propertyrestrictiontype import PropertyRestrictionType
from omaslib.src.helpers.context import Context
from omaslib.src.propertyrestrictions import PropertyRestrictions
from omaslib.src.xsd.xsd_boolean import Xsd_boolean
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_float import Xsd_float
from omaslib.src.xsd.xsd_integer import Xsd_integer
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_string import Xsd_string


class TestPropertyRestrictions(unittest.TestCase):

    test_restrictions = {
        PropertyRestrictionType.LANGUAGE_IN: LanguageIn('de', 'fr', 'it', 'en'),
        PropertyRestrictionType.IN: RdfSet({Xsd_string('A'), Xsd_string('B'), Xsd_string('C')}),
        PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(True),
        PropertyRestrictionType.MIN_COUNT: Xsd_integer(1),
        PropertyRestrictionType.MAX_COUNT: Xsd_integer(4),
        PropertyRestrictionType.MIN_LENGTH: Xsd_integer(8),
        PropertyRestrictionType.MAX_LENGTH: Xsd_integer(64),
        PropertyRestrictionType.MIN_EXCLUSIVE: Xsd_float(6.5),
        PropertyRestrictionType.MIN_INCLUSIVE: Xsd_integer(8),
        PropertyRestrictionType.MAX_EXCLUSIVE: Xsd_float(6.5),
        PropertyRestrictionType.MAX_INCLUSIVE: Xsd_integer(8),
        PropertyRestrictionType.PATTERN: Xsd_string('.*'),
        PropertyRestrictionType.LESS_THAN: Xsd_QName('test:greater'),
        PropertyRestrictionType.LESS_THAN_OR_EQUALS: Xsd_QName('test:gaga')
    }
    test_restrictions2 = {
        PropertyRestrictionType.LANGUAGE_IN: LanguageIn('el', 'he'),
        PropertyRestrictionType.IN: RdfSet({Xsd_string('X'), Xsd_string('Y'), Xsd_string('Z')}),
        PropertyRestrictionType.UNIQUE_LANG: Xsd_boolean(False),
        PropertyRestrictionType.MIN_COUNT: Xsd_integer(0),
        PropertyRestrictionType.MAX_COUNT: Xsd_integer(10),
        PropertyRestrictionType.MIN_LENGTH: Xsd_integer(3),
        PropertyRestrictionType.MAX_LENGTH: Xsd_integer(12),
        PropertyRestrictionType.MIN_EXCLUSIVE: Xsd_float(10),
        PropertyRestrictionType.MIN_INCLUSIVE: Xsd_integer(80),
        PropertyRestrictionType.MAX_EXCLUSIVE: Xsd_float(65),
        PropertyRestrictionType.MAX_INCLUSIVE: Xsd_integer(80),
        PropertyRestrictionType.PATTERN: Xsd_string('^.*$'),
        PropertyRestrictionType.LESS_THAN: Xsd_QName('test:less_than'),
        PropertyRestrictionType.LESS_THAN_OR_EQUALS: Xsd_QName('test:gugus')
    }



    def test_constructor(self):
        val = PropertyRestrictions()
        val = PropertyRestrictions(restrictions=self.test_restrictions)
        self.assertEqual(len(val), 14)

        for key, expected_val in self.test_restrictions.items():
            self.assertEqual(val[key], expected_val)
        s = str(val)

    def test_restriction_setitem_on_empty(self):
        val = PropertyRestrictions()
        for key, newval in self.test_restrictions.items():
            val[key] = newval
        for key, expected_val in self.test_restrictions.items():
            self.assertEqual(val[key], expected_val)

    def test_restriction_setitem(self):
        restrictions = deepcopy(self.test_restrictions)
        val = PropertyRestrictions(restrictions=restrictions)
        for key, newval in self.test_restrictions2.items():
            val[key] = newval
        for key, expected_val in self.test_restrictions2.items():
            self.assertEqual(val[key], expected_val)

    def test_restriction_undo(self):
        restrictions = deepcopy(self.test_restrictions)
        val = PropertyRestrictions(restrictions=restrictions)
        for key, newval in self.test_restrictions2.items():
            val[key] = newval
        for key in self.test_restrictions2.keys():
            val.undo(key)
        for key, expected_val in self.test_restrictions.items():
            self.assertEqual(val[key], expected_val)

    def test_restriction_update_shacl(self):
        context = Context(name='hihi')
        context['test'] = "http://www.test.org/test#"

        r1 = PropertyRestrictions(restrictions=self.test_restrictions)
        modified = Xsd_dateTime()
        data = context.sparql_context
        data += f'''test:shacl {{
  test:testShape a sh:PropertyShape ;
    sh:path test:test {r1.create_shacl(indent=2, indent_inc=2)} ;
    dcterms:creator <https://orcid.org/0000-0003-1681-4036> ;
    dcterms:created {modified.toRdf} ;
    dcterms:contributor <https://orcid.org/0000-0003-1681-4036> ;
    dcterms:modified {modified.toRdf} ;
}} 
'''
        g1 = ConjunctiveGraph()
        g1.parse(data=data, format='trig')

        for key, newval in self.test_restrictions2.items():
            r1[key] = newval

        querystr = context.sparql_context
        querystr += r1.update_shacl(graph=Xsd_NCName('test'), prop_iri=Xsd_QName('test:test'), modified=modified)
        g1.update(querystr)



if __name__ == '__main__':
    unittest.main()
