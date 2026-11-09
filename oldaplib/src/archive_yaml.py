"""Canonical editable YAML model for OLDAP archive structures.

This module is the only authority for archive YAML version 1.  It deliberately
contains no project lookup or persistence logic: documents remain editable,
nested values until :mod:`oldaplib.src.archive_import` resolves them for one
OLDAP project.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

import yamale
import yaml

from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.xsd.dating import Dating
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


ARCHIVE_LEVELS = frozenset(
    {"ArchiveGroup", "Fonds", "Subfonds", "Series", "Subseries", "File", "Item"}
)
ARCHIVE_YAML_VERSION = 1
ArchiveText = str | Mapping[str, str]


@dataclass(frozen=True)
class ArchiveDate:
    """Editable representation of one OLDAP date or date range."""

    start: str
    end: str | None = None
    verbatim: str | None = None
    calendar: str = "GREGORIAN"


@dataclass(frozen=True)
class ArchiveUnit:
    """One nested, project-neutral archive unit in an editable document."""

    unit_id: str
    level: str
    title: ArchiveText
    parent: str | None = None
    identifier: str | None = None
    description: ArchiveText | None = None
    date: ArchiveDate | None = None
    extent: ArchiveText | None = None
    creators: tuple[str, ...] = ()
    provenance: ArchiveText | None = None
    access_conditions: ArchiveText | None = None
    about: tuple[str, ...] = ()
    position: int | None = None
    children: tuple["ArchiveUnit", ...] = ()


@dataclass(frozen=True)
class ArchiveDocument:
    """Validated archive YAML version 1, independent of a target project."""

    version: int
    language: str
    units: tuple[ArchiveUnit, ...]


def archive_schema_path() -> Path:
    """Return the single bundled Yamale schema for archive YAML version 1."""

    return Path(str(resources.files("oldaplib.src") / "schemas" / "archive_schema.yaml"))


def _validate_schema(text: str, schema: Path | None = None) -> None:
    """Validate YAML text structurally before building the document model."""

    try:
        schema_obj = yamale.make_schema(str(schema or archive_schema_path()))
        data = yamale.make_data(content=text)
        yamale.validate(schema=schema_obj, data=data)
    except Exception as error:
        raise ValueError(f"Archive YAML validation failed: {error}") from error


def _reject_yaml_aliases(text: str) -> None:
    """Reject aliases before schema parsing to prevent expansion abuse."""

    try:
        if any(isinstance(event, yaml.events.AliasEvent) for event in yaml.parse(text)):
            raise ValueError("Archive YAML aliases are not allowed.")
    except yaml.YAMLError as error:
        raise ValueError(f"Archive YAML parsing failed: {error}") from error


def _validate_text(value: ArchiveText, default_language: str, field_name: str) -> None:
    """Validate text by constructing the same LangString used during import."""

    values = (
        [f"{value}@{default_language}"]
        if isinstance(value, str)
        else [f"{text}@{language}" for language, text in value.items()]
    )
    if not values:
        raise ValueError(f'Field "{field_name}" must not be an empty language map.')
    try:
        LangString(values)
    except Exception as error:
        raise ValueError(f'Invalid multilingual value in "{field_name}": {error}') from error


def _validate_iri(value: str, field_name: str) -> None:
    """Validate an IRI or QName and retain field context in failures."""

    try:
        Iri(value, validate=True)
    except Exception as error:
        raise ValueError(f'Invalid IRI "{value}" in "{field_name}".') from error


def _parse_date(raw: dict[str, Any] | None, unit_id: str) -> ArchiveDate | None:
    """Build and semantically validate an editable date value."""

    if raw is None:
        return None
    date = ArchiveDate(
        start=raw["start"],
        end=raw.get("end"),
        verbatim=raw.get("verbatim"),
        calendar=raw.get("calendar", "GREGORIAN"),
    )
    try:
        Dating(
            dateStart=date.start,
            dateEnd=date.end,
            verbatimDate=date.verbatim,
            inCalendar=date.calendar,
        )
    except Exception as error:
        raise ValueError(f'Invalid date on archive unit "{unit_id}": {error}') from error
    return date


def loads_archive_yaml(text: str, *, schema: Path | None = None) -> ArchiveDocument:
    """Parse and validate an archive YAML document from memory.

    Args:
        text: UTF-8 YAML text.
        schema: Optional schema override intended for validation tooling.

    Returns:
        A nested, immutable :class:`ArchiveDocument`.

    Raises:
        ValueError: If structural or semantic validation fails.
    """

    _reject_yaml_aliases(text)
    _validate_schema(text, schema=schema)
    try:
        raw_document = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ValueError(f"Archive YAML parsing failed: {error}") from error

    archive = raw_document["archive"]
    language = archive["language"]
    seen_ids: set[str] = set()

    def parse_unit(raw: dict[str, Any], *, top_level: bool, depth: int = 1) -> ArchiveUnit:
        if depth > 100:
            raise ValueError("Archive YAML exceeds the maximum hierarchy depth of 100.")
        unit_id = raw["id"]
        if unit_id in seen_ids:
            raise ValueError(f'Duplicate archive unit id "{unit_id}".')
        seen_ids.add(unit_id)
        try:
            Xsd_NCName(unit_id, validate=True)
        except Exception as error:
            raise ValueError(f'Archive unit id "{unit_id}" is not a valid NCName.') from error
        if not top_level and "parent" in raw:
            raise ValueError(
                f'Nested archive unit "{unit_id}" must not define "parent"; '
                "its parent is given by the YAML hierarchy."
            )
        if raw["level"] not in ARCHIVE_LEVELS:
            raise ValueError(f'Invalid archive level "{raw["level"]}" on unit "{unit_id}".')

        _validate_text(raw["title"], language, f"{unit_id}.title")
        for field_name in ("description", "extent", "provenance", "access_conditions"):
            if raw.get(field_name) is not None:
                _validate_text(raw[field_name], language, f"{unit_id}.{field_name}")
        if raw.get("parent"):
            _validate_iri(raw["parent"], f"{unit_id}.parent")
        for field_name in ("creators", "about"):
            for value in raw.get(field_name, []):
                _validate_iri(value, f"{unit_id}.{field_name}")

        return ArchiveUnit(
            unit_id=unit_id,
            level=raw["level"],
            title=raw["title"],
            parent=raw.get("parent"),
            identifier=raw.get("identifier"),
            description=raw.get("description"),
            date=_parse_date(raw.get("date"), unit_id),
            extent=raw.get("extent"),
            creators=tuple(raw.get("creators", [])),
            provenance=raw.get("provenance"),
            access_conditions=raw.get("access_conditions"),
            about=tuple(raw.get("about", [])),
            position=raw.get("position"),
            children=tuple(
                parse_unit(child, top_level=False, depth=depth + 1)
                for child in raw.get("children", [])
            ),
        )

    return ArchiveDocument(
        version=archive["version"],
        language=language,
        units=tuple(parse_unit(unit, top_level=True) for unit in archive["units"]),
    )


def load_archive_yaml(path: Path | str, *, schema: Path | None = None) -> ArchiveDocument:
    """Read and validate an archive YAML document from ``path``."""

    return loads_archive_yaml(Path(path).read_text(encoding="utf-8"), schema=schema)


def _text_value(value: ArchiveText) -> str | dict[str, str]:
    """Return a plain stable YAML value from an archive text value."""

    return value if isinstance(value, str) else dict(value)


def _unit_mapping(unit: ArchiveUnit) -> dict[str, Any]:
    """Serialize one nested unit while preserving the canonical field order."""

    result: dict[str, Any] = {
        "id": unit.unit_id,
        "level": unit.level,
        "title": _text_value(unit.title),
    }
    optional: tuple[tuple[str, Any], ...] = (
        ("parent", unit.parent),
        ("identifier", unit.identifier),
        ("description", None if unit.description is None else _text_value(unit.description)),
        (
            "date",
            None
            if unit.date is None
            else {
                key: value
                for key, value in (
                    ("start", unit.date.start),
                    ("end", unit.date.end),
                    ("verbatim", unit.date.verbatim),
                    ("calendar", unit.date.calendar if unit.date.calendar != "GREGORIAN" else None),
                )
                if value is not None
            },
        ),
        ("extent", None if unit.extent is None else _text_value(unit.extent)),
        ("creators", list(unit.creators) if unit.creators else None),
        ("provenance", None if unit.provenance is None else _text_value(unit.provenance)),
        (
            "access_conditions",
            None if unit.access_conditions is None else _text_value(unit.access_conditions),
        ),
        ("about", list(unit.about) if unit.about else None),
        ("position", unit.position),
        ("children", [_unit_mapping(child) for child in unit.children] if unit.children else None),
    )
    result.update({key: value for key, value in optional if value is not None})
    return result


def dumps_archive_yaml(document: ArchiveDocument) -> str:
    """Serialize a validated document as stable, human-readable YAML."""

    data = {
        "archive": {
            "version": document.version,
            "language": document.language,
            "units": [_unit_mapping(unit) for unit in document.units],
        }
    }
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def dump_archive_yaml(document: ArchiveDocument, path: Path | str) -> None:
    """Serialize ``document`` to a UTF-8 YAML file."""

    Path(path).write_text(dumps_archive_yaml(document), encoding="utf-8")


def archive_yaml_hash(text: str) -> str:
    """Return the SHA-256 binding used between HTTP preflight and apply."""

    return sha256(text.encode("utf-8")).hexdigest()
