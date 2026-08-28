# Massive Stocks Basic Evaluation

## Purpose

This document records the official-source evaluation for using Massive Stocks Basic as the first EOD development provider for Trading Intelligence Platform.

## Status

Accepted for Private EOD Development — Bounded Identity and EOD Workflows Verified

## Last Reviewed

2026-08-28

## Official Sources

- [Stocks pricing](https://massive.com/pricing?product=stocks)
- [Market Data Terms of Service](https://massive.com/legal/market-data-terms-of-service)
- [Stocks REST API overview](https://massive.com/docs/rest/stocks)
- [All Tickers](https://massive.com/docs/rest/stocks/tickers/all-tickers)
- [Custom Bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- [Daily Market Summary / Grouped Daily Bars](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary)
- [Day Aggregates Flat Files](https://massive.com/docs/flat-files/stocks/day-aggregates)
- [Stock adjustment FAQ](https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends)
- [Splits](https://massive.com/docs/rest/stocks/corporate-actions/splits)
- [Dividends](https://massive.com/docs/rest/stocks/corporate-actions/dividends)
- [Ticker Events](https://massive.com/docs/rest/stocks/corporate-actions/ticker-events)
- [Contact](https://massive.com/contact)

## Plan Summary

Public Plan Information rechecked on 2026-08-27:

- plan: Stocks Basic
- price: USD 0/month
- use category shown by pricing page: individual use
- rate limit: 5 API calls per minute
- history: 2 years of historical data
- coverage: all U.S. stock tickers and 100% market coverage as stated on the public pricing page
- recency: end-of-day data
- included categories: reference data, corporate actions, technical indicators, minute aggregates

These facts are externally controlled. They must be rechecked before implementation, plan changes, credential creation, deployment, or public release.

## Technical Fit

Massive Stocks Basic is suitable as the first private EOD development provider candidate because it provides public documentation for reference tickers, EOD aggregate bars, corporate actions, and endpoint-level plan access. It fits the currently implemented provider capabilities:

- `instrument_master`
- `eod_price_bars`

It does not remove the provider-neutral boundary. Massive response schemas must be mapped into canonical contracts before analytics or dashboard logic consumes data.

## Instrument Master Mapping Potential

The All Tickers endpoint can provide candidate inputs for Instrument Master mapping, including ticker, name, market, primary exchange, currency, active status, CIK when available, Composite FIGI when available, Share Class FIGI when available, ticker type, delisting metadata when available, point-in-time date query, active/inactive filtering, and pagination.

Mapping rules:

- Massive ticker must not become the internal `instrument_id`.
- Internal `instrument_id` remains a canonical UUID.
- FIGI, CIK, source ticker, and source provider identifiers can be identity-resolution inputs.
- CUSIP may be accepted as a query condition by the provider, but the All Tickers documentation states it is not returned in responses for legal reasons.
- The adapter must resolve ticker changes and identity continuity explicitly.
- Exact identity-resolution methodology remains a deferred implementation detail.

## EOD Bar Access Strategy

Candidate endpoints:

- Daily Market Summary / Grouped Daily Bars for one-date broad-market EOD retrieval
- Custom Bars for ticker/date-range historical bars
- Previous Day Bar for limited single-ticker checks
- Daily Open/Close for specific ticker/date checks

Initial recommendation:

- Evaluate Grouped Daily as the daily increment path because it can reduce request pressure under the 5 calls/minute Basic limit.
- Use Custom Bars for targeted historical backfill.
- Do not scan the whole universe with per-ticker Previous Day requests.
- Do not use snapshot endpoints as canonical EOD bars.

This was the initial evaluation direction. Subsequent separately authorized operations verified Grouped Daily access and published bounded canonical EOD sessions; Custom Bars, corporate actions, and general history entitlement remain unverified.

## Corporate Actions

The public pricing page lists corporate actions in Stocks Basic. Current official documentation includes newer Splits and Dividends endpoints and also documents deprecated split/dividend endpoints.

Implementation direction:

- Prefer current non-deprecated Splits and Dividends endpoints when implementing a future adapter.
- Do not use deprecated split/dividend endpoints as the first implementation target.
- Ticker Events may help identity continuity, but the endpoint is marked experimental.
- Corporate Action V1 now has a provider-neutral typed source-observation
  contract, but no Massive adapter, PyArrow repository, or completed dataset.
- The provider Protocol is not expanded in this evaluation.

## Adjustment Semantics

Massive aggregate documentation states that aggregate responses are adjusted for splits by default and can request unadjusted responses with `adjusted=false`. The stock adjustment FAQ states that historical market data is split-adjusted by default and not dividend-adjusted.

Canonical direction:

- Map canonical raw OHLC preferentially from unadjusted aggregate responses.
- Keep raw OHLC, split adjustment factors, dividend adjustment factors, total-return adjustment factors, and adjusted close conceptually separate.
- Use corporate-action data to support adjustment factors.
- Do not treat provider adjusted close as the only source of truth.
- Reconcile aggregate adjustment behavior with newer dividend adjustment-factor documentation during adapter implementation.

Implementation-time verification required: newer Dividends documentation references adjustment factors, while the FAQ states aggregate history is not dividend-adjusted.

## Rate Limit Impact

The 5 calls/minute Basic limit is acceptable for initial development, schema mapping, reference-data tests, EOD prototype work, limited historical backfill, and small controlled validation runs.

Limitations:

- Whole-market per-ticker daily requests are not suitable as the daily workflow.
- Grouped/bulk endpoints should be preferred where available.
- All Tickers pagination must be handled.
- Large per-ticker detail backfills will be slow.
- Retry, request pacing, and resumability are adapter requirements.

Future adapter requirements:

- respect 5 calls/minute
- central request pacing
- retry-after handling
- no concurrency bursts
- resumable backfill
- idempotent ingestion
- request audit without secrets

The public Grouped Daily documentation does not guarantee a precise
post-close stable-publication minute. Provider readiness must therefore remain
separate from exchange close and use bounded operational evidence rather than
an inferred availability promise.

## History Limit

Stocks Basic is currently listed with 2 years of historical data. This is enough for development and initial validation, but not enough for long-term regime research or full historical market-structure studies.

## Flat File Availability

The Day Aggregates Flat Files documentation lists Stocks Basic as not included. Initial implementation should use REST API, not S3 or flat-file architecture. A paid Starter or higher plan may be evaluated later if flat files become important.

## Licensing Boundary

Operational Interpretation — Not Legal Advice.

Massive Market Data Terms restrict Market Data use to personal, non-business,
non-commercial, non-transferable use under the applicable agreement. The
2026-08-28 review found explicit language prohibiting an application intended
for end users other than the subscriber and third-party display/transfer of
Market Data or Derived Works. The terms also restrict non-display/derivative
use unless licensed and require deletion of Market Data after account
termination.

Accepted engineering boundary:

- Massive-backed real-data pages are private-owner only unless a suitable authorization or license is obtained.
- Session protection or a “friends only” guest link does not make another end
  user an owner-only use.
- Provider-backed API responses must be protected before deployment.
- Public static exports must not contain restricted provider data or provider-derived analytics.
- Public demos must use synthetic/demo fixtures or data with explicit public-display rights.
- Public release requires terms review and, where appropriate, legal/compliance review.
- Owner-only research calculation and long-term retention require
  account-specific permission clarification before historical expansion.

## Deployment Implications

The workstation remains the source of truth for provider access, data processing, and derived results. OCI remains a lightweight public serving layer.

The personal-prototype path subsequently selected and implemented a server-side
Session boundary plus equal-capability guest entry for static Dashboard
snapshots. The guest behavior is technically active but is not compatible with
the currently documented owner-only Massive boundary absent express permission
or an alternate source. This document authorizes no access or deployment
change. See the dated
[historical research review](massive-historical-research-review-2026-08-28.md).

## Public Demo Boundary

A public data-free portfolio demo may be built later only if it uses clearly marked synthetic/demo fixtures or a data source with explicit public-display rights. It must not imply live or real market state and must remain separated from the private real-data dashboard.

## Private Dashboard Requirement

The private real-data dashboard must be intended only for the owner, protected by effective access control, not publicly indexable, and not exposed through unrestricted public endpoints or static exports containing restricted data or derived analytics.

## Account Entitlement Status

Stocks Reference, All Tickers, and Grouped Daily Bounded Access Verified.

A protected credential file was provisioned outside Git by the user. The initial one-request Stocks reference smoke test succeeded. Later separately authorized bounded operations exercised All Tickers pagination, Grouped Daily inspection/publication, and security-type evidence endpoints. These operations do not verify Custom Bars, corporate actions, full history depth, general rate-limit behavior, or public-display permission.

## Implementation Status

A one-request Grouped Daily inspection for 2026-08-13 verified access and payload structure without persisting raw data or canonical records. After Instrument Master snapshot publication and Decimal volume correction, the authorized 2026-08-13 Grouped Daily ingestion published canonical EOD bars.

- API key configured outside Git in the protected workstation credential file
- mocked adapter skeleton implemented
- secure credential-file loader implemented
- minimal standard-library HTTPS transport implemented
- one read-only Stocks reference smoke test succeeded
- bounded All Tickers Instrument Master, provider identity, and ticker resolver publication implemented
- bounded Grouped Daily publication implemented; completed EOD sessions cover 2026-07-17 through 2026-08-26
- provider security-type catalog, observation, canonical evidence, and logical completion implemented for 2026-08-14
- canonical Parquet persistence, private analytics APIs, Dashboard snapshots, and versioned static bundle workflow implemented
- Git records private authenticated static Dashboard deployments; current OCI health was not checked for this status reconciliation
- no automated daily ingestion, corporate-action ingestion, or unrestricted public provider-backed serving

## Risks

- Pricing, terms, endpoint availability, coverage, and entitlement can change.
- The Basic rate limit can slow historical backfill.
- Two years of history is not enough for long-term regime research.
- Identity continuity across ticker changes is non-trivial.
- Adjustment semantics require implementation-time verification.
- Public display of provider-backed derived works is restricted unless separately authorized.

## Open Questions

- Rate limiter implementation
- Historical backfill strategy
- Adjustment reconciliation
- Identity-resolution methodology
- Public demo data source
- Plan upgrade threshold
- Business/display/redistribution license threshold

## Re-evaluation Triggers

Re-evaluate before:

- expanding the Massive adapter beyond the currently verified bounded endpoints
- changing credential storage or service injection
- changing plan
- deploying real provider-backed data
- publishing provider-derived content
- relying on flat files
- changing public/private access posture

Re-evaluate if Massive pricing, terms, endpoint access, or documentation changes.

## Recommendation

Keep future Massive operations separately authorized and bounded. The next provider work is not another exploratory Grouped Daily request: historical backfill, automation, corporate actions, new endpoints, or broader display rights each require their own reviewed boundary. Ordinary development and tests must remain fixture/fake-transport based.
