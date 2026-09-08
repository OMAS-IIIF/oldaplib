"""Offline ownership and failure tests for composed resource transactions."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.helpers.oldaperror import (
    OldapErrorAlreadyExists,
    OldapErrorNoPermission,
    OldapErrorValue,
    OldapErrorInUse,
)
from oldaplib.src.objectfactory import ResourceInstance
from oldaplib.src.resource_transaction import (
    ResourceTransactionError,
    resource_operation,
    resource_query,
    resource_transaction,
)
from oldaplib.src.xsd.iri import Iri


class MemoryConnection:
    """Stage writes separately so tests observe atomic commit and rollback."""

    context_name = "AS02-transactions"
    userIri = Iri("urn:as02:actor")

    def __init__(self):
        self.active = False
        self.events = []
        self.durable = []
        self.pending = []
        self.commit_error = None
        self.abort_error = None
        self.exists = False

    def in_transaction(self):
        return self.active

    def transaction_start(self):
        assert not self.active
        self.active = True
        self.events.append("start")

    def transaction_update(self, query):
        assert self.active
        self.pending.append(query)

    def transaction_query(self, query, result_format=SparqlResultFormat.JSON):
        assert self.active
        self.events.append(("transaction-query", result_format))
        return {"boolean": self.exists}

    def query(self, query, format=SparqlResultFormat.JSON):
        self.events.append(("query", format))
        return {"boolean": self.exists}

    def transaction_commit(self):
        self.events.append("commit")
        if self.commit_error:
            raise self.commit_error
        self.durable.extend(self.pending)
        self.pending = []
        self.active = False

    def transaction_abort(self):
        self.events.append("abort")
        if self.abort_error:
            raise self.abort_error
        self.pending = []
        self.active = False


class ResourceTransactionTest(unittest.TestCase):
    def setUp(self):
        self.con = MemoryConnection()

    def test_nested_operations_commit_once(self):
        with resource_transaction(self.con):
            self.con.transaction_update("first")
            with resource_transaction(self.con):
                self.con.transaction_update("second")
            self.assertEqual(self.con.durable, [])
        self.assertEqual(self.con.durable, ["first", "second"])
        self.assertEqual(self.con.events, ["start", "commit"])

    def test_late_non_oldap_exception_rolls_back_all_writes(self):
        with self.assertRaisesRegex(ValueError, "late"):
            with resource_transaction(self.con):
                self.con.transaction_update("first")
                with resource_transaction(self.con):
                    self.con.transaction_update("second")
                    raise ValueError("late")
        self.assertEqual(self.con.durable, [])
        self.assertEqual(self.con.events, ["start", "abort"])

    def test_caught_inner_failure_still_prevents_commit(self):
        with self.assertRaises(ResourceTransactionError):
            with resource_transaction(self.con):
                try:
                    with resource_transaction(self.con):
                        raise ValueError("rejected")
                except ValueError:
                    pass
                self.con.transaction_update("must not commit")
        self.assertEqual(self.con.durable, [])
        self.assertEqual(self.con.events, ["start", "abort"])

    def test_failed_commit_is_not_retried(self):
        self.con.commit_error = TimeoutError("ambiguous commit")
        with self.assertRaises(TimeoutError):
            with resource_transaction(self.con):
                self.con.transaction_update("pending")
        self.assertEqual(self.con.events, ["start", "commit", "abort"])

    def test_rollback_failure_preserves_original_exception(self):
        self.con.abort_error = RuntimeError("rollback unavailable")
        original = ValueError("original")
        with self.assertRaises(ValueError) as caught:
            with resource_transaction(self.con):
                raise original
        self.assertIs(caught.exception, original)
        self.assertIn("Rollback also failed", original.__notes__[0])

    def test_failed_final_precondition_rolls_back(self):
        callback = Mock(side_effect=RuntimeError("coordination lost"))
        with self.assertRaisesRegex(RuntimeError, "coordination lost"):
            with resource_transaction(self.con, before_commit=callback):
                self.con.transaction_update("pending")
        callback.assert_called_once_with()
        self.assertEqual(self.con.events, ["start", "abort"])
        self.assertEqual(self.con.durable, [])

    def test_callback_runs_only_before_outer_commit(self):
        def check():
            self.assertTrue(self.con.active)
            self.assertEqual(self.con.pending, ["pending"])
            self.assertEqual(self.con.durable, [])

        with resource_transaction(self.con, before_commit=check):
            with resource_transaction(self.con):
                self.con.transaction_update("pending")
        self.assertEqual(self.con.durable, ["pending"])

    def test_nested_callback_rejected_and_poisons_outer_scope(self):
        with self.assertRaises(ResourceTransactionError):
            with resource_transaction(self.con):
                with resource_transaction(self.con, before_commit=lambda: None):
                    pass
        self.assertEqual(self.con.events, ["start", "abort"])

    def test_unmanaged_transaction_never_aborted(self):
        self.con.transaction_start()
        with self.assertRaises(ResourceTransactionError):
            with resource_transaction(self.con):
                pass
        self.assertEqual(self.con.events, ["start"])
        self.assertTrue(self.con.active)

    def test_independent_connections_do_not_share_ownership(self):
        other = MemoryConnection()
        with resource_transaction(self.con):
            with resource_transaction(other):
                other.transaction_update("other")
            self.assertEqual(other.durable, ["other"])
            self.assertTrue(self.con.active)

    def test_scope_is_reset_after_failure(self):
        with self.assertRaises(ValueError):
            with resource_transaction(self.con):
                raise ValueError("failed")
        with resource_transaction(self.con):
            self.con.transaction_update("next")
        self.assertEqual(self.con.durable, ["next"])

    def test_query_uses_transaction_and_preserves_format(self):
        resource_query(self.con, "read")
        with resource_transaction(self.con):
            resource_query(self.con, "read", format=SparqlResultFormat.JSONLD)
        self.assertIn(("query", SparqlResultFormat.JSON), self.con.events)
        self.assertIn(("transaction-query", SparqlResultFormat.JSONLD), self.con.events)

    def test_actual_create_joins_outer_transaction(self):
        instance = SimpleNamespace(
            _con=self.con,
            _iri=Iri("urn:as02:resource"),
            name="shared:ArchiveUnit",
            _graph="shared",
            _values={},
            _attached_roles={},
            properties={},
            check_for_permissions=lambda permission: (True, ""),
        )
        with resource_transaction(self.con):
            ResourceInstance.create(instance)
            self.assertEqual(self.con.durable, [])
        self.assertEqual(len(self.con.durable), 1)
        self.assertEqual(self.con.events.count("start"), 1)
        self.assertEqual(self.con.events.count("commit"), 1)

    def test_actual_create_duplicate_aborts_once(self):
        self.con.exists = True
        instance = SimpleNamespace(
            _con=self.con,
            _iri=Iri("urn:as02:resource"),
            name="shared:ArchiveUnit",
            _graph="shared",
            _values={},
            _attached_roles={},
            properties={},
            check_for_permissions=lambda permission: (True, ""),
        )
        with self.assertRaises(OldapErrorAlreadyExists):
            ResourceInstance.create(instance)
        self.assertEqual(self.con.events.count("abort"), 1)
        self.assertEqual(self.con.durable, [])

    def test_actual_delete_denial_writes_nothing(self):
        instance = SimpleNamespace(
            _con=self.con,
            _iri=Iri("urn:as02:resource"),
            _graph="shared",
            check_for_permissions=lambda permission: (False, ""),
            get_data_permission=lambda permission: False,
        )
        with self.assertRaises(OldapErrorNoPermission):
            ResourceInstance.delete(instance)
        self.assertEqual(self.con.durable, [])
        self.assertEqual(self.con.events, ["start", "abort"])

    def test_decorator_includes_preparation_in_transaction(self):
        @resource_operation
        def write(instance):
            self.assertTrue(instance._con.in_transaction())
            raise ValueError("preparation failed")

        with self.assertRaises(ValueError):
            write(SimpleNamespace(_con=self.con))
        self.assertEqual(self.con.events, ["start", "abort"])

    def test_actual_delete_reference_rejection_poisoning(self):
        instance = SimpleNamespace(
            _con=self.con,
            _iri=Iri("urn:as02:resource"),
            _graph="shared",
            check_for_permissions=lambda permission: (True, ""),
        )
        self.con.exists = True
        with self.assertRaises(ResourceTransactionError):
            with resource_transaction(self.con):
                self.con.transaction_update("earlier change")
                try:
                    ResourceInstance.delete(instance)
                except OldapErrorInUse:
                    pass
        self.assertEqual(self.con.durable, [])
        self.assertEqual(self.con.events.count("abort"), 1)

    def test_resource_hook_composes_with_outer_owner_precondition(self):
        instance = SimpleNamespace(
            _con=self.con,
            _iri=Iri("urn:as02:hook"),
            _graph="shared",
            check_for_permissions=lambda permission: (True, ""),
        )

        def append(connection):
            self.assertIs(connection, self.con)
            self.assertTrue(connection.in_transaction())
            connection.transaction_update("hook write")

        with resource_transaction(
            self.con, before_commit=lambda: self.con.transaction_update("final check")
        ):
            ResourceInstance.delete(instance, before_commit=append)
            self.assertEqual(self.con.pending[-1], "hook write")
            self.assertEqual(self.con.durable, [])
            self.con.transaction_update("outer write")
        self.assertEqual(
            self.con.durable[-3:], ["hook write", "outer write", "final check"]
        )
        self.assertEqual(self.con.events.count("commit"), 1)

    def test_caught_resource_hook_failure_poisoning(self):
        instance = SimpleNamespace(
            _con=self.con,
            _iri=Iri("urn:as02:hook"),
            _graph="shared",
            check_for_permissions=lambda permission: (True, ""),
        )

        def reject(connection):
            connection.transaction_update("hook write must roll back")
            raise RuntimeError("hook rejected")

        with self.assertRaises(ResourceTransactionError):
            with resource_transaction(self.con):
                try:
                    ResourceInstance.delete(instance, before_commit=reject)
                except RuntimeError:
                    pass
                self.con.transaction_update("outer write must roll back")
        self.assertEqual(self.con.durable, [])
        self.assertEqual(self.con.events.count("abort"), 1)

    def test_rejected_resource_never_calls_hook(self):
        instance = SimpleNamespace(
            _con=self.con,
            _iri=Iri("urn:as02:hook"),
            _graph="shared",
            check_for_permissions=lambda permission: (True, ""),
        )
        self.con.exists = True
        hook = Mock()
        with self.assertRaises(OldapErrorInUse):
            ResourceInstance.delete(instance, before_commit=hook)
        hook.assert_not_called()
        self.assertEqual(self.con.durable, [])

    def test_resource_hook_runs_after_retention_and_audit_and_rolls_back_both(self):
        # Exercise the real operation boundary with controlled domain effects:
        # the caller's hook must observe the completed private reference/audit.
        @resource_operation
        def transform_class(instance, *, before_commit=None):
            instance._con.transaction_update("transform")
            return instance

        instance = SimpleNamespace(_con=self.con, project="test")
        policy = SimpleNamespace(enabled=True)
        transfer = SimpleNamespace(
            finish=lambda result, policy: self.con.transaction_update(
                "retain reference"
            )
        )

        def reject(connection):
            self.assertEqual(
                connection.pending, ["transform", "retain reference", "audit"]
            )
            connection.transaction_update("caller effect")
            raise ValueError("caller rejected")

        with (
            patch(
                "oldaplib.src.resource_transaction.archive_coordination_enabled",
                return_value=True,
            ),
            patch("oldaplib.src.resource_transaction.mutation_gate"),
            patch(
                "oldaplib.src.resource_transaction.archive_policy_for",
                return_value=policy,
            ),
            patch("oldaplib.src.archive_domain.guard_resource_operation"),
            patch(
                "oldaplib.src.archive_domain.audit_resource_operation",
                side_effect=lambda *args: self.con.transaction_update("audit"),
            ),
            patch(
                "oldaplib.src.archive_transfer.ArchiveTransfer.prepare",
                return_value=transfer,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "caller rejected"):
                transform_class(instance, before_commit=reject)
        self.assertEqual(self.con.durable, [])
        self.assertEqual(self.con.events, ["start", "abort"])

    def test_unknown_setter_property_has_typed_error(self):
        instance = SimpleNamespace(properties={}, name="shared:ArchiveUnit")
        with self.assertRaisesRegex(OldapErrorValue, "Unknown property"):
            ResourceInstance._ResourceInstance__set_value(
                instance, ["invalid"], "schema:unknown"
            )

    def test_callback_cannot_swallow_inner_failure(self):
        def check():
            try:
                with resource_transaction(self.con):
                    raise ValueError("failed final operation")
            except ValueError:
                pass

        with self.assertRaises(ResourceTransactionError):
            with resource_transaction(self.con, before_commit=check):
                self.con.transaction_update("pending")
        self.assertEqual(self.con.durable, [])
        self.assertEqual(self.con.events, ["start", "abort"])


if __name__ == "__main__":
    unittest.main()
