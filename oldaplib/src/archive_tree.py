"""Minimal safe operations for the shared OLDAP archive tree.

Archive units remain ordinary :class:`ResourceInstance` objects.  This module
only centralizes the one phase-2 operation whose integrity must not depend on a
frontend: changing a node's parent without creating a hierarchy cycle.
"""

from typing import Final

from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapErrorValue
from oldaplib.src.iconnection import IConnection
from oldaplib.src.objectfactory import ResourceInstance, ResourceInstanceFactory
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class _PositionUnset:
    """Sentinel distinguishing an omitted position from an explicit removal."""


POSITION_UNSET: Final = _PositionUnset()


class ArchiveTree:
    """Apply integrity-sensitive operations to ``shared:ArchiveUnit`` resources.

    The service deliberately does not replace generic resource CRUD or search.
    It reads archive nodes through :class:`ResourceInstanceFactory`, so normal
    OLDAP visibility and update permissions continue to apply.

    Args:
        con: Authenticated OLDAP connection used for reads and updates.
        project: Project containing the archive-unit instances.
    """

    ARCHIVE_UNIT_CLASS = Xsd_QName("shared:ArchiveUnit", validate=False)
    PARENT_PROPERTY = Xsd_QName("shared:parentArchiveUnit", validate=False)
    POSITION_PROPERTY = Xsd_QName("schema:position", validate=False)

    def __init__(self, con: IConnection, project: Project | Xsd_NCName | str):
        self._con = con
        self._factory = ResourceInstanceFactory(con=con, project=project)

    @staticmethod
    def _as_iri(value: Iri | str) -> Iri:
        """Return a validated IRI for a public method argument."""
        return value if isinstance(value, Iri) else Iri(value, validate=True)

    def _read_archive_unit(self, iri: Iri) -> ResourceInstance:
        """Read one resource and reject values outside the archive-unit class."""
        instance = self._factory.read(iri)
        if instance.__class__.name != self.ARCHIVE_UNIT_CLASS:
            raise OldapErrorValue(f'Resource "{iri}" is not a shared:ArchiveUnit.')
        return instance

    @classmethod
    def _parent_iri(cls, instance: ResourceInstance) -> Iri | None:
        """Extract the optional single parent IRI from an archive instance."""
        parents = instance.get(cls.PARENT_PROPERTY)
        if not parents:
            return None
        if len(parents) != 1:
            raise OldapErrorInconsistency(
                f'Archive unit "{instance.iri}" has more than one parent.'
            )
        parent = next(iter(parents))
        return parent if isinstance(parent, Iri) else Iri(parent, validate=True)

    def path_to_root(self, archive_unit: Iri | str) -> list[ResourceInstance]:
        """Return the visible path from a root node to ``archive_unit``.

        Existing corrupt cycles are detected explicitly instead of causing an
        endless traversal.

        Args:
            archive_unit: IRI of the node whose ancestor path is required.

        Returns:
            Archive-unit instances ordered from the root to the requested node.

        Raises:
            OldapErrorInconsistency: If the stored hierarchy already contains a
                cycle or an invalid multiple-parent value.
            OldapErrorNotFound: If the node or one of its visible ancestors
                cannot be read.
            OldapErrorValue: If a traversed resource is not an archive unit.
        """
        current_iri = self._as_iri(archive_unit)
        path: list[ResourceInstance] = []
        visited: set[Iri] = set()

        while True:
            if current_iri in visited:
                raise OldapErrorInconsistency(
                    f'Archive hierarchy contains a cycle at "{current_iri}".'
                )
            visited.add(current_iri)
            current = self._read_archive_unit(current_iri)
            path.append(current)
            parent_iri = self._parent_iri(current)
            if parent_iri is None:
                return list(reversed(path))
            current_iri = parent_iri

    def move(
        self,
        archive_unit: Iri | str,
        parent_archive_unit: Iri | str | None,
        *,
        position: int | Xsd_integer | None | _PositionUnset = POSITION_UNSET,
    ) -> ResourceInstance:
        """Move an archive unit below another unit or make it a root.

        Parent and optional position changes are written together by the normal
        ``ResourceInstance.update()`` transaction.  Before the update, the new
        parent's complete ancestor path is checked to ensure that the moved node
        is not an ancestor of its new parent.

        Args:
            archive_unit: IRI of the node to move.
            parent_archive_unit: IRI of the new parent, or ``None`` to make the
                node a root.
            position: Optional sibling position. Omitting the argument preserves
                the current value; ``None`` removes it.

        Returns:
            The updated archive-unit instance.

        Raises:
            OldapErrorInconsistency: If the move would create a cycle or the
                stored hierarchy is already inconsistent.
            OldapErrorNoPermission: If normal OLDAP permissions reject the read
                or update.
            OldapErrorNotFound: If the node or new parent cannot be read.
            OldapErrorValue: If either resource is not an archive unit.
        """
        node_iri = self._as_iri(archive_unit)
        node = self._read_archive_unit(node_iri)
        new_parent_iri = (
            self._as_iri(parent_archive_unit)
            if parent_archive_unit is not None
            else None
        )

        if new_parent_iri == node_iri:
            raise OldapErrorInconsistency("An archive unit cannot be its own parent.")
        if new_parent_iri is not None:
            parent_path = self.path_to_root(new_parent_iri)
            if any(parent.iri == node_iri for parent in parent_path):
                raise OldapErrorInconsistency(
                    "An archive unit cannot be moved below one of its descendants."
                )

        changed = False
        current_parent_iri = self._parent_iri(node)
        if current_parent_iri != new_parent_iri:
            if new_parent_iri is None:
                del node[self.PARENT_PROPERTY]
            else:
                node[self.PARENT_PROPERTY] = new_parent_iri
            changed = True

        if not isinstance(position, _PositionUnset):
            current_positions = node.get(self.POSITION_PROPERTY)
            current_position = next(iter(current_positions)) if current_positions else None
            new_position = None if position is None else Xsd_integer(position, validate=True)
            if current_position != new_position:
                if new_position is None:
                    del node[self.POSITION_PROPERTY]
                else:
                    node[self.POSITION_PROPERTY] = new_position
                changed = True

        if changed:
            node.update()
        return node
