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
