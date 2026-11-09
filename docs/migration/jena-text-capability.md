# Jena Text: initial compatibility probe

Follow-up: [public full-text integration](jena-fulltext-integration.md) now connects a validated subset through oldaplib and Fuseki.
The scope below describes the earlier standalone milestone.

## Completed scope

`tools/migration/JenaTextProbe.java` exercises Jena Text/Lucene from the existing
Fuseki 6.2.0 jar, over a new owned persistent TDB2 dataset and separate Lucene index.
This is a standalone Java capability test, not an HTTP/Fuseki servlet test or an
OLDAP search implementation. Public library/API code and production configuration
are unchanged. The existing Jena prototype still rejects connector full-text.

The checkout was clean on entry, on `migration/jena`. The fixture uses explicit
field mappings for title/body, graph/language fields, a UID field for deletion and
StandardAnalyzer. GraphDB/Redis/live connector settings were not queried or changed.

## Repository findings and compatibility boundary

`ResourceInstance.search(ftfilter=...)` uses project-named GraphDB Lucene
connectors and a combined field-qualified query. `ResourceInstance.search_fulltext`
is a separate literal-substring search and must not silently change to token
semantics. `ProjectLuceneConnector` and the API expose GraphDB configuration,
including arbitrary options and property chains. The connector unit fixture also
preserves valueFilter and unknown nested options. Actual deployed connector
settings have not been inventoried; checked-in examples are not that inventory.

The initial Jena setup maps one indexed literal quad to one Lucene document.
The probe explicitly demonstrates that raw `title:red AND body:forest` does not
match an entity with those terms in separate fields. Similarly `red AND portrait`
does not join two separate title literals. Independent text:query patterns joined
by the resource return the expected entity; UNION handles an explicit field OR.
These are known capability limits recorded as passing assertions, not proof of
complete GraphDB equivalence. Arbitrary Lucene expression translation, including
NOT, grouping, boosts and scores, is not implemented by this probe.

The StandardAnalyzer fixture keeps accents significant: `wälder` matches,
`walder` does not. That is an observed default, not a chosen OLDAP search policy.
Language restriction is tested independently of analyzer equivalence.

## Validation

All 24 checks pass in the accepted owned run:
`~/Library/Application Support/OLDAP-Jena/probes/j12-text-03`.
See `jena-text-capability-results.json` for individual checks.

Coverage includes committed indexing, case/phrase/wildcard/boolean token queries,
graph isolation (including the same subject in two graphs), language restrictions,
accent behavior, cross-field and multivalue limits/joins, field OR, RDF 1.2 role
and permission joins, distinct counts and permission-before-page selection,
rollback of insertion/deletion, committed replacement/deletion, and clean close
and reopen of the dataset/index in the same JVM. This is not process-crash recovery.
The ACL fixture mirrors the earlier permission rules but does not call Python
OLDAP authorization code or the protected receipt dataset view.

The first run stopped at a probe assertion that assumed a particular Jena literal
string representation for COUNT. The check now reads the typed integer directly;
the accepted run passes it. A final run added the separate-literal AND checks.
Only this new probe was run; unchanged Python suites were not rerun for this step.

Reproduction (output directory must not already exist):

```sh
java --enable-native-access=ALL-UNNAMED \
  --class-path '/Users/rosenth/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0/fuseki-server.jar' \
  tools/migration/JenaTextProbe.java '/absolute/path/to/new/output'
```

## Next implementation step and gates

Retain public search arguments and keep query adaptation at the internal backend
boundary. First inventory actual field mappings/options, then implement and test
an explicit supported subset of direct-property field searches through the real
Python search/permission/pagination path. Unsupported configuration/query options
must be diagnosed rather than ignored. Do not publish a partial implementation as
full GraphDB parity or silently redefine entity-level multivalue semantics.

The alternative of entity-oriented index documents requires a separate, concrete
evaluation if existing expressions need it; no custom index lifecycle or generic
query parser is introduced here. Also pending: property chains, type restrictions,
analyzer parity, ranking/score aggregation, index rebuild, protected-dataset and
HTTP/session integration, resource limits, concurrent reads, cache behavior and
hard-crash consistency of TDB2 versus Lucene. Successful normal rollback/reopen
checks do not establish atomic persistence across the two storage systems.

## Source

[Apache Jena full-text documentation](https://jena.apache.org/documentation/query/text-query.html)
describes the default per-triple document model, graph/language/UID fields and
SPARQL combinations of text queries. Its multiple-fields section references an
older Jena version; this report therefore uses the bundled 6.2.0 runtime checks
for its concrete conclusions rather than treating that historical note as current
implementation status. No production switch, commit or push was performed.
