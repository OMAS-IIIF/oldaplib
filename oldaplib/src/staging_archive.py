"""Build an editorial archive YAML proposal from visible Staging folders."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
import unicodedata

from oldaplib.src.archive_yaml import ArchiveDocument, ArchiveUnit


SYSTEM_FOLDER_NAMES = frozenset({"top", "Mobile", "Trash"})


@dataclass(frozen=True)
class StagingFolderSnapshot:
    """Minimal visible Staging-folder fact required by the proposal generator."""

    iri: str
    name: str
    parent_iri: str | None
    position: int | None = None
    visible_media_count: int = 0


@dataclass(frozen=True)
class ArchiveProposalWarning:
    """One editorial or structural uncertainty in a generated proposal."""

    code: str
    message: str
    folder_iri: str | None = None


@dataclass(frozen=True)
class ArchiveProposal:
    """Generated canonical document plus non-fatal editorial warnings."""

    document: ArchiveDocument
    warnings: tuple[ArchiveProposalWarning, ...]


def _base_id(name: str) -> str:
    """Return a readable NCName-compatible identifier stem."""

    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", normalized).strip("-.").lower() or "archive-unit"
    if not re.match(r"[A-Za-z_]", stem):
        stem = f"unit-{stem}"
    return stem


def staging_folders_to_archive_proposal(
    folders: tuple[StagingFolderSnapshot, ...] | list[StagingFolderSnapshot],
    *,
    language: str = "de",
) -> ArchiveProposal:
    """Convert visible Staging folders into a conservative archive proposal.

    Technical ``top``, ``Mobile``, and ``Trash`` folders are omitted and their
    eligible user-folder children are promoted. Inner user folders are proposed
    as ``Series`` and leaves as ``File``. Media are counted only for warnings;
    they never become ``Item`` units.

    Raises:
        ValueError: If folder IRIs are duplicated, the visible hierarchy has a
            cycle, or no editorial folder remains after technical-folder removal.
    """

    by_iri: dict[str, StagingFolderSnapshot] = {}
    input_order: dict[str, int] = {}
    for index, folder in enumerate(folders):
        if folder.iri in by_iri:
            raise ValueError(f'Duplicate StagingFolder IRI "{folder.iri}".')
        by_iri[folder.iri] = folder
        input_order[folder.iri] = index

    children: dict[str | None, list[StagingFolderSnapshot]] = {}
    warnings: list[ArchiveProposalWarning] = []
    for folder in folders:
        parent = folder.parent_iri if folder.parent_iri in by_iri else None
        if folder.parent_iri and parent is None:
            warnings.append(
                ArchiveProposalWarning(
                    "ORPHANED_FOLDER",
                    f'Folder "{folder.name}" has no visible parent and was promoted to a root.',
                    folder.iri,
                )
            )
        children.setdefault(parent, []).append(folder)

    def ordered(values: list[StagingFolderSnapshot]) -> list[StagingFolderSnapshot]:
        return sorted(
            values,
            key=lambda folder: (
                folder.position is None,
                folder.position if folder.position is not None else 0,
                input_order[folder.iri],
                folder.name.casefold(),
            ),
        )

    editorial_roots: list[StagingFolderSnapshot] = []
    visited_technical: set[str] = set()

    def promote(folder: StagingFolderSnapshot) -> None:
        if folder.iri in visited_technical:
            raise ValueError(f'Visible Staging folder hierarchy contains a cycle at "{folder.iri}".')
        if folder.name not in SYSTEM_FOLDER_NAMES:
            editorial_roots.append(folder)
            return
        visited_technical.add(folder.iri)
        if folder.visible_media_count:
            warnings.append(
                ArchiveProposalWarning(
                    "TECHNICAL_FOLDER_MEDIA",
                    f'Technical folder "{folder.name}" contains visible media; media were not converted.',
                    folder.iri,
                )
            )
        if folder.name != "Trash":
            for child in ordered(children.get(folder.iri, [])):
                promote(child)
        visited_technical.remove(folder.iri)

    for root in ordered(children.get(None, [])):
        promote(root)
    if not editorial_roots:
        raise ValueError("The visible StagingArea contains no editorial folders to export.")

    name_counts: dict[str, int] = {}
    for folder in folders:
        if folder.name not in SYSTEM_FOLDER_NAMES:
            name_counts[folder.name.casefold()] = name_counts.get(folder.name.casefold(), 0) + 1

    assigned_ids: set[str] = set()
    active: set[str] = set()

    def build(folder: StagingFolderSnapshot, depth: int, sibling_position: int) -> ArchiveUnit:
        if folder.iri in active:
            raise ValueError(f'Visible Staging folder hierarchy contains a cycle at "{folder.iri}".')
        active.add(folder.iri)
        user_children = [
            child
            for child in ordered(children.get(folder.iri, []))
            if child.name not in SYSTEM_FOLDER_NAMES
        ]
        if folder.visible_media_count == 0 and not user_children:
            warnings.append(
                ArchiveProposalWarning(
                    "EMPTY_FOLDER",
                    f'Folder "{folder.name}" is empty; keep or remove the proposed File after review.',
                    folder.iri,
                )
            )
        if folder.visible_media_count and user_children:
            warnings.append(
                ArchiveProposalWarning(
                    "MIXED_FOLDER",
                    f'Folder "{folder.name}" contains media and subfolders; review the proposed Series level.',
                    folder.iri,
                )
            )
        if depth > 6:
            warnings.append(
                ArchiveProposalWarning(
                    "DEEP_HIERARCHY",
                    f'Folder "{folder.name}" is deeper than six editorial levels.',
                    folder.iri,
                )
            )
        if name_counts.get(folder.name.casefold(), 0) > 1:
            warnings.append(
                ArchiveProposalWarning(
                    "DUPLICATE_NAME",
                    f'Folder name "{folder.name}" occurs more than once; generated IDs disambiguate it.',
                    folder.iri,
                )
            )

        unit_id = _base_id(folder.name)
        if unit_id in assigned_ids or name_counts.get(folder.name.casefold(), 0) > 1:
            unit_id = f"{unit_id}-{sha256(folder.iri.encode('utf-8')).hexdigest()[:8]}"
        while unit_id in assigned_ids:
            unit_id = f"{unit_id}-x"
        assigned_ids.add(unit_id)
        built_children = tuple(
            build(child, depth + 1, index)
            for index, child in enumerate(user_children, start=1)
        )
        active.remove(folder.iri)
        return ArchiveUnit(
            unit_id=unit_id,
            level="Series" if built_children else "File",
            title=folder.name,
            position=folder.position if folder.position is not None else sibling_position,
            children=built_children,
        )

    units = tuple(build(root, 1, index) for index, root in enumerate(editorial_roots, start=1))
    return ArchiveProposal(
        document=ArchiveDocument(version=1, language=language, units=units),
        warnings=tuple(warnings),
    )
