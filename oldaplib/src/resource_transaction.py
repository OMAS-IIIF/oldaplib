"""Explicit transaction ownership for composed resource operations.

This boundary provides atomicity, not serializable isolation. Callers performing
check-then-write domain operations must also coordinate competing writers. A
connection and the objects read through it must not be shared between tasks.
Discard mutable resource instances after a rollback; their in-memory values may
already reflect the attempted operation.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.iconnection import IConnection
from oldaplib.src.mutation_gate import archive_coordination_enabled, mutation_gate


class ResourceTransactionError(OldapError):
    """The transaction cannot safely commit or has an unrecognised owner."""


@dataclass
class _Scope:
    connection: IConnection
    rollback_only: bool = False
    archive_policies: dict = field(default_factory=dict)


_scopes: ContextVar[tuple[_Scope, ...]] = ContextVar(
    "resource_transactions", default=()
)


@contextmanager
def _resource_transaction(
    connection: IConnection, *, before_commit: Callable[[], None] | None = None
) -> Iterator[None]:
    """Own one transaction or join an explicitly owned resource transaction.

    Args:
        connection: Authenticated, task-local connection.
        before_commit: Optional final precondition, executed inside the outer
            boundary immediately before commit. Only its owner may supply it.

    Raises:
        ResourceTransactionError: For an unmanaged active transaction, a nested
            commit callback, or an inner failure caught by the calling code.
        BaseException: Any operation or commit failure, after attempting rollback.

    Nested operations never commit or abort the server transaction themselves.
    An inner failure poisons the outer scope even if a caller catches it. Failed
    commit responses remain ambiguous; this function never retries a mutation.
    """
    active = next((s for s in _scopes.get() if s.connection is connection), None)
    if active is not None:
        try:
            if before_commit is not None:
                raise ResourceTransactionError(
                    "Only the transaction owner may set before_commit."
                )
            if active.rollback_only or not connection.in_transaction():
                raise ResourceTransactionError(
                    "The resource transaction is no longer usable."
                )
            yield
        except BaseException:
            active.rollback_only = True
            raise
        return

    if connection.in_transaction():
        raise ResourceTransactionError("An unmanaged transaction is already active.")
    connection.transaction_start()
    scope = _Scope(connection)
    token = _scopes.set((*_scopes.get(), scope))
    try:
        yield
        if scope.rollback_only:
            raise ResourceTransactionError(
                "An inner resource operation failed; rollback is required."
            )
        if before_commit is not None:
            before_commit()
        if scope.rollback_only or not connection.in_transaction():
            raise ResourceTransactionError(
                "The resource transaction is no longer usable."
            )
        connection.transaction_commit()
    except BaseException as error:
        if connection.in_transaction():
            try:
                connection.transaction_abort()
            except BaseException as rollback_error:
                error.add_note(
                    f"Rollback also failed ({type(rollback_error).__name__})."
                )
        raise
    finally:
        _scopes.reset(token)


@contextmanager
def resource_transaction(
    connection: IConnection, *, before_commit: Callable[[], None] | None = None
) -> Iterator[None]:
    """Compose resource writes, using the persistent gate in archive deployments.

    See this module's ownership and rollback rules. All direct library workers
    must receive the same server-owned archive policy and coordination settings.
    """
    if archive_coordination_enabled():
        with mutation_gate():
            with _resource_transaction(connection, before_commit=before_commit):
                yield
    else:
        with _resource_transaction(connection, before_commit=before_commit):
            yield


def archive_policy_for(connection, project):
    """Resolve policy once per project inside one owned resource transaction."""
    if not archive_coordination_enabled():
        return None
    from oldaplib.src.archive_policy import ArchivePolicy

    scope = next((s for s in _scopes.get() if s.connection is connection), None)
    if scope is None:
        return ArchivePolicy.load(connection, project)
    key = str(getattr(project, "projectShortName", project))
    if key not in scope.archive_policies:
        scope.archive_policies[key] = ArchivePolicy.load(connection, project)
    return scope.archive_policies[key]


def coordinated_domain_operation(method: Callable) -> Callable:
    """Include domain reads and validations in the coordinated write boundary."""

    @wraps(method)
    def coordinated(service, *args, **kwargs):
        if archive_coordination_enabled():
            with resource_transaction(service._con):
                return method(service, *args, **kwargs)
        return method(service, *args, **kwargs)

    return coordinated


def resource_operation(method: Callable) -> Callable:
    """Run a ResourceInstance mutation inside the explicit resource boundary.

    Optional resource ``before_commit(connection)`` hooks run synchronously after
    successful domain retention/audit work, before returning to the caller. They
    join the same transaction: failure rolls everything back (or poisons a joined
    outer scope). Only the owner commits. This operation-level callback differs
    from the owner's final ``resource_transaction(before_commit=...)`` precondition.
    Hooks must keep side effects transaction-local and never commit/abort directly.
    """

    @wraps(method)
    def atomic(instance, *args, **kwargs):
        with resource_transaction(instance._con):
            policy = (
                archive_policy_for(instance._con, instance.project)
                if archive_coordination_enabled()
                else None
            )
            previous = None
            link_before = None
            transfer = None
            if policy is not None and policy.enabled:
                from oldaplib.src.archive_domain import (
                    guard_resource_operation,
                    audit_resource_operation,
                )

                if method.__name__ == "transform_class":
                    from oldaplib.src.archive_transfer import ArchiveTransfer

                    transfer = ArchiveTransfer.prepare(instance, args, kwargs, policy)
                previous = guard_resource_operation(
                    instance, method.__name__, args, kwargs, policy
                )
                if (
                    method.__name__ == "transform_class"
                    and kwargs.get("link_from_iri") is not None
                ):
                    from oldaplib.src.xsd.iri import Iri

                    link_before = instance.factory.read(Iri(kwargs["link_from_iri"]))
            result = method(instance, *args, **kwargs)
            if policy is not None and policy.enabled:
                if transfer is not None:
                    transfer.finish(result, policy)
                audit_resource_operation(instance, previous, method.__name__, policy)
                if link_before is not None:
                    link_after = instance.factory.read(link_before.iri)
                    audit_resource_operation(
                        link_after, link_before, "attach-media", policy
                    )
            # Run caller-owned transactional effects only after the archive
            # reference and audit are complete. The enclosing scope owns rollback.
            before_commit = kwargs.get("before_commit")
            if before_commit is not None:
                before_commit(instance._con)
            return result

    return atomic


def resource_query(
    connection: IConnection,
    query: str,
    format: SparqlResultFormat = SparqlResultFormat.JSON,
) -> Any:
    """Read resource state from the active transaction, including own writes."""
    active = getattr(connection, "in_transaction", None)
    if active is not None and active() is True:
        return connection.transaction_query(query, result_format=format)
    if format == SparqlResultFormat.JSON:
        return connection.query(query)
    return connection.query(query, format=format)
