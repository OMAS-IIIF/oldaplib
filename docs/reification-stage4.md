# Stage 4: assertion annotation search

Implemented locally on `codex/reification-properties` in oldaplib and oldap-api.
No live configuration, ontology, dependency installation or deployment changes.
The [working plan](reification-properties-plan.md) tracks all four stages.

## Contract

`ResourceInstance.search` adds two opt-in keyword arguments:

- `annotationFilter`: a list of `AnnotationFilter` groups, combined with AND.
  Requires `resClass` and the RDF 1.2 search backend. Groups also combine with
  existing ordinary/fulltext/hierarchical filters using AND.
- `includeAnnotations`: boolean, default false. Adds complete annotation groups
  under `@annotations` on each selected result. Counts never hydrate annotations.

No changes are made to ordinary filters, result payloads or query generation
when these options are omitted. New modules/model resolution are lazy. Existing
sorting/count/paging and permission checks remain in the main search pipeline.
Annotation filtering uses correlated EXISTS clauses, without adding result rows.

```python
from oldaplib.src.annotation_search import AnnotationFilter, AnnotationFieldFilter
from oldaplib.src.objectfactory import ResourceInstance

rows = ResourceInstance.search(
    con, project, resClass='travel:Trip',
    annotationFilter=[AnnotationFilter(
        property='travel:isAt', value='travel:A',
        fields=(
            AnnotationFieldFilter('travel:dateTime', 'ge', '2026-11-01T00:00:00Z'),
            AnnotationFieldFilter('travel:dateTime', 'lt', '2026-12-01T00:00:00Z'),
        ),
    )],
    includeAnnotations=True, limit=25,
)
```

The base predicate and each field resolve against the requested class's current
annotation model, including inherited shapes. Subclass instances may match a base
class search, but subclass-only fields require searching that subclass explicitly.
The base predicate is a simple forward predicate and matches the actual asserted
triple, not inferred inverse or subproperty triples. Protected system/permission
predicates cannot be annotation-search fields.

## Grouping and missing values

Each group selects **one asserted base value and one managed reifier**. All field
conditions in that group must hold on that reifier. Repeated conditions on the
same field use **one field value**, so range endpoints cannot be satisfied by two
different values. Separate groups can match separate visits; they do not require
distinct reifier IDs and may match the same visit.

| Form | Meaning |
| --- | --- |
| `value` omitted | Any asserted value of the base property |
| `value` supplied | Exact model-typed base-value comparison |
| Empty `fields` | A managed reifier exists for the selected assertion |
| Field `eq/ne/lt/le/gt/ge` | A present field value satisfies the comparison |
| Field `exists` | A field value exists and, for object links, is visible |
| Field `not_exists` | The field has no RDF values on that reifier |
| Group `exists=False` | An asserted base value has no reifier satisfying the group's conditions |

A missing base property never satisfies a group, including `exists=False`. To
search for missing base properties, use the existing ordinary `not_exists` filter.
`ne` is existential inequality on a present value; it does not mean absence or
that every value differs. For a forbidden value, use a group with an equality
condition and `exists=False`, remembering that base-value selection is existential.
Null is not an RDF value; omit optional keys instead.

Filter comparisons use model-directed scalar coercion or the typed scalar term
objects from [stage 3](reification-stage3.md). Datatypes and lexical forms are
checked. Query range endpoints need not satisfy stored-data bounds/cardinalities.
No raw SPARQL operands are accepted. Blank-node operands, structured Dating,
recursive annotations and inverse base properties are unsupported.

## Visibility, graph scope and projection

Root results retain existing DATA_VIEW authorization. Object-valued base matches
and positive annotation-field matches additionally require current target
DATA_VIEW visibility through asserted role membership/grants. Controlled vocabulary
fields with `inSet` use existing vocabulary semantics rather than instance ACLs.
A missing-field check tests physical absence; an inaccessible value is not treated
as missing. A negative group means no *visible matching* annotation, not a claim
that no hidden object target exists.

Both the base assertion and reifier/field patterns are scoped to the selected
project's data graph. Orphan and foreign-graph records do not satisfy filters.
Filters select `oldap:AssertionAnnotation` records. Explicit projection retains
stage-3 diagnostics and may include external records; it returns **complete groups,
not just the records which matched the filter**. Projection is not an ownership
validation or import-normalization mechanism.

