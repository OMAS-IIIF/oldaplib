# Offline GraphDB RDF-star to OLDAP RDF 1.2 conversion

`tools/migration/ConvertLegacyRdfStar.java` is the first executable conversion
step for an existing legacy TriG export. It does not contact GraphDB, Fuseki,
Redis or any other service, and does not load its result into a live database.
It produces a new private directory with `converted.trig` and `report.json`.

## Supported input and semantics

Input is UTF-8 TriG or gzip-compressed TriG, at most 16 MiB **decompressed**.
The scope is the flat quoted-subject permission representation used by OLDAP:

```trig
@prefix oldap: <http://oldap.org/base#> .
@prefix p: <https://example.org/project/> .
p:data {
    p:object oldap:attachedToRole p:Reader .
    << p:object oldap:attachedToRole p:Reader >> oldap:hasDataPermission oldap:DATA_VIEW .
}
```

Supported membership predicates are `oldap:inProject`, `oldap:hasRole` and
`oldap:attachedToRole`, with IRI subjects/objects and named IRI graphs.
Permissions must match their membership type (admin, creation default, data).
Additional annotation metadata is retained. All ordinary RDF quads are copied,
including language literals and blank nodes shared across named graphs.
Prefixes, comments and textual formatting are not preserved as formatting.
No general OWL reasoning or SHACL validation is applied.

Jena 6.2.0 parses legacy `<< s p o >>` as reified-triple syntax, introducing
individual reifiers. The converter deliberately groups those occurrences by
**graph and membership triple**. It replaces generated reifiers with stable
`urn:oldap:migrated-grant:` IRIs derived from SHA-256 over a versioned canonical
membership key. Repeated values deduplicate according to RDF set semantics;
distinct permission values and other annotation metadata remain intact.
Identities are stable across repeated conversions. They need not equal the
UUID-based identifiers in the hand-migrated initialization files.

Crucially, a quoted membership is never asserted by conversion. Orphaned
annotations remain orphaned and are counted in the report. An annotation in
one graph cannot acquire a membership from another graph. Raw output is for
review, not evidence that every role/project/account reference is provisioned.

## Explicit refusals

- RDF4J encoded triple URIs (`urn:rdf4j:triple:`), produced by non-star export
  formats. Use GraphDB TriG-star/Turtle-star; do not treat these URIs as ordinary
  grants or decode them with ad-hoc text replacements.


The tool fails before publishing output for:

- Nested quoted triples, quoted triples used as objects or graph names, blank-node
  membership identities, unknown membership predicates, or mismatched permissions.
- Native RDF 1.2 triple terms mixed into the legacy input, explicit reification
  outside the supported representation, annotation shorthand and named-reifier syntax.
- Permission annotations in the default graph, unbased relative IRIs, generated
  identifier collisions, malformed RDF, invalid UTF-8 or oversized input.
- Old tools `#>>` serialized-user comments. Those are an administrative
  side-channel outside RDF; ignoring them would lose account information. This
  conservative line check can also refuse such text inside multiline literals.

Files containing that user side-channel need a separate account migration path.
Do not remove those records merely to get a nominally complete backup accepted.
A plain RDF file without annotations is supported, with zero generated reifiers.
Non-permission default-graph RDF is preserved, though the existing scoped Jena
project importer refuses default-graph data; conversion does not promise import
eligibility for every preserved graph.

## Running and reviewing

Use the already installed Java/Jena runtime; no additional parser dependency is
needed. Run from the oldaplib repository root:

```sh
java --class-path /path/to/fuseki-server.jar \
  tools/migration/ConvertLegacyRdfStar.java \
  /path/to/export.trig.gz /path/to/new-conversion-directory
```

The output directory must not exist. It is created with mode 0700, since exports
may contain administrative or private data. Inputs remain untouched. The tool
serializes and reparses the result and checks **dataset isomorphism**, including
cross-graph blank-node identity, before publishing output. The verification maps
quad components into one temporary RDF graph and uses Jena's graph matcher.
This preserves global blank-node identity (including blank graph names), while
avoiding the generic tuple matcher's exponential backtracking observed on the
real Chama model. The temporary verification representation never changes output. It cleans its own
partial output if writing fails; an existing destination is never overwritten.
A complete package contains both files.

The JSON report includes hashes of decompressed source text and output bytes,
the count of preserved ordinary quads, parsed annotation occurrences, normalized
membership reifiers, orphaned reifiers, zero added memberships and the verified
serialization round-trip. It contains no credential values or full RDF content.
The source hash describes decompressed UTF-8 text, not gzip container bytes.

This tool reads datasets into memory; the bound is deliberate. It is not a
streaming production migration tool. The existing private Jena HTTP transfer
limit (256 KiB per JSON request) is unchanged. The output is plain native TriG,
not the versioned `project dump` wrapper accepted by the tools project loader.
Graph selection, packaging and administrative provisioning must be checked before
an actual target import. Managed fulltext configuration and binary media are not
converted or activated by this step.

## Acceptance and next step

`LegacyRdfStarConversionProbe.java` supplies 28 passing checks, including the
optional comparison against the untouched original GraphDB seed files. Converted
permission relations match the migrated seed files. Synthetic cases cover value
merging, additional metadata, literal text containing quotation syntax, cross-
graph blank nodes, graph isolation, orphan preservation, explicit refusals and
lossless import into a separate owned TDB2 dataset. Additional checks reject
split cross-graph identity, altered graph/value/predicate and RDF4J-encoded triple
URIs; accept renamed nodes, reordered quads and blank graph names. No existing database changes.

`probe_legacy_conversion_cli.py` adds eight real CLI checks for plain/gzip files,
checksum/report validity, private output, no overwrite, invalid input, the
decompression limit and unchanged sources. Its temporary files are removed.
Retained results are in `graphdb-rdfstar-conversion-results.txt`.

The [real Chama rehearsal](../../../oldap-api/doc/graphdb-project-rehearsal.md)
now exercises a GraphDB export and isolated import/API comparison. Transfer
succeeds; content differences identify remaining bounded entailment work. Legacy
administrative side-channel migration, large packages, index configuration and
full migration acceptance remain open.
