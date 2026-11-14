"""Property history for Thing instances; all writes join resource transactions.

Values remain RDF terms. Dating subgraphs are frozen as N-Triples literals so
later edits to their live IRIs cannot alter historical states. History is never
used as an application data graph or a fulltext source.
"""
from dataclasses import dataclass
import json
from uuid import uuid4

from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef, XSD

from rdflib.compare import isomorphic

from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.construct_processor import ConstructProcessor
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapErrorValue, OldapErrorUpdateFailed
from oldaplib.src.resource_transaction import resource_query, resource_transaction
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp

H = Namespace('http://oldap.org/base#')
SYSTEM_PROPERTIES = frozenset(H[name] for name in (
    'createdBy', 'creationDate', 'lastModifiedBy', 'lastModificationDate',
    'attachedToRole', 'hasDataPermission',
    'historyResource', 'historyProperty', 'historyUser', 'historyTimestamp',
    'historyValue', 'historyDatingSnapshot', 'historyReifierSnapshot',
)) | {RDF.type}


def _uri(context, value) -> URIRef:
    """Expand a validated OLDAP IRI/QName to its canonical RDF identity."""
    iri = value if isinstance(value, Iri) else Iri(str(value))
    return URIRef(str(context.qname2iri(iri.as_qname)) if iri.is_qname else str(iri))


def history_properties(instance, properties=None) -> dict:
    """Select writable, modeled business properties, including inherited ones."""
    from oldaplib.src.objectfactory import resource_class_is_or_extends
    if not resource_class_is_or_extends(type(instance), 'oldap:Thing'):
        return {}
    context = Context(name=instance._con.context_name)
    return {key: prop for key, prop in (instance.properties if properties is None else properties).items()
            if _uri(context, key) not in SYSTEM_PROPERTIES and prop.inversePath is None}


def capture_properties(instance, properties) -> dict:
    """Read only selected explicit values and their Dating closures in one query.

    Must run inside the mutation transaction. Also reject stale resource objects
    before writing, even when an old property value would otherwise still match.
    Returns a property-to-RDF-snapshot mapping; absent properties have empty graphs.
    """
    properties = history_properties(instance, properties)
    if not properties:
        return {}
    context = Context(name=instance._con.context_name)
    predicates = ' '.join(key.toRdf for key in properties)
    query = context.sparql_context + f'''
    CONSTRUCT {{ {instance.iri.toRdf} ?p ?v . ?node ?dp ?dv . }}
    WHERE {{ GRAPH {instance._graph}:data {{
      {{ VALUES ?p {{ {predicates} oldap:lastModificationDate }}
         {instance.iri.toRdf} ?p ?v . }}
      OPTIONAL {{ ?v a oldap:Dating ; oldap:before* ?node . ?node ?dp ?dv . }}
    }} }}'''
    graph = resource_query(instance._con, query, format=SparqlResultFormat.JSONLD)
    subject = _uri(context, instance.iri)
    modified = graph.value(subject, H.lastModificationDate)
    if modified is None or Xsd_dateTimeStamp(str(modified)) != instance.lastModificationDate:
        raise OldapErrorUpdateFailed('Resource changed since it was read; read it again.')
    snapshots = {key: _property_graph(graph, subject, _uri(context, key)) for key in properties}
    state = getattr(instance, '_annotation_write', None)
    if state is not None:
        from oldaplib.src.assertion_annotation import snapshot
        for key, graph in snapshots.items():
            graph.add((subject, H.historyReifierSnapshot, Literal(snapshot(state.before, _uri(context, key)))))
    return snapshots


def _property_graph(graph, subject, predicate) -> Graph:
    """Copy one value set and reachable Dating nodes without following object links."""
    result = Graph()
    pending = []
    for value in graph.objects(subject, predicate):
        result.add((subject, predicate, value))
        if (value, RDF.type, H.Dating) in graph:
            pending.append(value)
    seen = set()
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        for triple in graph.triples((node, None, None)):
            result.add(triple)
        pending.extend(graph.objects(node, H.before))
    return result


def _same_state(left: Graph, right: Graph) -> bool:
    """Compare Dating content independently of generated implementation IRIs."""
    if set(left) == set(right):
        return True
    if len(left) != len(right):
        return False

    def anonymous_dates(graph):
        nodes = {node: BNode() for node in graph.subjects(RDF.type, H.Dating)}
        result = Graph()
        for subject, predicate, value in graph:
            result.add((nodes.get(subject, subject), predicate, nodes.get(value, value)))
        return result

    return isomorphic(anonymous_dates(left), anonymous_dates(right))