Projection runs after page selection, rechecks each parent's visibility and loads
its records. It adds one factory/model setup plus two resource queries per result
(parent read and annotation read). A concurrent loss of parent visibility fails
the request rather than returning unauthorized annotations. This explicit cost
does not apply to ordinary searches or counts. The stage-3 parent-ACL contract
continues to govern projected annotation metadata.

Annotation-field sorting, aggregation and fulltext indexing are deferred. Ordinary
resource sorting is unchanged, including deterministic resource-IRI tie breaking.
No new YAML search syntax is required in oldap-tools.

## REST API

`POST /data/search/{project}` (with `resClass`) or
`POST /data/search/{project}/class/{resclass}`:

```json
{
  "resClass": "travel:Trip",
  "annotationFilter": [{
    "property": "travel:isAt",
    "value": "travel:A",
    "fields": [
      {"property":"travel:dateTime","op":"ge","value":"2026-11-01T00:00:00Z"},
      {"property":"travel:dateTime","op":"lt","value":"2026-12-01T00:00:00Z"}
    ]
  }],
  "includeAnnotations": true,
  "limit": 25
}
```

`countOnly: true` returns the existing `{"count": N}` response. Ordinary page rows
are unchanged unless projection is requested. Field/group keys are strict;
existence operators omit `value`. New annotation options require POST on the
structured search endpoint; GET/text routes reject them rather than ignoring them.
See [OpenAPI](../../oldap-api/API-def/oldap-api.yaml).

## Acceptance and measurement

Native tests use disposable Jena 6.2.0/TDB2, actual OLDAP model/permission queries
and Flask routing. They cover cross-visit and cross-field false matches, repeated
field ranges, separate groups, existence/absence, literal bases, duplicate matches,
counts/pages, explicit projection, orphan/foreign graphs, target/root permissions,
model/datatype errors and strict parsing. Stage-3 lifecycle and focused existing
query/read/API regressions are rerun alongside them.

The comparative [ordinary-path receipt](reification-stage4-performance.json)
compares the saved stage-3 objectfactory source (hash matches the stage-3 receipt)
with stage 4, using the same current supporting libraries and native dataset.
Both versions must return identical values and **identical query text/count** for
`read`, `read_data` and a 25-result ordinary search page. It uses 100 extra resources,
500 annotations and 300 warm interleaved calls per version/operation, with paired
bootstrap intervals. This is local evidence, not production capacity acceptance.

The [annotated-search receipt](reification-stage4-search.json) separately records
optimized Jena algebra and bounded timings for 100 resources with five annotations
each. The plan applies annotation EXISTS before page selection or distinct count;
no annotation variables enter the resource projection/grouping. Model resolution
is intentionally measured: the uncached fixture makes 25 queries for an annotated
page/count (24 model queries, one resource query), versus one for the ordinary page.
This cost is confined to explicitly requested annotation search. The receipt does
not imply that new annotation searches cost the same as ordinary searches.

To reproduce, use matching library/API sources on PYTHONPATH, the pinned
`OLDAP_TEST_FUSEKI_JAR` and Java 25 from stage 1A. Set
`OLDAP_ANNOTATION_SEARCH_RECEIPT=/tmp/search.json` for the bounded evidence test.
For paired timing, set `OLDAP_ANNOTATION_BENCHMARK=/tmp/performance.json` and
`OLDAP_ANNOTATION_BASELINE_SOURCE` to the baseline objectfactory file. Without the
latter, the harness uses git HEAD, which is the older pre-stage-1 local baseline.
Live HTTP/Redis/deployment checks remain a separate release gate.

Final local acceptance: **11 stage-4 tests** (six native integration/evidence
cases and five parser cases), **18 stage-3 lifecycle/performance tests**, and
**122 focused library/API regressions plus two subtests** pass. The final
read/read_data/search timing intervals all include zero; no slowdown is resolved.
The timing test was run separately from the functional suite to avoid contention.
Three old query-string assertions were corrected to include the already existing
SPARQL triple terminator; runtime ordinary query generation was not changed.
OpenAPI parses with unique keys and all local references resolve.

The exact stage-3 objectfactory baseline can be reconstructed from this stage-4
source with the stored reverse patch, without modifying the checkout:

```sh
patch -o /tmp/stage3-objectfactory.py oldaplib/src/objectfactory.py \
  tools/reification/stage4-baseline.patch
```

Verify its SHA-256 against `baselineSourceSha256` in the performance receipt before
using it as `OLDAP_ANNOTATION_BASELINE_SOURCE`. The patch is evidence for this
specific source version, not a migration or production rollback procedure.
