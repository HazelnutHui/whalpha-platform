# Historical Research Source Capability V1

## Purpose and evidence date

This matrix separates repository-verified capability, publicly documented
potential, live entitlement, and missing implementation for the historical
research foundation.

It uses only evidence already recorded in the repository through 2026-08-27.
No documentation site, provider, credential, or network endpoint was accessed
for this matrix. Externally controlled plan, endpoint, price, rate-limit,
history, and licensing facts must be freshly reviewed before acquisition.

## Status meanings

- `verified_current`: exercised by the bounded current pipeline.
- `documented_unverified`: repository records official documentation, but the
  required endpoint/date range/entitlement has not been exercised.
- `derived_required`: WH Alpha must calculate a canonical decision from
  governed inputs; no provider payload is the final authority.
- `missing`: no credible source or implementation has been established.
- `not_applicable`: deliberately outside this history slice.

## Capability matrix

| Required family | Repository evidence | Massive potential recorded in repository | Live/physical state | Current conclusion |
| --- | --- | --- | --- | --- |
| Broad-market daily unadjusted OHLCV | Grouped Daily `adjusted=false` published 29 sessions | Grouped Daily and Custom Bars documented; Basic previously listed two years history | Grouped Daily current-session path verified; Custom Bars and broad historical entitlement unverified | `verified_current` for bounded daily sessions; `documented_unverified` for 252/504 backfill |
| Point-in-time reference Identity | All Tickers pagination produced 30 dated snapshots | Date query, active/inactive fields, identifiers, delisting metadata documented as potential inputs | Current dated snapshots verified; historical inactive/delisted completeness not verified | `verified_current` for snapshot mechanics; insufficient for lifecycle history |
| Daily Universe Membership | One active Activation and one full-base decision session | No provider response can replace WH Alpha methodology | No physical daily dataset | `derived_required` and a hard blocker |
| Historical security-form evidence | One provider evidence date | Point-in-time reference/type endpoints may supply observations | Historical coverage and revision semantics unverified | `documented_unverified`; cannot backcast current evidence |
| Splits/reverse splits | Corporate actions listed in recorded Basic plan/docs | Current Splits endpoint documented | No adapter, request, entitlement test, or dataset | `documented_unverified` |
| Cash/stock dividends | Corporate actions listed in recorded Basic plan/docs | Current Dividends endpoint documented | No adapter, request, entitlement test, or dataset | `documented_unverified` |
| Ticker events/symbol continuity | Ticker Events documentation recorded as experimental | May support symbol changes | No request, mapping, or reliability review | `documented_unverified`; cannot be sole lineage source |
| Merger/spinoff/successor lineage | Corporate Action V1 permits relationships | No complete source established | No canonical source or dataset | `missing` |
| Delisting and terminal outcome | Current snapshots expose no retained inactive/delisted rows or terminal dates | All Tickers may expose status and delisting metadata | Completeness, cash consideration, last tradable session, and successor coverage unverified | `missing` as an evaluation-ready source |
| Split adjustment | Aggregate defaults and `adjusted=false` behavior are documented | Provider-adjusted history may assist reconciliation | Canonical factors are unverified all-one; no action ledger | `documented_unverified`; raw bars remain authoritative inputs |
| Dividend/total-return adjustment | Repository notes aggregate history is not dividend-adjusted while newer dividend docs mention factors | Dividends may support derived factors | Exact semantics and independent reconciliation absent | `missing` as a governed factor series |
| Point-in-time sector/industry | Current repository explicitly lacks it | No accepted source selected | No dataset | `missing`; defensive/fundamental stratification cannot claim taxonomy support |
| Fundamentals and valuation | Explicitly absent | Not evaluated in this slice | No dataset | `not_applicable` to the first technical-history pilot |
| Options/IV/Greeks/OI | Explicitly absent | Separate future provider decision | No dataset | `not_applicable`; stock outcomes remain stock outcomes |

## What Massive can and cannot currently mean

Massive remains the accepted first private EOD development adapter, not a
permanent exclusive source. Repository evidence supports bounded Identity and
Grouped Daily mechanics. It does not yet prove:

- that the current account can retrieve every required historical date;
- that 252 or 504 sessions can be acquired through an efficient endpoint;
- that corporate-action endpoints are included in the current live account;
- that inactive/delisted and successor coverage is complete;
- that provider adjustment factors meet WH Alpha price/total-return semantics;
- that stored history may be retained or displayed beyond the existing private
  personal-use boundary.

The recorded Basic-plan history claim was two years as of 2026-08-27. That
could cover the 252-session floor and approach the 504-session target if the
exact date boundary, entitlement, endpoint behavior, retention, and
completeness are verified. It is not enough for long-cycle research and is not
a current entitlement assertion.

## Source composition direction

One provider need not supply every family. The canonical design permits:

- Massive or another adapter for EOD and point-in-time reference observations;
- one or more corporate-action sources normalized into Corporate Action V1;
- WH Alpha-derived daily membership under a frozen methodology;
- a separately governed lifecycle reconciliation layer;
- WH Alpha-derived adjustment ledgers with independent cross-source checks.

Provider priority is never resolved by “first non-null value.” Every canonical
family needs source precedence, contradiction handling, evidence quality, and
quarantine rules before physical publication.

Free sources should be evaluated before paid expansion, but this document does
not guess which free source is complete enough. A paid source should later plug
into the same provider-neutral observations and must expand coverage rather
than replace canonical identities or rewrite history.

## Required next review packet

Before a pilot, produce one bounded packet containing:

- official source URLs and review timestamp;
- current account plan and endpoint entitlement without exposing credentials;
- exact endpoint, parameters, adjusted/unadjusted semantics, and pagination;
- proposed pilot dates and representative action/lifecycle cases;
- worst-case request count, fixed pacing, no-concurrency rule, and retry limit;
- expected rows and storage bytes;
- raw-response retention and licensing decision;
- canonical mapping, contradiction, quarantine, and completion gates;
- explicit list of gaps that remain after the pilot.

The packet is a review artifact, not standing authority. Provider access and
canonical Apply remain separately authorized transitions.
