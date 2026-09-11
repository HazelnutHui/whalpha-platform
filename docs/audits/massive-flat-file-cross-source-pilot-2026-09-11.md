# Massive Flat File Cross-Source Pilot — 2026-09-11

## Scope

This bounded pilot tested the separately configured Massive S3 Flat Files
credential and compared one current Day Aggregates object with a newly fetched
same-session Grouped Daily REST package. It wrote only disposable `/tmp`
packages and isolated working files. It did not write `/data`, publish a
research candidate, alter Production, or expose credential values.

## Access results

- The owner-only Flat Files credential passed the strict local loader.
- The exact 2021-09-09 Day Aggregates object returned access denied. This is
  consistent with the current Starter rolling-five-year boundary.
- The 2026-09-09 Day Aggregates control object succeeded in one request. Its
  package content fingerprint was
  `d52deb35f64e8eb426ab34c078f11a4bd12da45fb98ccbab4c9bf4d208048c6c`.
- A new 2026-09-09 Grouped Daily REST control package succeeded in one request.
  Its package content fingerprint was
  `b86407f75dc5949a1212129e233ab00b47e97fd5460e520309dd5efe71d422d2`.

The successful current-date control proves that the S3 credential and general
Flat Files entitlement work. It does not grant access outside Starter depth.

## Normalized comparison

Both packages were mapped through the same case-sensitive, same-session
Identity-bound Reconciled EOD builder in isolated temporary workspaces.

| Measure | Result |
| --- | ---: |
| Flat File mapped records | 9,945 |
| Current REST mapped records | 9,958 |
| Shared instrument records | 9,945 |
| REST-only records | 13 |
| Flat-only records | 0 |
| Shared open/high/low/close differences | 0 / 0 / 0 / 0 |
| Shared volume/trade-count differences | 0 / 0 |
| Shared adjustment-factor differences | 0 |
| Shared VWAP differences | 9,945 |

The 13 REST-only records were on the zero-volume path. The Day Aggregates Flat
File schema has no VWAP column, so every shared Flat File record has missing
optional VWAP while REST supplies it. The two sources otherwise agree exactly
on shared OHLCV, trade count, currency, and adjustment fields.

The earlier same-evening canonical EOD contained 9,916 records. Against the
later Flat File it had 55 close, 5 high, 27 low, 7,496 volume, and 7,493
trade-count differences. The current REST/Flat File agreement shows these were
same-evening-versus-finalized source revisions, not evidence that Flat File
OHLCV is wrong.

## Disposition

Day Aggregates Flat Files are a valid independent OHLCV cross-check but are not
a drop-in replacement for the current canonical contract because they omit
VWAP and the REST zero-volume path. Do not silently merge or fill those fields.

For the two missing evaluation EOD sessions and 20 earlier warm-up sessions,
the lowest-complexity consistent route is a temporary Stocks Developer
entitlement followed by the existing Grouped Daily REST pipeline. That keeps
one source schema and one normalization path across the acquired interval.
This is a recommendation, not purchase or execution authority. A different
source would require its own identity, completeness, revision, and field-level
reconciliation before use.
