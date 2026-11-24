# Repository instructions

- Keep predicate semantics in the library; HTTP and UI clients must not write SPARQL directly.
- Reifier fields belong to their shape. Follow `docs/reification-stage1b.md` for ownership, transactions and shared predicate semantics.
- Use isolated RDFLib fixtures for model regression tests. Do not run service-backed tests against a non-disposable database.
- Default test discovery and `make test` include service-backed suites; select isolated test modules explicitly. Install test/docs tooling with `poetry sync --with dev,docs`.
