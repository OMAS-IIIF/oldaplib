"""Offline regressions for transport reuse and isolated project read snapshots."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
import unittest
from unittest.mock import Mock, patch

from oldaplib.src import cachesingleton
from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.mutation_gate import require_separate_cache, MutationGateUnavailable
from oldaplib.src.project import Project, reuse_project_reads, _project_reads
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.iconnection import IConnection
from oldaplib.src.xsd.iri import Iri


class PoolTests(unittest.TestCase):
    def setUp(self):
        cachesingleton._reset_redis_clients_after_fork()
        self.addCleanup(cachesingleton._reset_redis_clients_after_fork)

    def test_threads_share_pool_and_urls_remain_separate(self):
        with patch.object(
            cachesingleton.redis, "from_url", side_effect=lambda *a, **k: Mock()
        ) as create:
            with ThreadPoolExecutor(max_workers=8) as executor:
                clients = list(
                    executor.map(
                        lambda _: cachesingleton._shared_redis_client(
                            "redis://cache/0"
                        ),
                        range(40),
                    )
                )
            self.assertTrue(all(client is clients[0] for client in clients))
            self.assertIsNot(
                cachesingleton._shared_redis_client("redis://cache/1"), clients[0]
            )
            self.assertEqual(create.call_count, 2)
            self.assertEqual(create.call_args.kwargs["max_connections"], 32)

    def test_eviction_does_not_close_borrowed_clients(self):
        with patch.object(
            cachesingleton.redis, "from_url", side_effect=lambda *a, **k: Mock()
        ):
            borrowed = cachesingleton._shared_redis_client("redis://cache/0")
            for index in range(1, 10):
                cachesingleton._shared_redis_client(f"redis://cache/{index}")
            self.assertEqual(len(cachesingleton._redis_clients), 8)
            borrowed.close.assert_not_called()
            self.assertIsNot(
                cachesingleton._shared_redis_client("redis://cache/0"), borrowed
            )

    def test_fork_reset_replaces_inherited_lock_and_clients(self):
        old_lock = cachesingleton._redis_clients_lock
        with patch.object(
            cachesingleton.redis, "from_url", side_effect=lambda *a, **k: Mock()
        ):
            old = cachesingleton._shared_redis_client("redis://cache/0")
            with old_lock:
                cachesingleton._reset_redis_clients_after_fork()
                new = cachesingleton._shared_redis_client("redis://cache/0")
            self.assertIsNot(old, new)
            self.assertIsNot(old_lock, cachesingleton._redis_clients_lock)

    def test_isolation_is_rechecked_on_wrapping_and_flush(self):
        with patch.object(
            cachesingleton, "_shared_redis_client"
        ) as client, patch.object(cachesingleton, "require_separate_cache") as check:
            cache = CacheSingletonRedis()
            CacheSingletonRedis()
            check.side_effect = MutationGateUnavailable("refuse")
            with self.assertRaises(MutationGateUnavailable):
                cache.clear()
            self.assertEqual(check.call_count, 3)
            client.return_value.flushdb.assert_not_called()

    def test_distinct_db_uses_redis_url_precedence_without_gate_client(self):
        cache = Mock()
        cache.connection_pool.connection_kwargs = {"db": 0}
        with patch.dict(
            os.environ,
            {
                "OLDAP_ARCHIVE_POLICY_FILE": "policy",
                "OLDAP_STAGING_LOCK_REDIS_URL": "redis://localhost:6379/0?db=1",
            },
        ), patch("oldaplib.src.mutation_gate.Redis.from_url") as create:
            require_separate_cache(cache)
            create.assert_not_called()
            cache.info.assert_not_called()

    def test_matching_db_still_checks_actual_server_identity(self):
        cache = Mock()
        cache.connection_pool.connection_kwargs = {"db": 0}
        cache.info.return_value = {"run_id": "same-server"}
        with patch.dict(
            os.environ,
            {
                "OLDAP_ARCHIVE_POLICY_FILE": "policy",
                "OLDAP_STAGING_LOCK_REDIS_URL": "redis://alias/0",
            },
        ), patch("oldaplib.src.mutation_gate.Redis.from_url") as create:
            create.return_value.info.return_value = {"run_id": "same-server"}
            with self.assertRaises(MutationGateUnavailable):
                require_separate_cache(cache)
            create.return_value.close.assert_called_once()


class ProjectSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock(
            spec=IConnection,
            context_name="CACHE_READ_TEST",
            userIri=Iri("urn:uuid:11111111-1111-1111-1111-111111111111"),
        )
        self.project = Project(
            con=self.connection,
            projectIri="http://example.org/project",
            projectShortName="example",
            namespaceIri="http://example.org/ns/",
            label=LangString("Original@en"),
        )
        self.cache_patch = patch("oldaplib.src.project.CacheSingletonRedis")
        self.cache = self.cache_patch.start().return_value
        self.addCleanup(self.cache_patch.stop)
        self.cache.get.side_effect = lambda key, connection: deepcopy(
            self.project, {id(self.connection): connection}
        )

    def test_alias_reuse_preserves_independent_mutability_and_connection(self):
        @reuse_project_reads
        def operation(_, con):
            first = Project.read(con, "example")
            first.label["en"] = "Modified"
            second = Project.read(con, "http://example.org/project")
            third = Project.read(con, "example")
            self.assertEqual(str(second.label["en"]), "Original")
            second.label["en"] = "Second"
            self.assertEqual(str(third.label["en"]), "Original")
            self.assertTrue(second._changeset)
            self.assertFalse(third._changeset)
            self.assertIs(third._con, con)
            self.assertEqual(self.cache.get.call_count, 1)

        operation(None, self.connection)
        self.assertIsNone(_project_reads.get())
        Project.read(self.connection, "example")
        self.assertEqual(self.cache.get.call_count, 2)

    def test_nested_different_connection_cannot_share_snapshot(self):
        other = Mock(
            spec=IConnection, context_name="OTHER", userIri=self.connection.userIri
        )

        @reuse_project_reads
        def operation(_, con):
            value = Project.read(con, "example")
            if con is self.connection:
                nested = operation(None, other)
                self.assertIs(nested._con, other)
                self.assertIs(Project.read(con, "example")._con, con)
            return value

        operation(None, self.connection)
        self.assertEqual(self.cache.get.call_count, 2)

    def test_exception_discards_snapshot(self):
        @reuse_project_reads
        def operation(_, con):
            Project.read(con, "example")
            raise ValueError("failed read")

        with self.assertRaises(ValueError):
            operation(None, self.connection)
        self.assertIsNone(_project_reads.get())
        Project.read(self.connection, "example")
        self.assertEqual(self.cache.get.call_count, 2)

    def test_identity_aliases_copy_only_independent_values(self):
        @reuse_project_reads
        def operation(_, con):
            first = Project._read_identity(con, IriOrNCName("example"))
            with patch.object(Project, "__deepcopy__", side_effect=AssertionError(
                    "Identity hits must not copy complete projects")):
                second = Project._read_identity(
                    con, IriOrNCName("http://example.org/project"))
            self.assertEqual(first, second)
            for left, right in zip(first, second):
                self.assertIsNot(left, right)
            first[0].__init__("changed")
            first[2].__init__("http://changed.example/")
            self.assertEqual(str(second[0]), "example")
            self.assertEqual(str(second[2]), "http://example.org/ns/")
            full = Project.read(con, "example")
            self.assertEqual(str(full.projectShortName), "example")
            full.label["en"] = "Independent"
            self.assertTrue(full._changeset)
            self.assertFalse(self.project._changeset)
            self.assertEqual(self.cache.get.call_count, 1)

        operation(None, self.connection)
        self.assertIsNone(_project_reads.get())

    def test_identity_outside_scope_and_other_connection_read_normally(self):
        for _ in range(2):
            Project._read_identity(self.connection, IriOrNCName("example"))
        self.assertEqual(self.cache.get.call_count, 2)
        other = Mock(spec=IConnection, context_name="IDENTITY_OTHER",
                     userIri=self.connection.userIri)

        @reuse_project_reads
        def operation(_, con):
            Project._read_identity(con, IriOrNCName("example"))
            with patch.object(Project, "read", side_effect=RuntimeError("other read")):
                with self.assertRaisesRegex(RuntimeError, "other read"):
                    Project._read_identity(other, IriOrNCName("example"))

        operation(None, self.connection)

    def test_identity_scopes_are_isolated_across_threads_and_failures(self):
        @reuse_project_reads
        def operation(_, con, index):
            identity = Project._read_identity(con, IriOrNCName("example"))
            identity[0].__init__(f"thread{index}")
            again = Project._read_identity(con, IriOrNCName("example"))
            self.assertEqual(str(again[0]), "example")
            return again

        with ThreadPoolExecutor(max_workers=4) as executor:
            identities = list(executor.map(
                lambda index: operation(None, self.connection, index), range(16)))
        self.assertEqual(len({id(values[0]) for values in identities}), 16)
        self.assertIsNone(_project_reads.get())
        self.cache.get.side_effect = RuntimeError("project unavailable")
        with self.assertRaisesRegex(RuntimeError, "project unavailable"):
            operation(None, self.connection, 0)
        self.assertIsNone(_project_reads.get())

    def test_identity_uses_refreshed_snapshot(self):
        @reuse_project_reads
        def operation(_, con):
            Project._read_identity(con, IriOrNCName("example"))
            refreshed = deepcopy(self.project, {id(con): con})
            refreshed.namespaceIri.__init__("http://updated.example/")
            # Successful cache-bypassing Project.read uses this same boundary.
            refreshed._remember_read()
            identity = Project._read_identity(con, IriOrNCName("example"))
            self.assertEqual(str(identity[2]), "http://updated.example/")

        operation(None, self.connection)

    def test_property_constructor_retains_independent_identity(self):
        @reuse_project_reads
        def operation(_, con):
            first = PropertyClass(con=con, project="example")
            second = PropertyClass(con=con, project="example")
            self.assertIs(first._con, con)
            self.assertIs(second._con, con)
            self.assertEqual(first._projectIri, self.project.projectIri)
            self.assertIsNot(first._projectIri, second._projectIri)
            first._projectShortName.__init__("changed")
            self.assertEqual(str(second._projectShortName), "example")
            self.assertFalse(second._changeset)

        operation(None, self.connection)

    def test_ignore_cache_reaches_connection_even_with_snapshot(self):
        self.connection.query = Mock(side_effect=RuntimeError("fresh GraphDB request"))

        @reuse_project_reads
        def operation(_, con):
            Project.read(con, "example")
            Project.read(con, "example", ignore_cache=True)

        with self.assertRaisesRegex(RuntimeError, "fresh GraphDB"):
            operation(None, self.connection)
        self.connection.query.assert_called_once()
        self.assertIsNone(_project_reads.get())


if __name__ == "__main__":
    unittest.main()
