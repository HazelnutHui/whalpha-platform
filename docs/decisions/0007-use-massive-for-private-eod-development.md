# 0007: Use Massive for Private EOD Development

> The initial private-owner serving boundary below is historical. ADR 0019 and
> ADR 0052 now require identical guest/credential shared content and prohibit an
> owner-only market-analysis tier. Massive remains a private Dell development
> source candidate, but it is not cleared for future equal-capability web
> publication without compatible permission or replacement.

## Status

Accepted

## Date

2026-08-14

## Context

Trading Intelligence Platform needs a first real EOD provider candidate so the next implementation work can be scoped against actual endpoint shape, coverage, entitlement, rate limits, and licensing constraints. The project already has provider-neutral canonical contracts and a minimal synchronous MarketDataProvider boundary, but no real provider adapter, credentials, API requests, ingestion, persistence, or deployment exists.

The project remains a personal, private, non-commercial development prototype. Public whalpha.com content is currently a development placeholder and must not expose restricted provider-backed market data or derived analytics without an appropriate authorization and access-control decision.

## Decision

Use Massive Stocks Basic as the first EOD development provider for private, personal, non-commercial development and validation.

This selection is limited to private EOD development. It is not a public display authorization, redistribution authorization, commercial license, production-public-data approval, real-time provider decision, options provider decision, or permanent exclusive provider lock-in.

No Massive account entitlement, API key, adapter, API request, ingestion, persistence, or deployment is created by this decision.

## Technical Fit

Massive Stocks Basic is technically aligned with the current V1 provider capabilities because the public documentation lists EOD stock aggregates, reference tickers, corporate actions, and technical indicators under the Stocks Basic plan. The All Tickers endpoint can support Instrument Master mapping inputs. Daily grouped aggregates and custom aggregate bars can support EOD Price Bar mapping candidates.

The provider boundary remains provider-neutral. Massive response fields must be mapped by an adapter into canonical contracts before any domain calculation consumes them.

## Plan Assumptions

Last reviewed: 2026-08-14.

Current public pricing pages list Stocks Basic as a free individual plan with all U.S. stock tickers, 5 API calls per minute, 2 years of historical data, 100% market coverage, end-of-day data, reference data, corporate actions, technical indicators, and minute aggregates.

Provider pricing, entitlement, coverage, endpoint availability, and terms are externally controlled and must be rechecked before implementation, plan changes, credential creation, deployment, or public release.

## Provider-Neutral Boundary

Massive is the first adapter candidate, not a canonical schema owner. Business logic must not depend on Massive proprietary response shapes. Internal contracts continue to use canonical instrument IDs, canonical date and revision semantics, and explicit data-quality status.

Future providers can be added or substituted if entitlement, coverage, cost, reliability, or licensing requirements change.

## Data Access Strategy

Initial REST strategy:

- Use All Tickers as an Instrument Master mapping candidate.
- Prefer Grouped Daily bars for daily broad-market EOD increment evaluation.
- Use Custom Bars for targeted historical backfill.
- Avoid per-ticker Previous Day requests as a whole-universe daily scan.
- Do not use snapshots as the canonical EOD bar source.

The 5 calls/minute Basic limit requires rate-aware implementation. Request pacing, retry-after handling, no concurrency bursts, resumable backfill, idempotent ingestion, pagination handling, and request audit without secrets are future adapter requirements.

Flat files are not part of the Basic plan according to the public day-aggregate flat-file documentation. The initial implementation direction is REST API, not S3/flat-file architecture.

## Adjustment Semantics

Massive aggregate documentation states that aggregate responses are split-adjusted by default and can request unadjusted results. Massive's adjustment FAQ states that historical market data is adjusted for splits by default and not dividends.

Canonical raw OHLC should therefore be mapped preferentially from unadjusted aggregate responses. Split factors, dividend factors, and total-return factors should be handled from explicit corporate-action data rather than treating provider-adjusted close as the only source of truth.

New dividend documentation references dividend adjustment factors. The exact reconciliation between aggregate adjustment behavior and dividend endpoint adjustment factors requires implementation-time verification.

## Licensing and Access Boundary

This documentation records an operational interpretation for engineering boundaries and is not legal advice. Terms and provider permissions must be rechecked before public release.

Massive Market Data Terms grant personal, non-business, non-commercial, non-transferable use under the applicable restrictions. The terms restrict unauthorized redistribution and public display of Market Data and also restrict charts, analytics, research, and other derived works based on Market Data.

Initial operational boundary at the time of this ADR:

- Provider-backed real-data dashboard views are private-owner only.
- Provider-backed API responses must be protected before deployment.
- Public static exports must not include restricted provider data or provider-derived analytics.
- Public portfolio demos must use clearly marked synthetic/demo fixtures or data with appropriate public-display rights.
- Public real-data products require explicit authorization, suitable license terms, an alternative data source with public-display rights, or appropriate legal/compliance review.

The first bullet is superseded as a product-serving choice by ADR 0019 and ADR
0052. Current shared product capability does not branch by entry path. A source
that cannot support equal-capability use remains out of future shared
publications for both guest and credential Sessions.

## Public Placeholder

The public development placeholder may show WH Alpha branding, project description, development status, architecture overview, and feature descriptions. It must not contain restricted provider data or provider-derived analytics.

## Public Portfolio Demo

A public portfolio demo may be built later for portfolio or hiring presentation purposes only if it is separated from the private real-data dashboard and does not include Massive Market Data or derived works from Massive data. Synthetic or clearly licensed public-display data must be visibly identified and must not be presented as live or real market state.

## Private Real-Data Dashboard

Before any Massive-backed data or derived work is exposed through whalpha.com, effective private access control is required. Candidate mechanisms include Cloudflare Access, application authentication, Nginx Basic Auth, or VPN/Tailscale-only access. This ADR does not select or configure an access-control mechanism.

## Consequences

- The next implementation can target Massive configuration and credential boundaries with mocked HTTP responses only.
- The provider Protocol remains stable and provider-neutral.
- Public demos and private real-data workflows are explicitly separated.
- Public release of provider-backed data is blocked until authorization and access-control requirements are satisfied.
- Basic plan rate limits and 2-year history constrain early development and backfill scope.

## Risks

- Public plan details, endpoint access, and terms can change.
- Actual account entitlement is not verified.
- Two years of history is not enough for long-term regime research.
- 5 calls/minute requires careful adapter pacing.
- Identity continuity across ticker changes requires explicit adapter design.
- Adjustment semantics require implementation-time verification.

## Deferred Decisions

- Actual account signup and entitlement verification
- Credential storage mechanism
- Massive adapter configuration contract
- HTTP client choice
- Rate limiter implementation
- Grouped Daily response verification
- Historical backfill strategy
- Identity-resolution methodology
- Adjustment reconciliation
- Private access-control mechanism
- Public demo data source
- Plan upgrade threshold
- Business/display/redistribution license threshold
- Options data source

## Non-Goals

- Creating a Massive account
- Creating or reading API credentials
- Calling Massive APIs
- Implementing a Massive adapter
- Downloading market data
- Implementing access control
- Deploying provider-backed data
- Creating public real-data pages
- Selecting an options provider
- Making Massive a permanent exclusive provider

## Review Trigger

Re-review this decision:

- before implementing a Massive adapter
- before creating account credentials in the project
- before changing plan
- before deploying real data
- before making provider-derived content public
- if Massive pricing, terms, endpoint availability, or entitlement changes
