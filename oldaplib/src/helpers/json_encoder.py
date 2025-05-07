import json
from datetime import datetime

from oldaplib.src.helpers.oldaperror import OldapErrorType


class SpecialEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except:
            if type(obj).__name__ == 'OldapListNode' :
                jsonobj = {
                    'oldapListNodeId': str(obj.oldapListNodeId),
                    'created': str(obj.created),
                    'creator': str(obj.creator),
                    'modified': str(obj.modified),
                    'contributor': str(obj.contributor),
                    'iri': str(obj.iri)
                }
                if obj.prefLabel:
                    jsonobj['prefLabel'] = obj.prefLabel
                if obj.definition:
                    jsonobj['definition'] = obj.definition
                if obj.nodes:
                    jsonobj['nodes'] = obj.nodes
                return jsonobj
            elif type(obj).__name__ == 'OldapList':
                jsonobj = {
                    'oldapListId': str(obj.oldapListId),
                    'created': str(obj.created),
                    'creator': str(obj.creator),
                    'modified': str(obj.modified),
                    'contributor': str(obj.contributor),
                    'nodeClassIri': str(obj.node_classIri),
                    'nodeNamespaceIri': str(obj.node_namespaceIri),
                    'nodePrefix': str(obj.node_prefix),
                    'iri': str(obj.iri)
                }
                if obj.prefLabel:
                    jsonobj['prefLabel'] = obj.prefLabel
                if obj.definition:
                    jsonobj['definition'] = obj.definition
                if obj.nodes:
                    jsonobj['nodes'] = obj.nodes
                return jsonobj
            elif type(obj).__name__ == 'LangString':
                return [str(x) for x in obj]
            elif type(obj).__name__ == 'Xsd_dateTime':
                return str(obj)
            else:
                raise OldapErrorType(f'SpecialEncoder: Cannot convert to JSON: "{type(obj).__name__}"')
