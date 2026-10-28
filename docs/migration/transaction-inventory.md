# Transaction boundary inventory

Snapshot: 2026-10-27. Generated AST locations with provisional migration dispositions.

One row identifies a function containing an explicit start/context or a transaction decorator, not an HTTP route or a count of possible runtime transactions. Nested boundaries may join an outer transaction. Definitions and comments are not counted as starts. Source hashes/call sites are in `transaction-call-sites.json`.

Classes: **U** fixed update payload; **G** conditions can be mapped explicitly, with result reporting; **D** Python-dependent/composed workflow needs redesign; **R** read-only snapshot; **I** transaction infrastructure; **T** operational test/migration script. Classifications are design assessments, not completed ports.

## oldaplib

Commit: `9f7610de81cb37b9fb87b93c4c637b16c5e22a4b`. Parsed Python files: 192.

| Function | Boundary location | Class | Required treatment |
| --- | --- | --- | --- |
| `ArchiveAdoption.apply` | `oldaplib/src/archive_adoption.py:786` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `ArchiveAdoption.default_proposal` | `oldaplib/src/archive_adoption.py:453` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `ArchiveAdoption.preflight` | `oldaplib/src/archive_adoption.py:703` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `ArchiveAdoption.proposal` | `oldaplib/src/archive_adoption.py:331` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `ArchiveInventory.page` | `oldaplib/src/archive_inventory.py:103` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `ArchivePublication.apply` | `oldaplib/src/archive_publication.py:456` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `ArchivePublication.apply_link` | `oldaplib/src/archive_publication.py:577` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `ArchivePublication.operation` | `oldaplib/src/archive_publication.py:611` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `ArchivePublication.preview` | `oldaplib/src/archive_publication.py:424` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `ArchivePublication.preview_link` | `oldaplib/src/archive_publication.py:554` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `ArchiveRepository.move_reference` | `oldaplib/src/archive_repository.py:205` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `ArchiveTree.move` | `oldaplib/src/archive_tree.py:114` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `DataModel.create` | `oldaplib/src/datamodel.py:660` | U | Batch fixed writes; keep authorization/existence policy and update memory/cache only after success. |
| `DataModel.delete` | `oldaplib/src/datamodel.py:760` | U | Batch fixed writes; keep authorization/existence policy and update memory/cache only after success. |
| `ExternalOntology.create` | `oldaplib/src/externalontology.py:233` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `ExternalOntology.delete` | `oldaplib/src/externalontology.py:600` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `ExternalOntology.update` | `oldaplib/src/externalontology.py:493` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `ResourceInstance.create` | `oldaplib/src/objectfactory.py:1646` | D | Include resource_operation decorator: policy guards, reference retention, audit and optional outbox callback, not just the method body. |
| `ResourceInstance.delete` | `oldaplib/src/objectfactory.py:2356` | D | Include resource_operation decorator: policy guards, reference retention, audit and optional outbox callback, not just the method body. |
| `ResourceInstance.transform_class` | `oldaplib/src/objectfactory.py:2063` | D | Include resource_operation decorator: policy guards, reference retention, audit and optional outbox callback, not just the method body. |
| `ResourceInstance.update` | `oldaplib/src/objectfactory.py:1754` | D | Include resource_operation decorator: policy guards, reference retention, audit and optional outbox callback, not just the method body. |
| `OldapList.create` | `oldaplib/src/oldaplist.py:767` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `OldapList.delete` | `oldaplib/src/oldaplist.py:1015` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `OldapList.in_use` | `oldaplib/src/oldaplist.py:931` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `OldapList.update` | `oldaplib/src/oldaplist.py:843` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `OldapListNode.create_root_node` | `oldaplib/src/oldaplistnode.py:443` | G | Guard root uniqueness/version and all affected writes; report conflict explicitly. |
| `OldapListNode.delete_node` | `oldaplib/src/oldaplistnode.py:1061` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `OldapListNode.delete_node_recursively` | `oldaplib/src/oldaplistnode.py:1203` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `OldapListNode.insert_node_below_of` | `oldaplib/src/oldaplistnode.py:862` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `OldapListNode.insert_node_left_of` | `oldaplib/src/oldaplistnode.py:733` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `OldapListNode.insert_node_right_of` | `oldaplib/src/oldaplistnode.py:579` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `OldapListNode.move_node_below` | `oldaplib/src/oldaplistnode.py:1362` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `OldapListNode.move_node_left_of` | `oldaplib/src/oldaplistnode.py:1871` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `OldapListNode.move_node_right_of` | `oldaplib/src/oldaplistnode.py:1615,1646` | D | Translate Python-derived state/branches and preserve all read dependencies. Existing code starts twice in one method (1615, 1646); resolve ownership before porting. |
| `OldapListNode.update` | `oldaplib/src/oldaplistnode.py:498` | G | Guard root uniqueness/version and all affected writes; report conflict explicitly. |
| `Project.create` | `oldaplib/src/project.py:613` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `Project.update` | `oldaplib/src/project.py:724` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `PropertyClass.create` | `oldaplib/src/propertyclass.py:741` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `PropertyClass.delete` | `oldaplib/src/propertyclass.py:1311` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `PropertyClass.update` | `oldaplib/src/propertyclass.py:1048` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `_resource_transaction` | `oldaplib/src/resource_transaction.py:78` | I | Preserve join/rollback-only, hooks, error and post-commit semantics. |
| `coordinated_domain_operation.coordinated` | `oldaplib/src/resource_transaction.py:146` | I | Preserve join/rollback-only, hooks, error and post-commit semantics. |
| `resource_operation.atomic` | `oldaplib/src/resource_transaction.py:166` | I | Preserve join/rollback-only, hooks, error and post-commit semantics. |
| `ResourceClass.create` | `oldaplib/src/resourceclass.py:769` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `ResourceClass.delete` | `oldaplib/src/resourceclass.py:1261` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `ResourceClass.update` | `oldaplib/src/resourceclass.py:1152` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `Role.create` | `oldaplib/src/role.py:259` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `Role.delete` | `oldaplib/src/role.py:670` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `Role.in_use` | `oldaplib/src/role.py:617` | R | Return one consistent read snapshot; preserve visibility and existing coordination requirements. |
| `Role.update` | `oldaplib/src/role.py:540` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `User.create` | `oldaplib/src/user.py:893` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `User.revoke_authentication` | `oldaplib/src/user.py:499` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |
| `User.update` | `oldaplib/src/user.py:1476` | G | Move existence/references/version predicates and final verification inside the command; preserve typed errors. |

