# Publication domain command

`ArchivePublication` is an opt-in project-configured service built on the existing
resource transaction and durable writer gate. It supports preview, revision-bound
apply and actor-scoped receipt lookup. It writes only the configured published
status, public role read grant and modification metadata; private role grants are
preserved. No additional ontology term is introduced.

The `publication` object in each enabled archive policy requires:

- `publisherRoleIris`, `rootClassIris`, `mediaClassIris`: nonempty unique absolute IRIs.
- `statusPropertyIri`, `publishedStatusIri`, `mediaToRootPropertyIri`, `publicRoleIri`.
- `maxResources`: integer 1..500, including dependencies in a review.

Role resources and model properties are validated against the repository.
Publisher membership is queried freshly without the creator/admin bypass; normal
resource UPDATE remains required for every affected root and medium. Other linked
roots must already be public; their most restrictive read permission constrains
media publication. Hidden/unauthorized links fail the whole command. Revoked
membership also prevents receipt replay; receipts never substitute for authority.

The generic resource guard blocks public-state/public-ACL changes via create,
update and transform, including inherited public transform state. Published
media-to-root links are immutable through generic updates. Other projects retain
existing contracts when this configuration is absent. Direct administrative SPARQL
is outside the application-domain boundary and must remain an operator function.

A root publication includes its directly linked media. The operation is bounded,
not a recursive graph-wide cascade or an unpublication workflow. Existing public
read access is never widened by re-publication. Every apply includes an immutable
review digest and a caller UUID; preserve both on an uncertain transport outcome.

The API contract is maintained in sibling oldap-api/API-def/oldap-api.yaml.
Release all writers with the matching library before distributing the additional
policy field; older closed parsers reject it. See sibling FasnachtsPage
`docs/permissions/archive-roles.md` for rollout and role documentation. This change
has been tested with rolled-back local GraphDB fixtures, not activated globally.
