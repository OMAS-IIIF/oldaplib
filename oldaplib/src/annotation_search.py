"""Opt-in, model-resolved assertion annotation search for the RDF 1.2 backend.

Groups are conjunctive. Each group is anchored to one asserted base triple and
one reifier; repeated comparisons of a field bind the same field value. Nothing
in this module is loaded by ordinary searches without annotation options.
"""
from dataclasses import dataclass
from typing import Any

from rdflib import BNode, Literal, RDF, URIRef

from oldaplib.src.assertion_annotation import PROTECTED, _typed_term, resolve_policies, uri
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapErrorValue


@dataclass(frozen=True)
class AnnotationFieldFilter:
    """One field comparison; existence operators take no value.

    Args:
        property: Modeled annotation-field QName or IRI.
        op: eq, ne, lt, le, gt, ge, exists or not_exists.
        value: Model-coerced scalar or RDF-term JSON for comparison operators.
    """
    property: str
    op: str
    value: Any = None

    def __post_init__(self):
        if not isinstance(self.property, str) or not self.property:
            raise OldapErrorValue('Annotation field property must be a QName or IRI string.')
        if not isinstance(self.op, str) or self.op not in {'eq', 'ne', 'lt', 'le', 'gt', 'ge', 'exists', 'not_exists'}:
            raise OldapErrorValue('Unsupported annotation comparison operator.')
        if (self.op in {'exists', 'not_exists'}) != (self.value is None):
            raise OldapErrorValue('Existence operators have no value; comparisons require one.')


@dataclass(frozen=True)
class AnnotationFilter:
    """Match an asserted base value and one annotation satisfying every field.

    Args:
        property: Forward base predicate in the requested resource-class model.
        value: Optional exact base value; None means any asserted value.
        fields: Conjunctive field comparisons on the same reifier.
        exists: False selects an asserted value with no matching reifier.
            It does not select resources missing the base property entirely.
    """
    property: str
    value: Any = None
    fields: tuple[AnnotationFieldFilter, ...] = ()
    exists: bool = True

    def __post_init__(self):
        if not isinstance(self.property, str) or not self.property:
            raise OldapErrorValue('Annotation base property must be a QName or IRI string.')
        if not isinstance(self.exists, bool):
            raise OldapErrorValue('Annotation group exists must be boolean.')
        if not isinstance(self.fields, (tuple, list)) or not all(isinstance(f, AnnotationFieldFilter) for f in self.fields):
            raise OldapErrorValue('Annotation fields must contain AnnotationFieldFilter objects.')
        object.__setattr__(self, 'fields', tuple(self.fields))


def parse_annotation_filters(data):
    """Decode the strict JSON group contract shared with the REST endpoint."""
    if not isinstance(data, list):
        raise OldapErrorValue('annotationFilter must be an array.')
    result = []
    for group in data:
        if not isinstance(group, dict) or 'property' not in group or set(group) - {'property', 'value', 'fields', 'exists'}:
            raise OldapErrorValue('Invalid annotation filter group.')
        if 'value' in group and group['value'] is None:
            raise OldapErrorValue('Omit the base value to match any asserted value; null is not an RDF term.')
        if not isinstance(group.get('fields', []), list):
            raise OldapErrorValue('Annotation filter fields must be an array.')
        fields = []
        for field in group.get('fields', []):
            if not isinstance(field, dict) or not {'property', 'op'} <= set(field) or set(field) - {'property', 'op', 'value'}:
                raise OldapErrorValue('Invalid annotation field filter.')
            if 'value' in field and (field['value'] is None or field['op'] in ('exists', 'not_exists')):
                raise OldapErrorValue('Existence operators omit value; comparison values cannot be null.')
            fields.append(AnnotationFieldFilter(**field))
        result.append(AnnotationFilter(**{**group, 'fields': tuple(fields)}))
    return result


def _search_term(value, prop, context):
    """Coerce query operands by datatype without enforcing data cardinality/bounds.

    Range endpoints may lie outside allowed data bounds. Exact RDF datatypes and
    lexical validation still apply, and blank nodes are never query operands.
    """
    term = _typed_term(value, prop, context)
    if isinstance(term, BNode):
        raise OldapErrorValue('Blank nodes are not annotation search operands.')
    if prop.datatype is None:
        if not isinstance(term, URIRef):
            raise OldapErrorValue('Object annotation search requires an IRI.')
    else:
        if not isinstance(term, Literal) or (term.datatype or (RDF.langString if term.language else URIRef('http://www.w3.org/2001/XMLSchema#string'))) != uri(context, prop.datatype.value):
            raise OldapErrorValue('Annotation search operand has the wrong datatype.')
        # Explicit RDF-term inputs must pass the same lexical conversion as scalars.
        _typed_term(str(term) + ('@' + term.language if term.language else ''), prop, context)
    return term.n3()


