# Can OLDAP transactions become one HTTP request?

Implementation follow-up: the [authentication revocation pilot](authentication-revocation-pilot.md) now proves the first bounded guarded mutation with digest-bound receipts. Public connection integration and composed operations remain pending.

Date: 2026-10-27. Status: source audit plus isolated Fuseki tests; proposed design,
not a port of production operations. No application transaction implementation,
live database, Redis state or API service was changed.

## Conclusion

One **mutating** HTTP request per complete business operation is a sound target.
It is not a transparent replacement for every current transaction context:
Python currently consumes intermediate results, computes subsequent writes and
can execute arbitrary callbacks before committing. Those decisions must be
expressed server-side or prepared outside the write transaction and revalidated
inside it. Merely collecting UPDATE strings cannot preserve the contract.

Distinguish three claims:

1. **One SPARQL Update request:** feasible for fixed updates and carefully coupled
   conditional mutations. It does not return ordinary SELECT result sets or an
   application conflict result just because a WHERE matched nothing.
2. **One HTTP command request to a Jena extension:** can run checks, writes and
   result queries in one local transaction, then report a result after commit.
   This needs a small maintained server component, but no remote transaction
   session. It is the promising direction for the harder cases.
3. **Exactly one HTTP round trip for all preparation, arbitrary Python branching
   and returned business results, with unchanged code:** not established and not
   provided by stock Fuseki. This requires moving the relevant computation to
   the server, or deliberately changing the application contract.

Prefer one atomic mutation command, allowing preparatory reads where necessary.
Do not make the total request count a stronger requirement than correctness and
maintainability. No automatic replay of ambiguous writes is introduced.

## Public compatibility requirements

User requirement (2026-10-27): preserve existing HTTP API routes, methods,
request/response contracts and externally observable behaviour. Preserve public
oldaplib function/method signatures, return values, exception semantics and
transaction composition, including callers in oldap-harvesters and oldap-tools.
Internal helpers and backend transport may change. New internal operation IDs or
receipts must not force callers to supply additional arguments.

Do not silently weaken public resource_transaction or before_commit semantics to
meet a one-request target. If that target conflicts with compatibility, revise the
internal design first. Arbitrary Python callbacks and transaction-local reads are
explicit compatibility questions, not implicitly deprecated features.

Any unavoidable public incompatibility must be identified before adopting it:
record old/new signatures or behaviour, rationale, every known caller and affected
repository, required edits, tests, and coordinated migration/release order. Discuss
such an exception with the user before implementation. Document it in a dedicated
migration note and link it from both project contexts; never hide it among helper
refactors. External consumer changes are not authorized merely by this requirement.

For each pilot, verify compatibility through the existing public entrypoint,
including return type, error mapping, cache effects and replay/commit uncertainty.
A backend-only capability probe is not sufficient acceptance of the public API.

## Inventory and coverage

[Boundary inventory](transaction-inventory.md) lists every detected owning/context
function and its provisional disposition. [Call-site snapshot](transaction-call-sites.json)
includes helper, callback and bypass-writer locations with source hashes.
The reproducible scanner is `tools/migration/inventory_transactions.py`.

- 620 Python files parsed in eight repositories, including tests and tools.
- Core library: 53 functions with a start/context/decorator, including three
  transaction-infrastructure functions; not 53 independent business transactions.
- API: 20 such functions, including import/export/mobile repositories and staging.
- Direct external consumers: four harvester functions and one taxonomy migration.
- FasnachtsPage: eight operational/probe functions in documented scripts.
- No direct transaction owner found in the inspected mediaserver, import-tool or
  setup Python. Their indirect library/API use still needs migration.

Both explicit `transaction_*` calls and `Model.safe_*`, modification helpers,
resource decorators, `resource_query`, method references passed to helpers and
`before_commit` keyword callbacks were inspected. A workspace text search added
operational scripts missed by limiting the scope to the two core repositories.
Tests were parsed but do not count as production owners.

This is complete for the scanner's recognized syntax in that source snapshot,
not proof of all dynamic runtime paths or arbitrary downstream library clients.
Do not say the migration covers everything until each inventory row has a test
and the remaining direct write escape routes have an explicit policy.

## Concrete operation traces

