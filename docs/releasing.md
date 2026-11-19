# Releasing oldaplib

`poetry update` updates dependency resolution, not the project version. Review and
commit those changes separately from version selection. Run the relevant isolated
regression suites against the locked dependencies before publishing. `make test`
loads fixtures into a configured database: use only a disposable test installation.

The bump configuration uses `rc` followed by the optional `final` value. Bumping
patch/minor/major resets the lower components to `rc1`. Therefore a patch bump
from `1.2.1` produces `1.2.2rc1`. `make build` uses the declared version exactly;
`.tar.gz` is the source distribution, while `.whl` is the installable wheel.

For the existing release-candidate workflow:

```sh
# Preview before changing versions.
poetry run bump-my-version bump patch --dry-run --verbose
make bump-patch-level
# Validate the candidate. Optional candidate builds remain separately versioned.
poetry run bump-my-version bump release --dry-run --verbose
make finalize-release
make build
# Verify wheel metadata, install/import and regressions from the built wheel.
git push origin main
git push origin v1.2.2  # Substitute the actual final version.
make publish
```

The bump targets create local commits/tags. Existing patch/minor/major targets
also push the branch, but do not explicitly push tags. `finalize-release` creates
only a local commit/tag, allowing validation before pushing. Do not invoke another
patch bump merely to remove `rc1`: bump the `release` component instead. Finalize
from a clean working tree; commit source, tests and documentation first.

Build/publish default to `dist/<declared-version>`; override both with the same
`DIST_DIR` for a private release bundle. Older flat `dist/` artifacts are retained
but no longer selected automatically. Publish only the exact verified files and
compare their SHA-256 hashes with PyPI afterwards. Never replace a published
version or move an existing release tag.

Check consumer compatibility before publication. The 1.2.2 `subPropertyOf` getter
changes from a scalar to a set, requiring coordinated consumers and a migration
note. Version numbers alone do not establish backwards compatibility. For future
incompatible public APIs, prefer a major version or preserve the old contract.
API/tools dependency updates, Docker publication and deployment are separate
steps. A library publication does not restart any installation.
