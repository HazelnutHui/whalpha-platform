# EOD History Backfill Plan

## Status

The single-session pilot and first two three-session batches completed through 2026-07-27. This document remains planning-only for every later session; no next batch or date is authorized.

The 2026-08-14 liquidity window now has 11 missing XNYS sessions from 2026-07-28 through 2026-08-11. Each missing session requires a completed same-day Instrument Master, Provider Identity, and Resolver before one Grouped Daily acquisition. The 2026-08-14 resolver must never map July tickers; latest-resolver fallback and ticker/name/CIK/FIGI guessing are prohibited.

## Conservative Request Model

- reference pagination: at most 20 pages per session;
- Grouped Daily: at most 1 request per session;
- per-session ceiling: 21;
- retries: 0;
- serial fixed rate limiter: 15 seconds;
- 11-session conservative ceiling: 231 requests.

The completed pilot and batches used 14 reference pages plus one Grouped Daily request per session. At that planning rate, 11 remaining sessions are approximately 165 requests. These are planning estimates, not authorization or a success gate.

## Proposed Execution Sequence

1. Manually review the completed 2026-07-23, 07-24, and 07-27 batch.
2. If accepted, separately authorize the next chronological batch of at most three sessions.
3. Preserve same-day identity, Grouped Daily mapping, atomic publication, and resume gates.
4. After every batch, validate manifests, staging residue, protected inventory, and completed-target non-overwrite.
5. Four batches cover the current 11-session gap.

Completed identity or EOD partitions are validated and reused, never overwritten. If identity completes and EOD fails, a future authorized resume may reuse that same-day identity after full manifest/fingerprint validation. The planner has no transport or credential-loader dependency.
