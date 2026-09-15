# Free Performance-Evidence Source Review — 2026-09-15

## Result

`FREE_COMPOSITION_REMAINS_VALID_FOR_CORROBORATION`

`NO_FREE_SINGLE_SOURCE_PROVEN_FOR_FULL_PERFORMANCE_ADMISSION`

LSEG is optional and no longer treated as a prerequisite. This review used
official public documentation only. It made no credentialed request, received
or retained no provider sample, and changed no canonical or Production state.

## Bounded source roles

| Source | Officially documented capability | Accepted role | Material limit |
| --- | --- | --- | --- |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) and [exchange delistings](https://www.sec.gov/rules-regulations/exchange-delistings) | Free bulk Submissions/Company Facts and Form 25/25-NSE filing access | Filing clock, filer metadata, transaction/termination document evidence | CIK is not a listed-security ID; a filing date does not prove last tradability, consideration, or terminal return |
| [FINRA OTC Daily List](https://otce-dr.finra.org/otce/dailyList?viewType=Symbol%2FName+Changes) | OTC additions, deletions, name/symbol changes and corporate actions | Official OTC continuation and action corroboration | Not complete major-exchange lifecycle, stable identity, source-time history, or terminal payoff authority |
| [OpenFIGI](https://www.openfigi.com/api/documentation) | Free identifier mapping with reusable FIGI symbology | Stable-ID crosswalk and ambiguity detection | Mapping is not effective-dated lifecycle, tradability, reason, successor, or consideration evidence |
| [Alpha Vantage Listing Status](https://www.alphavantage.co/documentation/#listing-status) | Historical active/delisted US stock and ETF lists for dates after 2010-01-01; free key documented | Candidate historical population and delisting-date corroborator | Does not document the complete frozen identity, revision, availability, action, successor, consideration, and terminal semantics; [standard terms](https://www.alphavantage.co/terms_of_service/) limit use to private individual research |
| [Nasdaq Symbol Directory](https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs) | Current, timestamped Nasdaq and other-exchange reference files | Prospective/current reference cross-check | Current-state files are not a complete five-year lifecycle ledger |
| [Nasdaq Daily List](https://classic.nasdaqtrader.com/Trader.aspx?id=DailyListPD) | Historical listings, delistings, symbol/name changes, dividends and splits since 1999 | Potential venue source | It is a subscribed product with agreements and approval, not a free source |
| [QuantConnect dataset licensing](https://www.quantconnect.com/docs/v2/cloud-platform/datasets/licensing) | Most price data can be used free in its cloud; algorithms expose delisting and symbol-change events | Independent cloud backtest/replay comparator | Most datasets cannot be freely redistributed or exported into the Dell security master |

## University access

The University of Utah public database catalog did not expose a current WRDS,
CRSP, or Compustat listing during this review. It does list one on-campus
[Bloomberg Terminal](https://databases.tools.lib.utah.edu/index.php?subjID=8).
This is not proof that school- or faculty-level research access is absent;
academic entitlement remains `unverified` and must not be assumed.

## Decision

1. Preserve the existing SEC and FINRA custody and OpenFIGI identifier role.
2. Evaluate Alpha Vantage only through the frozen provider-neutral acceptance
   contract. A free-key sample may be useful locally, but cannot be promoted
   to shared-product authority from marketing coverage or private-use terms.
3. Treat exchange public pages as targeted corroboration and prospective
   evidence, not as a silent historical backfill.
4. Use QuantConnect only as an independent result comparator unless a separate
   download license and Dell-retention review is passed.
5. Keep unresolved records quarantined. Do not lower complete-session,
   lifecycle, action-neutrality, terminal-outcome, or permission gates.

## Next bounded action

Finish and fixture-test the provider-neutral result evaluator. A later
Alpha Vantage sample requires a locally configured free key, an explicit
request budget, a permission review, and a separate read-only acquisition
authorization. Until such a sample exists, the formal Strong-Leader Pullback
performance decision remains `rejected_data_blocked`.
