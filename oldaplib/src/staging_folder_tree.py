"""Integrity-sensitive operations for shared OLDAP Staging folders.

Staging folders and their children remain ordinary resource instances. Moving
one folder therefore only changes its ``shared:inStagingFolder`` relation; all
descendant folders and media keep their existing relations and move with the
subtree logically. This module centralizes the checks that must not depend on a
frontend.
"""

import unicodedata

from oldaplib.src.helpers.oldaperror import (
    OldapErrorAlreadyExists,
    OldapErrorInconsistency,
    OldapErrorValue,
)
from oldaplib.src.iconnection import IConnection
from oldaplib.src.objectfactory import (
    CompOp,
    LogicOp,
    ResourceInstance,
    ResourceInstanceFactory,
    SearchFilter,
)
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class StagingFolderTree:
    """Move ``shared:StagingFolder`` resources without corrupting their tree.

    Args:
        con: Authenticated OLDAP connection used for reads and updates.
        project: Project containing the Staging folder instances.
    """

    FOLDER_CLASS = Xsd_QName("shared:StagingFolder", validate=False)
    AREA_PROPERTY = Xsd_QName("shared:inStagingArea", validate=False)
    PARENT_PROPERTY = Xsd_QName("shared:inStagingFolder", validate=False)
    NAME_PROPERTY = Xsd_QName("schema:name", validate=False)
    RESERVED_NAMES = frozenset({"top", "trash", "mobile"})

    def __init__(self, con: IConnection, project: Project | Xsd_NCName | str):
        self._con = con
        self._project = (
            project
            if isinstance(project, Project)
            else Project.read(con=con, projectIri_SName=project)
        )
        self._factory = ResourceInstanceFactory(con=con, project=self._project)

    @staticmethod
    def _as_iri(value: Iri | str) -> Iri:
        """Return a validated IRI for a public method argument."""
        return value if isinstance(value, Iri) else Iri(value, validate=True)

    @staticmethod
    def _single_iri(
        instance: ResourceInstance,
        prop: Xsd_QName,
        *,
        required: bool,
    ) -> Iri | None:
        """Read an optional or required single-valued IRI property."""
        values = instance.get(prop)
        if not values:
            if required:
                raise OldapErrorInconsistency(
                    f'Staging folder "{instance.iri}" has no {prop} value.'
                )
            return None
        if len(values) != 1:
            raise OldapErrorInconsistency(
                f'Staging folder "{instance.iri}" has more than one {prop} value.'
            )
        value = next(iter(values))
        return value if isinstance(value, Iri) else Iri(value, validate=True)

    @classmethod
    def _name(cls, instance: ResourceInstance) -> str:
        """Read the required single folder name as plain text."""
        values = instance.get(cls.NAME_PROPERTY)
        if not values or len(values) != 1:
            raise OldapErrorInconsistency(
                f'Staging folder "{instance.iri}" must have exactly one schema:name.'
            )
        return str(next(iter(values))).strip()

    @staticmethod
    def _portable_name_key(value: str) -> str:
        """Normalize names like the ZIP-import collision boundary."""
        return unicodedata.normalize("NFC", value).rstrip(" .").casefold()

    @classmethod
    def _is_reserved(cls, name: str) -> bool:
        """Return whether a name identifies an application-managed folder."""
        return cls._portable_name_key(name) in cls.RESERVED_NAMES

    def _read_folder(self, iri: Iri) -> ResourceInstance:
        """Read one resource and reject values outside the folder class."""
        instance = self._factory.read(iri)
        if instance.__class__.name != self.FOLDER_CLASS:
            raise OldapErrorValue(f'Resource "{iri}" is not a shared:StagingFolder.')
        return instance

    def path_to_root(self, folder: Iri | str) -> list[ResourceInstance]:
        """Return the visible root-to-folder path and reject stored cycles."""
        current_iri = self._as_iri(folder)
        path: list[ResourceInstance] = []
        visited: set[Iri] = set()

        while True:
            if current_iri in visited:
                raise OldapErrorInconsistency(
                    f'Staging folder hierarchy contains a cycle at "{current_iri}".'
                )
            visited.add(current_iri)
            current = self._read_folder(current_iri)
            path.append(current)
            parent_iri = self._single_iri(
                current,
                self.PARENT_PROPERTY,
                required=False,
            )
            if parent_iri is None:
                return list(reversed(path))
            current_iri = parent_iri

    def _assert_name_available(self, folder: ResourceInstance, target_parent: Iri) -> None:
        """Reject a portable-name collision among the target's direct children."""
        area_iri = self._single_iri(folder, self.AREA_PROPERTY, required=True)
        assert area_iri is not None
        candidates = ResourceInstance.search(
            con=self._con,
            project=self._project,
            resClass=self.FOLDER_CLASS,
            includeProperties={self.NAME_PROPERTY},
            filter=[
                SearchFilter(self.AREA_PROPERTY, CompOp.EQ, area_iri),
                LogicOp.AND,
                SearchFilter(self.PARENT_PROPERTY, CompOp.EQ, target_parent),
            ],
            limit=10_000,
        )
        if len(candidates) >= 10_000:
            raise OldapErrorInconsistency(
                "The target folder inventory is too large to validate safely."
            )
        name_key = self._portable_name_key(self._name(folder))
        for candidate in candidates:
            if candidate["iri"] == folder.iri:
                continue
            names = candidate.get(str(self.NAME_PROPERTY)) or []
            if any(self._portable_name_key(str(name)) == name_key for name in names):
                raise OldapErrorAlreadyExists(
                    f'Target folder already contains a folder named "{self._name(folder)}".'
                )

    def move(self, folder: Iri | str, parent_folder: Iri | str) -> ResourceInstance:
        """Move a user folder and its complete logical subtree below a new parent.

        Args:
            folder: IRI of the user folder to move.
            parent_folder: IRI of the new parent folder.

        Returns:
            The updated Staging folder instance.

        Raises:
            OldapErrorAlreadyExists: If the target already has a folder with
                the same portable name.
            OldapErrorInconsistency: If the move would create a cycle or stored
                cardinalities are inconsistent.
            OldapErrorNoPermission: If normal OLDAP permissions reject a read
                or the update.
            OldapErrorNotFound: If the folder or parent cannot be read.
            OldapErrorValue: If either resource is not a Staging folder, a
                system folder is involved, or the folders belong to different
                Staging areas.
        """
        folder_iri = self._as_iri(folder)
        parent_iri = self._as_iri(parent_folder)
        node = self._read_folder(folder_iri)
        parent = self._read_folder(parent_iri)

        if folder_iri == parent_iri:
            raise OldapErrorInconsistency("A Staging folder cannot be its own parent.")
        node_name = self._name(node)
        parent_name = self._name(parent)
        if self._is_reserved(node_name):
            raise OldapErrorValue(f'System folder "{node_name}" cannot be moved.')
        if self._portable_name_key(parent_name) in {"trash", "mobile"}:
            raise OldapErrorValue(
                f'System folder "{parent_name}" cannot contain moved folders.'
            )

        node_area = self._single_iri(node, self.AREA_PROPERTY, required=True)
        parent_area = self._single_iri(parent, self.AREA_PROPERTY, required=True)
        if node_area != parent_area:
            raise OldapErrorValue(
                "Staging folders can only be moved within the same Staging area."
            )

        current_parent = self._single_iri(node, self.PARENT_PROPERTY, required=False)
        if current_parent == parent_iri:
            return node

        parent_path = self.path_to_root(parent_iri)
        if any(ancestor.iri == folder_iri for ancestor in parent_path):
            raise OldapErrorInconsistency(
                "A Staging folder cannot be moved below one of its descendants."
            )

        self._assert_name_available(node, parent_iri)
        node[self.PARENT_PROPERTY] = parent_iri
        node.update()
        return node
