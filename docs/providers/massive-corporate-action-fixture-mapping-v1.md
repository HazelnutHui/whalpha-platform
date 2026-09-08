# Massive Corporate Action Fixture Mapping V1

## Status

The mapper remains validated against saved synthetic response fixtures only.
ADR 0169 separately implements a resumable, temporary Massive V1 split and
dividend source-custody boundary. The first real range completed and matched
the documented mapper fields, but it has not been passed through an event-date
stable-ID adapter. No source-to-canonical adapter, canonical Corporate Action
dataset, or `/data` write exists.

## Public shape review

The response shape was rechecked on 2026-08-28 against the current public
[Splits](https://massive.com/docs/rest/stocks/corporate-actions/splits) and
[Dividends](https://massive.com/docs/rest/stocks/corporate-actions/dividends)
documentation. The fixture mapper accepts only already-loaded mappings and has
no transport dependency.

The allowlisted V1 fields are:

- Splits: `id`, `ticker`, `execution_date`, `adjustment_type`, `split_from`,
  `split_to`, and `historical_adjustment_factor`.
- Dividends: `id`, `ticker`, `declaration_date`, `ex_dividend_date`,
  `record_date`, `pay_date`, `cash_amount`, `currency`, `distribution_type`,
  `frequency`, `split_adjusted_cash_amount`, and
  `historical_adjustment_factor`.

Unexpected response fields are ignored and do not enter issue fingerprints.
Synthetic tests contain no credential or real provider payload.

## Mapping rules

- `forward_split`, `reverse_split`, and `stock_dividend` remain distinct
  source action types; ratio direction conflicts quarantine the row.
- A cash dividend uses `ex_dividend_date` as its effective date while retaining
  announcement, record, and pay dates separately.
- JSON numeric values are normalized through the existing Massive Decimal
  boundary before entering financial fields. Binary floats never enter the
  canonical Pydantic contract.
- Ticker resolution is an explicit point-in-time input. One stable ID resolves;
  zero IDs quarantine as unresolved; multiple IDs quarantine as ambiguous.
- The endpoint does not provide a defensible source-publication timestamp, so
  mapped records use `first_observed_only`. They cannot be inserted as facts
  known to an earlier sealed signal.
- A missing or unsafe provider action ID receives a deterministic allowlisted-
  field fingerprint ID and remains quarantined.
- Anchored incomplete rows remain typed quarantine records. Rows without a
  usable ticker, effective/ex date, or supported action type remain explicit
  mapping issues rather than being coerced or silently dropped.

Provider source observations remain separate from canonical Corporate Action
facts and cannot satisfy the canonical research-readiness family.

## Provider adjustment evidence

Provider-reported `historical_adjustment_factor` and
`split_adjusted_cash_amount` are preserved as source evidence, never copied
directly into the WH Alpha Adjustment Ledger. The public documentation defines
the historical factor relative to a later basis and it may be cumulative.

The independent fixture math therefore requires an explicit comparison basis:

- `same_event_and_basis` permits exact/tolerance comparison;
- `cumulative_or_unverified` returns `not_comparable`, not pass or mismatch;
- absent provider evidence returns `unavailable`.

For a split `from -> to`, the post-event-basis price multiplier is
`from / to` and the volume multiplier is `to / from`. The cash-dividend
backward continuity factor is `(same-basis pre-ex close - same-basis cash) /
same-basis pre-ex close`. Tests independently apply and reverse both directions
using deterministic Decimal arithmetic. This is adjusted-price mechanics, not
a return forecast, alpha, option return, or permission to create a real ledger.

## Remaining boundary

- The earlier account probe reached deprecated V3 endpoints only. ADR 0169 now
  separately proves current V1 access and complete real page chains for the
  exact 2025-06-23 through 2026-09-04 range.
- The real source rows have not yet been mapped against event-date Identity;
  adapter integration and append-only revision handling remain absent.
- No provider observation has been promoted into canonical Corporate Action.
- Merger, spinoff, symbol-change, delisting, successor, and terminal-outcome
  sources remain absent.
- General multi-event basis ordering and a canonical adjustment-ledger builder
  remain future work after source governance.
