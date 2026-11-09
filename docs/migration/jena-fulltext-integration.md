# Public OLDAP full-text search through Fuseki

Follow-up: [project configuration and chains](jena-configured-fulltext.md) replace the fixed fixture mapping with YAML-driven fields.
The earlier milestone below documents the initial direct-field scope.

## Completed path

`ResourceInstance.search(..., ftfilter=...)` now uses Jena Text through the owned,
authenticated Fuseki session servlet, with real Python search generation, model
metadata, authorization query and result processing. Public signatures and result
keys remain unchanged. The normal Connection/GraphDB path is unchanged; this is
an opt-in migration implementation, not a production backend switch.

The concrete internal `IConnection._resource_fulltext_pattern` hook refuses an
unconfigured index. The migration ReadConnection supplies its project's reviewed
field map to `helpers/jena_fulltext.py`. The helper validates and builds the text
pattern; existing search code handles permission joins, structured/list filters,
COUNT(DISTINCT), property expansion and final ordering/pagination.

Deep-page correction (2026-11-01): omitting the Jena Text limit does **not** mean
unlimited hits. Jena 6.2 defaults omitted/nonpositive values to 10000 index
entries, before OLDAP permission filtering. Each generated text lookup now uses
Java's maximum positive integer to cover Lucene's document domain. Final resource
LIMIT/OFFSET remains outside access/filter joins. Broad matches still need memory
and query work proportional to their candidates; this is not streaming search.
No reindex or ontology change is required. See the
[100-row paging rehearsal](../../../oldap-api/doc/jena-search-pagination.md) for
the reproduced failure and corrected count/deep-page checks.

## Explicit supported subset

The fixture maps `name` to `test:name` and `description` to `test:subName`, using
StandardAnalyzer. This is a matching Python/Java test configuration, not a
translator or inventory of deployed GraphDB connector configurations.

Supported expressions are a single word, a word with nonleading `*`/`?` wildcards,
or a double-quoted phrase containing words. FTSearchFilter items must alternate
with `AND`/`OR`; AND binds more tightly. Each atom has its own score variable.
AND joins text matches on the same resource, including different values of the
same property. OR uses UNION. AND scores are added, with the existing resource
aggregation taking MAX over literal combinations and OR branches. Scores are
numeric and drive pagination, but neither score values nor ranking equivalence
to GraphDB are promised by this step.

Example using the unchanged public method on a configured Jena connection:

```python
ResourceInstance.search(
    con, project,
    ftfilter=[FTSearchFilter('name', 'fox'), 'AND',
              FTSearchFilter('description', 'forest')],
    limit=20,
)
```

Unknown fields, arbitrary field-qualified Lucene, raw Boolean expressions,
leading wildcards, NOT, boosts, proximity/fuzzy syntax
and malformed sequences are rejected with OldapErrorValue. These restrictions
are deliberate migration limitations, not full GraphDB compatibility. Atomic
expressions use Xsd_string serialization rather than raw SPARQL interpolation.
The separate legacy `search_fulltext` substring method remains unchanged and
unmigrated. Property-chain and connector administration APIs are also unchanged.
No harvester/tool signature changes are required; consumers must not be switched
to this subset until their actual query/configuration usage is reviewed.

## Index, transactions and metadata protection

The experimental engine optionally wraps TDB2 in a TextDataset so its existing
begin/commit/abort lifecycle also drives index changes. The protected application
view receives only the text-index context entry, not a transparent dataset
wrapper that could be unwrapped by optimizers. The explicit fixture producer
indexes only the selected project data graph. Internal receipts, admin graphs
and other projects never enter this index, even if they contain an indexed
predicate. This matters because text property functions can read an index
independently of RDF graph views.

A private receipt canary with an indexed predicate is seeded by the trusted
fixture loader. An unrestricted text lookup finds no hit, while ordinary project
text searches work. Normal RDF receipt protection and the default non-text
engine are also regression-tested. Future production mappings must preserve
these graph restrictions rather than exposing an unrestricted index.

## Validation

The accepted run passes 113 checks: the earlier 86 checks (the old full-text
refusal check now checks an unknown field) and 27 additional integration checks.
Coverage includes public field/phrase/wildcard/AND/OR search, same-property
multivalue AND, operator precedence, numeric scores, projection, superclass and
ordinary/list filters, no duplicate counts, permission-filtered paging, live role
removal, private receipt canary exclusion, unsupported-input rejection before
search HTTP calls, and index rollback/replacement/deletion through HTTP sessions.

Accepted run:
`~/Library/Application Support/OLDAP-Jena/probes/j12-text-integration-03`.
See `jena-fulltext-integration-results.json`. Reproduce with the existing
`probe_model_reads.py --jar ... --output <fresh-directory>` command. It enables
PROBE_TEXT_FIXTURE and invokes `probe_fulltext_checks.py` after the earlier checks.
Only cache I/O is replaced; real model/domain/search code executes.

The native identity/session/callback regression passes 20 + 20 + 11 checks in
`j12-text-identity-regression-01` with the text option disabled. These regressions
do not establish text-index hard-crash recovery. Sixty offline tests plus seven
subtests pass. Fourteen GraphDB query comparisons match HEAD modulo whitespace.
All datasets/processes are owned by the probes and closed; shared GraphDB/Redis
are untouched. No commit, push, deployment or production switch was performed.

## Remaining gates

Review actual field mappings, property chains, type restrictions, analyzers and
consumer expressions before expanding the subset or enabling a real API backend.
Complex Lucene/entity semantics and ranking need explicit comparison. Index
rebuild, concurrent/uncommitted text visibility, resource limits, hard-crash
consistency of TDB2/Lucene and durable recovery remain open. The earlier standalone
probe proves normal clean reopen, not distributed/dual-store atomic recovery.

Since 2026-10-31, ordinary unquoted words are supported as AND matches within
each configured field, including across literal values. Word order is irrelevant.
Quoted phrases still match a single indexed value. Separate configured fields
retain their explicit AND/OR relationship; arbitrary Lucene syntax is not enabled.
See the real Fasnacht rehearsal in ../../../oldap-api/doc/jena-fasnacht-fulltext.md.

## Query placement (2026-10-31)

The shared search/count builder now places Jena text patterns before root ACL
and property/list filters, keeping independent class choices first. All access,
scoring and paging rules remain unchanged. [Measured HTTP comparison and
regressions](../../../oldap-api/doc/jena-fulltext-performance.md) show identical
responses with representative medians reduced from seconds to 56–143 ms.

Ordinary input now accepts hyphens between words (AND semantics) and apostrophes
inside words. Quoted phrases accept both. See [language behavior and pending
analyzer decisions](jena-fulltext-language.md) for tested examples and Unicode
limitations; no index rebuild is required for this input-only correction.

The approved language-neutral folding analyzer now treats Latin accent/umlaut/ß
variants equivalently, including prefix queries and canonical Unicode forms.
Word forms remain distinct. Existing managed indexes require startup rebuilding;
see [current language contract and upgrade steps](jena-fulltext-language.md).
