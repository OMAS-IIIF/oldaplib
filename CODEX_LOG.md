# CODEX_LOG

### Update 2026-05-14 02:12
- Decisions: Added required project context files before making packaging changes.
- Implementation: Created `codex.md` with concise project context and initialized this technical work log.
- Open: `pyproject.toml` cleanup still in progress.
- Risks/Assumptions: Context is inferred from current repository files and may need refinement as project conventions evolve.

### Update 2026-05-14 02:13
- Decisions: Modernized package metadata with PEP 621 `[project]` fields and kept Poetry-only packaging controls under `[tool.poetry]`.
- Implementation: Split runtime dependencies from optional `docs` and `dev` dependency groups, removed redundant `[tool.mkdocs]` config, updated the build backend requirement to Poetry Core 2, and synchronized `oldaplib/src/version.py` with the package version.
- Open: Fresh local installs that need documentation or release tooling should use `poetry install --with docs,dev`.
- Risks/Assumptions: License was normalized to the SPDX expression `AGPL-3.0-only`, matching the previous "GNU Affero General Public License version 3" wording.
