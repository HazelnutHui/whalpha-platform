# 2026-09-09 Canonical Split Coverage Diagnostic Audit

## Result

The ADR 0182 network-prohibited diagnostic scanned the exact canonical EOD
family and canonical split-action publication without writing a file. It found
no extreme adjusted residual among the 645 comparable active split groups, but
it found 387 severe adjacent-session price discontinuities across 321 stable
`instrument_id` values with no same-date canonical split evidence.

This is a falsification result, not a corporate-action inference. It supports
the internal consistency of the currently resolved active split facts while
contradicting any claim that absence from the bounded source publication can be
treated as a neutral factor. Complete split coverage, omitted-row neutrality,
total return, Historical Coverage, and research performance remain
unauthorized.

## Bound inputs

| Field | Verified value |
| --- | --- |
| Source revision | `d38634ec42cde23929dfa955ccce3fd1ceaa520b` |
| Calculated at | `2026-09-09T05:03:28+00:00` |
| EOD evidence fingerprint | `923f27a8fa4e85c6d20b5c8ac0804f17dbab7437b350f02d54fea2ed5293aeb1` |
| EOD evidence SHA-256 | `ba652cb4ed21a0bfce1ce0cbd690c933cb8ae98de3f39231e282ea8f22789593` |
| EOD scope | 304 sessions, 2025-06-23 through 2026-09-04, 2,816,903 rows |
| Canonical split publication | `76f017a1547e20b997e40cd1e61497b71c749a94e88a8632a3898fe84c106218` |
| Canonical split manifest SHA-256 | `a5ec5ced94d0596fc2a3e7bf247210c7a0fd1e7486e5847e0c226b2b309e95f4` |
| Diagnostic fingerprint | `d32222eb64bc4d18563fb58a14416922170f0faccf0612cf5701cf0070d930cc` |
| Registered severe ratio | open / prior close `<= 0.5` or `>= 2.0` |

The evidence contains 304 exact single-session artifacts with one Parquet
payload each. The scan compared only transitions whose dates are adjacent XNYS
sessions and joined only on stable `instrument_id`.

## Findings

| Classification | Count |
| --- | ---: |
| Adjacent stable-ID transitions scanned | 2,802,728 |
| Known event/date keys | 745 |
| Known keys with comparable two-sided EOD | 665 |
| Active split residual bounded | 645 |
| Active split residual extreme | 0 |
| Canonical multiple-action quarantine | 1 |
| Unresolved possible-impact quarantine | 19 |
| Known event current bar missing | 24 |
| Known event adjacent prior transition missing | 56 |
| Unexplained severe price discontinuities | 387 |
| Stable IDs with unexplained discontinuities | 321 |
| Total diagnostic flags | 1,132 |

The 645 bounded active groups are useful reconciliation evidence, but they do
not establish source completeness. The 387 unexplained discontinuities can
include missing corporate actions, stale or erroneous bars, distress moves,
listing/lifecycle transitions, or other market events. Price behavior alone
cannot choose among those explanations or create a canonical action.

## Prioritization-only cross-check

A second clean-revision read recomputed the same 387 flags / 321 stable IDs and
crossed only their stable IDs against current Activation and the exact
owner-only lifecycle corroboration plan:

| Review locator | Stable IDs |
| --- | ---: |
| Current Primary overlap | 13 |
| Current Secondary overlap | 14 |
| Existing 547-item lifecycle queue overlap | 31 |
| Current Secondary and lifecycle overlap | 0 |
| Ratio at or beyond one-quarter / fourfold | 44 IDs / 45 flags |
| IDs with repeated unexplained flags | 57 |
| Maximum flags on one ID | 5 |

The unexplained range is 2025-06-24 through 2026-09-02. Current Activation is
only a review-priority locator: it is not projected backward and does not make
those instruments historically eligible. Lifecycle overlap similarly does not
prove that a lifecycle event caused a price gap. The first independent-source
sample should prioritize the 14 current Secondary IDs, then lifecycle overlap
and the most extreme/repeated cases, while retaining representative ordinary
threshold cases.

### Frozen current-Secondary locator sample

The exact current-Secondary intersection was recomputed on clean revision
`642179eb1795d809fa29966a87469927ed869323`. The read is bound to Activation
pointer `dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168`
and 2026-09-08 Identity snapshot
`ccada891e47725796142b08381e4a24026ee074d8d5dc4cf1d33b9fbc7e422a5`.
The ticker and exchange values below are current review locators only.

| Stable `instrument_id` | Current locator | Exchange | Flagged transition(s), open / prior close |
| --- | --- | --- | --- |
| `00217daa-6715-58e4-b2ce-803cdd61da8d` | NKTR | XNAS | 2025-06-24, 2.088050314465 |
| `05b2b2c9-62a7-5809-b728-529559223ba3` | PRAX | XNAS | 2025-10-16, 2.760069747167 |
| `2350e2c7-2abd-5991-8a05-24491ed171b7` | MBX | XNAS | 2025-09-22, 2.240000000000 |
| `25c11c01-1a8a-5410-96f8-e12709b9f286` | ABVX | XNAS | 2025-07-23, 6.310000000000 |
| `2e1122b6-ec37-5862-837b-4080372facb0` | KD | XNYS | 2026-02-09, 0.461472967220 |
| `35fecc90-d036-537f-b3ca-ae95d6992316` | DFNS | XNAS | 2026-07-31, 0.435396563897 |
| `3db26832-ec26-5c19-8f27-895a3271c2c5` | BMNR | XNYS | 2025-06-30, 3.516998827667 |
| `4aac80aa-8249-5a34-b30b-4829814f00af` | CELC | XNAS | 2025-07-28, 3.337690631808 |
| `7a3fbf7a-d8ff-55d4-afa8-b22b5e9d45a6` | ALMS | XNAS | 2026-01-06, 2.671480144404; 2026-09-01, 0.455295735901 |
| `92d3373f-d5de-5a25-86e5-a336826a1bda` | SION | XNAS | 2026-08-10, 0.095023510972 |
| `b558c3ee-71dd-5799-8eb8-e69069a4983b` | GRAL | XNAS | 2026-02-20, 0.489116517286 |
| `d3c6132c-c802-52ca-a172-d8c87c3266b0` | VISN | XNAS | 2026-04-28, 0.493599590374 |
| `dad83406-1370-5c94-a7c9-a506b0b72717` | EYPT | XNAS | 2026-08-17, 0.275254237288 |
| `fa0991af-f9df-5c86-99f5-9758bd155068` | COGT | XNAS | 2025-11-10, 2.210526315789 |

This freezes 14 stable IDs and 15 discontinuity flags. It does not assert that
the current ticker existed on the flagged date, that the security was then in
either Universe, or that any listed transition was caused by a split.

## Safety and verification

- Six focused diagnostic/CLI tests passed after a test caught and corrected a
  typed-flag construction defect.
- The expanded split action, adjustment, invariant, and diagnostic suite passed
  35 tests.
- The real scan completed in about 24 seconds with zero external requests,
  filesystem writes, and canonical writes.
- `/data` remained 4,204 files / 2,151,679,313 bytes with zero symlinks.
- No Snapshot, bundle, deployment, timer, or scheduler action occurred.

## Next evidence gate

Do not create inferred split facts or a dense factor-one ledger from these
flags. Resolve a bounded, priority-ordered sample against an independent
licensed corporate-action/lifecycle source or issuer/exchange evidence. Until
that evidence exists, retain the 387 discontinuities as review candidates and
keep Historical Coverage and strategy-performance authority blocked.
