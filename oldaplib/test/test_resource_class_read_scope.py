"""Model-load reuse must not share mutable classes or outlive the operation."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass, reuse_resource_class_reads, _resource_class_reads
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@pytest.fixture
def model():
    con = Mock(spec=IConnection, userIri=Iri('oldap:Tester'), context_name='MODEL_SCOPE_TEST')
    con.in_transaction.return_value = False
    project = Project(con=con, projectIri=Iri('oldap:SystemProject'),
                      projectShortName='oldap', namespaceIri='http://oldap.org/base#')
    with patch.object(Project, 'read', return_value=project):
        resource = ResourceClass(con=con, project=project, owlclass_iri=Xsd_QName('oldap:Thing'),
                                 label=['Thing@en'])
    return con, project, resource


def test_independent_copies_notifiers_and_fresh_next_operation(model):
    con, project, template = model
    cache = Mock()
    cache.get.side_effect = lambda *a, **kw: deepcopy(template, {id(con): con})

    @reuse_resource_class_reads
    def load(_self, con):
        first = ResourceClass.read(con, project, 'oldap:Thing')
        first.label['en'] = 'Changed'
        second = ResourceClass.read(con, project, 'oldap:Thing')
        assert second.label['en'] != first.label['en']
        assert second._con is con
        second.label['en'] = 'Second'
        assert first.label['en'] != second.label['en']
        assert first.changeset and second.changeset
        return second

    with patch('oldaplib.src.resourceclass.CacheSingletonRedis', return_value=cache):
        load(None, con)
        assert cache.get.call_count == 1
        load(None, con)
        assert cache.get.call_count == 2
    assert _resource_class_reads.get() is None


def test_scope_cleanup_nested_connections_and_bypass():
    con = SimpleNamespace(in_transaction=lambda: False)
    other = SimpleNamespace(in_transaction=lambda: False)

    @reuse_resource_class_reads
    def inspect(_self, connection, project=None, ignore_cache=False):
        return _resource_class_reads.get()

    @reuse_resource_class_reads
    def outer(_self, connection):
        active = _resource_class_reads.get()
        assert inspect(None, con) is active
        assert inspect(None, other)[0] is other
        assert _resource_class_reads.get() is active
        assert inspect(None, con, None, True) is None
        assert inspect(None, con, ignore_cache=True) is None
        assert _resource_class_reads.get() is active
        raise RuntimeError('failed model load')

    with pytest.raises(RuntimeError):
        outer(None, con)
    assert _resource_class_reads.get() is None
    assert inspect(None, SimpleNamespace(in_transaction=lambda: True)) is None


def test_overlapping_threads_keep_separate_snapshots():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    con = SimpleNamespace(in_transaction=lambda: False)
    barrier = Barrier(2)

    @reuse_resource_class_reads
    def load(_self, connection, marker):
        snapshots = _resource_class_reads.get()[1]
        snapshots['marker'] = marker
        barrier.wait(timeout=5)
        return snapshots['marker']

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(load, None, con, marker) for marker in ('first', 'second')]
        assert [future.result() for future in futures] == ['first', 'second']
    assert _resource_class_reads.get() is None
