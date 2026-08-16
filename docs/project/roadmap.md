# Roadmap

This roadmap is a proposed sequence, not a commitment or date plan.

## Phase 0 — Foundation

- [x] Infrastructure audit and cleanup
- [x] Access normalization
- [x] Documentation bootstrap
- [x] Storage preparation
- [x] Application technology stack decision
- [x] Target application architecture documentation

## Phase 1 — Market Dashboard MVP

- [x] Minimal application scaffold
- [x] Local frontend/backend development toolchain
- [x] Define Initial EOD Universe
- [x] Define Sector/Industry, Theme, and Analytical Group boundary
- [x] Define normalized EOD logical contracts
- [x] Instrument Master V1 model and validation tests
- [x] EOD Price Bar V1 model and validation tests
- [ ] Remaining logical contract models
- [x] Minimal provider boundary Protocol
- [x] Deterministic in-memory provider contract tests
- [x] First real EOD provider evaluation
- [x] Massive adapter configuration and credential boundary with mocked HTTP responses
- [x] Massive account entitlement and secure credential provisioning smoke test
- [x] First bounded EOD ingestion slice with mocked fixtures
- [x] Separately authorized one-session Grouped Daily inspection without publication
- [x] Point-in-time Massive Instrument Master snapshot ingestion path
- [x] Instrument Master snapshot quality-gate remediation and publication
- [x] Grouped Daily parser, identity-ordering, and duplicate-isolation remediation
- [x] Decimal aggregate-volume correction and first canonical EOD session publication
- [x] Private canonical EOD read/query API for the completed 2026-08-13 session
- [x] 2026-08-12 bounded ingestion and first close-to-close Market Summary analytics
- [x] Bounded real-provider identity and EOD ingestion workflows
- [x] Initial three-session EOD development dataset
- [x] Initial close-to-close market summary, breadth, movers, benchmark, and trading-activity calculations
- [x] Local React Market Dashboard V1 shell
- [x] Liquidity Map V1 treemap
- [x] EOD breadth and up/down volume views
- [x] Private static dashboard snapshot exporter and OCI bundle package

- [ ] Rotation
- [ ] Relationship monitor
- [ ] Lightweight developments
- [x] First usable private static deployment
- [x] Dashboard V1.1 professional universe and market overview cleanup
- [x] Dashboard V1.1 trust/usability pass with benchmark strip, Sector ETF relative performance, conservative freshness, and top-50 Trading Activity Map default
- [x] Provider-neutral offline XNYS market-session calendar and explicit freshness contract
- [x] Corrected Phase B1 provider security-type evidence publication and provisional universe disclosure source
- [x] Offline SEC issuer-structure evidence boundary, private User-Agent tool, fixture state machines, and tmp-only persistence
- [x] Bounded SEC live transport, source-cache/evidence publication boundaries, fail-closed discovery, and diagnostic schema `2.0`
- [ ] Successful SEC issuer-structure evidence publication and Core/Broad activation review

## Next Small Target

Review the fifth-run schema `2.0` evidence for the 2023 Series/Class underscore-style basename against the historical path contract. Do not generalize the observed path to 2022 or earlier, and do not issue another live request without separate authorization. Core/Broad activation remains deferred.

## Phase 2 — Intraday and Options

- [ ] Delayed/intraday upgrades
- [ ] Selected Options structure
- [ ] Scheduling and reliability
- [ ] Stronger monitoring

## Later

- Portfolio
- Richer Event workflows
- Formal multi-user authentication beyond the personal-prototype session boundary
- AI explanation
- Broader public showcase
