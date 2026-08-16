# EOD History Backfill Plan

## Status

The first single-session pilot completed for 2026-07-17. This document remains planning-only for every later session; no batch or next date is authorized.

The 2026-08-14 liquidity window now has 17 missing XNYS sessions from 2026-07-20 through 2026-08-11. Each missing session requires a completed same-day Instrument Master, Provider Identity, and Resolver before one Grouped Daily acquisition. The 2026-08-14 resolver must never map July tickers; latest-resolver fallback and ticker/name/CIK/FIGI guessing are prohibited.

## Conservative Request Model

- reference pagination: at most 20 pages per session;
- Grouped Daily: at most 1 request per session;
- per-session ceiling: 21;
- retries: 0;
- serial fixed rate limiter: 15 seconds;
- 17-session conservative ceiling: 357 requests.

The pilot used 14 reference pages plus one Grouped Daily request. At that planning rate, 17 remaining sessions are approximately 255 requests. These are planning estimates, not authorization or a success gate.

## Proposed Execution Sequence

1. Manually review the completed 2026-07-17 pilot.
2. If accepted, separately authorize a first chronological batch of at most three sessions.
3. Preserve same-day identity, Grouped Daily mapping, atomic publication, and resume gates.
4. After every batch, validate manifests, staging residue, protected inventory, and completed-target non-overwrite.
5. Six batches cover the current 17-session gap.

Completed identity or EOD partitions are validated and reused, never overwritten. If identity completes and EOD fails, a future authorized resume may reuse that same-day identity after full manifest/fingerprint validation. The planner has no transport or credential-loader dependency.
