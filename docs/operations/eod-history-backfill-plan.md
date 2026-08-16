# EOD History Backfill Plan

## Status

Planning only. No pilot, provider request, credential access, `/data` write, or scheduler is authorized.

The 2026-08-14 liquidity window has 18 missing XNYS sessions from 2026-07-17 through 2026-08-11. Each missing session requires a completed same-day Instrument Master, Provider Identity, and Resolver before one Grouped Daily acquisition. The 2026-08-14 resolver must never map July tickers; latest-resolver fallback and ticker/name/CIK/FIGI guessing are prohibited.

## Conservative Request Model

- reference pagination: at most 20 pages per session;
- Grouped Daily: at most 1 request per session;
- per-session ceiling: 21;
- retries: 0;
- serial fixed rate limiter: 15 seconds;
- 18-session conservative ceiling: 378 requests.

The observed reference shape suggests approximately 14 reference pages plus one Grouped Daily request per session: about 270 requests total. At a fixed 15-second interval, request spacing alone is approximately 67 minutes. These are planning estimates, not authorization or a success gate.

## Proposed Execution Sequence

1. Separately authorize the earliest missing session as one pilot.
2. Validate same-day identity, Grouped Daily mapping, atomic publication, and resume behavior.
3. If accepted, authorize chronological batches of at most three sessions.
4. After every batch, validate manifests, staging residue, protected inventory, and completed-target non-overwrite.
5. Six batches cover the current 18-session gap.

Completed identity or EOD partitions are validated and reused, never overwritten. If identity completes and EOD fails, a future authorized resume may reuse that same-day identity after full manifest/fingerprint validation. The planner has no transport or credential-loader dependency.
