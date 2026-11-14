# Reification final merge-readiness review

Completed local source review, 2026-11-14. No commit, push, merge or service mutation.

## Scope and method

All tracked working-tree changes and untracked additions in oldaplib (HEAD/main
717feec), oldap-api (c37b95d) and oldap-tools (6f28088). No staged changes or commits
ahead of locally recorded origin/main. Remote refs were not refreshed.
The explicitly invoked final-check skill requires an audit-only first pass,
collective fixes, a second complete pass and relevant verification.

Checklist used in both passes:

| Area | First pass | Second pass |
| --- | --- | --- |
| Architecture/responsibilities | Reviewed domain/model/search/tools boundaries | Reviewed; corrections and verification below |
| Data model/integrity | Findings below | Reviewed; corrections and verification below |
| Domain/technical invariants | Findings below | Reviewed; corrections and verification below |
| Error/abort/recovery | Findings below | Reviewed; corrections and verification below |
| Concurrency/transactions | Cache completion needs coverage | Reviewed; corrections and verification below |
| Security/privacy | Graph ownership and nested ownership findings | Reviewed; corrections and verification below |
| Dependencies/platform | Matched sibling sources required; legacy dialect gap | Reviewed; corrections and verification below |
| Backward compatibility/performance | Factory/model-cache path missing from prior benchmark | Reviewed; corrections and verification below |
| Tests/documentation | Add targeted coverage and corrected evidence | Reviewed; corrections and verification below |

## First-pass findings (before edits)

1. **P1: cached reads execute a new RDF ASK.** DataModel.read checks reifier
   presence before returning cache hits and bypasses annotated-model caching.
   Factory construction loads project/shared models; prior timings start after
   factory creation. Restore cached reads without RDF probes, invalidate owned
   snapshots on shape writes at transaction completion, and cover factory setup.
2. **P1: policies can be injected from unrelated project graphs.** The fresh
   traversal scans all named graphs for a class-shape IRI. Restrict traversal to
   the owning project, shared and system shape graphs, including transform guards.
3. **P1: shape replacement can delete shared blank property/list nodes.** The
   deletion closure assumes ownership without checking incoming references.
   Reject shared/cross-graph nested nodes before any deletion; retain rollback.
4. **P2: DataModel.create bypasses used-policy attachment guards.** Individual
   ResourceClass writes protect used predicates, but whole-model insertion does
   not. Apply the same guard within its transaction.
5. **P2: ownership copies lose change tracking/isolation.** PropertyClass deepcopy
   assigns `_changset` instead of `_changeset`, and ResourceClass assignment sets
   the caller's notifier before copying. Correct ownership and nested callbacks.
6. **P2: legacy writes receive RDF 1.2 syntax before capability rejection.**
   Ordinary non-RDF-1.2 CRUD and transformation guards must use their supported
   quoted-triple dialect. Explicit annotated writes remain capability-gated.
7. **P2: copied scalar comparison uses the wrong sibling key.** The shared
   lessThanOrEquals implementation looks up lessThan; missing sibling values
   are also wrapped before the absence check. Correct and cover both operators.
8. **P2: hierarchy history restore bypasses annotation restoration.** API archive/
   staging move branches restore values without the annotation group. Explicitly
   reject annotated hierarchy restoration before movement until a composed
   annotation-aware hierarchy-restore contract exists; generic restores remain.
9. **P2: model/API invalid-input gaps.** Protected system predicates can enter
   reifier definitions, and annotation scalar inconsistencies on instance creation
   become HTTP 500. Reject protected definitions/policies and return client errors.

Typed literal/date/decimal/boolean/language lifecycle and native noncanonical
integer/boolean probes passed in an isolated temporary audit module; no finding
is claimed for those hypotheses. No changes were made during the first audit.

## Verification constraints

Makefile test/load targets clear or replace service data. Do not run them against
existing services. Use offline regression suites and disposable native Jena/TDB2.
No CI workflow or configured repository-wide lint/type-check gate was found.
Build wheels locally without publishing or installing into active environments.
Installed dependency/version coordination and live HTTP/Redis/other-platform
acceptance remain separate from source review.

## Corrections and second complete pass

All nine first-pass finding groups were corrected together, with regression
coverage in `test_reification_final_review.py`, the model/transaction tests and
API history tests. No new production dependency or broad redesign was needed.
The same complete checklist was then applied again. Two additional findings were
corrected together:

