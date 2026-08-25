# Roadmap

- Next proposed product step: human-review the refined local Market Regime
  page. Only after explicit acceptance should immutable Production analytics
  publication be designed as a separate authorization.
  EOD catch-up, sector taxonomy, candidates, Production snapshot, guest access,
  bundle, and OCI remain separate authorizations.

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
- [x] Approval-bound same-day fetch/plan/apply/reread workflow with offline
  apply, same-day Identity dependency, recovery, and fake-transport rehearsal
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
- [x] Bounded SEC live transport, source-cache/evidence publication boundaries, two-stage selected-source discovery gate, and diagnostic schema `3.0` with historical schema `2.0` audit compatibility
- [x] Exact nine-artifact private SEC source-cache reconciliation and hardened submissions ZIP validation
- [ ] Successful SEC issuer-structure evidence publication and Core/Broad activation review — paused for the current product stage after the final bounded run failed closed
- [x] Offline Provider-Classified Common Shares (CS-only) and CS+ADRC shadow audit with stable-ID reconciliation and deterministic fingerprints
- [x] Provider-neutral 20-session XNYS history planner, bounded canonical reader, Decimal trailing-liquidity contract, readiness audit, and offline backfill plan
- [x] Successful 2026-07-17 same-day identity plus Grouped Daily single-session production backfill pilot
- [x] Successful first three-session production backfill batch for 2026-07-20 through 2026-07-22
- [x] Successful second three-session production backfill batch for 2026-07-23, 2026-07-24, and 2026-07-27
- [x] Successful third three-session production backfill batch for 2026-07-28 through 2026-07-30
- [x] Successful fourth three-session production backfill batch for 2026-07-31, 2026-08-03, and 2026-08-04
- [x] Successful fifth three-session production backfill batch for 2026-08-05 through 2026-08-07
- [x] Successful final two-session production backfill batch for 2026-08-10 and 2026-08-11; 20-session partition descriptor ready
- [x] Calendar-bounded latest EOD catch-up for 2026-08-17 through 2026-08-19; canonical freshness lag zero
- [x] Versioned Trailing Liquidity V1 metric/decision shadow publication for 2026-08-19 with logical completion marker
- [x] Stable-ID Legacy/A/B pre-activation comparison and Reviewed Eligibility Override V1 shadow publication
- [x] Versioned Dashboard Universe Activation V1 with selectable Common Shares and Common Shares + ADRs
- [x] Multi-Universe private API, snapshot, and React selector integration
- [x] Market Regime & Opportunity Map V1 product, quantitative, data-contract,
  architecture, validation, and phased-delivery design
- [x] Market Regime Phase 1a offline raw-metric and five-dimension ledger
- [x] Market Regime Phase 1b offline state/hysteresis ledger
- [x] Market Regime Phase 2 offline fixed-basket ETF Relationship Map
- [x] Market Regime read-only local API, preview bundle, and desktop page

## Next Small Target

Repeat human visual review of the refined local Market Regime page at the three
desktop viewports and with pair detail open. Do not start Production analytics
publication design, publication, snapshot integration, or deployment without
a separate authorization. Keep SEC B2 paused.

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
