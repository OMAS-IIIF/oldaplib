# Stage 3: assertion annotation lifecycle

Status: accepted locally on 2026-11-14, branch `codex/reification-properties`.
Matching oldaplib/API development sources and the RDF 1.2 backend are required.
No package release, service activation or production migration was performed.
The [working plan](reification-properties-plan.md) tracks the remaining search stage.

## Explicit API, unchanged ordinary reads

`ResourceInstance.annotations()` explicitly loads the current annotation groups
after checking current parent visibility. It returns immutable
`AssertionAnnotation` records with `iri`, `property_iri`, `value`, `fields`,
`managed` and `asserted`. RDFLib scalar terms preserve IRIs, datatypes and languages;
`to_json()` produces the wire representation. This does not populate or change
ordinary property values. Normal reads, summaries and searches never load annotations.

Assuming the Travel model from the earlier stages, with a required `dateTime` field:

```python
from oldaplib.src.xsd.iri import Iri

Trip = factory.createObjectInstance('travel:Trip')
trip = Trip(iri=Iri('travel:T'), isAt=['travel:A'])
first = trip.add_annotation('travel:isAt', 'travel:A', {
    'travel:dateTime': ['2026-11-01T10:00:00Z'],
})
second = trip.add_annotation('travel:isAt', 'travel:A', {
    'travel:dateTime': ['2026-11-02T10:00:00Z'],
})
trip.create()  # One base assertion, two independent visits, one transaction.

trip = factory.read('travel:T')
trip.replace_annotation(first, {'travel:dateTime': ['2026-11-01T11:00:00Z']})
trip.update()
records = trip.annotations()
trip.remove_annotation(second)
trip.update()  # Retains the base assertion and the first visit.
```

`add_annotation` returns a fresh `urn:uuid:` IRI immediately; persistence occurs
with `create()` or `update()`. `replace_annotation` replaces the complete field
mapping of that ID without changing its assertion. Fields are arrays; empty arrays
mean no RDF values. Plain scalar values use model-directed coercion. Explicit RDF
term objects avoid ambiguity:

```json
{"type":"literal","value":"2026-11-01T10:00:00Z","datatype":"http://www.w3.org/2001/XMLSchema#dateTime"}
```

IRIs use `{"type":"uri","value":"travel:A"}` and language literals use
`{"type":"literal","value":"Visit","xml:lang":"en"}`. Reads expand IRIs.

## Validation, ownership and transactions

OLDAP resolves current property-use policies, including inherited constraints,
inside the resource transaction. All attached shapes apply conjunctively;
inherited required reification cannot be weakened by a child `false`. At least
one reifier is required for each base value when required reification applies.
Base cardinality counts assertions; field cardinality counts values per reifier.
Scalar validation is shared with ordinary properties, with explicit field
cardinality, datatype, language and node-kind checks. Object links use existing
visibility/class rules; controlled vocabulary `inSet` follows existing semantics.

Managed reifiers carry `rdf:type oldap:AssertionAnnotation`, belong exclusively to
one asserted triple and reside in the owner's project data graph. Permission and
system predicates are protected. Blank-node, external, orphan, shared and
cross-graph records remain diagnosable through explicit reads but cannot be
modified through generic instance operations. No automatic adoption or identity
renumbering occurs. Incoming references to reifiers also block mutation.

Parent ACLs apply. Explicit annotation edits require UPDATE; parent deletion
requires DELETE, subject to existing administrator rules. Stale resource timestamps
reject writes. Base data, annotations, modification metadata and history share the
existing transaction and rollback boundary. After a failed write, reload the
instance before further editing. Identical field replacements and repeated
identical history restores do not change timestamps or create history.

Removing one reifier retains its assertion. Removing the last required reifier
fails while the assertion remains. Removing a base value removes its exclusively
owned reifiers; deleting the parent removes all owned reifiers. External inbound
references are not cascaded. A link from an owned annotation back to its own parent
does not prevent parent deletion; cleanup and the remaining inbound-reference
check execute in one transaction.

