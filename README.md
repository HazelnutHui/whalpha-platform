# Trading Intelligence Platform

## Security Type Governance

The repository implements a provider-neutral, effective-dated Security
Classification boundary keyed by stable `instrument_id`. Security form, issuer
structure, listing scope, evidence quality, and Universe disposition remain
separate. Unknown, ambiguous, malformed, heuristic-only, and insufficient-
evidence records are quarantined.

The active provisional Dashboard Universe uses the reviewed Activation V2
publication: 1,718 provider-classified Common Shares as Primary and those same
1,718 plus 113 ADRCs as Secondary. This is not evidence that every member is a
U.S.-domestic operating company. Core remains the future default policy and
Broad the future secondary policy only after authoritative issuer-structure
and domicile evidence satisfies the documented gates.

Phase B1 provider evidence is completed. SEC Phase B2 transport and fail-closed
publication boundaries are implemented, but no completed SEC evidence
publication exists and B2 is paused. See the [classification audit](docs/audits/security-type-classification-2026-08-14.md),
[provider-evidence audit](docs/audits/security-type-provider-evidence-2026-08-14.md),
[Universe activation architecture](docs/architecture/dashboard-universe-activation.md),
and [SEC evidence architecture](docs/architecture/sec-issuer-structure-evidence.md).

Trading Intelligence Platform is a personal single-user prototype for U.S. equity market intelligence. It is designed to help the user understand market structure, sector and theme rotation, stock strength, breadth, options structure, relationship shifts, and significant market developments quickly enough to support discretionary research and trading decisions.

The platform should help answer:

- What is the market structure today?
- Which sectors and themes are strengthening or weakening?
- Is risk appetite expanding or contracting?
- Which stocks show genuine relative strength?
- What relationships or rotations deserve further investigation?
- What developments are significant enough for human review?

## Current Phase

Documentation, infrastructure, storage, the application stack, canonical
EOD/Identity, private analytics, Activation V2, immutable Market Intelligence,
MI 1.2, Snapshot 1.7 / Dashboard 2.4, entry-location consumers, bilingual
presentation, equal-capability guest Sessions, and Session-protected static
publication are implemented. The deployed product includes the audited Stock
Candidate pipeline and third Candidate workspace. Canonical sessions cover
every XNYS session from 2026-07-17 through 2026-08-26. The active Dashboard is
the ordinary fresh 2026-08-26 release with lag zero.

Repository development source adds verified-prior one-session append for both
Candidate and corrected V1.0.1 Market Regime state. The state daily path
formally consumes current Phase 1a plus prior Phase 1b audits without reopening
canonical EOD. These changes are offline development work and are not deployed.

Repository development source also contains an exact-session read-only daily
planner and a single-action executor for the four offline analytics stages.
Execution is bound to an unchanged plan fingerprint, global Dell lock,
immutable hash-chained journal, validated output evidence, and post-action
formal re-plan. This boundary is tested but has not been run against real daily
state; provider acquisition, canonical apply, publication, deployment, and
scheduler activation remain separately unauthorized.

The next repository-only control slice separates XNYS close from provider
readiness. It applies a provisional post-close stabilization window, bounded
retry and `Retry-After`, explicit alert state, and oldest-missing-session
recovery without making a provider request or completeness claim. Durable
acquisition-attempt custody is now implemented through fresh readiness reservation,
persistent bounded outcomes, exact frozen-package evidence, and no-request
interruption recovery under the same Dell global lock and hash chain.
The repository now also defines an expiring, exact-revision standing data-
authorization contract for Identity/EOD fetch and canonical apply. It is
default-deny: no real authorization artifact or external SHA pin exists.
The one-transition coordinator core now joins wait, recovery, authorization
review, offline execution, diagnosis, and publication-review states without
looping. Canonical Identity/EOD Apply now also has exact reservation and no-
write interruption recovery under a third disjoint journal family. Explicit
standing-authorized fetch/Apply adapters now compose those boundaries and
preserve actual Identity pagination request counts, but remain uninstalled and
inactive. No real authorization, run root, credential read, fetch attempt, or
Apply has been created; notification delivery and scheduler activation remain
unimplemented. A one-transition CLI and externally SHA-pinned host-runtime
contract are also repository-tested: capability ports remain absent unless an
external owner-only config enables them, the invocation explicitly opts in,
and actual Dell/source/clean-HEAD/policy identity all match. No real host config
or CLI transition exists. Explicit one-transition recovery routing now covers
the acquisition, canonical-Apply, and offline-action journal families. It
formally rereads the exact pending event, keeps the socket guard active, and
never fetches, applies canonical data, replays calculation, or loops. No real
recovery invocation has occurred.
Repository source now also preserves alert-required coordinator states and can
explicitly emit a channel-neutral, deterministic alert intent. It does not
persist or deliver notifications; no channel, credential, retry, or delivery
receipt is installed. External authorization remains intentionally unprovisioned
until the remaining control-plane code stops changing revision.

