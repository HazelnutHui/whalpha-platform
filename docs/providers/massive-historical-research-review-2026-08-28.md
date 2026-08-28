# Massive Historical Research Review — 2026-08-28

## Result

`NOT_READY_FOR_PROVIDER_PILOT_AUTHORIZATION`

The public technical surface can plausibly support an owner-only 252-session
EOD/Identity/corporate-action pilot, but three gates remain open:

1. the current individual-use terms do not support an application for other
   end users and restrict third-party display of Market Data and Derived Works;
2. the same terms also restrict non-display/derivative use unless separately
   licensed, so account-specific permission for WH Alpha calculations and
   retention must be clarified rather than inferred;
3. no complete merger, spinoff, successor, and terminal-outcome source has been
   established.

This is an engineering interpretation, not legal advice. No account endpoint,
credential, or provider data was accessed during this review.

## Evidence scope

Official public pages reviewed on 2026-08-28:

- [Stocks pricing](https://massive.com/pricing?product=stocks)
- [Daily Market Summary / Grouped Daily](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary)
- [All Tickers](https://massive.com/docs/rest/stocks/tickers/all-tickers)
- [Splits](https://massive.com/docs/rest/stocks/corporate-actions/splits)
- [Dividends](https://massive.com/docs/rest/stocks/corporate-actions/dividends)
- [Ticker Events](https://massive.com/docs/rest/stocks/corporate-actions/ticker-events)
- [Day Aggregates Flat Files](https://massive.com/docs/flat-files/stocks/day-aggregates)
- [Market Data Terms](https://massive.com/legal/market-data-terms-of-service)

Public documentation can establish advertised plan and endpoint behavior. It
does not verify the user's current account entitlement or replace a bounded
authenticated pilot.

## Current public plan facts

Stocks Basic is publicly listed as free individual use with:

- five API calls per minute;
- two years of historical data;
- end-of-day stock data;
- reference data and corporate actions;
- no Day Aggregates flat-file access.

The Grouped Daily, All Tickers, Splits, and Dividends pages currently show
Stocks Basic access and a two-year history boundary. Grouped Daily is one
broad-market date request and supports `adjusted=false`. All Tickers accepts an
explicit point-in-time `date`, defaults `active=true`, and allows at most 1,000
rows per page. Splits and Dividends are updated daily, allow at most 5,000 rows
per page, and expose source adjustment fields.

These are current public claims, not stored entitlement evidence. Two calendar
years should not be assumed to contain 504 usable XNYS sessions after exact
date boundaries, feature warm-up, and outcome maturity.

## Endpoint assessment

| Need | Proposed public endpoint | Assessment |
| --- | --- | --- |
| Unadjusted full-market EOD | Grouped Daily with exact date and `adjusted=false` | Preferred; one request/session and already verified for bounded current sessions |
| Point-in-time active Identity | All Tickers with exact date, `active=true`, limit 1,000 | Technically suitable; current runs use about 14 pages/session |
| Inactive/delisted observations | All Tickers with exact date, `active=false` | Documented, but historical completeness and efficient cadence are unverified |
| Split/stock-dividend facts | `/stocks/v1/splits` | Preferred over deprecated V3 endpoint; entitlement and mapping unverified live |
| Cash-dividend facts | `/stocks/v1/dividends` | Date-rich and exposes adjustment fields; entitlement and reconciliation unverified live |
| Ticker changes | experimental Ticker Events | Targeted evidence only; currently only ticker-change events and unsuitable for broad bulk lineage |
| Merger/spinoff/successor | no accepted endpoint | Missing hard source |
| Terminal proceeds/outcome | no accepted complete source | Missing hard source |
| Flat-file daily history | Day Aggregates flat files | Not included in Basic; do not build the first plan around S3 |
| Per-ticker Custom Bars | Custom Bars | Fallback for targeted repair only; whole-Universe backfill would be request-inefficient |

## Adjustment semantics

Grouped Daily defaults to split-adjusted output, while WH Alpha's canonical path
explicitly requests `adjusted=false`. The current Splits endpoint documents a
historical price adjustment factor and the Dividends endpoint documents a
separate historical dividend adjustment factor and split-adjusted cash amount.

Those fields are useful source evidence, not automatic canonical truth. The
first adapter must:

- retain raw OHLC unchanged;
- normalize split and dividend events separately;
- define multiplier direction and basis date explicitly;
- reconstruct known provider examples;
- independently recompute factors from event facts;
- quarantine contradictions and missing coverage;
- keep price return and total return distinct.

## Licensing and product compatibility gate

The public Market Data Terms reviewed on 2026-08-28 state that individual-use
Market Data is for personal, non-business, non-commercial use; that an
application may not be intended for end users other than the subscriber; and
that Market Data and Derived Works may not be displayed or transferred to a
third party without permission. They also restrict non-display/derivative use
unless licensed and require deletion of Market Data after account termination.

Engineering consequences:

- Session protection is not a license and does not make friend/guest access an
  owner-only use.
- The active equal-capability guest path is technically working but lacks a
  documented compatible Massive permission for third-party access.
- No additional Massive-backed guest/friend feature or historical publication
  should be activated until written permission, a suitable plan/license, or a
  public-display-compatible alternate source is established.
- Owner-only calculation and long-term retention also need account-specific
  clarification because the terms contain non-display/derivative restrictions.
- “No automatic expiry” in the canonical retention design applies only while
  the source license permits possession; source termination/deletion duties
  override it and require a reviewed deletion/recovery procedure.

This review does not authorize or perform an access change, takedown, data
deletion, or deployment. The user must choose the future product/source path.

## Account entitlement state

Locally verified historical evidence remains limited to:

- bounded All Tickers pagination;
- bounded Grouped Daily retrieval/publication;
- provider security-type evidence.

The current account has not live-verified:

- historical Grouped Daily across the proposed range;
- point-in-time All Tickers at older dates and `active=false` completeness;
- current Splits or Dividends endpoints;
- experimental Ticker Events;
- exact two-year earliest accessible date;
- retention, derived-use, or friend/guest permission.

## Technical conclusion

The EOD and corporate-action API shapes are promising and Basic's request limit
is slow but workable on Dell. Identity pagination, not EOD, is the dominant
runtime. Data-source completeness and permission are the blockers, not Dell
CPU, disk, or Parquet.

The safe next implementation work is fixture-only physical contracts and
readers. A real provider pilot remains blocked until the licensing/product
posture and exact account entitlement are reviewed.
