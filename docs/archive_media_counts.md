# Direct media counts for folder defaults

`ArchiveAdoption.default_proposal()` includes `directMediaCount` on each visible
folder row. The optional v1 response extension requires no ontology or request
change. Structure-import proposals may omit it; older consumers can ignore it.

`_direct_media_counts` makes one GROUP BY query for the complete selected scope
(up to the existing 5,000-folder limit). It counts distinct media identities:

- Direct `shared:inStagingFolder` children classified as StagingMediaObject,
  with the same `shared:inStagingArea` as the source.
- `shared:referencedMediaObject` targets classified through configured archive
  media classes. No project-specific class or role is hard-coded.
- The existing visibility predicate (creator or current role with VIEW) applies
  to both branches. Multiple classes, hierarchy paths and relations count once
  per folder; the same medium placed in different folders counts in each.

The result initializes missing groups to zero without OPTIONAL row expansion.
It reads no medium metadata or thumbnails, uses no persistent cache or per-folder
requests, and runs inside the existing proposal read transaction. The count is
added after the source snapshot has been calculated. It neither invalidates
review hashes nor authorizes any write/deletion. Zero means zero visible media,
not necessarily a globally empty folder. Descendants are not counted.

Validation includes RDF dataset query execution (duplicate classes/relations,
hidden identities, foreign areas, descendants and empty scopes), schema backward
compatibility and preserved source snapshots. A local GraphDB sample covered 46
folders and 125 visible placements in 7–30 ms for the aggregation; three individual
inventory queries agreed. These timings are not a large-repository benchmark.
The full sampled HTTP proposal took 21.6 s cold after API restart and 1.86 s warm;
that includes existing model, policy, folder-state and receipt work.

Local activation used a development wheel built from the current 0.7.19 source,
without changing dependencies, followed by `make restart` in oldap-api. The prior
installed package is archived under BACKUP/local-media-counts-20260914-224638.
Publish a new version through the regular release process before deploying.
