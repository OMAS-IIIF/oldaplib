# Reification model management — stage 1B

Implemented locally on 2026-11-14 in oldaplib and oldap-api on
`codex/reification-properties`. No release, deployment, live ontology update,
or oldap-tools change is included. [Working plan](reification-properties-plan.md).

## Model contract

`ReifierShape` is a named, project-owned SHACL NodeShape marked with
`oldap:ReifierShape`. It is independent of ResourceClass and is not a Thing
subclass. Its fields are copied PropertyClass definitions owned by the shape.
Use `shape[field_iri] = field` and `del shape[field_iri]` to change membership;
`shape.properties` exposes a read-only mapping with editable field objects.
Persist changes through the shape, not an individual owned field.

A property use carries `reifierShapes` (a set of shape IRIs) and optional
`reificationRequired`. RDF uses `sh:reifierShape` and
`sh:reificationRequired`. Explicit false is preserved. Several references
apply conjunctively, including inherited references. Attachments belong to
the class's property use, not globally to the predicate. Reusing `ex:isAt` in
another class does not copy its annotation policy.

References may point to local or shared definitions. Shared definitions remain
in their owning graph and are resolved afresh. Referenced, unmarked named
NodeShapes can be read; managed writes add the marker. Anonymous definitions,
unknown constraints and `oldap:statementShape` input fail explicitly. Existing
`appliesToProperty` / API `annotationProperties` retain their legacy meaning.

Fields require a datatype or class constraint. Supported constraints include
cardinality, node kind, bounds, string restrictions, enumeration and language
restrictions, plus field display metadata. Node kind alone, nested reifier
constraints, inverse paths and cross-property constraints are outside this
initial profile. Unsupported input is rejected rather than dropped.

## Python

```python
from oldaplib.src.reifier_shape import ReifierShape
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes

visit = ReifierShape(
    con=con, project=project, shape_iri="ex:VisitShape",
    properties=[PropertyClass(
        con=con, project=project, property_class_iri="ex:dateTime",
        datatype=XsdDatatypes.dateTime, minCount=1, maxCount=1,
    )],
)
visit.create()
visit = ReifierShape.read(con, project, "ex:VisitShape")

# Set on the PropertyClass owned by the intended ResourceClass.
travel["ex:isAt"].reifierShapes = {"ex:VisitShape"}
travel["ex:isAt"].reificationRequired = True
travel.update()
```

`DataModel(..., reifier_shapes=[visit])` supports aggregate authoring;
`model.reifier_shapes`, `model.get_reifier_shapes()` and mapping operations
expose definitions. Read/write/export include complete named shapes and field
predicate declarations. Shapes do not produce OWL class restrictions.
The isolated [Travel fixture](../oldaplib/testdata/reification/travel.trig)
illustrates the RDF format; it is not loaded into a live project.

## API

Authenticated `/admin/datamodel/<project>/reifier-shape/<shape>` supports:

| Method | Behavior |
| --- | --- |
| GET | Read one definition with field and available audit metadata |
| PUT | Create; return 201, conflict if already present |
| POST | Update; supplied `properties` replaces the full field list |
| DELETE | Delete an unreferenced definition; return 204 |

Write body: `{"properties": [{"iri": "ex:dateTime", "datatype": "xsd:dateTime", "minCount": 1, "maxCount": 1}]}`.
On POST, omitted properties retain fields; `[]` removes all fields subject to
in-use checks. Unknown keys and duplicate field IRIs fail. Model GET adds
`reifierShapes`; property responses include the references and optional flag.
Existing property update endpoints accept `reifierShapes: []` to clear links,
`reificationRequired: null` to remove the flag, and `false` to retain an explicit
false value. Omitting keys retains their current values. Removing all links
while retaining a required flag is invalid unless references are inherited.

Malformed input returns 400, missing shapes 404, denied writes 403, and
in-use/concurrent-write/create conflicts 409. Library writes require project
ADMIN_MODEL or global ADMIN_OLDAP. Library modification tokens protect the
read-to-write transaction; the API does not add client ETag concurrency.
See the sibling API repository's `API-def/oldap-api.yaml` for schemas.

## Integrity and staged boundary

Writes check references, ownership and incompatible OWL predicate types.
Deleting a referenced shape is refused. Structural definition changes and
policy attachment changes are conservatively refused when relevant predicates
have asserted values; metadata-only shape edits remain possible. This is not
a data migration facility. Shape CRUD is transactional. DataModel.update keeps
its existing per-object transaction behavior, not whole-model atomicity.

Complete DataModel snapshots, including owned reifier definitions, are cached.
Cache hits perform no reifier-presence probe. Explicit shape reads and mutation
validation remain fresh; active transactions bypass model snapshot caching.
Shape writes evict the owner model immediately and at outer transaction completion
(commit or abort). Property-use writes invalidate owner and dependent subclass
model snapshots across graphs. See the final-review report for updated evidence.

OLDAP remains responsible for validation. Stage 1B does not implement instance
annotation CRUD or replace validation with an external SHACL engine. A fresh,
transaction-local barrier rejects instance writes for affected models, inherited
policies, transformation source/target classes and optional link sources. It
also checks for existing business reifiers even after model links disappear.
Existing permission reifiers are excluded. Direct administrative SPARQL/import
access is outside this library instance-operation barrier.

## Verification

83 focused library/API tests pass, covering model round trips, field ownership,
false/removal semantics, shared references, cache invalidation, authorization,
transaction rollback, history regressions and the instance barrier. API tests
use Flask with an isolated RDFLib dataset; they are not live HTTP acceptance.
Seven native Jena checks pass for actual shape CRUD and generated RDF 1.2
barrier queries in a disposable TDB2 directory. No HTTP or Redis service is
required by the native probe. This is focused acceptance, not the full suite.

[Native evidence and source hashes](reification-stage1b-results.json).
Run with the existing API development environment and pinned Fuseki 6.2.0 jar:

```sh
../oldap-api/.venv/bin/python tools/reification/probe_model.py \
  --java-home /opt/homebrew/opt/openjdk@25 \
  --fuseki-jar /path/to/fuseki-server.jar \
  --output /tmp/new-empty-stage1b-output
```

Next is stage 2: YAML authoring and round trips in oldap-tools. Instance writes
remain gated until the complete stage 3 lifecycle is implemented and tested.