## oldap-api

Commit: `9d58a12fd443a2e2b8b62aa3f0d078c45ee7ba26`. Parsed Python files: 177.

| Function | Boundary location | Class | Required treatment |
| --- | --- | --- | --- |
| `GraphDbExportJobRepository.claim_next` | `oldap_api/exports/repository.py:449` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbExportJobRepository.complete_cleanup` | `oldap_api/exports/repository.py:581` | G | Guard full state/claim identity; serialize job/receipt and all effects together; distinguish replay/conflict. |
| `GraphDbExportJobRepository.create` | `oldap_api/exports/repository.py:325` | G | Guard full state/claim identity; serialize job/receipt and all effects together; distinguish replay/conflict. |
| `GraphDbExportJobRepository.create_with_manifest` | `oldap_api/exports/repository.py:345` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbExportJobRepository.expire_next_ready` | `oldap_api/exports/repository.py:505` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbExportJobRepository.purge_expired_audits` | `oldap_api/exports/repository.py:554` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbExportJobRepository.renew_claim` | `oldap_api/exports/repository.py:491` | G | Guard full state/claim identity; serialize job/receipt and all effects together; distinguish replay/conflict. |
| `GraphDbExportJobRepository.save` | `oldap_api/exports/repository.py:394` | G | Guard full state/claim identity; serialize job/receipt and all effects together; distinguish replay/conflict. |
| `GraphDbExportJobRepository.update_notification` | `oldap_api/exports/repository.py:538` | G | Guard full state/claim identity; serialize job/receipt and all effects together; distinguish replay/conflict. |
| `GraphDbImportJobRepository.claim_next` | `oldap_api/imports/repository.py:326` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbImportJobRepository.commit_import` | `oldap_api/imports/repository.py:378` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbImportJobRepository.create` | `oldap_api/imports/repository.py:257` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbImportJobRepository.replace` | `oldap_api/imports/repository.py:299` | G | Guard full state/claim identity; serialize job/receipt and all effects together; distinguish replay/conflict. |
| `GraphDbMobileMediaLifecycleOutbox.claim_next` | `oldap_api/mobile_media/lifecycle.py:248` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbMobileMediaLifecycleOutbox.complete` | `oldap_api/mobile_media/lifecycle.py:288` | G | Guard full state/claim identity; serialize job/receipt and all effects together; distinguish replay/conflict. |
| `GraphDbMobileMediaLifecycleOutbox.normalize_legacy_resource_reference` | `oldap_api/mobile_media/lifecycle.py:173` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbMobileMediaRepository.commit` | `oldap_api/mobile_media/repository.py:125` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `GraphDbStagingAreaRepository.delete_empty` | `oldap_api/staging_area.py:491` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `provision_staging_system_folders.provision` | `oldap_api/staging_area.py:389` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `update_instance.update` | `oldap_api/views/instance_views.py:1571` | D | Translate Python-derived state/branches and preserve all read dependencies. |

## oldap-harvesters

Commit: `4cc2d1607893abe819bf4e7668e1c6e91a32d429`. Parsed Python files: 66.

| Function | Boundary location | Class | Required treatment |
| --- | --- | --- | --- |
| `BibliographicOldapSink.fill_missing_dating` | `src/oldap_harvesters/sinks/fasnacht_oldap.py:210` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `FasnachtResourceSink.write_linked_pdf` | `src/oldap_harvesters/sinks/fasnacht_oldap.py:115` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `FasnachtResourceSink.write_payload` | `src/oldap_harvesters/sinks/fasnacht_oldap.py:81` | D | Translate Python-derived state/branches and preserve all read dependencies. |
| `PdfTextEnricher.enrich_iri` | `src/oldap_harvesters/sinks/pdf_text.py:82` | D | Translate Python-derived state/branches and preserve all read dependencies. |

## oldap-tools

Commit: `1949fc5015b22a3a99b2d02908f1c7daecc2f48c`. Parsed Python files: 46.

| Function | Boundary location | Class | Required treatment |
| --- | --- | --- | --- |
| `apply_fasnacht_taxonomy_migration` | `src/oldap_tools/fasnacht_taxonomy_migration.py:840` | D | Translate Python-derived state/branches and preserve all read dependencies. |

## oldap-mediaserver

Commit: `89be99ddf98ab295e5e94eae48e13efbcaf5f1a1`. Parsed Python files: 69.

| Function | Boundary location | Class | Required treatment |
| --- | --- | --- | --- |
| No direct transaction owner found | — | — | Indirect CRUD users still need dependency/configuration migration. |

## import-tool

Commit: `7d522d803148a12e412e7075924423f97212c611`. Parsed Python files: 11.

| Function | Boundary location | Class | Required treatment |
| --- | --- | --- | --- |
| No direct transaction owner found | — | — | Indirect CRUD users still need dependency/configuration migration. |

## oldap-setup

Commit: `938f7ed656be006dfcdf206696728811ddbd06b6`. Parsed Python files: 26.

| Function | Boundary location | Class | Required treatment |
| --- | --- | --- | --- |
| No direct transaction owner found | — | — | Indirect CRUD users still need dependency/configuration migration. |

## FasnachtsPage

Commit: `c2297fe552f22cfd912c84aa747237c1e36f221c`. Parsed Python files: 33.

| Function | Boundary location | Class | Required treatment |
| --- | --- | --- | --- |
| `run_probe` | `docs/as-02/probe_archive_integration.py:416,513` | T | Explicitly port or keep as GraphDB-only; never run unchanged against Jena. |
| `run_probe.concurrent_moves` | `docs/as-02/probe_archive_integration.py:466` | T | Explicitly port or keep as GraphDB-only; never run unchanged against Jena. |
| `<module>` | `docs/as-02/probe_graphdb_transactions.py:113,134,143,144` | T | Explicitly port or keep as GraphDB-only; never run unchanged against Jena. |
| `run` | `docs/as-03/probe_repository_lifecycle.py:386` | T | Explicitly port or keep as GraphDB-only; never run unchanged against Jena. |
| `run` | `docs/as-04/probe_reviewed_adoption.py:502` | T | Explicitly port or keep as GraphDB-only; never run unchanged against Jena. |
| `run` | `docs/as-09/local_migration.py:109` | T | Explicitly port or keep as GraphDB-only; never run unchanged against Jena. |
| `main` | `docs/permissions/verify-publication-local.py:60` | T | Explicitly port or keep as GraphDB-only; never run unchanged against Jena. |
| `run` | `docs/production-rollout/apply_migration.py:153` | T | Explicitly port or keep as GraphDB-only; never run unchanged against Jena. |

## Additional paths without their own transaction boundary

- `Model.safe_query`, `safe_update`, `safe_commit`, modification readers/setters; `resource_query`; policy and archive transfer/audit helpers: included in the call-site snapshot and must join the owning command.
- `DataModel.update`: invokes child mutations with their own commits; it is not currently one atomic operation.
- `StagingFolderTree.move`: imports the coordinator but has no decorator; reads/validates then calls the decorated resource update. Do not infer an outer transaction from an import.
- API `_mobile_lifecycle_hook` returns a callback that appends an outbox record to the active transaction; transform/delete routes can join the resource decorator without opening their own context.
- Single-request bypass writers (`update_query`, upload, clear/move graph, Lucene connector commands) require backend routing and participate in any future revision/fencing policy. GraphDB connector side effects are not ordinary RDF transactional writes.
- Existing public `resource_transaction` and arbitrary caller `before_commit` functions are extension points; this inventory cannot enumerate code outside the inspected repositories.

## Coverage limits

AST scanning includes tracked and untracked non-ignored Python files, tests separately, operational scripts and known wrappers. A workspace-wide text search added FasnachtsPage rollout/probe scripts to the initial seven-repository scope. No scanned source is imported or executed. Python dynamic dispatch, future aliases, external clients and shell-driven SPARQL require separate review; a static inventory is not proof that all possible runtime paths have been exercised.
