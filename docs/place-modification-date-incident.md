# Duplicate Place modification dates: local investigation and repair

## Established facts

The history dialog exposed invalid existing data when it re-read a Place. A scan
of all named graphs in the local Jena dataset found exactly four subjects with
multiple `oldap:lastModificationDate` values, all in `fasnacht:data`:

| Place | Subject suffix | Retained modification date |
| --- | --- | --- |
| Aeschenplatz | `77b2648b-7134-4d9e-ad36-42792cf09225` | `2026-06-18T23:14:53.255254+00:00` |
| Barfüsserplatz | `f16cf028-69e4-483c-adaf-337aada8bb57` | `2026-06-18T23:14:39.971653+00:00` |
| Gerbergasse | `5bc7d713-adfb-4e6d-a004-18939cc7e2e4` | `2026-06-18T23:15:40.837020+00:00` |
| BMG Cliquenkeller BMG | `20d58f62-2cd6-4439-aa56-719e466b8841` | `2026-06-18T23:15:17.243829+00:00` |

All subjects use the `urn:uuid:` prefix. Each obsolete date was identical to that
subject's creation date in May 2026. Each subject had one lastModifiedBy value.
The **same pairs of dates** are already present in
`../oldap-tools/RepoBackups/repo-backup-2026-08-28.trigs.zip`, member
`repo-backup-2026-08-28.trigs`. ZIP SHA-256:
`1bc13ccfdb85d14d732c4ea1901f8b372407d1ddf0f17105ee5c16143b40d20f`.

This proves the duplicates predate Jena migration and the new property-history UI.
The stored dates indicate an old creation timestamp was retained alongside a June
modification timestamp. They do **not** identify the exact historical request,
writer, or import that introduced the duplicate. No historical request log proving
that original trigger was located. Do not attribute it to trailing-zero handling,
Jena or the history implementation without further evidence.

## Timestamp spelling experiment

Native local Jena tests ran in temporary diagnostic graphs in transactions that
were always aborted. Jena returned inserted lexical spellings unchanged, including
`.837020+00:00` and `.83702Z`. The old constant-based WHERE/DELETE worked for the
actual stored May/June spellings. For the equivalent `.83702Z` spelling, Python
re-serialized it to `.837020+00:00`; the old update matched nothing (it did not
produce two dates). The new bound-variable DELETE plus value-equality FILTER
correctly replaced all three tested variants with one new value.

The write path now deletes the actual matched RDF literal instead of reconstructing
it, retains the expected-time concurrency check, and verifies **exactly one**
modification date before commit. This is independently justified hardening; it is
not proof of the historical June trigger.

## Local correction and validation

`tools/repair_place_modification_dates.py` defaults to a read-only plan. Apply checks
the four exact reviewed date pairs, Place type, creation date and contributor count,
creates a private before-image, rechecks all direct subject triples inside the normal
resource transaction/writer gate, and deletes only the four obsolete date triples.
It verifies that all other direct triples are unchanged before committing.

Applied only to `http://127.0.0.1:3031/tx`. Private before-image:
`/Users/rosenth/Library/Application Support/OLDAP/diagnostics/place-modification-dates-before-20261111T235546.json`.
The original old dates are also retained in the unmodified August backup. No
business-property values or history entries were changed by the repair.

After repair, the all-graph duplicate scan returned zero rows. Generic data GET
and property-history GET returned HTTP 200 for all four subjects (eight checks).
The local API uses this editable library checkout and was restarted using its
existing guarded `restart_api.py` workflow. A real ResourceInstance update and
re-read on local Jena passed with one modification date; that diagnostic
transaction was fully rolled back and the repaired subject remained unchanged.

18 resource-history tests pass, including rollback on a non-singleton timestamp
result and the bound-literal update. No PyPI release, Docker image or remote
home/production deployment was performed. Remote datasets were not inspected or
repaired in this task.
