"""Explicit Jena Text query adaptation for configured resource searches.

The backend supplies a reviewed project-specific field map. This module does not
translate GraphDB connector options or arbitrary Lucene. Fixed property chains
are evaluated against current project data, ending in an indexed text property.
"""
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.xsd.xsd_qname import Xsd_QName

if TYPE_CHECKING:
    from oldaplib.src.objectfactory import FTSearchFilter

# Jena Text 6.2 uses 10000 index hits when the limit is omitted or nonpositive.
# Use Java's maximum positive int to cover the whole Lucene index. Lucene bounds
# the collector by its actual document count; this does not allocate billions of
# hits. Only the outer resource query may page after permissions and filtering.
JENA_ALL_TEXT_HITS = 2**31 - 1


def jena_fulltext_fields(configuration: dict, context: Context) -> dict[str, tuple[Iri, ...]]:
    """Validate a portable fulltext YAML section and resolve its field paths.

    Args:
        configuration: ``{'fields': {'title': ['schema:name'], ...}}`` after
            YAML/JSON decoding. Unknown keys are errors, never ignored options.
        context: Project Context used to expand QName predicates to full IRIs.

    Returns:
        Field names mapped to nonempty immutable tuples of full predicate IRIs.
        The last predicate is indexed; earlier predicates form a forward path.

    Raises:
        OldapErrorValue: Malformed fields, unknown options/prefixes, or invalid
            predicate identifiers. No backend/index operation occurs here.
    """
    from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

    if not isinstance(configuration, dict) or set(configuration) != {'fields'}:
        raise OldapErrorValue('Fulltext configuration supports exactly a fields mapping.')
    fields = configuration['fields']
    if not isinstance(fields, dict) or not fields:
        raise OldapErrorValue('Fulltext fields must be a nonempty mapping.')
    result = {}
    for name, path in fields.items():
        if not isinstance(name, str):
            raise OldapErrorValue('Fulltext field names must be strings.')
        Xsd_NCName(name, validate=True)
        if not isinstance(path, list) or not path:
            raise OldapErrorValue(f'Fulltext field {name} needs a nonempty predicate list.')
        predicates = []
        for raw in path:
            if not isinstance(raw, str):
                raise OldapErrorValue(f'Fulltext field {name} predicates must be strings.')
            predicate = Iri(raw, validate=True)
            try:
                if predicate.is_qname:
                    predicate = Iri(str(context.qname2iri(Xsd_QName(str(predicate), validate=True))), validate=True)
            except (KeyError, ValueError) as error:
                raise OldapErrorValue(f'Unknown fulltext predicate prefix: {raw}.') from error
            predicates.append(predicate)
        result[name] = tuple(predicates)
    return result