def record_changes(instance, before, timestamp) -> None:
    """Append changed property states after successful writes, before commit.

    Comparing actual RDF avoids history for no-op updates, independent of how a
    setter or observable collection represented its changeset.
    """
    if not before:
        return
    context = Context(name=instance._con.context_name)
    subject = _uri(context, instance.iri)
    predicates = ' '.join(key.toRdf for key in before)
    query = context.sparql_context + f'''
    CONSTRUCT {{ {instance.iri.toRdf} ?p ?v . ?node ?dp ?dv . }}
    WHERE {{ GRAPH {instance._graph}:data {{
      VALUES ?p {{ {predicates} }} {instance.iri.toRdf} ?p ?v .
      OPTIONAL {{ ?v a oldap:Dating ; oldap:before* ?node . ?node ?dp ?dv . }}
    }} }}'''
    after = resource_query(instance._con, query, format=SparqlResultFormat.JSONLD)
    records = Graph()
    for prop, snapshot in before.items():
        predicate = _uri(context, prop)
        current = _property_graph(after, subject, predicate)
        state = getattr(instance, '_annotation_write', None)
        if state is not None:
            from oldaplib.src.assertion_annotation import snapshot as annotation_snapshot
            current.add((subject, H.historyReifierSnapshot, Literal(annotation_snapshot(state.after, predicate))))
        if _same_state(snapshot, current):
            continue
        entry = URIRef(f'urn:uuid:{uuid4()}')
        records.add((entry, RDF.type, H.PropertyHistory))
        records.add((entry, H.historyResource, subject))
        records.add((entry, H.historyProperty, predicate))
        records.add((entry, H.historyUser, _uri(context, instance._con.userIri)))
        records.add((entry, H.historyTimestamp, Literal(str(timestamp), datatype=XSD.dateTimeStamp)))
        for value in snapshot.objects(subject, predicate):
            records.add((entry, H.historyValue, value))
        annotations = snapshot.value(subject, H.historyReifierSnapshot)
        if annotations is not None:
            records.add((entry, H.historyReifierSnapshot, annotations))
        nested = Graph()
        for triple in snapshot:
            if triple[0] != subject:
                nested.add(triple)
        if nested:
            records.add((entry, H.historyDatingSnapshot, Literal(nested.serialize(format='nt'))))
    if records:
        instance._con.transaction_update(context.sparql_context +
            f'INSERT DATA {{ GRAPH {instance._graph}:history {{ {records.serialize(format="nt")} }} }}')


@dataclass(frozen=True)
class PropertyHistoryEntry:
    """One previous complete value set; an empty tuple represents absence.

    Values are typed OLDAP values suitable for ordinary property assignment.
    The timestamp describes replacement, not creation of the previous values.
    """
    iri: Iri
    timestamp: Xsd_dateTimeStamp
    user_iri: Iri
    resource_iri: Iri
    property_iri: Xsd_QName | Iri
    values: tuple[object, ...]
    annotations: tuple[dict, ...] = ()


