# EOD History Backfill Plan

## Status

The single-session pilot, five three-session batches, and final two-session batch completed the 2026-08-14 history window through 2026-08-13.

The window now has all 20 expected XNYS sessions, zero missing, and zero corrupt/unavailable. Every historical EOD partition references its completed same-day Instrument Master, Provider Identity, and Resolver. Latest-resolver fallback and ticker/name/CIK/FIGI guessing remain prohibited.

## Conservative Request Model

- reference pagination: at most 20 pages per session;
- Grouped Daily: at most 1 request per session;
- per-session ceiling: 21;
- retries: 0;
- serial fixed rate limiter: 15 seconds;
- current missing-session ceiling: 0 requests.

The completed final batch used 30 requests total. No further acquisition is planned for this window.

## Proposed Execution Sequence

1. Preserve all completed same-day identity and EOD partitions without overwrite.
2. Review instrument-level incomplete histories separately from partition readiness.
3. Keep any future acquisition separately authorized and outside this completed window.

Completed identity or EOD partitions are validated and reused, never overwritten. If identity completes and EOD fails, a future authorized resume may reuse that same-day identity after full manifest/fingerprint validation. The planner has no transport or credential-loader dependency.
