# China A-share Five-Year Population Freeze Audit — 2026-09-17

## Scope

This audit freezes the evaluated SSE/SZSE listed-security occurrences for the
five-year interval from 2021-09-16 through 2026-09-16 before bulk daily-source
acquisition. It does not authorize a backtest, canonical Apply, Product use,
publication, or deployment.

## Evidence and method

The population joins the exact five official current/delisted exchange
artifacts retained by the stable-identity package to a fresh BaoStock
security-basic census. Official listing and delisting dates are primary;
BaoStock is an independent A-share/security-occurrence cross-check. Every
official candidate receives exactly one resolved, quarantined, or
outside-scope disposition.

Resolved occurrences use an append-only identity key containing provider
security ID, exchange, official board, and official listing date. Ticker alone
is never the identity. SSE B-share rows and records outside the target interval
remain explicit outside-scope evidence. The 113 SZSE historical delist rows
that pass the A-share cross-check but lack official board evidence remain
quarantined; code-pattern inference is not allowed to resolve them. They remain
source-keyed acquisition targets so later evidence can recover them without
data loss.

## Result

| Population disposition | Count |
| --- | ---: |
| Official candidate occurrences | 5,588 |
| Resolved stable occurrences | 5,296 |
| Current resolved occurrences | 5,220 |
| Delisted resolved occurrences | 76 |
| Quarantined acquisition targets | 113 |
| Outside target scope | 179 |
| Total five-year expansion targets | 5,409 |

The source census contains 5,557 BaoStock stock-basic rows. Three official
listing dates differ from BaoStock and retain the official date plus an
explicit conflict reason. Twenty-three terminal records retain a documented
difference between the provider's last date and the exchange's official
delisting date. No discrepancy was silently overwritten.

## Custody and verification

- population package logical fingerprint:
  `13595c0645aa36acc5fea8d818509b484582ad13d7def53d377b984d549c02c0`;
- report logical fingerprint:
  `9251d5cb0d3f227a8efc85cb2a6ab75ed02f243c051beafb49a95e1878e79434`;
- manifest physical SHA-256:
  `809494cc5f3942fecaa3c0e502dc39b80fbaeb6ca9bd296408b79aee614c7a84`;
- 9 files and 10,250,621 bytes under owner-only persistent workstation
  custody;
- zero symlinks, no unexpected files, and exact reread passed;
- 72 focused A-share/BaoStock tests and all 3,146 backend tests passed.

The next gate is restartable, bounded daily-bar/state/adjustment acquisition
for the exact 5,409 targets. The 113 quarantined occurrences may retain
source-keyed rows but cannot enter stable-ID research panels until their board
evidence is resolved. Research-backtest authority remains false.
