"""GraphDB-independent tests for generic ArchiveUnit hierarchy operations."""

import unittest
from types import SimpleNamespace

from oldaplib.src.archive_tree import ArchiveTree
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName


ARCHIVE_UNIT = Xsd_QName("shared:ArchiveUnit", validate=False)


class FakeResource:
    """Minimal dynamic resource whose concrete class metadata is configurable."""

    def __init__(self, iri: str, class_iri: str, superclass: dict | None = None):
        self.iri = Iri(iri)
        self.values = {}
        self.__class__ = type(
            class_iri,
            (FakeResource,),
            {
                "name": Xsd_QName(class_iri, validate=False),
                "superclass": superclass or {},
            },
        )

    def get(self, prop):
        """Return an optional fake property value."""
        return self.values.get(str(prop))


class FakeFactory:
    """Read fake resources by IRI."""

    def __init__(self, *resources: FakeResource):
        self.resources = {resource.iri: resource for resource in resources}

    def read(self, iri: Iri):
        """Return the requested fake resource."""
        return self.resources[iri]


def tree_with(*resources: FakeResource) -> ArchiveTree:
    """Construct an ArchiveTree without loading a project data model."""
    tree = ArchiveTree.__new__(ArchiveTree)
    tree._con = object()
    tree._factory = FakeFactory(*resources)
    return tree


class ArchiveTreeSubclassTest(unittest.TestCase):
    """Ensure Shared archive behavior applies to project subclasses."""

    def test_accepts_direct_project_subclass(self) -> None:
        work = FakeResource(
            "chama:LobatoTrestlePhotograph1981",
            "chama:PhotographicWork",
            {ARCHIVE_UNIT: SimpleNamespace(superclass={})},
        )

        self.assertIs(tree_with(work)._read_archive_unit(work.iri), work)

    def test_accepts_transitive_project_subclass(self) -> None:
        specialized = FakeResource(
            "chama:SpecializedPhotograph",
            "chama:SpecializedPhotographicWork",
            {
                Xsd_QName("chama:PhotographicWork", validate=False): SimpleNamespace(
                    superclass={ARCHIVE_UNIT: SimpleNamespace(superclass={})}
                )
            },
        )

        self.assertIs(tree_with(specialized)._read_archive_unit(specialized.iri), specialized)

    def test_rejects_unrelated_resource_class(self) -> None:
        media = FakeResource("chama:PICT0111", "shared:MediaObject")

        with self.assertRaisesRegex(OldapErrorValue, "not a shared:ArchiveUnit"):
            tree_with(media)._read_archive_unit(media.iri)


if __name__ == "__main__":
    unittest.main()
