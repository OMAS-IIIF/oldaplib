# Private repository links

Shared ontology version **0.7.0** adds two optional object properties to
`shared:StagingFolder`. No existing required field, archive level, media identity,
class hierarchy, or permission enumeration changes.

| Property | Target | Cardinality per folder | Meaning |
| --- | --- | --- | --- |
| `shared:defaultArchiveUnit` | `shared:ArchiveUnit`, including project subclasses | 0..1 | Explicit, curator-confirmed suggestion for future capture from this folder. |
| `shared:referencedMediaObject` | `shared:MediaObject`, including project subclasses | 0..n | Private folder membership of an existing catalogued medium. |

The vocabulary is project-neutral. It requires neither Fasnacht publication
states nor a particular project's catalogued-media class. A museum or photographic
collection may reuse it with its own ArchiveUnit and MediaObject subclasses.

## Example

This is a relationship fragment, not a complete media/ArchiveUnit description:

```turtle
@prefix shared: <http://oldap.org/shared#> .
@prefix schema: <https://schema.org/> .
@prefix ex: <https://example.org/repository/> .

ex:folder a shared:StagingFolder ;
    schema:name "Photographs" ;
    shared:inStagingArea ex:area ;
    shared:defaultArchiveUnit ex:series ;
    shared:referencedMediaObject ex:photograph, ex:recording .
```

The folder's name and position in the private hierarchy remain independent of
the suggested archive unit. Renaming or moving either resource retains its IRI
and therefore the relationship. Multiple folders may suggest the same unit or
reference the same medium. Defaults do not implicitly inherit to child folders
and never reassign media already placed in the archive.

## Integrity and authorization boundaries

SHACL validates target classes and the single-default constraint. It deliberately
does not impose global uniqueness or require the new links on existing folders.
The OWL domain is StagingFolder; using these properties does not turn the folder
into an ArchiveUnit. `shared:hasMediaObject` retains its ArchiveUnit domain and
must not be reused for private folder membership.

The generic MediaObject range does **not** prove a medium has completed archive
transfer: staging media also extend MediaObject. Catalogued lifecycle checks,
role authorization, same-area moves, atomic reference preservation during
transfer, deletion guards, and mixed ZIP exports are backend responsibilities.
A reference grants no permission, ownership or publication; deleting a reference
must never delete its medium or original binary.

The ontology alone does not enforce write protection or enable the repository
workflow. In AS-01 only the vocabulary and tests are implemented. Deploying or
loading it does not constitute acceptance of the later backend/UI workflow.
Load into running environments only in the coordinated rollout; retain the
existing upload and CaptureApp contracts.

## Compatibility and verification

The source of truth is `oldaplib/ontologies/shared.trig`; the initialization copy
in oldap-setup must be synchronized byte-for-byte. Both SHACL and OWL advertise
0.7.0. This is an ontology version update, not a library package release.

Run the GraphDB-independent suites with the library's Python dependencies:

```sh
python -m unittest discover -s oldaplib/test -p 'test_shared_*ontology.py'
```

The repository-link tests validate the actual folder shape in isolation from
unrelated required media metadata. They cover legacy folders, wrong ranges and
literals, conflicting defaults, many references, shared targets, project
subclasses, and unwanted archive-unit inference. Lifecycle/permission enforcement
and live OLDAP model/cache reloads require the later backend acceptance tests.
