# Retained FINRA/SEC Foundation Integration Audit — 2026-09-12

## Reconciliation boundary

The old `codex/strong-leader-pullback-v2-admission` worktree was clean and
contained 23 data-foundation commits after its common ancestor with main. The
data sequence ends at
`0bc1dad21ae3099b88d9a0c17068329b32bcef36`. Its later UI-only commit was not
imported because main already contains the newer deployed public-entry and
application hierarchy.

Only new FINRA/SEC providers, services, tests, data contracts, operations
guides, and dated audits were adopted. Main's current status, current context,
roadmap, changelog, EOD audit, web code, and already assigned ADR 0202–0211
files were not overwritten. ADR 0215 now resolves the branch-local numbering
collision and adopts the surviving data decisions.

## Persistent evidence revalidated from main

| Evidence | Result | Logical fingerprint |
| --- | --- | --- |
| FINRA five-year range | 62 packages / 68,714 rows | `badd20a33f0b668c5a39cfb4d45e86c0daf7b2c229c655a242436a07b9d95f41` |
| FINRA/Massive action census | 2,298 split / 8,205 dividend unique numeric matches | `0559b1488ced840d786734b3dfa8b054d3c65dd18365d9d77c7a4616b9cd5317` |
| Company Facts payload census | 41,619,407 in-range occurrences / 172,265 accessions | `e98ea73df73777a937568f643e5aaf55c6a2f11daeebe13be775190ca10a0724` |
| Submissions payload census | 27,217,476 filing rows / 172,262 target matches | `bfa416ca41003e163932b8c0185386ea4fd5d9a461146274918dfbadb7c41004` |
| Filing-clock ledger | 172,265 rows / 172,262 admitted | `da75607b52e044f003a10f9988023b4d6545e0ed7e1d01c75b42713a69e658bd` |
| Normalized Company Facts | 41,619,407 rows / 41,619,004 clock-admitted | `e45b6624398767e2d96c5e05f56cbf9e73c79e4651a13927a3256f0a7739d5da` |
| Filer/security pilot | 1 session / 8,201 stable-ID decisions | `e7efd0f6b530be218e6c64cea71a8f4fa7be4c2febc55d3098a8681d08c28421` |

The roots contain 436 files / 6,849,867,479 bytes in total, with zero symlinks
and zero partial or staging residue. These are private source/derived evidence,
not part of the canonical `/data` inventory.

## Validation and authority

The 129 imported focused tests passed from the current main tree. Sealed
census, filing-clock, and one-session link readers passed against their exact
persistent files. The normalized 41.6-million-occurrence reader also passed its
complete transitive reread: 41,619,407 rows, 41,619,004 clock-admitted rows,
403 quarantined rows, and logical fingerprint
`e45b6624398767e2d96c5e05f56cbf9e73c79e4651a13927a3256f0a7739d5da`.
That low-frequency audit path took 2,508.68 seconds and peaked at 766,476 KiB
resident memory. Routine recovery should therefore use the sealed manifest and
census readers; the full row reread is reserved for integrity investigations or
contract changes.

The complete main API suite then passed with 2,574 tests and the same two
pre-existing dependency deprecation warnings in 262.47 seconds. This validates
the adopted implementation against the current EOD, identity, universe,
research, and production-reader behavior rather than only against its retained
branch-era focused tests.

No network acquisition, canonical `/data` write, Historical Coverage,
research admission, Candidate result, analytics, Snapshot, bundle, deployment,
or scheduler change occurred during integration. SEC facts remain filer-level
sparse source revisions; FINRA remains OTC corroboration; lifecycle,
fundamental security projection, action/adjustment completion, and final
coverage remain fail-closed.