def jena_fulltext_pattern(graph: str, filters: Sequence['FTSearchFilter | str'], fields: Mapping[str, Iri | tuple[Iri, ...]],
                          score_var: str, *, user_iri: str | None = None) -> str:
    """Build entity-level AND/OR joins for a supported configured-field search.

    Args:
        graph: Trusted project data graph in SPARQL notation.
        filters: Alternating FTSearchFilter and AND/OR tokens; AND binds tighter.
        fields: Explicit backend field-name to predicate or forward predicate-path mapping.
        score_var: Trusted SPARQL variable name receiving the combined score.
        user_iri: Trusted SPARQL user term. The normal Jena adapter supplies this
            to require read access at each referenced hop; root access is checked
            by the surrounding resource query. Omission is for structural probes.

    Returns:
        A grouped SPARQL pattern binding ?res and the requested score variable.
        AND adds term scores; the caller uses MAX across OR branches/literal hits.
        These scores are not numerically equivalent to GraphDB connector scores.
        Text candidates cover the index; the caller applies permissions and
        resource pagination afterwards, without Jena's implicit hit cutoff.

    Raises:
        OldapErrorValue: Unknown field, invalid sequence or unsupported Lucene
            syntax. Ordinary words (with optional nonleading wildcards) are
            joined with AND within each configured field, across literal values.
            Hyphens separate ordinary words; apostrophes remain within words.
            Quoted phrases match a single indexed value. Raw Boolean expressions
            remain unsupported; use separate AND/OR filter entries.
    """
    from oldaplib.src.objectfactory import FTSearchFilter

    if not filters or len(filters) % 2 == 0:
        raise OldapErrorValue('Jena full-text expects filters separated by AND or OR.')
    branches: list[list[tuple[str, tuple[Iri, ...], str]]] = [[]]
    for index, item in enumerate(filters):
        if index % 2:
            if item not in ('AND', 'OR'):
                raise OldapErrorValue('Jena full-text supports only AND/OR between filters.')
            if item == 'OR':
                branches.append([])
            continue
        if not isinstance(item, FTSearchFilter):
            raise OldapErrorValue('Jena full-text expects a field filter at this position.')
        predicate = fields.get(str(item.field_name))
        if predicate is None:
            raise OldapErrorValue(f'Unknown Jena full-text field: {item.field_name}.')
        # Canonically equivalent input must pass the same safe-word grammar.
        # Index token normalization also handles decomposed stored literals.
        expression = unicodedata.normalize('NFC', str(item.query)).strip()
        # Hyphens separate words in the text index; apostrophes can belong to
        # a word (e.g. French names). Accept these ordinary spellings without
        # opening Lucene operators such as leading minus, colon or parentheses.
        separator = r'(?:\s+|[-‐‑])'
        word = r"\w[\w*?]*(?:['’]\w[\w*?]*)*"
        phrase_word = r"\w+(?:['’]\w+)*"
        words = re.split(separator, expression)
        phrase = re.fullmatch('"' + phrase_word + '(?:' + separator + phrase_word + ')*"', expression)
        plain_words = bool(re.fullmatch(word + '(?:' + separator + word + ')*', expression)) and all(
            word not in {'AND', 'OR', 'NOT'} for word in words)
        if not phrase and not plain_words:
            raise OldapErrorValue('Unsupported Jena full-text expression; use words, '
                                  'nonleading wildcards or a quoted phrase, with separate AND/OR filters.')
        path = (predicate,) if isinstance(predicate, Iri) else predicate
        if not isinstance(path, tuple) or not path or not all(isinstance(p, Iri) for p in path):
            raise OldapErrorValue(f'Invalid predicate path for fulltext field {item.field_name}.')
        # Separate index lookups are joined on the resource: all ordinary
        # words must match this field, even across different literal values.
        # A quoted phrase stays one lookup and must match one indexed value.
        atoms = words if plain_words else [expression]
        for atom_index, atom in enumerate(atoms):
            variable_id = str(index) if len(atoms) == 1 else f'{index}_{atom_index}'
            branches[-1].append((variable_id, path, atom))

    patterns = []
    for branch in branches:
        terms, scores = [], []
        for index, path, expression in branch:
            score = f'?ft_{index}_score'
            scores.append(score)
            # Explicitly bypass Jena's default 10000-hit window. Index hits are
            # literal documents, not authorized/distinct resource results.
            target = '?res'
            if len(path) > 1:
                target = f'?ft_{index}_target'
                if user_iri is None:
                    links = '/'.join(p.toRdf for p in path[:-1])
                    terms.append(f'GRAPH {graph} {{ ?res {links} {target} . }}')
                else:
                    previous = '?res'
                    for hop, predicate in enumerate(path[:-1]):
                        current = target if hop == len(path) - 2 else f'?ft_{index}_hop_{hop}'
                        terms.append(f'GRAPH {graph} {{ {previous} {predicate.toRdf} {current} . }}')
                        # A public root is not a grant to search private linked
                        # text. EXISTS checks current asserted membership and
                        # its RDF 1.2 grant without multiplying result scores.
                        stem = f'ft_{index}_{hop}'
                        terms.append(f'''FILTER EXISTS {{
                            GRAPH oldap:admin {{ {user_iri} oldap:hasRole ?{stem}_role .
                                ?{stem}_permission oldap:permissionValue ?{stem}_value .
                                FILTER(?{stem}_value >= 2) }}
                            GRAPH {graph} {{ {current} oldap:attachedToRole ?{stem}_role .
                                ?{stem}_grant rdf:reifies <<( {current} oldap:attachedToRole ?{stem}_role )>> ;
                                    oldap:hasDataPermission ?{stem}_permission . }}
                        }}''')
                        previous = current
            terms.append(f'GRAPH {graph} {{ ({target} {score}) '
                         f'<http://jena.apache.org/text#query> '
                         f'({path[-1].toRdf} {Xsd_string(expression).toRdf} {JENA_ALL_TEXT_HITS}) }}')
        terms.append(f'BIND(({" + ".join(scores)}) AS ?{score_var})')
        patterns.append('{ ' + '\n'.join(terms) + ' }')
    return '{ ' + '\nUNION\n'.join(patterns) + ' }'
