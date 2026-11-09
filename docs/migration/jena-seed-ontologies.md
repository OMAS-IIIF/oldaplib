# RDF 1.2 initialization files

The migration checkout now supplies native RDF 1.2 permission annotations in
`oldaplib/ontologies/admin.trig` and `admin-testing.trig`. This changes files only;
no live database was imported or rewritten. The original GraphDB checkout is
unchanged. These migration files must be loaded with an RDF 1.2-capable parser;
legacy GraphDB test/setup loaders are not acceptance targets for these files.

## Representation and preserved meaning

An asserted membership and its permission annotation are separate facts:

```trig
@prefix oldap: <http://oldap.org/base#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

oldap:admin {
    <urn:example:user> oldap:inProject oldap:SystemProject .
    <urn:example:grant> rdf:reifies <<( <urn:example:user> oldap:inProject oldap:SystemProject )>> ;
        oldap:hasAdminPermission oldap:ADMIN_OLDAP .
}
```

A triple term does not assert its triple. Every seed grant retains its asserted
membership in the same graph. Each reifier describes exactly one membership.

Seed reifier IRIs use UUIDv5 (URL namespace) over newline-separated values:
`oldap-seed-permission-v1`, the full admin graph IRI, subject IRI, membership
predicate IRI and target IRI. Permission values do not participate in identity.
The resulting `urn:uuid:` identifiers remain stable on reload. This avoids
creating duplicate permission reifiers when loading the same seed again; it
does not claim that all blank-node model content in a full reload is idempotent.

The two files contained 19 annotation statements for 18 distinct memberships.
The duplicated Fornaro/HyperHamlet administrative annotation now uses the same
reifier at both source locations. Its permission union is unchanged: all 29
unique original permission values remain. Password hashes, user/project/role
properties, asserted memberships, dates and embedded model data are unchanged.
No credential values are included in the acceptance report.

`oldap.trig` updates RDF-star examples and the `statementShape` descriptive label
and comment. The model term, shape structure and public APIs are unchanged.
Examples distinguish creation defaults on user/role memberships from actual
permissions on instance/role memberships; defaults do not cap existing grants.
SHACL remains model documentation, not an enabled validation engine.

`shared.trig`, `example.trig`, `oldap.ttl` and the standard vocabularies require no
syntax changes. They are included in native parsing acceptance rather than
rewritten unnecessarily.

## Verification

`tools/migration/JenaSeedOntologyProbe.java` parses every supplied TriG/Turtle/XML
file with the installed Jena 6.2.0 runtime, without a server or reasoner. The
versioned `ontology-seed-grants.tsv` records the original expected permission
relations independently of the new reifier identifiers.

```sh
java --class-path /path/to/fuseki-server.jar \
  tools/migration/JenaSeedOntologyProbe.java \
  oldaplib/ontologies tools/migration/ontology-seed-grants.tsv
```

The normal run checks all ten files, all permission values, membership presence,
reifier exclusivity/stable IRIs and reload stability. An optional third argument
accepts a baseline directory containing the original two admin files with only
the old annotation statements removed. The migration acceptance used this
baseline to compare every remaining named/default graph by RDF isomorphism.

The retained `jena-seed-ontologies-results.txt` records **24 native checks**,
including those one-time baseline comparisons. **Nine offline tests** also pass:
shared archive ontology, user permission ordering and Jena user writes. The
baseline comparisons do not require storing credential-bearing copies in a new
repository fixture; the permanent regression manifest contains permission IRIs
only. Existing RDFLib tests emit deprecation warnings.

## Reasoning policy and remaining migration

No general OWL reasoner is enabled. Required class ancestry uses explicit,
project-scoped `rdfs:subClassOf+`/`*` paths. Additional inference requirements must
be identified from actual OLDAP use and tested before introducing new behavior.

Migrating these initialization files is not a conversion of existing GraphDB
project data or account state. Controlled legacy export/conversion, administrative
restore, larger transfer packages and the remaining inference-dependency audit
remain separate migration steps.
