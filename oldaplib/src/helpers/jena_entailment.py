"""Small, explicit read entailment shared by Jena resource query builders.

Class ancestry, subproperties and legacy declared inverse properties are supported.
No data is materialized and no general OWL reasoner is enabled. Authorization
queries must continue using asserted data, never the property pattern below.
"""
# Direct type equality is checked separately; this path adds ancestors only.
CLASS_PATH = 'rdfs:subClassOf+'

# Ontology axioms must not manufacture types, ACL links, grants, grant values or provenance.
# Type expansion has its own path; authorization is always asserted separately.
ASSERTED_ONLY = ('rdf:type', 'rdf:reifies', 'oldap:attachedToRole', 'oldap:hasRole',
                 'oldap:inProject', 'oldap:hasAdminPermission',
                 'oldap:hasDataPermission', 'oldap:hasDefaultDataPermission',
                 'oldap:permissionValue', 'oldap:createdBy', 'oldap:creationDate',
                 'oldap:lastModifiedBy', 'oldap:lastModificationDate')


def schema_dataset(con, graph):
    """Return explicit FROM clauses for this project's selected schema graphs.

    The real adapter resolves current external registrations transaction-locally.
    Lightweight native test connections without discovery retain base schemas.
    This never selects other projects' data or an unrestricted union graph.
    """
    discover = getattr(con, '_resource_schema_graphs', None)
    graphs = discover(graph) if callable(discover) else [f'{graph}:onto', 'shared:onto', 'oldap:onto']
    return ' '.join('FROM ' + name for name in dict.fromkeys(graphs))


