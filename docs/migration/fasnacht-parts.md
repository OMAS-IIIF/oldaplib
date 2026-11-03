# Fasnacht part relationships: use only isPartOf

## Decision

Store only `Child dcterms:isPartOf Parent`. Neither a public `hasPart` field nor
an inverse SHACL field is required. Find children by filtering `isPartOf` against
the parent's IRI. Keep the visible labels “Enthält Teile” and “Ist Teil von”.
This decision applies to Fasnacht Places and CarnivalThings (including their
subclasses). Chama's schema.org story relations require separate consumer review;
the scripts here deliberately do not rewrite schema:isPartOf/schema:hasPart.

## Prepared implementation

- The migration tools' Fasnacht YAML removes both `dcterms:hasPart` field
  declarations and explicitly clears `inverse_of` on the remaining `isPartOf`
  fields. Place retains max_count 1; CarnivalThing remains multi-valued.
- FasnachtsPage public archive detail now searches readable CarnivalThing children
  using the ordinary API equality filter on `dcterms:isPartOf`. It requests names,
  pages results, deduplicates identities and reports an error rather than silently
  exceeding 10,000 results. Parent links and admin writes remain `isPartOf`.
- `tools/migration/sparql/fasnacht-parts-preflight.rq` reports invalid endpoints,
  self-links, RDF 1.2 relation annotations and multiple resulting Place parents.
- `tools/migration/sparql/fasnacht-parts.ru` reverses legacy assertions in the
  selected Fasnacht data graph in one atomic update. Existing reverse edges are
  naturally deduplicated by RDF set semantics; repeating the update is harmless.

## Target migration sequence

No live data was changed. Use an isolated, backed-up RDF 1.2 target with writers
stopped. Verify the graph namespace before running these fixed-Fasnacht scripts.

1. Retain the source export and its conversion report. Do not assume hasPart
   statements in an export were originally asserted rather than inferred.
2. Run the preflight against the target. It must return zero rows. Resolve any
   reported issues explicitly; in particular do not pick an arbitrary Place
   parent or discard annotations. The update itself does not enforce preflight.
3. Apply the data update once through the transaction-owning Jena adapter. Compare
   the resulting isPartOf pairs with the union of original isPartOf and reversed
   hasPart pairs, and verify no hasPart assertions remain in the data graph.
4. Provision the revised YAML model in a fresh target, or explicitly migrate the
   existing target model. YAML omission alone does **not** remove old fields in
   incremental imports; in-use class guards can prevent `--remove-unused`.
   Do not bypass those guards or claim that the data script removes model fields.
   Remove both project OWL inverse axiom orientations and inspect registered
   vocabularies. Full in-place shape/restriction cleanup remains a separate step.
5. Test public detail links, no-child results, permission-filtered children and
   place editing. Publish neither model nor frontend without coordinated target
   acceptance. Existing API routes and library signatures are unchanged, but
   consumers that requested `hasPart` must now query the reverse direction.

## Validation

2026-10-30: 156 owned native model/search checks pass (four new conversion checks),
including duplicate directions, Place multiplicity conflicts, repeat conversion
and foreign-graph isolation. The full migration YAML validates. FasnachtsPage
changed-file ESLint and production build pass. Browser smoke was attempted but
blocked by missing anonymous authentication on the local page; visual acceptance
and testing with real migrated data remain open. No service deployment, source
GraphDB/Redis writes, commit or push.

## Complete fresh-target model acceptance

The subsequent [full Fasnacht import](../../../oldap-api/doc/jena-fasnacht-model.md)
verifies all source classes/taxonomies through tools and HTTP, zero-write replay
and permission-filtered reverse lookup after conversion. This closes the fresh
model provisioning check in step 4. Existing-target cleanup, real-data comparison
and browser smoke remain open.

## Real local source validation

The [subsequent real-export rehearsal](../../../oldap-api/doc/jena-fasnacht-export.md)
passes: two hasPart assertions become part of 11 canonical isPartOf pairs;
38,663 other triples are unchanged. Five parent API lookups match the expected
readable children. No live data was changed; production and real-user acceptance
remain separate.
