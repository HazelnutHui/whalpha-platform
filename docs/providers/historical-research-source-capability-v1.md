# Historical Research Source Capability V1

## Purpose and evidence date

This matrix separates repository-verified capability, publicly documented
potential, live entitlement, and missing implementation for the historical
research foundation.

Repository-verified operational evidence is current through 2026-09-09. The
official-public free-source review is current through 2026-09-15. ADR
0196 makes the Dell-owned rolling five-year foundation and reviewed
Massive/official-free composition the active construction program. The latest
narrow official-public-page reconciliation covers current-session EOD
access on 2026-09-09; the broader source and permission comparison remains
dated 2026-08-28. Later
bounded account operations established technical access and retained source
custody without changing the dated public permission conclusion. Externally
controlled plan, endpoint, price, rate-limit, history, and licensing facts must
still be rechecked before a new source-family acquisition.

On 2026-09-09 the owner supplied a Massive dashboard payment confirmation for
Stocks Starter. This establishes the intended subscription tier from
owner-provided account evidence. A later controlled run verified live API
access, removal of the old Basic request-rate limit, and same-evening Grouped
Daily availability for 2026-09-09. Five-year endpoint completeness and a
guaranteed finality minute remain unverified.

The broader official-source comparison is recorded in the dated
[Equal-Capability Historical Source Review](equal-capability-historical-source-review-2026-08-28.md).
It found no single cleared source and recommends provider-neutral source
composition under Source Permission Governance V1.

The 2026-09-10 Stocks Starter depth probe adds a narrower current result:
Grouped Daily REST denied 2021-09-09 and 2021-09-10 but returned 11,063 rows
for 2022-09-09, while PIT Tickers, splits, and dividends were accessible on all
three dates. Massive's official Day Aggregates Flat Files documentation lists
five-year Starter history and recommends Flat Files for bulk download, so that
becomes the preferred price-backfill route. It requires separate dashboard S3
credentials and has not yet been accessed.

