# Composing resource transactions

`resource_transaction(connection)` provides explicit ownership for multi-resource
commands. `ResourceInstance.create`, `update`, `transform_class` and `delete` open
this boundary when called alone and join it when a domain command already owns
it. Existing calls remain valid; update/transform/delete also accept the additive
keyword-only `before_commit` hook from version 0.7.17. Resource reads and searches use the
active transaction, so they can see earlier writes in the same command.

```python
from oldaplib.src.resource_transaction import resource_transaction

with resource_transaction(connection):
    source = factory.read(source_iri)
    target = factory.read(target_iri)
    # Validate domain rules and change both resources here.
    source.update()
    target.update()
```

Only the outer owner commits or rolls back. Any exception, including a non-OLDAP
exception, causes rollback. Catching an inner operation's error does not make the
transaction usable again: the outer owner must still roll back. An unmanaged
transaction opened with `connection.transaction_start()` cannot be joined; replace
that manual resource-operation boundary with `resource_transaction` explicitly.
Do not manually commit or abort inside the managed scope, and do not share the
connection or its mutable resources between threads or asynchronous tasks.

After rollback, discard resource instances used by the failed operation and read
them again. Their in-memory properties/changesets may already reflect attempted
writes. An ambiguous commit response is never retried automatically. Domain
commands must use durable, transactional receipts to resolve such retries.

The outer owner may supply a `before_commit` callback that raises when its final
precondition fails. This is a final check, **not a fencing mechanism**: a lease
may still expire between the callback and the database commit.

## Resource hooks and transaction ownership

`update(before_commit=hook)`, `transform_class(..., before_commit=hook)` and
`delete(before_commit=hook)` invoke `hook(connection)` after the operation's
resource writes, archive reference retention and audit have succeeded. A trusted
caller can append related GraphDB outbox/receipt facts using the active connection.
The hook is synchronous and must use transaction-local writes only: no network
notifications, manual commit/abort or other irreversible external effects.

Standalone calls commit only after the hook succeeds. In an explicitly composed
transaction the hook runs before that resource call returns; the outer owner
still controls the eventual commit. A hook failure rolls back the full transaction,
including archive references and audit. Catching the failure inside the outer
scope does not make that scope committable. Re-read mutable instances after rollback.

This operation-level extension is distinct from the optional **zero-argument**
`resource_transaction(connection, before_commit=final_check)` owner precondition,
which runs at the end of the complete composed command. Both can be used together;
resource hooks do not replace or bypass the owner's final check or writer gate.

## Isolation remains a separate requirement

This boundary guarantees atomic composition, not serializable execution.
GraphDB's normal read-committed isolation permits two transactions to pass the
same check before either commits. On the tested local server, two simultaneous
conditional claims both committed. Archive moves, emptiness checks, reference
moves and lifecycle guards must therefore share an additional proven writer
coordination mechanism, including direct library writers. Merely renewing a
Redis lease or checking it before commit does not establish that guarantee.

AS-02 now supplies a persistent writer gate for deployments selecting an archive
policy file. It coordinates resource writers across projects, has no automatic
expiry and requires controlled recovery after a crash or uncertain transaction.
See [archive domain policy](archive_domain.md) for guards and reference commands,
and [writer recovery](writer_recovery.md) for the mandatory Redis durability,
cache isolation, worker rollout and recovery conditions. No deployment is enabled
merely by installing these source files.