def compile_annotation_filters(con, project, res_class, groups):
    """Return graph-scoped correlated EXISTS clauses after fresh model checks.

    Root permissions/paging remain the responsibility of ResourceInstance.search.
    Object-valued filters additionally require target visibility unless the model
    identifies a controlled vocabulary through inSet.
    """
    from oldaplib.src.objectfactory import ResourceInstanceFactory
    if not res_class:
        raise OldapErrorValue('Annotation filters require resClass for model resolution.')
    if not isinstance(groups, (list, tuple)) or not all(isinstance(group, AnnotationFilter) for group in groups):
        raise OldapErrorValue('annotationFilter must contain AnnotationFilter objects.')
    context = Context(name=con.context_name)
    graph = project.projectShortName
    model = ResourceInstanceFactory(con, project).createObjectInstance(res_class)
    props = {uri(context, key): prop for key, prop in model.resolved_properties().items()}
    policies = resolve_policies(con, project, res_class)
    operators = {'eq': '=', 'ne': '!=', 'lt': '<', 'le': '<=', 'gt': '>', 'ge': '>='}

    def visible(variable, prop, alias):
        if prop.datatype is not None or prop.inSet:
            return ''
        return f'''FILTER EXISTS {{
          GRAPH {graph}:data {{ {variable} oldap:attachedToRole ?{alias}Role .
            ?{alias}Grant rdf:reifies <<( {variable} oldap:attachedToRole ?{alias}Role )>> ; oldap:hasDataPermission ?{alias}Permission . }}
          GRAPH oldap:admin {{ {con.userIri.toRdf} oldap:hasRole ?{alias}Role .
            ?{alias}Permission oldap:permissionValue ?{alias}Level . FILTER(?{alias}Level >= {DataPermission.DATA_VIEW.numeric.toRdf}) }}
        }}'''

    clauses = []
    for index, group in enumerate(groups):
        predicate = uri(context, group.property)
        prop = props.get(predicate)
        shapes = policies.get(predicate, ((), False))[0]
        if prop is None or not shapes or str(predicate) in PROTECTED or prop.inversePath or str(prop.toClass) == 'oldap:Dating':
            raise OldapErrorValue('Annotation search requires a modeled forward property with reifier shapes.')
        definitions = {}
        for shape in shapes:
            for key, field in shape.properties.items():
                definitions.setdefault(uri(context, key), []).append(field)
        base, reifier = f'?annotation{index}Base', f'?annotation{index}Reifier'
        outer = [f'GRAPH {graph}:data {{ ?res {predicate.n3()} {base} . }}', visible(base, prop, f'annotation{index}Base')]
        if group.value is not None:
            outer.append(f'FILTER({base} = {_search_term(group.value, prop, context)})')
        inner = [f'{reifier} a oldap:AssertionAnnotation ; rdf:reifies <<( ?res {predicate.n3()} {base} )>> .']
        field_vars = {}
        for field_filter in group.fields:
            field = uri(context, field_filter.property)
            definitions_for_field = definitions.get(field)
            if not definitions_for_field or str(field) in PROTECTED:
                raise OldapErrorValue('Unknown or protected annotation search field.')
            field_prop = definitions_for_field[0]
            variable = field_vars.setdefault(field, f'?annotation{index}Field{len(field_vars)}')
            triple = f'{reifier} {field.n3()} {variable} .'
            # All attached shapes apply: a vocabulary constraint on one shape
            # cannot disable target ACL checks required by another shape.
            access_prop = next((definition for definition in definitions_for_field
                                if definition.datatype is None and not definition.inSet), field_prop)
            access = visible(variable, access_prop, variable[1:])
            if field_filter.op == 'not_exists':
                inner.append(f'FILTER NOT EXISTS {{ {triple} }}')
                continue
            if triple not in inner:
                inner.extend([triple, access])
            if field_filter.op not in {'exists', 'not_exists'}:
                terms = {_search_term(field_filter.value, definition, context) for definition in definitions_for_field}
                if len(terms) != 1:
                    raise OldapErrorValue('Conjunctive annotation fields require an unambiguous operand datatype.')
                inner.append(f'FILTER({variable} {operators[field_filter.op]} {terms.pop()})')
        test = 'EXISTS' if group.exists else 'NOT EXISTS'
        outer.append(f'FILTER {test} {{ GRAPH {graph}:data {{ {" ".join(inner)} }} }}')
        clauses.append('\nFILTER EXISTS { ' + ' '.join(outer) + ' }')
    return ''.join(clauses)


def project_annotations(con, project, rows):
    """Explicitly hydrate complete groups for the selected page only.

    Recheck each parent's visibility before fetching its records. This deliberately
    costs additional reads and never runs for ordinary searches or counts.
    """
    from oldaplib.src.assertion_annotation import read_annotations
    from oldaplib.src.objectfactory import ResourceInstanceFactory
    factory = ResourceInstanceFactory(con, project)
    for row in rows:
        instance = factory.read(row['iri'])
        row['@annotations'] = [record.to_json() for record in read_annotations(instance)]