The narrower 2026-09-08
[Lifecycle Corroboration Source Review](lifecycle-corroboration-source-review-2026-09-08.md)
compares current official cross-venue and exchange documentation against the
exact 547-item inactive queue. LSEG was the preferred first inquiry/sample
candidate under ADR 0168, while Nasdaq, NYSE, and Cboe remain official venue
benchmarks. ADR 0196 supersedes that mandatory ordering: LSEG is now a later
measured-gap option. The later first-strategy gate has now measured that gap;
LSEG remains an optional first sample candidate for its exact frozen
population, followed by ICE and then S&P on failure. The owner reported
submitting LSEG contact forms, but no additional cross-venue lifecycle source
has been selected, purchased, accessed, permission-cleared, or implemented.
The 2026-09-15 review confirms that LSEG is optional: the first no-cost
incremental candidate is Alpha Vantage Listing Status, evaluated only as a
private corroborator against the same frozen sample. SEC, FINRA, OpenFIGI, and
exchange evidence retain their narrower roles. No free source or composition
has passed the complete performance-admission gate.

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
| Broad-market daily unadjusted OHLCV | Canonical Grouped Daily `adjusted=false` history contains 306 sessions | Recorded plan descriptions list Basic as end-of-day and Starter as 15-minute delayed with five years of history | Exact 306-session range acquired; a post-upgrade 9/9 request succeeded same evening; five-year depth is untested | `verified_current` for acquired history and one Starter session; expanded depth/finality remain unverified |
| Point-in-time reference Identity | 306 resolved snapshots plus 304 canonical source-observation partitions | Recorded endpoint evidence includes date query, active/inactive filter, identifiers, and pagination | Active acquisition completed with two exact source-observation gaps; inactive source has two retained anchors; post-upgrade daily access succeeded | `verified_current` only for exact acquired scopes; not complete lifecycle coverage |
| Daily Universe Membership | Retrospective mechanics plus three prospective canonical signal-eligible partitions | No provider response can replace WH Alpha methodology | Three physical daily partitions and markers | `derived_required`; historical series remains incomplete |
| Historical security-form evidence | One provider evidence date | Point-in-time reference/type endpoints may supply observations | Historical coverage and revision semantics unverified | `documented_unverified`; cannot backcast current evidence |
| Splits/reverse splits | Bounded source custody and sparse canonical split facts exist | Dated endpoint review recorded ratios and adjustment fields | Source observations, exact-date resolution, 709 split-only fact rows, and sparse affected-path adjustments exist; complete/neutral coverage does not | `verified_current` for the bounded acquired scope; incomplete for research |
| Cash/stock dividends | Bounded source custody and a read-only date/arithmetic diagnostic exist | Dated endpoint review recorded event dates, cash, and adjustment fields | Source observations exist, but date semantics, multi-events, currency, revisions, and total-return authority remain unresolved | `verified_current` source custody; missing as canonical total-return evidence |
| Ticker events/symbol continuity | Ticker Events is documented as experimental and symbol-change-only | May support symbol changes | The fixed 30-item Composite FIGI diagnostic matched 6 instruments, returned 9 `ticker_change` events, and returned HTTP 404 for 24 instruments | `verified_current` as a sparse symbol-change corroborator; rejected as sole lineage source |
| Merger/spinoff/successor lineage | Corporate Action V1 permits relationships | No complete source established | No canonical source or dataset | `missing` |
| Delisting and terminal outcome | Two complete inactive anchors are retained in temporary custody and resolved one-to-one into a shadow | All Tickers exposes substantial delisting metadata | Latest anchor has 547 stable-ID review candidates and 22,922 quarantined rows; ADR 0167 creates an exact corroboration queue, but last tradable session, reason, consideration, successor, and source availability remain unverified | `verified_current` source observation for exact anchors; still missing as evaluation-ready lifecycle |
| Split adjustment | Aggregate defaults and `adjusted=false` behavior are documented | Provider-adjusted history may assist reconciliation | Canonical sparse affected-path ledger exists for outcome reconciliation; omitted-row neutrality is unproven | `verified_current` partial evidence; raw bars remain authoritative inputs |
| Dividend/total-return adjustment | Repository notes aggregate history is not dividend-adjusted while newer dividend docs mention factors | Dividends may support derived factors | Exact semantics and independent reconciliation absent | `missing` as a governed factor series |
| Point-in-time sector/industry | Current repository explicitly lacks it; ADR 0173 and the 2026-09-08 source review define temporal/identity gates | GICS History is the first specification/sample candidate; TRBC second; Massive SIC current-diagnostic only | No source selected, licensed, sampled, acquired, or implemented | `documented_unverified` source potential and `missing` physical data; defensive/fundamental stratification cannot claim taxonomy support |
| Fundamentals and valuation | Explicitly absent | Not evaluated in this slice | No dataset | `not_applicable` to the first technical-history pilot |
| Options/IV/Greeks/OI | Explicitly absent | Separate future provider decision | No dataset | `not_applicable`; stock outcomes remain stock outcomes |

## What Massive can and cannot currently mean

Massive remains the accepted first private EOD development adapter, not a
permanent exclusive source. Repository evidence supports bounded Identity and
Grouped Daily acquisition plus complete inactive-source observation at two
anchors. A 2026-09-10 fixed 30-item Composite FIGI diagnostic also proved that
Ticker Events is only a sparse symbol-change source: six instruments matched,
24 returned HTTP 404, and all nine returned events were `ticker_change`. It
does not yet prove:

- that every required historical Identity source date is retrievable; two
  exact source-observation gaps remain;
- that the newly purchased Starter entitlement supplies complete five-year
  coverage across each required endpoint;
- complete, revision-aware Splits or Dividends coverage beyond the bounded
  acquired query snapshot;
- that inactive/delisted and successor coverage is complete;
- terminal reasons, suspension/resumption history, successor/consideration,
  event revisions, or a source-availability clock;
- that provider adjustment factors meet WH Alpha price/total-return semantics;
- that stored history may be retained or displayed beyond the existing private
  personal-use boundary.

The public Basic-plan history claim remained two years on 2026-08-28. Current
official marketing describes Starter as five years, and the owner supplied a
successful Starter purchase confirmation on 2026-09-09. Exact date boundaries,
endpoint behavior, and completeness are still not current account-entitlement
proof until exercised. Five years can support longer chronological studies but
does not fill the separate membership, lifecycle, corporate-action, adjustment,
cost, or availability families.

The first 2026-09-09 comparison isolated the former date-scoped recency
boundary. The later controlled Starter daily run then proved 14 Identity
requests and one same-evening Grouped Daily request without the Basic pacing
limit. This is a one-session operational observation, not proof of an exact
aggregate-release minute or five-year completeness. No credential rotation or
adapter rewrite is indicated.

