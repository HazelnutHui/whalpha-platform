# Massive Historical Lifecycle Probe — 2026-09-01

## Result

One exactly authorized probe ran from clean Dell `main` revision
`64a35b61da304bb412230c00d697155de41c6d9d` for anchor 2026-07-16.
It consumed its two-page ceiling and returned `truncated_at_ceiling` because a
further page existed.

| Aggregate fact | Count | Share of 2,000 rows |
| --- | ---: | ---: |
| Explicit `active=false` | 2,000 | 100.00% |
| Active-state conflict/missing | 0 | 0.00% |
| `delisted_utc` present | 1,965 | 98.25% |
| `last_updated_utc` present | 2,000 | 100.00% |
| CIK present | 1,724 | 86.20% |
| Composite FIGI present | 533 | 26.65% |
| Share Class FIGI present | 469 | 23.45% |
| Duplicate ticker occurrences | 14 | 0.70% |

There were two requests, no retry, no retained response body or identifier and
zero data writes. Result fingerprint:
`8fa2c864851f43fdc24c321922f41d2d41c8bf180d384e6485126d3acd8ce2cd`.

## Interpretation boundary

The endpoint supplies substantial historical inactive/delisting observations,
but two pages do not complete the collection. Duplicate ticker occurrences
confirm that ticker cannot be a permanent key. Presence of `delisted_utc` does
not establish last-tradable session, delisting reason, merger consideration,
successor identity or terminal return. No full-pagination, coverage, Pilot,
Apply or performance authority follows from this result.
