# Massive Historical Entitlement Probe — 2026-08-31

## Result

One exactly authorized probe ran from clean Dell `main` revision
`df178b21266ebe733d937fed4f71a5b50176e1d6` for session 2026-07-16.

| Capability | Safe result | Count |
| --- | --- | ---: |
| Unadjusted Grouped Daily | accessible | 12,454 |
| Point-in-time active Tickers | accessible | 1 |
| Splits | accessible | 1 |
| Dividends | accessible | 1 |

The last three probes deliberately used `limit=1`; their counts establish only
that a result was returned. They do not establish full coverage or pagination.
There were four requests, no retry, no response-body retention and zero data
writes. Result fingerprint:
`34b4eafc8500b24a7d1625ee8fcc24c94509743f05be356c76ab774a58ff09d6`.

## Interpretation boundary

This establishes current technical accessibility for four endpoint classes.
It does not establish inactive-Ticker access, lifecycle/terminal coverage,
historical depth, correction semantics, data quality, commercial permission,
retention/display rights, Historical Pilot authorization, or `/data` Apply.