The current Market Data Terms add a separate hard product gate: individual-use
data is described as owner-only, third-party Market Data/Derived Works display
is restricted, non-display/derivative use may require a separate license, and
account termination requires deletion. See the dated
[Massive Historical Research Review](massive-historical-research-review-2026-08-28.md).

## Source composition direction

One provider need not supply every family. The canonical design permits:

- Massive or another adapter for EOD and point-in-time reference observations;
- one or more corporate-action sources normalized into Corporate Action V1;
- WH Alpha-derived daily membership under a frozen methodology;
- a separately governed lifecycle reconciliation layer;
- WH Alpha-derived adjustment ledgers with independent cross-source checks.

Provider priority is never resolved by “first non-null value.” The executable
[Source Resolution Governance V1](../data-contracts/source-resolution-governance-v1.md)
now binds precedence, evidence roles, permission-review fingerprints,
corroboration thresholds, and fail-closed conflict handling per family and fact
scope. No real source policy is selected or activated.

For lifecycle corroboration, do not implement an adapter until a real licensed
sample proves its identifiers, revisions, availability clocks, terminal terms,
delivery mechanics, and permitted uses. Start the commercial/sample comparison
with a cross-venue source to minimize fragmentation, then use exchange sources
as authoritative benchmarks or bounded corroborators. This ordering does not
weaken stable-ID or family-specific resolution gates.

Free sources should be evaluated before paid expansion, but no one free source
is promoted to sole authority. ADR 0196 assigns initial bounded roles to SEC
EDGAR, FINRA OTC Daily List/notices, OpenFIGI, Alpha Vantage Listing Status,
Nasdaq Trader current Symbol Directory, and named issuer/venue evidence. Each
role remains narrower than the source's marketing description and must pass a
fixture-first pilot. A paid source should later plug into the same provider-
neutral observations and must expand measured coverage rather than replace
canonical identities or rewrite history.

The dated
[Free Performance-Evidence Source Review](../audits/free-performance-evidence-source-review-2026-09-15.md)
records the current official capabilities and permissions. Alpha Vantage
documents historical active/delisted population queries after 2010 through a
free-key endpoint, but does not document all frozen stable-ID, revision,
availability, action, successor, consideration, last-tradable, and terminal
semantics. Its standard terms also remain private-individual rather than shared
product permission. It may therefore be tested as corroboration, not presumed
to be a sole source or publication authority.

The retained official FINRA OTC Daily List implementation covers 2021-08-11
through 2026-09-09 in 62 monthly packages / 68,714 observations. It is
`official_otc_corroboration_only`: four repeated source identifiers remain
distinct occurrences, ticker never creates stable identity, and the source
does not establish complete major-exchange lifecycle, original availability,
successor, consideration, last trade, or terminal return. The network-free
FINRA/Massive census found 2,298 unique numeric split candidates and 8,205
unique numeric dividend candidates; all remain candidate corroboration with
zero stable-ID resolution.

The official SEC Company Facts and Submissions bulk snapshots are also
retained and fully payload-censused. The composed source covers 41,619,407
five-year fact occurrences / 172,265 accessions; 172,262 accessions have
conservative acceptance-time clocks and three remain quarantined. The sparse
normalized occurrence ledger preserves amendments and availability rather
than projecting current values backward. CIK remains a filer key, so a
complete effective-dated filer/security link and registered concept, unit,
period, form, and projection methods are still required before security-level
fundamental features are admitted. ADR 0215 governs this retained foundation.

## Optional source-response packet

The repository now contains a
[Source Selection and Permission Inquiry Packet V1](source-selection-permission-inquiry-packet-v1.md)
covering the commercial and open-source questions below. LSEG contact is
owner-reported submitted, but none of the exact questions has a reviewed
response; other inquiries remain prepared and unsent. Before a pilot, the
reviewed response must contain:

- official source URLs and review timestamp;
- current account plan and endpoint entitlement without exposing credentials;
- exact endpoint, parameters, adjusted/unadjusted semantics, and pagination;
- proposed pilot dates and representative action/lifecycle cases;
- worst-case request count, fixed pacing, no-concurrency rule, and retry limit;
- expected rows and storage bytes;
- raw-response retention and licensing decision;
- canonical mapping, contradiction, quarantine, and completion gates;
- explicit list of gaps that remain after the pilot.

The packet is a review artifact, not standing authority or a prerequisite for
outcome-blind method engineering. For eventual performance admission, any
candidate source must address the measured lifecycle/action gap against the
same frozen gates. Provider response review, purchase, access, pilot
execution, and canonical Apply remain separately governed transitions.
