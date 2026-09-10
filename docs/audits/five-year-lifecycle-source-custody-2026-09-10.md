# Five-Year Lifecycle Source Custody Audit — 2026-09-10

## Result

Two complete Massive inactive-listing source anchors were copied from their
temporary acquisition directories into owner-only persistent Dell custody and
formally reread from the retained location.

| Anchor | Requests | Rows | Sanitized package bytes |
| --- | ---: | ---: | ---: |
| 2026-07-16 | 24 | 23,260 | 6,622,891 |
| 2026-09-03 | 24 | 23,469 | 6,692,893 |

The retained tree has 52 files / 13,358,318 total filesystem bytes. Recursive
comparison against both source packages reported no difference. All retained
directories are mode 0700, all files are mode 0400, and the relative-path plus
file-hash list fingerprint is
`e513227f734704ba8e295daea4d18c2d4a08f03f7d40aa29d2403620e88d54c2`.

The persistent reader accepted the exact custody root and formally reproduced
logical fingerprints
`5b298512378f80fc5e72eb90bf05b588feb91c1ea1caedd802c8d54ac8cee7fb`
and
`8ae15be74aa8c554ab83075346f93c3d966cec72811d47375f53a91a8734ff98`.

## Interpretation

These are two later-observed `active=false` provider snapshots. They support
inactive-security discovery and stable-ID reconciliation; they are not five
years of point-in-time lifecycle states. Provider `delisted_utc` remains a
candidate date and `last_updated_utc` remains an unverified provider-update
field. Neither proves the last tradable session, event publication time,
terminal reason, successor, consideration, or terminal return.

The 2026-09-03 package can be re-resolved against the completed five-year
Identity history without network access. Missing or contradictory facts will
remain quarantined and counted; the retained packages do not authorize
canonical `/data`, research, performance, analytics, or Production changes.
