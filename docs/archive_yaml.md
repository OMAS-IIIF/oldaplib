# Archive YAML version 1

`oldaplib` is the single source of truth for the editable archive YAML schema,
document model, validation rules, project resolution, create-only preflight,
and apply/rollback behavior. HTTP services and command-line tools must call
this implementation instead of copying its parser or schema.

## Document boundary

An archive document is project-neutral and nested. It starts with
`archive.version: 1`, one default language, and one or more root units:

```yaml
archive:
  version: 1
  language: de
  units:
    - id: bmg
      level: Fonds
      title: Archiv der BMG
      children:
        - id: bmg-protokolle
          level: Series
          title: Protokolle
```

Each document-wide unique `id` is an XML NCName. During project resolution it
becomes a deterministic project QName such as `fasnacht:bmg-protokolle`.
Nested units get their parent from the YAML hierarchy. Only a root may declare
`parent` to attach a new subtree below an existing `shared:ArchiveUnit`.

Supported levels are `ArchiveGroup`, `Fonds`, `Subfonds`, `Series`,
`Subseries`, `File`, and `Item`. The format also supports multilingual title,
description, extent, provenance, and informational access-condition values;
date ranges; record creators; subjects; identifiers; and sibling positions.

## Python API

Use `loads_archive_yaml()` and `dumps_archive_yaml()` for in-memory workflows,
or `load_archive_yaml()` and `dump_archive_yaml()` for files. Parsing returns an
immutable nested `ArchiveDocument`; serialization produces stable,
human-readable YAML suitable for editorial revision and safe roundtrips.

`prepare_archive_import()` resolves the document for one project and performs
a read-only preflight. `apply_archive_import()` repeats that preflight, creates
parents before children, and attempts reverse-order rollback after failures.
Rollback failures remain explicitly available on `ArchiveImportError`.

## Permission and mutation rules

- Creating units requires the authenticated user's `ADMIN_CREATE` permission.
- An external attachment point must be visible, must be a
  `shared:ArchiveUnit`, and must grant that user `DATA_UPDATE`.
- Existing target resources are collisions. Imports never update, merge, move,
  or delete pre-existing archive units.
- No `ADMIN_ARCHIVE`, `ADMIN_MODEL`, or `ADMIN_LISTS` permission is involved.
- Archive structure import is separate from Staging media transformation.

## Staging proposals

`staging_folders_to_archive_proposal()` accepts only folder facts already
visible to the caller. It collapses the application-managed `top`, `Mobile`,
and `Trash` folders, proposes `Series` for inner editorial folders and `File`
for leaves, preserves explicit sibling positions where available, and emits
stable NCName IDs. Empty, mixed, deep, orphaned, duplicate-name, and technical
folder cases produce editorial warnings. Visible media affect warnings only;
they never become `Item` ArchiveUnits.

HTTP preflight/apply callers should bind the exact UTF-8 YAML text with
`archive_yaml_hash()`. The parser rejects unsafe YAML object construction and
aliases, and limits hierarchy depth. Service boundaries should additionally
enforce request-byte and unit-count limits before any write.
