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
- [x] One 2026-08-13 Grouped Daily publication attempt with completed resolver and quality gates
- [ ] Real provider ingestion workflow
- [ ] EOD development dataset
- [ ] Core market calculations
- [ ] Dashboard shell
- [ ] Heatmap
- [ ] Breadth
- [ ] Rotation
- [ ] Relationship monitor
- [ ] Lightweight developments
- [ ] First usable deployment

## Next Small Target

Investigate the 2026-08-13 Massive Grouped Daily publication blockers using local captured-safe fixtures or a separately authorized diagnostic plan: required numeric field parsing, conflicting duplicate bars, and identity classification coverage; do not rerun the live Grouped Daily request until the corrected parser and gates are reviewed.

## Phase 2 — Intraday and Options

- [ ] Delayed/intraday upgrades
- [ ] Selected Options structure
- [ ] Scheduling and reliability
- [ ] Stronger monitoring

## Later

- Portfolio
- Richer Event workflows
- Authentication if needed
- AI explanation
- Broader public showcase