class ResourceHistory:
    """Read and restore project property history with current resource permissions.

    Args:
        con: Authenticated connection; task-local, as for ResourceInstanceFactory.
        project: Project identifier accepted by ResourceInstanceFactory.
    """

    def __init__(self, con, project):
        from oldaplib.src.objectfactory import ResourceInstanceFactory
        self.factory = ResourceInstanceFactory(con=con, project=project)
        self.con = con

    def list(self, resource_iri: Iri | str, *, property_iri: Iri | str | None = None,
             limit: int = 100, offset: int = 0) -> list[PropertyHistoryEntry]:
        """Return newest entries first after a fresh permission-checked read.

        Pagination counts entries, never individual values. Timestamp ties use
        entry IRI for deterministic ordering, not a causal sequence guarantee.
        Raises OldapErrorValue for invalid paging/property filters and the normal
        resource-read error for missing or inaccessible instances.
        """
        if type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
            raise OldapErrorValue('limit must be 1..1000 and offset must be nonnegative.')
        instance = self.factory.read(resource_iri)
        return self._read(instance, property_iri=property_iri, limit=limit, offset=offset)

    def get(self, resource_iri, entry_iri) -> PropertyHistoryEntry:
        """Read one entry bound to this project and currently readable instance."""
        instance = self.factory.read(resource_iri)
        entries = self._read(instance, entry_iri=Iri(str(entry_iri)))
        if not entries:
            raise OldapErrorNotFound('History entry not found for this resource.')
        return entries[0]

    def _read(self, instance, *, property_iri=None, entry_iri=None, limit=1, offset=0):
        """Fetch entry metadata and values together, paging before value expansion."""
        from oldaplib.src.objectfactory import _alias_requested_subjects, _normalize_construct_property, _construct_subject_key
        context = Context(name=self.con.context_name)
        allowed = history_properties(instance)
        from oldaplib.src.objectfactory import resource_class_is_or_extends
        if not resource_class_is_or_extends(type(instance), 'oldap:Thing'):
            return []
        # Entries remain readable after model changes, but can only be restored
        # if the property is writable in the current model.
        property_filter = ''
        if property_iri is not None:
            predicate = _uri(context, property_iri)
            if predicate in SYSTEM_PROPERTIES:
                raise OldapErrorValue('System properties have no property history.')
            property_filter = f'VALUES ?property {{ {predicate.n3()} }}'
        excluded = ', '.join(value.n3() for value in SYSTEM_PROPERTIES)
        entry_filter = f'VALUES ?entry {{ {entry_iri.toRdf} }}' if entry_iri else ''
        query = context.sparql_context + f'''
        CONSTRUCT {{ ?entry ?p ?v . }} WHERE {{
          {{ SELECT ?entry ?time WHERE {{ GRAPH {instance._graph}:history {{
            {entry_filter} {property_filter}
            FILTER(?property NOT IN ({excluded}))
            ?entry a oldap:PropertyHistory ; oldap:historyResource {instance.iri.toRdf} ;
              oldap:historyProperty ?property ; oldap:historyTimestamp ?time .
          }} }} ORDER BY DESC(?time) DESC(?entry) LIMIT {limit} OFFSET {offset} }}
          GRAPH {instance._graph}:history {{ ?entry ?p ?v . }}
        }}'''
        graph = resource_query(self.con, query, format=SparqlResultFormat.JSONLD)
        result = []
        subject = _uri(context, instance.iri)
        for entry in graph.subjects(RDF.type, H.PropertyHistory):
            predicate = graph.value(entry, H.historyProperty)
            prop = context.iri2qname(predicate) or Iri(str(predicate))
            snapshot = Graph()
            for value in graph.objects(entry, H.historyValue):
                snapshot.add((subject, predicate, value))
            dating = graph.value(entry, H.historyDatingSnapshot)
            if dating is not None:
                snapshot.parse(data=str(dating), format='nt')
            decoded = _alias_requested_subjects(context, ConstructProcessor.process(context, snapshot), [instance.iri])
            node = decoded.get(_construct_subject_key(instance.iri), {})
            raw = node.get(prop, node.get(predicate))
            if raw is None:
                values = ()
            else:
                value = _normalize_construct_property(raw, allowed.get(prop), decoded, {})
                from oldaplib.src.helpers.langstring import LangString
                values = tuple(value) if isinstance(value, (list, set, LangString)) else (value,)
            result.append(PropertyHistoryEntry(
                iri=Iri(str(entry)),
                timestamp=Xsd_dateTimeStamp(str(graph.value(entry, H.historyTimestamp))),
                user_iri=Iri(str(graph.value(entry, H.historyUser))),
                resource_iri=instance.iri,
                property_iri=prop,
                values=values,
                annotations=tuple(json.loads(str(graph.value(entry, H.historyReifierSnapshot) or '[]'))),
            ))
        return sorted(result, key=lambda item: (item.timestamp.value, str(item.iri)), reverse=True)

    @staticmethod
    def restoration_values(entry):
        """Return ordinary setter input, without reusing historical Dating identities.

        Dating roots acquire the current root identity through the normal update
        implementation. Nested dates are copied as values, so history restoration
        cannot overwrite unrelated live nodes using an old identity.
        """
        from oldaplib.src.xsd.dating import Dating

        def copy_value(value):
            if not isinstance(value, Dating):
                return value
            data = value._as_dict()
            data.pop('iri', None)
            if 'before' in data:
                data['before'] = {copy_value(item) for item in data['before']}
            return Dating(**data)

        return [copy_value(value) for value in entry.values] if entry.values else None

    def restore(self, resource_iri, entry_iri, *, before_commit=None):
        """Assign historical values through the ordinary setter and update path.

        Rechecks read/write permissions and current model constraints inside one
        transaction. System and inverse properties cannot be restored. Returns
        the updated instance; history is retained and the replaced state recorded.
        """
        with resource_transaction(self.con):
            instance = self.factory.read(resource_iri)
            entries = self._read(instance, entry_iri=Iri(str(entry_iri)))
            if not entries:
                raise OldapErrorNotFound('History entry not found for this resource.')
            entry = entries[0]
            if entry.property_iri not in history_properties(instance):
                raise OldapErrorValue('Historical property is not writable in the current model.')
            if entry.values:
                instance[entry.property_iri] = self.restoration_values(entry)
            elif instance.get(entry.property_iri) is not None:
                del instance[entry.property_iri]
            # Load annotation groups only on this explicit history restore path.
            if entry.annotations or any(getattr(prop, 'reifierShapes', None) for prop in instance.resolved_properties().values()):
                from oldaplib.src.assertion_annotation import restore_annotations
                restore_annotations(instance, entry.property_iri, entry.annotations)
            instance.update(before_commit=before_commit)
            return instance