## History and other write paths

Property history stores the previous complete annotation group as the separate
`oldap:historyReifierSnapshot` JSON literal. Annotation-only changes produce history.
Restore applies historical assertions and fields under current model/permission
checks. Changed groups receive fresh IDs; an already identical group keeps its
current IDs. Other property groups remain untouched.

Class transformations involving annotated data/models are explicitly rejected.
Inverse properties, structured Dating assertions and recursive annotations are
outside this profile. Instance-data YAML v1 cannot represent annotation identities
and explicitly rejects annotated models; ontology YAML remains supported.
There is no generic annotation-aware instance-copy API: callers must create the
new base instance and add new annotations with fresh IDs. Raw native data/history
graph export/import preserves existing IDs and snapshots; it is not a validating
import or an ownership-normalization mechanism. Imported unsupported records stay
read-only until an explicit migration is designed.

## REST API

See the [API contract](../../oldap-api/doc/reification-instances.md) and OpenAPI.
Creation/update accepts a reserved `@annotations` operations array. The dedicated
`GET /data/annotations/{project}/{instanceIri}` returns `{"items":[...]}`. Ordinary
GET/search payloads and query paths are unchanged. Search filters on annotation
fields are stage 4.

## Acceptance and performance

- 18 native tests pass on disposable Jena 6.2.0/TDB2, including actual Flask CRUD,
  independent visits, literal values, required/conjunctive/inherited shapes,
  language/IRI fields, permissions, stale writes, rollback, history/no-ops,
  ownership rejection, deletion cleanup and data/history transfer.
- 100 focused library/API regression tests pass.
- 200 tools tests and seven subtests pass with Python network sockets disabled,
  including native stage-2 round trips and the instance YAML guard.
- Live HTTP, Redis and deployment acceptance remain separate. Existing transform
  route tests requiring GraphDB on localhost:7200 could not run in this offline
  environment; native annotation-transform rejection is covered.

The [performance receipt](reification-stage3-performance.json) records source
hashes and the pre-stage-3 baseline commit. Both versions use the same current
supporting libraries and dataset, with 100 extra resources and 500 annotations.
Results and exact query text/count are equal: **one query per call** for ordinary
`read`, `read_data` and a 25-result search page. Each version has 300 measured calls
in 30 interleaved blocks after warmup. Paired bootstrap 95% intervals for runtime
differences include zero for all three operations; no slowdown is statistically
resolved in this local workload.

| Operation | Baseline median ms | Stage 3 median ms |
| --- | ---: | ---: |
| read | 3.656 | 3.659 |
| read_data | 3.127 | 3.093 |
| search page | 4.107 | 4.094 |

This verifies the unchanged query path and bounds local observations; it is not a
production latency guarantee. Explicit annotation reads and writes deliberately
perform additional validation/ownership queries. Reproduce with the pinned Jena
JAR from stage 1A, matching sibling sources on PYTHONPATH, and:

```sh
OLDAP_ANNOTATION_BENCHMARK=/tmp/annotation-performance.json \
python -m pytest oldaplib/test/test_assertion_annotation.py -q
```

`OLDAP_TEST_FUSEKI_JAR` must be set; the fixture uses the local Java 25 installation.
Without the benchmark environment variable only the timing test is skipped.

## Final-review refinements

Annotation SELECTs recheck current parent visibility in the same query, including
when a caller retains an instance across a permission revocation. Transactional
write preparation uses its existing write authorization boundary. Policies are
resolved only from the owning project, shared and system shape graphs.

Specialized archive/staging hierarchy history restores explicitly reject current
or historical annotations before moving nodes. Generic property history restores
remain annotation-aware. This restriction avoids silently dropping annotation
groups until the specialized move/restore contract supports them.

See [final review](reification-final-check.md) for corrected cache design and
current source-hashed performance evidence; previous receipts are historical.