- **P1: retained parent instances could bypass a later permission revocation.**
  Annotation reads now include a parent-visibility EXISTS in their own SELECT;
  native regression revokes membership between parent and annotation reads.
- **P2: absolute sibling-property IRIs did not match QName dictionary keys.**
  Scalar comparisons now resolve absolute targets through the connection context;
  both missing targets and equality/ordering behavior are covered.

Final OpenAPI validation additionally caught one unquoted comma in a flow-style
409 response description. Quoting the description restores full validation.
The corrections are bounded. They received targeted reinspection and tests;
no third complete review was performed. No concrete unresolved source finding
remains. Architecture stays proportionate: named shapes, property-use references,
existing transaction ownership, and explicit annotation read/search operations.

Test-fixture corrections provide the real `oldap:Thing` ontology and disable
RDFLib's remote FROM-graph loading. Cache tests use actual JSON serialization,
with Redis transport replaced by an in-memory store, so reconstruction and
independence are exercised rather than returning preconstructed model objects.

## Verification results

- Combined isolated suite: **366 passed, 9 subtests passed, 3 opt-in checks
  skipped**. Includes all tools tests/test, library model/history/transaction/
  barrier/cache/query tests, API model/history/read-fast-path/parser tests, and
  native annotation lifecycle/search/final-review regressions. Outbound socket
  connections were disabled. Native Jena used disposable local TDB2 storage.
- All **three opt-in checks passed separately**: ordinary read/search timing,
  fresh cached-factory timing, and bounded annotation-search query/algebra evidence.
- Wheels built successfully for library, API and tools; ZIP integrity verified,
  new feature modules included. All 37 changed/new Python files parsed.
  Artifact paths/hashes: [build receipt](reification-final-builds.json).
- OpenAPI 3.1: full `openapi_spec_validator.validate` passed; unique YAML keys
  and all 899 references checked across 102 paths. Baseline also validates.
- `git diff --check` passed in all three repositories.

Performance receipts use current source hashes and 300 measurements per version:

| Existing path | Baseline median ms | Current median ms | RDF queries |
| --- | ---: | ---: | ---: |
| read | 3.554 | 3.542 | 1, identical text |
| read_data | 2.919 | 2.941 | 1, identical text |
| search page | 3.852 | 3.848 | 1, identical text |
| Fresh factory / warm serialized model cache | 1.673 | 1.643 | 0 |

All paired 95% delta intervals include zero: no measurable slowdown in these
local comparisons. [Ordinary paths](reification-final-performance.json),
[factory setup](reification-final-factory-performance.json), and
[annotated search](reification-final-search.json) retain detailed evidence.
The factory comparison isolates HEAD versus current DataModel.read while sharing
the current serializer/factory and cached annotated models. Redis transport,
HTTP, cold caches and production-sized models are outside these measurements.
Earlier stage receipts remain historical; their preconstructed-factory timings
alone did not cover the model-cache regression found in this review.

## Boundaries, unavailable checks and conclusion

**Unresolved findings:** none in the reviewed local source scope.
**External blockers:** none for source merge. Release/deployment still requires
coordinated versions and installation tests for the three matching artifacts.
These locally built wheels retain development version 1.1.0 and are not release
artifacts; they were not installed, published or used to replace live services.

**Unavailable/not executed:** live HTTP/Redis/GraphDB integration, Linux/container
and installed-wheel end-to-end checks. Existing Makefile suites mutate service
data and were deliberately not run. No repository-wide configured lint/type-check
or CI gate was found. Native checks use macOS Python 3.14 and pinned Jena 6.2.0;
legacy quoted-triple selection is tested but not against a running GraphDB.

**Retained profile limits/risks:** OLDAP performs validation; the SHACL reifier
vocabulary remains a pinned draft profile. External/blank/shared reifiers stay
read-only; annotated transformations, instance-data YAML v1 and specialized
annotated hierarchy history restores are explicitly rejected. Local timing
supports the tested warm paths, not a universal zero-overhead or capacity claim.

**Optional future work:** no additional merge requirement. Deferred annotation
sorting/fulltext/aggregation and broader rollout acceptance remain separate work.

**Conclusion:** ready for a coordinated local source merge of the three branches
within these boundaries. This review does not authorize or certify a release or
deployment. Nothing has been committed, pushed or merged.
