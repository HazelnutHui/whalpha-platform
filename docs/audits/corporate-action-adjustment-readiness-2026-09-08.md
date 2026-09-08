# Corporate-Action Adjustment Readiness Audit — 2026-09-08

## Scope

This read-only Dell audit evaluates whether the completed ADR 0170 resolution
shadow is ready to feed split and dividend adjustments. Inputs are the exact
70,099-row owner-only shadow at
`/tmp/whalpha-corporate-action-resolution-shadow-20260908T091222Z`, all 304
canonical EOD/Identity sessions from 2025-06-23 through 2026-09-04, and the
active 2026-08-19 provider-form Universe.

No source row was remapped. Historical ticker presence was used only to build
a conservative possible-impact quarantine for unresolved split rows. The audit
made no external request and changed neither `/data` nor Production.

## Provider semantics

The current official [Splits documentation](https://massive.com/docs/rest/stocks/corporate-actions/splits)
states that the event is applied overnight and the execution-date bar is
already on the new basis. It defines `historical_adjustment_factor` as a
cumulative factor for translating history to a later/current basis. The
current official [Dividends documentation](https://massive.com/docs/rest/stocks/corporate-actions/dividends)
defines `split_adjusted_cash_amount` on the share basis after subsequent
splits. Massive's [2026-04-06 changelog](https://www.massive.com/changelog)
also records a correction to split-adjusted dividend cash histories involving
reverse splits or multiple same-day actions.

Therefore WH Alpha must derive a requested-basis split factor from event ratios
and dates. Provider cumulative factors and split-adjusted cash are audit
evidence, not ledger inputs.

## Split result

- All 1,949 source split-like rows have action-type/ratio direction consistent
  with the mapper contract: 1,384 reverse splits, 337 stock splits, and 228
  stock dividends.
- Exact-event-date Identity resolves 709 rows into 708 stable-ID/effective-date
  groups. One TTSH date contains reciprocal same-day actions; its composed
  daily price factor is exactly one. Events must therefore be grouped rather
  than deduplicated by stable ID and date.
- Reconstructing the cumulative factor from in-range event ratios matches the
  provider factor exactly for 1,595 rows and within `0.0000005` for another
  340. Fourteen differences are consistent with a provider current basis that
  includes later or differently ordered events; they confirm that the provider
  factor cannot define the 2026-09-04 basis.
- Of 1,240 unresolved split rows, 1,199 use tickers absent from every one of the
  304 historical Resolvers. Thirty-nine rows have one historical stable-ID
  candidate and two have multiple candidates, producing 43 conservative
  possible-impact stable IDs. These are quarantine candidates only; no event
  is assigned by this fallback.
- Only two of those 43 possible-impact IDs are members of the active Primary
  and Secondary Universes. Current product relevance is narrow, but the full
  historical research boundary must retain all 43 as non-clear.

Across 652 resolved split groups with both the prior-session and event-session
EOD bars, the ratio-adjusted price move is within 10% for 468 groups, within
25% for another 146, within 50% for 30, and above 50% for eight. Fifty-one
groups lack one EOD side and five fall on the first covered session without a
prior bar. Large residual moves are review flags, not automatic source errors.

## Dividend result

- Exact-date Identity resolves 41,347 dividend rows: 41,187 USD and 160 CAD.
- There are 41,200 stable-ID/ex-date groups. One hundred forty-five contain
  multiple events, 131 contain mixed distribution types, and 13 coincide with
  a resolved split date.
- `split_adjusted_cash_amount` matches original cash composed through resolved
  later split ratios exactly for 41,026 rows and within `0.0000005` for 127.
  Thirty-four USD rows differ and 160 CAD rows lack a directly comparable USD
  price basis.
- Twenty-nine resolved rows have ex-date after record date and 22 have ex-date
  after pay date. Special distributions can legitimately use nonstandard
  ordering, so these are review flags rather than automatic rejection.
- For 40,641 USD groups with comparable surrounding EOD bars, the cash-
  inclusive move is within 10% for 40,478, within 25% for another 150, and
  within 50% for 13; none exceeds 50% or has cash greater than the same-basis
  prior close. Seventy-one groups lack one EOD side and 328 fall on the first
  covered session.

Dividend total return is therefore not ready for implementation in the same
step as split adjustment. Currency conversion, special-distribution semantics,
same-date split/dividend ordering, the 34 mismatches, and price continuity need
separate treatment.

## Decision and unchanged state

ADR 0172 adopts a split-first candidate. The first real run has now completed
below `/tmp/whalpha-split-adjustment-candidate-20260908T103326Z`. It derives
target-basis factors only from resolved event ratios, composes same-date events,
marks the 43 possible-impact IDs non-clear, and keeps total return unavailable.
It contains one 564,826-byte owner-read-only file. File SHA-256 is
`83e8a3722132bd2172e0546e3d8fb84a5a5cece6e289a2b1c3744e1e8d175618`;
logical fingerprint is
`b3efa16da5570cddf41f7fc741d71a29e73e6a1f696f68828b2f5e67b596d226`.
A separate formal reread passed. This temporary candidate cannot satisfy
canonical Corporate Action, Adjustment Ledger, or Historical Coverage.

At the post-run audit checkpoint, Dell `/data` remains 4,060 files / 2,009,699,645
bytes with inventory fingerprint
`16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
zero symlinks, and zero publication residue. Production remains release
`2026-09-06T121300Z-ab1abf1afaaf`. No analytics, Snapshot, bundle, scheduler,
deployment, or website state changed. Repository implementation tests passed
2,209 tests with only the two pre-existing dependency deprecation warnings.