Primary is 1,718 Common Shares. Secondary is 1,831 securities: the same 1,718
Common Shares plus 113 ADRCs. Provider security form remains provisional and
does not establish issuer structure or domicile. There is no automated daily
ingestion, database/catalog service, general production API, point-in-time
sector taxonomy, fundamentals, valuation, or options dataset. Equal-capability
guest Session entry is implemented in repository source; it does not create a
role or a second data surface.
See the [authoritative current context](docs/project/current-context.md) for
the exact active publications, fingerprints, verification boundary, and next
authorized work.

## Application Entry Points

- Backend scaffold: [apps/api](apps/api/README.md)
- Frontend dashboard: [apps/web](apps/web/README.md)
- Local development guide: [docs/development/local-development.md](docs/development/local-development.md)

## Accepted Application Stack

- Frontend: React, TypeScript, Vite, Apache ECharts, and lightweight CSS.
- Backend/API boundary: Python 3.12, FastAPI, and Pydantic.
- Analytics: Pandas and NumPy.
- Initial storage path: EOD-first Parquet datasets under `/data/trading-intelligence-platform`.
- Data access: MarketDataProvider / adapter boundary before domain calculations.
- Initial EOD data foundation: accepted universe, classification, and normalized logical contract boundaries.
- Implemented data contracts: Instrument Master V1 and EOD Price Bar V1 Python/Pydantic models.
- Implemented provider boundary: synchronous MarketDataProvider Protocol, query models, capabilities, and errors.
- First EOD development provider: Massive Stocks Basic for private, personal EOD development only; secure credential/HTTPS transport, bounded All Tickers identity ingestion, Grouped Daily publication, and provider security evidence workflows are verified.
- Initial persistence: Instrument Master, provider identity, ticker resolver, provider security evidence, EOD Price Bar, and Trailing Liquidity shadow Parquet repositories use manifests, deterministic fingerprints, idempotency, conflict checks, and logical completion markers. Canonical EOD covers every XNYS session from 2026-07-17 through 2026-08-26.
- Initial private read API: default-disabled canonical EOD query routes can list completed sessions, summarize completed sessions, and return paginated joined bars with Decimal values serialized as strings.
- Market summary analytics use the latest two formally completed sessions and support close-to-close returns, Market Summary V1, liquidity-screened movers, and Trading Activity Map private responses.
- Market-session freshness: an offline XNYS exchange calendar distinguishes expected completed sessions from actual completed datasets and from file/schema consistency validation.
- Initial local dashboard: React Market Dashboard V1 renders Market Pulse, breadth, up/down volume, liquidity-screened movers, a Trading Activity Map, market/sector benchmarks, and categorized data details from default-disabled private APIs.
- Static deployment: the workstation exports protected Dashboard JSON snapshots
  and versioned `/dashboard/` React bundles. Git records OCI deployments with
  `/` as the branded credential/guest Session entry; live OCI state is not
  implied without a current check.
- Protected Session entry: the OCI design uses a localhost-only Auth Service,
  opaque HttpOnly Session cookies, owner credential login, equal-capability
  guest entry, and an interactive password-rotation helper. Guest and
  credential Sessions load the same product. Git records the design and
  verification gates; current service health remains an operational check.

