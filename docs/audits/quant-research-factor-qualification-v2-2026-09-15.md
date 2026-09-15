# Quant Research Factor Qualification V2 Audit — 2026-09-15

## Decision

Factor Catalog V2 completed the frozen ADR 0279 outcome-blind qualification
and one independent full replay. Both runs produced byte-identical reports.
The terminal status is `rejected_data_or_implementation`: no factor is
admitted, no outcome screen may begin, and Model Construction remains locked.

This is a source-coverage rejection, not a predictive result. No forward
return, performance metric, Validation row, Holdout row, prior strategy
outcome, or option return was read.

## Exact evidence

| Field | Verified value |
| --- | --- |
| Repository revision | `f0d9354f3b6ffeb21cf37bd696f3b6f9ee24398e` |
| Protocol fingerprint | `b74214155cc148d1e0d37c530ab4fea2f385af1a81237b901eec45e1fee2eb0b` |
| Catalog fingerprint | `6620000334a0a8bd23103341dfc1958d57c712a063dff0a39e23ffc82d51bed5` |
| Report logical fingerprint | `bed79513febf21dcf585a2e953c43fb66cb02824cd509800da39af452c0380ef` |
| Report SHA-256 | `a95f2ff95ee7d2083602568c457a929d33c3636794d0e991310bd042239a1d79` |
| Signal interval | 2025-06-23 through 2026-08-12 |
| Source interval | 2024-12-17 through 2026-08-12 |
| Sessions / declared paths | 287 / 437,402 |
| Complete / incomplete vectors | 266,335 / 171,067 |
| Available / unavailable factor cells | 2,130,680 / 1,368,536 |
| Eligible candidate Alpha | 0 of 4 |

The original and replay reports are 33,219 bytes each under separate
owner-only `0700/0400` Dell custody. Their canonical bytes, logical
fingerprint, and SHA-256 are identical. No symlink, staging, or partial residue
exists. Both runs recorded zero external requests, canonical-data writes, and
Production writes.

## Why qualification failed

Every factor has 266,335 available paths (60.8902%), 161 sessions with at
least 100 instruments, only 17 such sessions in the first chronological half,
and 144 in the second. All eight definitions therefore fail the frozen 90%
availability, 250-session, and 120-first-half-session gates. Distinct-value and
tie gates pass; no pair meets the frozen near-duplicate definition and there
is no cross-group redundancy block.

The dominant unavailable reason is
`benchmark_split_evidence_quarantined` on 167,294 paths. Canonical split action
and adjustment evidence both begin on 2025-06-23, while the registered
127-session factors require source history from 2024-12-17. The conservative
rule therefore closes early signal sessions whose SPY window begins outside
proved split coverage. Separate stock evidence contributes 3,773
`instrument_eod_unavailable` and 25
`instrument_split_evidence_quarantined` reason occurrences. Reason counts can
overlap on one unavailable path and are not additive path totals.

The strongest weighted pair relationships are 0.8996 between the two risk
guards and 0.8338 between standard and intraday short-term reversal. Neither
passes the required high-correlation session-share rule, so the failure is not
caused by post-hoc redundancy selection.

## Next bounded action

Do not lower the gates or change factor formulas. Dell already retains a
five-year Massive split source and stable-ID resolution evidence. The next
task is to design and verify a versioned historical split-action/adjustment
candidate that covers the V2 source start while preserving unresolved split
records as quarantine. Canonical Apply remains a separate reviewed action.

Only after an admitted source version covers the exact interval may the same
frozen V2 protocol run again. A later passing data qualification would permit
only the design of a preregistered Development outcome screen; it would still
not establish Alpha.
