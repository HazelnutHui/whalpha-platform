# China A-share Daily Universe Audit — 2026-09-17

## Scope

This audit closes only the point-in-time daily Universe family for the six
stable SSE/SZSE pilot instruments from 2021-09-16 through 2026-09-16. It does
not expand the market population, authorize a backtest, or claim historically
as-operated membership evidence.

## Method

The deterministic methodology emits exactly one disposition for every stable
instrument/session pair:

- a listed common stock without a risk warning is included;
- a risk-warning security is excluded rather than silently mixed into the
  baseline common-stock research population;
- suspension preserves membership but makes that session performance-
  ineligible;
- not-listed and non-common-stock observations are excluded; and
- unknown identity, lifecycle, trading, or risk-warning evidence is
  quarantined.

Every decision binds the immutable daily package, stable identity, and
identity/lifecycle package. Source availability is unavailable historically,
so the later retrieval clock is retained explicitly; the result is not
misrepresented as an as-operated historical list.

## Result

| Decision | Count |
| --- | ---: |
| Target instrument/session pairs | 7,266 |
| Included | 7,007 |
| Excluded risk-warning sessions | 259 |
| Quarantined | 0 |
| Performance-eligible included sessions | 6,997 |
| Included but suspended sessions | 10 |

The partition is complete: all six instruments times all 1,211 sessions have
exactly one decision. An independent replay from the exact input packages
reproduced every decision and the report byte-for-byte.

## Custody

- package logical fingerprint:
  `a33e2c0a52806b5dde0969a6403aebc302d74774992d272d068c8ae918b44f5d`;
- report logical fingerprint:
  `975d078ff8d6955a82b12f517f23e05c4e5adb576a6224736454ad7ed758fa51`;
- decision-set fingerprint:
  `36473cdbd4c1497ade9e5fc3e5ce2ca36f1423a9c01f4398183ec17392e10408`;
- manifest physical SHA-256:
  `d32852ef4a6066dc45eeb9c88f946fa4e4150ffbc7c2c9583a97d2cdb9361d61`;
- 3 files, 5,476,188 bytes, owner-only modes, zero symlinks, closed file set;
  and
- exact reread plus deterministic replay passed; and
- 68 focused A-share tests and all 3,142 backend tests passed.

All canonical Apply, research, Product, and deployment authority remains
false. The next gate is bounded, resumable full-population expansion using the
same identity, lifecycle, daily-state, and Universe semantics.
