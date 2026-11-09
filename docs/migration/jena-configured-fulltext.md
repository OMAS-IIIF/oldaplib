# Project-configured full-text fields and property chains

## Configuration principle

Field names and paths must be project configuration, not Python/Java constants.
The migration prototype now accepts a portable `fulltext` section after YAML/JSON
decoding. It is suitable for inclusion in a future oldap-tools ontology schema:

```yaml
fulltext:
  fields:
    archiveObjectTitle: [schema:name]
    archiveObjectDescription: [schema:description]
    representedArchiveObjectTitle:
      - fasnacht:archiveMediaObjectOf
      - schema:name
```

Each key is an existing public FTSearchFilter field name. Each value is a nonempty
forward predicate path; its last property contains the indexed literal. QNames
are resolved with the project's Context; full IRIs are accepted too. Aliases can
map to the same predicate. Unknown options, empty/malformed fields, invalid IRIs
and unknown prefixes raise OldapErrorValue rather than being ignored.

`jena_fulltext_fields` in `helpers/jena_fulltext.py` validates this section and
returns immutable full-IRI paths. `jena_fulltext_pattern` accepts these paths and
retains its earlier direct-Iri internal input for compatibility. Public search,
API and consumer method signatures remain unchanged.

**The section is implemented in the migration library/probe. It is not yet
accepted by the installed oldap-tools ontology importer or deployed admin API.**
Their schema, transport, persistence and index activation/rebuild workflow are
next integration work. Existing GraphDB YAML remains untouched. No silent
translation of GraphDB-specific flags, type/language restrictions or analyzers
is performed. The first portable schema intentionally rejects those options.

## One configuration source for queries and indexing

`tools/migration/fulltext-fixture.yaml` contains two project configurations. The
probe validates each section, uses the resulting paths for Python queries and
writes a normalized graph/terminal-predicate manifest consumed by Java.
`JenaTextFixture` derives its Lucene fields and graph/predicate allowlist from
that manifest. There are no hard-coded project fields in its index setup.
Aliases share a predicate index entry; identical field names in different
projects can refer to different properties. Internal receipt/admin graphs are
explicitly rejected and only configured graph/predicate pairs are indexed.

The file is loaded before fixture data is seeded. Changes to a running index,
adding fields to already populated datasets and rebuilding historical data are
not implemented here. A future activation workflow must rebuild/reconcile index
contents before exposing new configurations; this is not hot reload.

## Chains without copied root text

For a chain such as media -> represented object -> description, the index stores
the terminal description on its own subject. A project-scoped RDF path joins that
subject to the root search resource. Root permissions, class filters, distinct
counts and pagination remain in the existing search query. This avoids a custom
registry of copied root text and reverse dependencies.

Multiple target hits do not duplicate root counts. Independent AND conditions
can match different target values. Unlinking a root immediately changes the
query result without reindexing the unchanged terminal text. Changing terminal
text uses the normal transactional text index update.

The permission policy authorizes the root resource; there is no additional ACL
check on intermediate/terminal nodes. This follows the intended connector-style
field projection, but is not a live GraphDB policy comparison. Project owners
must treat configured chains as properties exposed through the root resource.
Paths are restricted to the root project's data graph; cross-project traversal,
reverse paths, wildcard paths and inferred property relations are unsupported.

## Findings from existing consumers

The read-only snapshot in `fulltext-consumer-inventory.json` records source paths
and hashes. The local fasnacht ontology export has eight fields: six direct
fields and two represented-object chains. Aliases share schema:name/description.
It also specifies types, languages and flags that the portable schema does not
yet reproduce. This export is not a verified current production configuration.

FasnachtsPage archive searches OR together named fields and pass normalized,
trimmed user text. They also request archiveMediaObjectText, absent from this
particular export. That mismatch must be checked against the real configuration,
not guessed. Arbitrary/multiword user text remains a separate Jena query-grammar
compatibility gap. The API preserves field names and accepts AND/OR between
filters. No external checkout was edited by this step.

## Validation and discovered class-filter issue

126 owned-Fuseki checks pass (113 earlier plus 13 configuration/chain checks).
They cover two projects, project-specific field names/aliases, two-link paths,
root ACL, distinct counts, independent chain predicates, cross-graph exclusion,
abort/commit of unlinking and terminal-text updates/deletions. The second project
is introduced entirely by configuration and fixture data, without code mappings.

That second-project fixture exposed a Jena class-filter bug: a zero-length
subClassOf path did not retain an asserted type absent from the selected schema
graph. The Jena path now explicitly accepts equality of asserted class and target,
or an existing positive-length subclass path. GraphDB behavior is unchanged;
all prior superclass/linked-class tests continue passing. The QName validation
test also led to passing an explicit Xsd_QName to Context.qname2iri, avoiding its
existing string-conversion positional-argument problem without changing Context.

76 offline tests plus 7 subtests pass, including 16 configuration cases. Fourteen
GraphDB query comparisons remain equal to HEAD modulo whitespace. Accepted run:
`~/Library/Application Support/OLDAP-Jena/probes/j12-configured-text-05`.
See `jena-configured-fulltext-results.json`. Reproduce via the existing model-read
runner with a fresh output directory; its YAML is now the authoritative fixture
configuration. Identity/session suite was not repeated because its non-text
configuration/lifecycle was unchanged in this step. All owned processes close;
shared GraphDB/Redis are untouched. No commit, push or deployment was performed.

## Next gates

Integrate this configuration concept into the oldap-tools ontology schema and
backend administration/persistence lifecycle; agree on missing type/language and
analyzer semantics before migration of native connector payloads. Resolve actual
consumer text grammar, ranking, initial indexing/rebuild, concurrent/uncommitted
visibility and hard-crash index consistency. The current configuration does not
establish complete GraphDB connector parity or production readiness.

## Follow-up: managed activation

The isolated service now persists field paths and supports controlled activation
and restart rebuilds. See [managed fulltext lifecycle](jena-fulltext-activation.md).
Public API/import authorization and dump/backup wiring remain pending.
