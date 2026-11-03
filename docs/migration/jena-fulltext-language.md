# Fulltext language behavior

## Accepted policy

The user approved tolerant accent/umlaut/sharp-s matching, with word forms kept
separate. Both indexed text and query terms use lowercase, canonical Unicode NFC
and Latin ASCII folding. Authoritative RDF literals and language tags remain
unchanged. No stemming, compound splitting or stop-word removal is introduced.

| Case | Current behavior |
| --- | --- |
| Case | `laterne` and `LATERNE` return identical hits. |
| Umlauts | `Zürich` and `Zurich` return identical hits. |
| Sharp s | `Straße` and `Strasse` return identical hits. |
| Accents | `école`, `École` and `ecole` return identical hits. |
| Canonical Unicode | Precomposed and decomposed umlauts share the same hits. |
| Prefixes | `Zür*`/`Zur*`, `Straß*`/`Strass*`, `éco*`/`eco*` share hits. |
| Word forms | `Laterne` does not also find `Laternen`; `Latern*` finds both. |
| Compounds | `Laterne` does not find `Fasnachtslaterne`. |
| German transliteration | `Zuerich` is not automatically equivalent to `Zürich`. |
| Multiple words | All words must occur within the same configured field, regardless of order; separate values may supply them. |
| Hyphens | `BMG-Stamm` has the same AND semantics as `BMG Stamm`. |
| Apostrophes | `L'art` can be searched as a word; `art` alone does not match it. |
| Phrases | Token order is preserved; `"BMG Stamm"` also matches stored `BMG-Stamm`. |
| Stop words | `die` remains searchable. |

Latin folding is not a general transliteration or phonetic matcher. No language
restriction is inferred from RDF language tags. Wildcard `?` counts characters
in the normalized indexed term, not in the original spelling (e.g. ß becomes ss).

## Implementation

`tools/migration/OldapTextAnalyzer.java` is the shared analyzer used by
`JenaTextFixture.open`, including managed index rebuilds and live writes. Its
standard tokenizer preserves the previous word boundaries. A small token filter
composes canonical Unicode, then Lucene's ASCIIFoldingFilter emits one folded
token per input token. Positions and original offsets are retained. The same
transformation implements Analyzer.normalize for wildcard/prefix queries.
No new external dependency or per-project analyzer registry is introduced.
See [Lucene ASCII folding API](https://svn.apache.org/repos/infra/sites/lucene/core/10_1_0/analysis/common/org/apache/lucene/analysis/miscellaneous/ASCIIFoldingFilter.html).

The Python query adapter normalizes input to NFC before safe grammar validation,
so decomposed words are accepted by API/library clients too. Leading minus/plus,
leading wildcards, field colons, parentheses and raw Boolean expressions remain
unsupported. Public signatures, configured fields, current permission checks and
the optimized text-before-root-ACL query order remain unchanged. GraphDB behavior
is unchanged.

## Index upgrade and operational boundary

Existing indexes must be rebuilt from authoritative RDF using the new analyzer.
The current managed Jena service already discards/rebuilds its derived indexes
on every startup before serving queries. Restarting the rebuilt service therefore
performs the upgrade from stored project configuration. Include the new analyzer
class in service packaging. Merely replaying identical YAML is a no-op and does
not upgrade a running service/index. No production service has been restarted
or deployed by this task. A deployment still needs its usual maintenance window
and startup/recovery checks; this document is not deployment authorization.

The managed acceptance verifies Unicode text written before activation, exact
and prefix folding, distinct singular/plural, startup rebuild, and byte-equivalent
literal content/language afterward. Existing crash, failed publication, revision,
rollback, private-graph and administration checks are retained.

## Validation and reproduction

The [recorded matrix](jena-fulltext-language-results.json) contains 34 language
queries over 13 synthetic resources, with explicit grants. Fixture text is
committed to exercise indexing, then removed in a finally block. All 181 native
checks (including 12 language assertions), 50 managed lifecycle checks and 41
offline grammar/configuration tests pass. No production corpus or GraphDB parity
is claimed. The source text remains unchanged; all services belong to the tests.

Run `tools/migration/probe_model_reads.py --java <java> --jar <fuseki-jar>
--output <new-private-directory>` for native language/search acceptance, and
`tools/migration/probe_fulltext_activation.py` with the same arguments for managed
activation/restart/recovery acceptance. The normal real-export API rehearsal also
checks new-field activation with decomposed text, folding, prefixes, word forms
and unchanged returned literal values. All 30 fulltext API checks and 23 export
checks pass; 26 timed API searches have median 87.5 ms and maximum 581 ms in the
owned local run. [API evidence](../../../oldap-api/doc/jena-fulltext-folding-results.json)
retains timings and check names. The source export SHA-256 is unchanged; all owned
services were stopped after acceptance. Production concurrency/load remains open.