def property_pattern(graph, subject, predicate, value, *, alias,
                     expand_subproperties=False, modeled_only=False):
    """Match asserted values, legacy inverses and optionally subproperty values.

    Args:
        graph: Validated project graph prefix.
        subject: Validated subject term or query variable.
        predicate: Validated predicate term or query variable.
        value: Validated value term or query variable.
        alias: Unique internal variable prefix for this query pattern.
        expand_subproperties: Include values asserted under narrower predicates.
        modeled_only: Restrict added superproperty keys to fields on this
            resource's class or ancestors. Requires project/shared/base SHACL
            graphs as named graphs. Filters leave this false; hydration uses true.

    Returns:
        A SPARQL union pattern; callers must enclose it in a group.

    No equivalence is evaluated. Permission queries must not use this helper.
    Legacy inverse behavior is retained until modeled inverse fields replace it.
    Returning an IRI does not authorize hydration of the linked resource.
    """
    if predicate in ASSERTED_ONLY:
        return f'GRAPH {graph}:data {{ {subject} {predicate} {value} . }}'
    blocked = ', '.join(ASSERTED_ONLY)
    shape_graph = '?' + alias + '_inverseShapeGraph'
    shape = '?' + alias + '_inverseShape'
    field = '?' + alias + '_inverseField'
    owner = '?' + alias + '_inverseOwner'
    direct_type = '?' + alias + '_inverseRootType'
    path = '?' + alias + '_inversePath'
    source_class = '?' + alias + '_inverseSourceClass'
    source_type = '?' + alias + '_inverseSourceType'
    source_property = '?' + alias + '_inverseSourceProperty'
    protected_inverse = '?' + alias + '_inverseProtected'
    # Resolve schema relationships before visiting instance data. In particular,
    # an absent inverse/subproperty definition should stop that UNION branch
    # without scanning incoming links or types for every candidate resource.
    definition = f'''
        VALUES {shape_graph} {{ {graph}:shacl shared:shacl oldap:shacl }}
        GRAPH {shape_graph} {{
            {shape} sh:targetClass {owner} ; sh:property {field} .
            {field} oldap:field {predicate} ; sh:path/sh:inversePath {path} ; sh:class {source_class} .
        }}
        GRAPH {graph}:data {{ {subject} a {direct_type} . }}
        FILTER({direct_type} = {owner} || EXISTS {{ {direct_type} {CLASS_PATH} {owner} }})
    '''
    # A modeled inverse is a read-only view, not a second storage predicate.
    # It overrides the old global inverse rule only for the applicable shape.
    direct = f'''GRAPH {graph}:data {{ {subject} {predicate} {value} . }}
        FILTER NOT EXISTS {{ {definition} }}'''
    inverse = '?' + alias + '_inverse'
    pattern = f'''{{ {direct} }} UNION {{
        {inverse} (owl:inverseOf|^owl:inverseOf) {predicate} .
        GRAPH {graph}:data {{ {value} {inverse} {subject} . }}
        FILTER(isIRI({predicate}) && {predicate} NOT IN ({blocked}) && {inverse} NOT IN ({blocked}))
        FILTER NOT EXISTS {{ {definition} }}
    }} UNION {{
        {definition}
        FILTER(isIRI({predicate}) && {predicate} NOT IN ({blocked}) && {path} NOT IN ({blocked}))
        GRAPH {graph}:data {{ {value} {source_property} {subject} ; a {source_type} . }}
        FILTER({source_type} = {source_class} || EXISTS {{ {source_type} {CLASS_PATH} {source_class} }})
        FILTER({source_property} = {path} || EXISTS {{ {source_property} rdfs:subPropertyOf+ {path} }})
        FILTER({source_property} NOT IN ({blocked}))
        FILTER NOT EXISTS {{
            VALUES {protected_inverse} {{ {' '.join(ASSERTED_ONLY)} }}
            {source_property} rdfs:subPropertyOf* {protected_inverse} .
            {protected_inverse} rdfs:subPropertyOf* {path} .
        }}
    }}'''
    if not expand_subproperties:
        return pattern

    source = '?' + alias + '_sourceProperty'
    protected = '?' + alias + '_protectedProperty'
    # Reject any source-to-target route that passes through a protected field,
    # including its endpoints. This is intentionally conservative when a model
    # also supplies an alternative, harmless route between the same predicates.
    hierarchy = f'''
        {source} rdfs:subPropertyOf+ {predicate} .
        FILTER(isIRI({predicate}) && {source} != {predicate})
        FILTER NOT EXISTS {{
            VALUES {protected} {{ {' '.join(ASSERTED_ONLY)} }}
            {source} rdfs:subPropertyOf* {protected} .
            {protected} rdfs:subPropertyOf* {predicate} .
        }}
    '''
    model = ''
    if modeled_only:
        schema = '?' + alias + '_shapeGraph'
        shape = '?' + alias + '_shape'
        field = '?' + alias + '_field'
        owner = '?' + alias + '_ownerClass'
        direct_type = '?' + alias + '_directClass'
        # EXISTS avoids multiplying results when several ancestors expose the
        # same field. Shape metadata describes fields; it does not validate data.
        model = f'''FILTER EXISTS {{
            GRAPH {graph}:data {{ {subject} a {direct_type} . }}
            VALUES {schema} {{ {graph}:shacl shared:shacl oldap:shacl }}
            GRAPH {schema} {{
                {shape} sh:targetClass {owner} ; sh:property {field} .
                {field} sh:path {predicate} .
            }}
            FILTER({direct_type} = {owner} || EXISTS {{ {direct_type} {CLASS_PATH} {owner} }})
        }}'''
    return pattern + f''' UNION {{
        {hierarchy}
        GRAPH {graph}:data {{ {subject} {source} {value} . }}
        FILTER NOT EXISTS {{ {definition} }}
        {model}
    }}'''


def class_choices(type_variable, target, data_graph):
    """Resolve each instantiated class once, then join authorized resources to it.

    Grouping the data graph's asserted types avoids both repeated walks per
    instance and enumeration of thousands of unused external vocabulary classes.
    The outer filter evaluates ancestry on that set. Equality retains classes with
    no schema definition. All arguments are validated SPARQL terms.

    For an outer-bound target variable (archive policy lists), retain a correlated
    test: an independent subquery cannot inherit that outer binding. Root ACL
    joins stay outside this helper; a class match never authorizes a resource.
    """
    condition = f'{type_variable} = {target} || EXISTS {{ {type_variable} {CLASS_PATH} {target} }}'
    if target.startswith('?'):
        return f'FILTER ({condition})'
    return f'''{{ SELECT {type_variable} WHERE {{
        {{ SELECT DISTINCT {type_variable} WHERE {{
            GRAPH {data_graph} {{ ?entailmentClassMember a {type_variable} . }}
        }} }}
        FILTER ({condition})
    }} }}'''
