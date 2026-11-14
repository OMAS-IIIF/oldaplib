"""Model reference checks and transactional barriers for staged RDF 1.2 support."""

from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def guard_instance_write(instance, operation, args, kwargs):
    """Prepare supported CRUD; reject annotated transformations and side links.

    Runs inside resource_operation's transaction. Ordinary reads/searches never
    call this boundary. Unsupported paths retain fresh model/data guards.
    Administrative permission annotations remain a separate subsystem.
    """
    if operation in {'create', 'update', 'delete'} and hasattr(instance, '_annotation_edits'):
        from oldaplib.src.assertion_annotation import prepare_write
        prepare_write(instance, operation)
        return
    con = instance._con
    context = Context(name=con.context_name)
    classes = [instance.name]
    if operation == 'transform_class':
        classes.append(kwargs.get('target_class', args[0] if args else None))
    pending = {Iri(str(name) + 'Shape') for name in classes if name is not None}
    seen = set()
    while pending:
        current = pending - seen
        if not current:
            break
        seen.update(current)
        terms = ' '.join(iri.toRdf for iri in current)
        query = context.sparql_context + f'''SELECT ?parent ?constraint WHERE {{
            VALUES ?shape {{ {terms} }} VALUES ?graph {{ {instance._graph}:shacl shared:shacl oldap:shacl }} GRAPH ?graph {{
                {{ ?shape sh:node ?parent }} UNION
                {{ ?shape sh:property ?use . ?use ?constraint ?value .
                   VALUES ?constraint {{ sh:reifierShape sh:reificationRequired }} }}
            }} }}'''
        rows = QueryProcessor(context, con.transaction_query(query))
        pending = set()
        for row in rows:
            if row.get('constraint') is not None:
                raise OldapErrorValue('This operation does not support annotated instances.')
            if row.get('parent') is not None:
                pending.add(Iri(row['parent']))
    subject = instance.iri.toRdf
    quoted = (f'<<( {subject} ?predicate ?value )>>' if getattr(con, '_resource_permissions_rdf12', False) is True
              else f'<< {subject} ?predicate ?value >>')
    query = context.sparql_context + f'''ASK {{ GRAPH {instance._graph}:data {{
        {subject} ?predicate ?value .
        ?reifier rdf:reifies {quoted} .
        FILTER(?predicate NOT IN (oldap:attachedToRole, oldap:hasRole, oldap:inProject))
    }} }}'''
    if con.transaction_query(query)['boolean']:
        raise OldapErrorValue('Existing business reifiers are not supported by this operation.')
    if operation == 'transform_class' and kwargs.get('link_from_iri') is not None:
        # The optional incoming link is written directly by transform_class,
        # so its source needs the same checks as an ordinary instance update.
        source = instance.factory.read(Iri(kwargs['link_from_iri']))
        guard_instance_write(source, 'transform_link', (), {})


def validate_property_reifiers(prop, con, project, available=None, inherited_refs=()):
    """Resolve supported local/shared shape links; reject incomplete policies."""
    from oldaplib.src.reifier_shape import ReifierShape
    from oldaplib.src.assertion_annotation import PROTECTED, uri
    refs = set(prop.reifierShapes or ()) | set(inherited_refs)
    if (refs or prop.reificationRequired is not None) and str(uri(Context(name=con.context_name), prop.property_class_iri)) in PROTECTED:
        raise OldapErrorValue('System/permission predicates cannot carry business annotations.')
    if prop.reificationRequired is not None and not refs:
        raise OldapErrorValue('reificationRequired requires reifierShapes on this property use.')
    if not refs:
        return
    if prop.inversePath or prop.appliesToProperty:
        raise OldapErrorValue('Reifier shapes require a simple forward business property.')
    for ref in refs:
        iri = Context(name=con.context_name).iri2qname(str(ref)) if not ref.is_qname else ref.as_qname
        if iri is None or iri.prefix not in {str(project.projectShortName), 'shared'}:
            raise OldapErrorValue('Reifier shape references must be local or shared.')
        if available is not None and iri in available:
            continue
        ReifierShape.read(con, project if iri.prefix == str(project.projectShortName) else 'shared', iri)


def validate_resource_reifiers(resource, available=None):
    """Validate conjunctive inherited policies without modifying parent objects."""
    active = set()
    completed = {}

    def visit(node):
        if node.owl_class_iri in active:
            raise OldapErrorValue('Cyclic class inheritance cannot define a reification policy.')
        if node.owl_class_iri in completed:
            return completed[node.owl_class_iri]
        active.add(node.owl_class_iri)
        policies = {}
        for parent in (node.superclass or {}).values():
            if parent is not None:
                for predicate, refs in visit(parent).items():
                    policies[predicate] = policies.get(predicate, set()) | refs
        for prop in node.properties.values():
            inherited = policies.get(prop.property_class_iri, set())
            validate_property_reifiers(prop, resource._con, resource._project, available, inherited)
            policies[prop.property_class_iri] = inherited | set(prop.reifierShapes or ())
        active.remove(node.owl_class_iri)
        completed[node.owl_class_iri] = policies
        return policies

    visit(resource)


def reject_used_policy_change(prop, *, newly_attached=False):
    """Refuse attachment changes while asserted values exist, inside a transaction."""
    from oldaplib.src.enums.propertyclassattr import PropClassAttr
    changed = {PropClassAttr.REIFIER_SHAPES, PropClassAttr.REIFICATION_REQUIRED} & set(prop.changeset)
    if not changed and not (newly_attached and (prop.reifierShapes or prop.reificationRequired is not None)):
        return
    context = Context(name=prop._con.context_name)
    query = context.sparql_context + f'ASK {{ GRAPH ?data {{ ?s {prop.property_class_iri.toRdf} ?value }} }}'
    if prop._con.transaction_query(query)['boolean']:
        raise OldapErrorValue('Cannot change reification policy while its predicate has asserted values.')


def invalidate_model_owners(con, graph, class_iri):
    """Evict owner/subclass snapshots across graphs without flushing Redis."""
    from oldaplib.src.cachesingleton import CacheSingletonRedis
    cache = CacheSingletonRedis()
    cache.delete(Xsd_QName(str(graph), 'shacl'))
    cache.delete(class_iri)
    context = Context(name=con.context_name)
    pending = {Iri(str(class_iri) + 'Shape')}
    seen = set()
    while pending - seen:
        current = pending - seen
        seen.update(current)
        terms = ' '.join(value.toRdf for value in current)
        query = context.sparql_context + f'''SELECT DISTINCT ?graph ?child ?class WHERE {{
            VALUES ?parent {{ {terms} }} GRAPH ?graph {{
                ?child sh:node ?parent ; sh:targetClass ?class .
            }} }}'''
        pending = set()
        for row in QueryProcessor(context, con.query(query)):
            cache.delete(row['graph'])
            cache.delete(row['class'])
            pending.add(Iri(row['child']))
