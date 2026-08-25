"""Unit tests for efficient hierarchical-list QName context preparation."""

from unittest import TestCase
from unittest.mock import Mock, patch

from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.helpers.context import Context
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


class TestListNodeContext(TestCase):
    """Verify request-scoped list-prefix discovery without GraphDB."""

    def setUp(self) -> None:
        self.context_name = f'LIST_CONTEXT_{self.id()}'
        self.connection = Mock(spec=IConnection)
        self.connection.context_name = self.context_name
        self.connection._list_node_context_projects = set()
        self.connection.query.return_value = {
            'head': {'vars': ['list']},
            'results': {
                'bindings': [{
                    'list': {
                        'type': 'uri',
                        'value': 'http://example.org/project#Subjects',
                    },
                }],
            },
        }
        self.project = Mock()
        self.project.projectShortName = Xsd_NCName('example')
        self.project.namespaceIri = NamespaceIRI('http://example.org/project#')

    def test_repeated_discovery_queries_once_per_connection_and_project(self) -> None:
        """A second ensure call must reuse the prepared connection context."""
        with patch('oldaplib.src.oldaplist.Project.read', return_value=self.project) as read_project:
            OldapList.ensure_list_node_context(self.connection, 'example')
            OldapList.ensure_list_node_context(self.connection, 'example')

        self.connection.query.assert_called_once()
        read_project.assert_called_once()
        context = Context(name=self.context_name)
        self.assertEqual(
            context['L-Subjects'],
            NamespaceIRI('http://example.org/project/Subjects#'),
        )
        self.assertEqual(context.graphs.count(Xsd_NCName('L-Subjects')), 1)

    def test_failed_discovery_remains_retryable(self) -> None:
        """A query failure must not mark an incomplete context as loaded."""
        self.connection.query.side_effect = [
            RuntimeError('temporary failure'),
            self.connection.query.return_value,
        ]

        with patch('oldaplib.src.oldaplist.Project.read', return_value=self.project):
            with self.assertRaisesRegex(RuntimeError, 'temporary failure'):
                OldapList.ensure_list_node_context(self.connection, 'example')
            OldapList.ensure_list_node_context(self.connection, 'example')

        self.assertEqual(self.connection.query.call_count, 2)
        self.assertEqual(self.connection._list_node_context_projects, {'example'})

    def test_new_connection_refreshes_project_lists(self) -> None:
        """Discovery state must not hide list changes from later requests."""
        next_connection = Mock(spec=IConnection)
        next_connection.context_name = self.context_name
        next_connection._list_node_context_projects = set()
        next_connection.query.return_value = self.connection.query.return_value

        with patch('oldaplib.src.oldaplist.Project.read', return_value=self.project):
            OldapList.ensure_list_node_context(self.connection, 'example')
            OldapList.ensure_list_node_context(next_connection, 'example')

        self.connection.query.assert_called_once()
        next_connection.query.assert_called_once()
