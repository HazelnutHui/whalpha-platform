# Five-Year Corporate-Action Source Audit — 2026-09-10

## Scope and result

The exact source-observation interval is 2021-08-11 through 2026-09-09.  It
includes the 20-session Membership warm-up boundary and the complete five-year
evaluation range.  All acquisition was serial, resumable, owner-only, and
source-observation-only.  No canonical `/data`, adjustment, analytics,
Production, publication, deployment, or scheduler write occurred.

| Kind / observation | Contract | Pages | Records | Natural completion |
| --- | --- | ---: | ---: | --- |
| split baseline | 1.0 | 2 | 6,491 | yes |
| split repeat | 1.1 | 2 | 6,491 | yes |
| dividend baseline | 1.1 | 48 | 235,751 | yes |
| dividend repeat | 1.1 | 48 | 235,751 | yes |

Every package reported zero malformed/out-of-range effective dates, duplicate
nonempty provider action IDs, and unexpected source fields.  The largest
package used 235,751 of the 400,000-row ceiling and 82.5 MB (78.7 MiB) of the
512-MiB byte ceiling.

Six independent annual-range dividend observations contained 17,170, 40,821,
42,330, 45,449, 51,731, and 38,250 rows.  Their 235,751 unique source IDs and
complete payloads exactly matched the five-year baseline.  Six annual split
observations contained 315, 996, 1,203, 1,325, 1,475, and 1,177 rows, totalling
6,491.

## Revision/conflict result

The repeat diff found every dividend row unchanged.  Dividend diff logical
fingerprint is
`74eb93977c6300f833a8209eaa9ae2a5cd0e700b696043de0b95a86c5cf6116a`.

The split repeat retained the same 6,491 semantic rows but reported five
provider IDs removed and five added.  The paired rows have identical complete
non-ID payloads: two forward splits and three reverse splits on 2022-04-01,
2022-07-13, 2022-10-19, 2023-03-20, and 2024-04-05.  Independently queried
annual packages match the repeat IDs exactly and match both full observations
after removing only the provider action ID.  Split diff logical fingerprint is
`fdadcdfd74ce2a6687698880ebb9f0024952d5d94d931a95a9f3749596367e4d`.

This is retained as observed provider-ID revision/instability, not coerced into
five new and five deleted economic events.  Provider action ID remains source
lineage, but cannot be the sole permanent economic-event key.  Downstream
resolution must preserve both observation vintages, bind the current repeated
payload, and identify an event by stable `instrument_id`, action kind,
effective date, economic terms, and source observation/revision.  The five
rows remain explicit revision cases until that append-only boundary exists.

## Custody fingerprints

| Package | Logical fingerprint |
| --- | --- |
| split baseline | `d3d13fef5b3f54f20916cb43ce7f19f03565b34326b0d17f8590a0c9d9871bfd` |
| split repeat | `a4f7dc2c510b34b5042932fd896205f3afd8f176a49b3c3b48b5d625885fc7a4` |
| dividend baseline | `016e5b4744856fa7bc9573424504ea273cb053147fd277d08ea58c4ee66cbfc5` |
| dividend repeat | `9681d36b4ab7c32449841878779a2ee647e664f6916b0cc7b0ca0845220cf5f3` |

The baseline dividend payload fingerprint independently reconstructed from
all rows is
`d29f83efe8d045b188f43340c7b6a249e861f5a8bd407f155dfea32623078c7a`;
the annual-package composition produced the same value.

## Persistent private custody

All 193 files from the baseline, annual cross-check, repeat, and repeat-diff
trees were copied byte-for-byte from the temporary acquisition roots into the
owner-only Dell historical-source state area.  The source and retained trees
both contain 252,132,705 bytes.  Recursive content comparison was empty, every
retained directory is mode 0700, every retained file is mode 0400, and the
relative-path/file-hash list fingerprint is
`4da1a226d7a47aa78871cd4295495839af043e4d94fa89b214893d9e5fad156b`.

This is private recovery custody, not a canonical `/data` publication.  The
explicit persistent-source reader subsequently reread all 16 baseline,
annual, and repeat packages and rejected a broader parent boundary in focused
tests.  The 16 overlapping observations contain 726,726 rows; each complete
five-year vintage contains 242,242 rows.  The copy does not grant action,
adjustment, signal, or performance authority.

## Remaining boundary

Source acquisition is complete for the declared range.  Corporate Actions are
not canonical or research-ready.  Exact event-date stable-ID resolution awaits
the completed five-year Identity family.  Lifecycle/successor/terminal facts,
authoritative large-distribution dates, neutral omitted-row evidence,
point-in-time availability, and total-return semantics remain separate gaps.