### User.revoke_authentication: first bounded port candidate

`oldaplib/src/user.py:446` (method; transaction starts at line 499):

1. Authorize actor and prepare expected authVersion, modification time and new values.
2. Conditional DELETE/INSERT changes authVersion and metadata.
3. Read authVersion and modification time inside the transaction.
4. Python compares the persisted values and aborts on conflict; otherwise commit.
5. Update the Python object and invalidate Redis only after successful commit.

The mutation already fits one guarded update. The unresolved part is reporting
whether it applied, plus ambiguous-commit/replay handling. A new request ID and
request digest stored atomically with the result can distinguish success from a
stale request; stock Update requires a separate receipt read. Alternatively, a
server command can return the checked result in the same HTTP response. Do not
infer success merely from HTTP 204 or from a later mutable authVersion value.
Current authorization and revocation semantics must remain equivalent.

### ResourceInstance.update with lifecycle hook: representative difficult case

`objectfactory.py:1754` is only the method body. Its decorator in
`resource_transaction.py:166` adds important work:

1. Join or open the outer transaction; load archive policy and inspect the old state.
2. Check permissions, domain constraints, linked/reference state and Dating usage.
3. Apply resource changes, conditionally change modification metadata, then read
   the new timestamp. Python raises if verification fails.
4. Complete reference retention/transfer and audit; those helpers may read the
   just-written state and perform more changes.
5. Execute `before_commit(connection)`. The API's `_mobile_lifecycle_hook` appends
   an outbox event in the same transaction.
6. Only the outer owner commits. Any nested failure marks the scope rollback-only.

A resource-body-only port would omit reference/audit/outbox atomicity. Some current
payload changes precede the timestamp check: placing those updates and the
conditional timestamp update in one request does not recreate Python's final
abort on a mismatch. Check the common preconditions before *all* effects, or
perform a real final assertion before commit in a server command.

For a prepared command, bind permission state, relevant schema/policy revisions,
resource revision, incoming/reference sets and nonexistence checks that determined
the plan. Object timestamps alone do not protect against newly inserted children,
references or changed user grants (phantoms). Do not add a global revision system
without proving that every writer updates it.

### Hierarchical lists: intermediate reads matter

`OldapListNode.insert_node_right_of` and `insert_node_left_of` write index changes,
read the altered state, compute further changes, then verify. Move/delete methods
read indices/parents and calculate multiple range updates in Python. A static
concatenation of today's already-computed strings is insufficient in general.
Candidates: explicit SPARQL arithmetic/subqueries with protected intermediate
values, or one bounded server command for the list operation. Preserve cycle,
usage and cardinality checks. Intermediate values overwritten by an earlier
update must not be naively read again as if they were the original snapshot.

### Jobs, archive operations and direct consumers

- Import/export job claims deserialize RDF/JSON into Python objects, select eligible
  work and construct a replacement. Quota checks are aggregate predicates; a
  revision check on one job does not protect against another new job.
- `commit_import` resolves current target grants, checks collisions and writes
  resources plus job state. Both must share one command and all guards.
- Mobile commits combine replay lookup, target resolution, permission checks,
  optional inbox creation and atomic resource/receipt insertion.
- Archive adoption/publication/reference moves compute digests, create new IRIs,
  loop over selected resources and write canonical JSON receipts. Preparing these
  in Python is possible only if the server validates the complete dependency set.
- Harvester `write_payload` composes search → create → publication preview → apply.
  Preview sees the newly created resource within the transaction. `write_linked_pdf`
  can nest another owner. This is a concrete counterexample to buffering writes
  while executing reads against an unchanged database.
- PDF text extraction already runs before its write transaction. Its final
  source/provenance/text comparison is a good candidate for a conditional plan.
- Taxonomy tooling performs multiple updates then a verification query and aborts
  on violations; a post-commit verification would weaken its behaviour.
- Read-only proposal/inventory/in-use methods can use a single consistent query
  snapshot plus Python processing; no write transaction is intrinsically needed.
  Removing existing gate behaviour still requires checking its role in coordination.

## Empirical single-request tests

