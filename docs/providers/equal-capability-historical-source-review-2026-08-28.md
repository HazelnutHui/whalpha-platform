# Equal-Capability Historical Source Review — 2026-08-28

## Result

`NO_SINGLE_SOURCE_CLEARED`

`HYBRID_SOURCE_PATH_RECOMMENDED`

This is an engineering and product-permission review, not legal advice. It used
only official public pages and existing repository evidence. No provider
account, credential, endpoint, data, Git remote, OCI, or production website was
accessed.

## Fixed product requirement

Guest and credential Sessions receive identical shared data, functions,
language, Universe, and analysis. A source that does not permit that use stays
out of the shared product for both paths. Owner-only market analysis is not a
fallback.

## Official-source matrix

| Source | Useful role | Permission conclusion | Coverage and evidence limit | WH Alpha disposition |
| --- | --- | --- | --- | --- |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) and [reuse policy](https://www.sec.gov/about/webmaster-frequently-asked-questions) | Submission history, XBRL fundamentals, filings and event evidence; bulk submissions and Company Facts | SEC states Government-created and public EDGAR filing content is free to access and reuse. Automated use must declare a User-Agent and remain within fair-access limits. | CIK identifies a filer, not a listed security. Ticker/exchange metadata and filings do not alone prove security identity, issuer operating structure, last tradable session, or complete merger successor lineage. | Preferred open filing/fundamental/event evidence source after separate SEC operational authorization; never the sole security identity or lifecycle authority. |
| [Nasdaq Symbol Directory](https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs) | Current Nasdaq-listed and other-exchange symbol/reference snapshot with creation timestamp | Public definitions and current files are documented; long-term retention and equal-capability derived/display use were not explicitly cleared in this review. | Updated during the day and primarily current-state; it is not the complete historical corporate-action ledger. Ticker remains display metadata. | Candidate current reference cross-check only; permission and historical completeness unresolved. |
| [Nasdaq Daily List](https://www.nasdaqtrader.com/Trader.aspx?id=DailyListPD) | New listings, delistings, name/symbol changes, dividends and splits; history since 1999 | Monthly subscription. Firms require forms, a Global Data Agreement, prior approval, and a System Application when displayed or used in an unapproved system. CUSIP adds a separate license. | Nasdaq coverage, not a complete all-exchange merger/successor truth by itself. | Strong corporate-action/lifecycle candidate if later licensed and reconciled; not a free or currently cleared source. Use the no-CUSIP form unless a CUSIP license is separately established. |
| [GLEIF LEI data](https://www.gleif.org/en/meta/lei-data-terms-of-use) | Open legal-entity identity, entity status/relationships, historical and delta files | Data is provided under CC0. | LEI identifies a legal entity, not an exchange-listed security; coverage is application-driven and GLEIF disclaims completeness/accuracy guarantees. | Cleared candidate issuer crosswalk/evidence source, never a replacement for stable `instrument_id` or listing lifecycle. |
| [OpenFIGI](https://www.openfigi.com/docs/terms-of-service) | Open financial-instrument identifier and mapping support | FIGI identifiers may be used, displayed, reproduced, distributed, and used in derived works. | Related security descriptions are provided as-is; mapping coverage, history, ticker reuse, and point-in-time availability still require validation. | Cleared identifier candidate, but not yet a canonical identity or historical lifecycle source. |
| Massive | Existing bounded private EOD and Identity adapter; technically plausible historical EOD/split/dividend candidate | Existing dated review finds owner-only and Derived Works/display restrictions incompatible with shared equal-capability use; Dell retention/non-display use also needs clarification. | Current live historical/corporate-action entitlement and complete inactive/delisted/successor coverage are unverified. | Keep as blocked private-research candidate pending written permission; no shared publication and no historical pilot. |
| [Alpaca](https://alpaca.markets/disclosures) | Brokerage-linked market data and future IBKR-independent reference comparison | Alpaca's customer market-data agreement restricts reproduction, distribution, sale, or commercial exploitation without written consent and incorporates exchange display agreements. | Brokerage entitlement is user access, not WH Alpha redistribution permission; no reviewed lifecycle completeness. | Reject the standard customer path as a shared-product fallback; reconsider only under a specific written data agreement. |
| [Alpha Vantage](https://www.alphavantage.co/terms_of_service/) | EOD and other API data candidate | Standard grant is personal, non-commercial use on a device the user owns or controls; activity beyond private individual research requires a separate written arrangement. | No reviewed point-in-time identity, complete lifecycle, or suitable equal-capability grant. | Reject the standard/free path for the shared product; no implementation work. |
| [Twelve Data](https://twelvedata.com/terms) | Potential EOD replacement adapter; official support states full-market U.S. EOD is available after midnight ET | Default license is internal use. External display or redistribution requires a Redistribution Rights Add-On or separate agreement; termination requires deletion of data. | Official coverage claims are not live account or quality verification. Point-in-time identity and complete lifecycle remain separate gaps. | Worth a future pricing/permission inquiry because it has an explicit redistribution path; not currently cleared and not a free equal-capability solution. |

## Architecture conclusion

Do not search for one provider that silently becomes the truth for every
family. Use a provider-neutral, evidence-tiered composition:

1. SEC for reusable filing, fundamental, and issuer-event evidence.
2. GLEIF and OpenFIGI as crosswalk evidence, never ticker-based canonical keys.
3. A separately licensed EOD source for raw bars and displayed/derived market
   analytics.
4. Exchange-grade action/listing evidence, potentially Nasdaq Daily List plus
   equivalent non-Nasdaq coverage, normalized into Corporate Action V1.
5. WH Alpha canonical resolution for stable-ID lifecycle, daily Universe
   membership, adjustment ledgers, contradictions, and quarantine.

No source wins by first non-null value. Source precedence is family-specific;
conflicts remain visible and unresolved records stay quarantined.

## Immediate decisions

- Do not authorize the Massive historical pilot.
- Do not build Alpha Vantage or Alpaca as fallback shared-product adapters.
- Treat Twelve Data only as a future commercial-permission inquiry, not a
  selected provider.
- SEC/GLEIF/OpenFIGI adapters may be designed later against fixtures, but real
  access, acquisition, and physical storage remain separately authorized.
- Preserve the 252-session floor and 504-session target. Source composition
  does not weaken point-in-time membership, lifecycle, adjustment, or
  survivorship gates.

## Next exact review packet

Before source implementation, obtain one written table that answers for each
candidate plan: Dell acquisition, indefinite canonical retention, raw and
derived computation, identical guest/credential display, JSON/browser
delivery, attribution, deletion on termination, historical depth, corporate
action coverage, and price-adjustment semantics. Then create a
`SourcePermissionReviewV1` evidence package and assess only the exact data
families and uses requested.
