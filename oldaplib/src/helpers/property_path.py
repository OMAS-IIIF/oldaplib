"""Decode the supported SHACL field paths without changing public field identity."""
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def decode_property_path(shape):
    """Return a copy with a stable path key and optional inversePath attribute.

    Stored inverse shapes use ``oldap:field`` as the API key and
    ``sh:path [ sh:inversePath predicate ]`` as their read path. Only a single
    inverse predicate is supported; malformed or compound paths fail explicitly.
    The returned mapping is library model input, not RDF to serialize verbatim.
    """
    result = dict(shape)
    path = result.get(Xsd_QName('sh:path'))
    field = result.pop(Xsd_QName('oldap:field'), None)
    if isinstance(path, dict):
        inverse = path.get(Xsd_QName('sh:inversePath'))
        if set(path) != {Xsd_QName('sh:inversePath')} or not isinstance(inverse, Xsd_QName) or not isinstance(field, Xsd_QName):
            raise OldapErrorInconsistency('Inverse fields require oldap:field and a single QName sh:inversePath.')
        result[Xsd_QName('sh:path')] = field
        result[Xsd_QName('sh:inversePath')] = inverse
    elif field is not None:
        raise OldapErrorInconsistency('oldap:field is reserved for inverse property shapes.')
    return result