The extended `probe_jena.py` ran on private Fuseki 6.2.0 / TDB2 at loopback:3032.
All 27 runner checks passed, including the previous Java/RDF tests and six new
batch checks. [Results](transaction-batch-results.json); raw logs/data:
`~/Library/Application Support/OLDAP-Jena/probes/j1-batch-20261027-02/`.
The owned server was stopped afterwards.

1. A conditional update with a stale revision followed by unconditional receipt
   insertion succeeds at HTTP level and commits the **false success receipt**.
   This deliberately reproduces the unsafe batching pattern on synthetic data.
2. A single DELETE/INSERT with one shared WHERE binds the data change, revision
   change and receipt together. Stale revision produces neither change nor receipt.
3. A valid revision changes all three atomically. Exact repetition leaves one
   receipt. Two concurrent requests for the same revision produce one winner and
   one receipt, advancing the revision once.

These tests establish a restricted compare-and-swap pattern, not an automatic
compiler for the application. Synthetic receipts do not yet include the request
hash/actor checks needed by production idempotency. Receipt verification queries
are separate HTTP observations; the test does not pretend Update returns a
business-result body. Broader concurrency, timeout and crash tests remain open.

## Existing issues exposed by the audit

These are findings to account for, not silently copied migration behaviour:

- `OldapListNode.move_node_right_of` calls transaction_start twice (1615, 1646),
  before one final commit. Connection overwrites its transaction URL. The apparent
  intent is one move transaction; inspect/fix this separately rather than model it
  as legitimate nesting. No live reproduction was attempted.
- `DataModel.update` calls multiple child methods with independent commits. It is
  not currently one atomic whole-model edit. Decide that boundary explicitly;
  do not accidentally promise whole-model rollback by renaming a transport method.
- `StagingFolderTree.move` imports `coordinated_domain_operation` but has no such
  decorator. Its reads precede the resource mutation boundary. Preserve/reassess
  call-site locking; do not count the import as an actual transaction wrapper.
- GraphDB Lucene connector management has external index side effects. It is not
  an ordinary RDF transaction to concatenate with data changes.

## Proposed implementation direction

Keep Python for domain modelling, serialization and preparation. Prefer a single
atomic server command for each complete operation. Start with fixed guarded
mutations; for necessary assertions and returned results, design a narrowly
scoped Jena endpoint that executes within a local TDB2 transaction. It should
commit before returning success and abort on any failed pre/postcondition.

Do not build a generic workflow language, Python replay engine or bytecode
executor. A small sequence of explicit guards and updates may serve several
real operations; dynamic cases still need domain-specific preparation or commands.
Do not expose unrestricted raw-write commands to end users: the API remains the
trusted authorization boundary, with protected backend access and all direct
writers using the same correctness rules.

For prepared plans, every fact used for authorization/decision must remain valid
at execution time. Validate positive and negative query results, aggregate counts
and collection membership as needed. Where that becomes too complicated, move
that bounded operation's decision to the server instead of weakening checks.
Cache invalidation, in-memory mutation and external notifications occur only after
known commit. A lost response remains ambiguous and is resolved by durable receipts;
post-commit network effects use the existing outbox pattern.

Arbitrary public `before_commit` callbacks cannot retain their old semantics
unchanged in a precomputed request. Known hooks should produce transactional
contributions (guards, writes, receipts) or become explicit command parameters.
External callers need a documented migration path. Nested operations must combine
under one outer command rather than each committing its own request.

## Next bounded implementation and acceptance

1. Port **only authentication revocation** as a tested pilot: successful change,
   stale revision, concurrent requests, exact replay, conflicting reuse of the
   same operation ID and lost-response reconciliation. Decide stock Update plus
   receipt read versus one command response explicitly.
2. Before scaling that design, prove **resource update + audit + lifecycle outbox**
   with rollback when any stage fails and one composed outer transaction.
3. Then cover a **list move** and **harvester create-and-publish**. They expose
   arithmetic/intermediate reads and nested composition respectively.
4. Track every inventory row as pending/ported/verified/not-applicable with a named
   test. During Jena rollout, reject remaining legacy multi-request write paths
   explicitly rather than falling back to separate auto-committed calls.

The present step deliberately stops before a production transaction rewrite.
The evidence supports pursuing one mutation request, but not claiming all
transactions have already been translated or that no server extension is needed.
