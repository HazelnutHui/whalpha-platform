# Lifecycle Corroboration Source Review — 2026-09-08

## Result

`SAMPLE_REQUIRED_BEFORE_ADAPTER`

`LSEG_FIRST_INQUIRY_CANDIDATE_NOT_SELECTED`

This is an official-public-material capability review, not a legal opinion,
license approval, purchase, account-entitlement test, or data acquisition. No
provider account, credential, API, SFTP service, vendor contact form, Git
remote, OCI host, Production website, or canonical `/data` path was accessed.

## Evidence to close

The exact ADR 0167 queue contains 547 unique canonical instruments: 271 XNAS
and 276 across ARCX, BATS, XASE, and XNYS. Every item still needs:

1. effective-date corroboration;
2. last tradable session;
3. source-published/source-available semantics;
4. successor and consideration applicability/facts; and
5. terminal classification.

The queue's provider `last_updated_utc` is not accepted as source availability.
Ticker, name, exchange locator, disappearance from a snapshot, and the last
available EOD bar are not positive lifecycle proof.

## Official-source capability map

| Candidate | Publicly documented useful scope | Material limitation before use | Review role |
| --- | --- | --- | --- |
| [LSEG Corporate Actions](https://www.lseg.com/en/data-catalogue/corporate-actions) and [reference-data overview](https://www.lseg.com/en/data-analytics/market-data/data-analytics-pricing/reference-data/corporate-actions) | Cross-venue corporate actions, deep history, trading-status events, and REST/SFTP/bulk delivery are documented | Exact licensed schema, identifiers, revision clocks, last-trade semantics, consideration detail, price, retention, derived-display use, and account entitlement are unverified | Preferred first inquiry and sample candidate; not selected |
| [Nasdaq Daily List](https://www.nasdaqtrader.com/Trader.aspx?id=DailyListPD) and [specification](https://nasdaqtrader.com/content/technicalSupport/specifications/dataproducts/dlcompletespec.pdf) | Nasdaq listing/delisting, symbol/name changes and other actions; effective dates, event types, delisting reasons, first-date-traded fields, and history back to 1999 are documented | Paid agreement/approval path; Nasdaq venue scope; CUSIP use requires separate licensing; availability/revision and complete successor/consideration semantics need a real sample | XNAS official benchmark and possible corroborator |
| [Nasdaq Trading Halt Search](https://www.nasdaqtrader.com/Trader.aspx?id=TradingHaltSearch) and [halt RSS](https://www.nasdaqtrader.com/Trader.aspx?id=TradeHaltRSS) | Halt/status evidence and historical lookup are publicly described | Free search is limited to the prior year, shorter than the current candidate interval beginning 2025-07-01; retention and complete historical status semantics remain unproven | Supplemental last-tradable/status evidence only |
| [NYSE Corporate Actions](https://www.nyse.com/market-data/corporate-actions), [catalog](https://www.nyse.com/data-products/catalog/corporate-actions-for-nyse-group-listings), and [Market Event Feed](https://www.nyse.com/market-data/corporate-actions/market-event-feed) | NYSE Group listings, including suspensions/delistings and reorganizations, with file/API delivery are documented | Paid access; payload identifiers, publication clocks, corrections, terminal terms, permission, and exact historical completeness require review | ARCX/XASE/XNYS official benchmark and possible corroborator |
| [Cboe BZX Listings, Distributions and Corporate Actions](https://datashop.cboe.com/listings-distributions-and-corporate-actions), [specification](https://www.cboe.com/document/tech-spec/document/technical-specifications/cboe-bzx-exchange-u.s.-listing-corporate-actions-specification), and [pending suspensions/delistings](https://www.cboe.com/us/equities/listings/listed_products/suspensions_delistings/) | BZX action IDs, status/revision fields, effective dates, delisting/merger/name-change events, daily delivery, and history from 2012 are documented | Paid dataset; current web list is not a complete historical structured source; identifier licensing, availability clock, terminal terms, and permissions require review | BATS official benchmark and possible corroborator |
| [ICE Reference Data Corporate Actions](https://www.ice.com/publicdocs/ICE_Reference_Data_Corporate_Actions_via_ISO15022.pdf) | Standardized global corporate-action aggregation and flexible delivery are documented | Exact U.S. lifecycle depth, security crosswalk, timestamps, sample, price, and license not reviewed | Secondary consolidated-source candidate |
| [S&P Global Market Intelligence Corporate Actions](https://www.spglobal.com/market-intelligence/en/solutions/mca) | Normalized multi-source event terms, dates, options, and validation are documented | Exact lifecycle/status scope, stable-ID crosswalk, timestamps, sample, price, and license not reviewed | Secondary consolidated-source candidate |

## Why the first sample is cross-venue

A single normalized cross-venue input could cover all five exchange locators
through one contract and one adapter while the exchange feeds independently
test high-risk facts. That is operationally smaller than beginning with three
venue-specific production adapters. It is acceptable only if the consolidated
source preserves source provenance and revisions rather than hiding conflicts.

LSEG is first in the inquiry order because its public materials describe the
broadest combination of venue coverage, history, corporate actions, trading
status, and machine delivery relevant to the current gaps. The evidence does
not prove it is more accurate, licensed for WH Alpha, affordable, or complete.

## Deterministic diagnostic sample

The exact ADR 0167 plan is the sampling frame. Define two gap classes between
the candidate effective date and the last canonical Identity observation:
`same_day` and `one_to_seven_days`. For every non-empty
`exchange_locator x effective_year x gap_class` stratum, select the earliest
and latest record ordered by `(candidate_effective_date, instrument_id)`.

Current stratum census:

| Exchange | 2025 / 1–7 days | 2026 / 1–7 days | 2026 / same day | Diagnostic items |
| --- | ---: | ---: | ---: | ---: |
| ARCX | 45 | 44 | 3 | 6 |
| BATS | 33 | 51 | 2 | 6 |
| XASE | 5 | 4 | 2 | 6 |
| XNAS | 102 | 156 | 13 | 6 |
| XNYS | 36 | 49 | 2 | 6 |
| **Total** | **221** | **304** | **22** | **30** |

The resulting diagnostic set has six items per exchange, ten effective in
2025, twenty effective in 2026, and 21 unique effective dates. It deliberately
tests edges across venue, year, and observation gap. It cannot estimate full
547-item coverage or error rates.

## Required sample package

Before coding, retain a reviewed, non-secret description of:

- exact product, version, delivery route, historical range, sample cutoff, and
  whether the sample is production-representative;
- all security identifiers and their licensing restrictions;
- action/event identifier, type, effective/announcement dates, status,
  cancellation, corrections, and complete revision behavior;
- source-published/source-available fields and their formal semantics;
- suspension, resumption, transfer, and last-tradable evidence;
- predecessor/successor identifiers, cash/stock consideration, exchange ratio,
  and explicit not-applicable representation;
- request/file pagination, limits, pacing, and reproducible bounded retrieval;
- Dell retention, non-display research, derived-work, equal guest/credential
  display, attribution, redistribution, and termination/deletion terms; and
- price and ongoing operational obligations.

Do not retain credentials, account identifiers, authorization headers, private
keys, or unrestricted raw sample bodies in Git.

## Acceptance and failure classification

The 30-item run must produce one explicit reconciliation row per requested
canonical instrument. `matched`, `not_covered`, `ambiguous`, `conflict`, and
`missing_required_semantics` remain different outcomes.

`sole_primary_candidate` requires all 30 items to pass stable-ID identity and
every mandatory semantic gate. This is a diagnostic qualification, not proof
of population completeness. A useful source that misses a scope is only
`corroborator_only`; its missing facts require another governed source.

Any ticker/name-only positive match, false stable-ID match, silent omission,
undocumented replacement of revisions, fabricated availability clock, or
permission incompatibility is a stop condition for the proposed role. Source
disagreement remains explicit and unresolved rather than first-non-null.

Last tradable session is derived only from canonical EOD plus authoritative
status/halt/suspension evidence. A delisting effective date or last observed bar
cannot be silently relabeled as the last tradable date. Information published
after a session close cannot enter that close's signal and is first eligible at
the next governed cutoff.

## Next authorized boundary

Prepare a price/sample/permission comparison for the LSEG candidate and, if
needed, the ICE and S&P alternatives. Show the user the exact cost, licensed
uses, delivery, identifiers, and remaining gaps before any commitment. After a
sample is explicitly provisioned, formalize the 30-item pilot request ceiling
from its actual delivery mechanics and only then implement a fixture-first
adapter.

No contact, purchase, trial activation, account access, acquisition, canonical
Apply, or lifecycle promotion is authorized by this review.

