from pprint import pprint
from typing import Set, List

from rdflib import Graph, URIRef, Literal, XSD, BNode

from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_base64binary import Xsd_base64Binary
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_byte import Xsd_byte
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_double import Xsd_double
from oldaplib.src.xsd.xsd_duration import Xsd_duration
from oldaplib.src.xsd.xsd_float import Xsd_float
from oldaplib.src.xsd.xsd_gday import Xsd_gDay
from oldaplib.src.xsd.xsd_gmonth import Xsd_gMonth
from oldaplib.src.xsd.xsd_gyear import Xsd_gYear
from oldaplib.src.xsd.xsd_gyearmonth import Xsd_gYearMonth
from oldaplib.src.xsd.xsd_hexbinary import Xsd_hexBinary
from oldaplib.src.xsd.xsd_id import Xsd_ID
from oldaplib.src.xsd.xsd_idref import Xsd_IDREF
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_language import Xsd_language
from oldaplib.src.xsd.xsd_long import Xsd_long
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_negativeinteger import Xsd_negativeInteger
from oldaplib.src.xsd.xsd_nmtoken import Xsd_NMTOKEN
from oldaplib.src.xsd.xsd_normalizedstring import Xsd_normalizedString
from oldaplib.src.xsd.xsd_positiveinteger import Xsd_positiveInteger
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_short import Xsd_short
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.xsd.xsd_time import Xsd_time
from oldaplib.src.xsd.xsd_token import Xsd_token
from oldaplib.src.xsd.xsd_unsignedbyte import Xsd_unsignedByte
from oldaplib.src.xsd.xsd_unsignedint import Xsd_unsignedInt
from oldaplib.src.xsd.xsd_unsignedlong import Xsd_unsignedLong
from oldaplib.src.xsd.xsd_unsignedshort import Xsd_unsignedShort


type ConstructResultDict = dict[Xsd_QName, ConstructResultDict | Xsd | LangString | List[Xsd] | Set[Xsd]]

class ConstructProcessor:

    @staticmethod
    def process(con: Context, g: Graph, as_langstrings: list[Xsd_QName | str] = []) -> ConstructResultDict:
        #print(g.serialize(format="turtle"))

        def process_rdfsets(nodes: dict):
            for key, val in nodes.items():
                 if isinstance(val, dict):
                    if not Xsd_QName('rdf:first') in val:
                        process_rdfsets(val)
                    else:
                        rdfset = {val[Xsd_QName('rdf:first')]}
                        tmpval = val
                        while not isinstance(tmpval, Xsd_QName):
                            rdfset.add(tmpval[Xsd_QName('rdf:first')])
                            tmpval = tmpval[Xsd_QName('rdf:rest')]
                        nodes[key] = rdfset

        topnodes: dict = {}
        bnodes: dict = {}
        to_ls = [x if isinstance(x, Xsd_QName) else Xsd_QName(x) for x in as_langstrings if x is not None]
        for s, p, o in g.triples((None, None, None)):
            if isinstance(p, URIRef):
                tmp = con.iri2qname(p)
                if tmp is not None:
                    p = tmp
            if isinstance(o, URIRef):
                tmp = con.iri2qname(o)
                o = tmp if tmp is not None else Iri(o)
            elif isinstance(o, Literal):
                match o.datatype:
                    case XSD.anyURI:
                        o = Xsd_anyURI(o)
                    case XSD.integer:
                        o = Xsd_integer(o)
                    case XSD.long:
                        o = Xsd_long(o)
                    case XSD.short:
                        o = Xsd_short(o)
                    case XSD.byte:
                        o = Xsd_byte(o)
                    case XSD.float:
                        o = Xsd_float(o)
                    case XSD.decimal:
                        o = Xsd_decimal(o)
                    case XSD.boolean:
                        o = Xsd_boolean(o)
                    case XSD.double:
                        o = Xsd_double(o)
                    case XSD.string:
                        o = Xsd_string(o)
                    case XSD.dateTime:
                        o = Xsd_dateTime(o)
                    case XSD.dateTimeStamp:
                        o = Xsd_dateTimeStamp(o)
                    case XSD.date:
                        o = Xsd_date(o)
                    case XSD.time:
                        o = Xsd_time(o)
                    case XSD.duration:
                        o = Xsd_duration(o)
                    case XSD.anyURI:
                        o = Xsd_anyURI(o)
                    case XSD.NCName:
                        o = Xsd_NCName(o)
                    case XSD.QName:
                        o = Xsd_QName(o)
                    case XSD.token:
                        o = Xsd_token(o)
                    case XSD.base64Binary:
                        o = Xsd_base64Binary(o)
                    case XSD.gDay:
                        o = Xsd_gDay(o)
                    case XSD.gMonth:
                        o = Xsd_gMonth(o)
                    case XSD.gYear:
                        o = Xsd_gYear(o)
                    case XSD.gYearMonth:
                        o = Xsd_gYearMonth(o)
                    case XSD.hexBinary:
                        o = Xsd_hexBinary(o)
                    case XSD.ID:
                        o = Xsd_ID(o)
                    case XSD.IDREF:
                        o = Xsd_IDREF(o)
                    case XSD.language:
                        o = Xsd_language(o)
                    case XSD.negativeInteger:
                        o = Xsd_negativeInteger(o)
                    case XSD.NMTOKEN:
                        o = Xsd_NMTOKEN(o)
                    case XSD.normalizedString:
                        o = Xsd_normalizedString(o)
                    case XSD.positiveInteger:
                        o = Xsd_positiveInteger(o)
                    case XSD.unsignedByte:
                        o = Xsd_unsignedByte(o)
                    case XSD.unsignedInt:
                        o = Xsd_unsignedInt(o)
                    case XSD.unsignedLong:
                        o = Xsd_unsignedLong(o)
                    case XSD.unsignedShort:
                        o = Xsd_unsignedShort(o)
                    case _:
                        if o.language:
                            o = Xsd_string(o, o.language)
                        else:
                            o = Xsd_string(o)

            if isinstance(s, BNode):
                if bnodes.get(s) is None:
                    bnodes[s] = {}
                if bnodes[s].get(p) is None:
                    bnodes[s][p] = o
                else:
                    if isinstance(bnodes[s][p], list):
                        bnodes[s][p].append(o)
                    else:
                        bnodes[s][p] = [bnodes[s][p], o]
            elif isinstance(s, URIRef):
                s = con.iri2qname(s)
                if topnodes.get(s) is None:
                    topnodes[s] = {}
                if topnodes[s].get(p) is None:
                    topnodes[s][p] = o
                else:
                    if isinstance(topnodes[s][p], list):
                        topnodes[s][p].append(o)
                    else:
                        topnodes[s][p] = [topnodes[s][p], o]

        #
        # rectify langstrings
        #
        for s in topnodes.keys():
            for p in topnodes[s].keys():
                if p in to_ls:
                    topnodes[s][p] = LangString(topnodes[s][p])
        for s in bnodes.keys():
            for p in bnodes[s].keys():
                if p in to_ls:
                    bnodes[s][p] = LangString(bnodes[s][p])

        #
        # Make dict of all
        #
        for s in bnodes.keys():
            for p in bnodes[s].keys():
                if isinstance(bnodes[s][p], BNode):
                    bnodes[s][p] = bnodes[bnodes[s][p]]

        for s in topnodes.keys():
            for p in topnodes[s].keys():
                if isinstance(topnodes[s][p], BNode):
                    topnodes[s][p] = bnodes[topnodes[s][p]]

        #
        # collapes rdfsets
        #
        process_rdfsets(topnodes)

        return topnodes