- Access boundary: provider-backed data and derived analytics must not be publicly exposed without an accepted authorization and access-control gate.

See [ADR 0005](docs/decisions/0005-application-technology-stack.md) and [Application Architecture](docs/architecture/application-architecture.md) for the authoritative decision details.

## Phase 1 Success Criteria

Phase 1 succeeds when the project delivers a usable Market Dashboard MVP that can show:

- Market Structure Summary
- Market Risk Regime
- Standard Market Heatmap / Treemap
- Market Breadth
- Index & Style Strength
- Sector / Theme Rotation
- Dynamic Relationship & Rotation Monitor
- Key Market Developments

## Core Modules

- Market Structure
- Sector / Theme Rotation
- Stock Strength
- Market Breadth
- Options Structure
- Dynamic Relationship & Rotation Monitor
- Lightweight Event Layer

## Explicitly Not Doing Now

- Automated trading
- Order execution
- HFT
- Complex ML or deep learning
- Large microservice systems
- Kubernetes
- Large Event Knowledge Base

## Public and Data-Licensing Boundary

This project is a personal single-user prototype. It may be reachable over the public internet, but it is not currently a commercial market-data redistribution product. Public access and data licensing must be reassessed before broader promotion or commercial use.

## Documentation Entry Points

- [Agent instructions](AGENTS.md)
- [Documentation index](docs/README.md)
- [Current status](docs/project/current-status.md)
- [Authoritative current context](docs/project/current-context.md)
- [Dashboard V1](docs/product/dashboard-v1.md)
- [Application architecture](docs/architecture/application-architecture.md)
- [Initial EOD Universe](docs/product/initial-eod-universe.md)
- [Classification Boundary](docs/architecture/classification-boundary.md)
- [Normalized Market Data Contracts](docs/architecture/normalized-market-data-contracts.md)
- [Market Data Provider Boundary](docs/architecture/market-data-provider-boundary.md)
- [Massive Stocks Basic Evaluation](docs/providers/massive-stocks-basic-evaluation.md)
- [Massive Adapter Boundary](docs/providers/massive-adapter-boundary.md)
- [Massive Credential Provisioning](docs/operations/massive-credential-provisioning.md)
- [Massive Grouped Daily Inspection](docs/operations/massive-grouped-daily-inspection.md)
- [Massive Grouped Daily Ingestion](docs/operations/massive-grouped-daily-ingestion.md)
- [Massive Instrument Master Ingestion](docs/operations/massive-instrument-master-ingestion.md)
- [Instrument Identity Resolution](docs/architecture/instrument-identity-resolution.md)
- [EOD Parquet Persistence](docs/architecture/eod-parquet-persistence.md)
- [Trailing Liquidity Shadow Publication](docs/architecture/trailing-liquidity-shadow-publication.md)
- [Dashboard Universe Activation](docs/architecture/dashboard-universe-activation.md)
- [Canonical Market Data Query Boundary](docs/architecture/canonical-market-data-query-boundary.md)
- [Private EOD Market Data API V1](docs/api/private-eod-market-data-v1.md)
- [Private Market Summary API V1](docs/api/private-market-summary-v1.md)
- [EOD Return Analytics](docs/architecture/eod-return-analytics.md)
- [Frontend Market Dashboard V1](docs/frontend/market-dashboard-v1.md)
- [Private Dashboard Publication](docs/architecture/private-dashboard-publication.md)
- [OCI Private Dashboard Deployment](docs/operations/oci-private-dashboard-deployment.md)
- [Private Dashboard Access](docs/operations/private-dashboard-access.md)

- [Data Access Boundary](docs/operations/data-access-boundary.md)
- [Data Contracts](docs/data-contracts/README.md)
- [System context](docs/architecture/system-context.md)
- [Deployment boundary](docs/operations/deployment-boundary.md)
- [Architecture decisions](docs/decisions/README.md)

## Current Dashboard

Dashboard Universe V1 uses `Common Shares` as the default and `Common Shares + ADRs` as the optional view. All Universe-dependent modules share the activated stable-ID membership; Legacy is retained internally for rollback and is not an ordinary selector option. Provider-backed data remains private.
