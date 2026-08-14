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
- [ ] Massive adapter configuration and credential boundary with mocked HTTP responses
- [ ] Real provider adapter implementation
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

Design and implement the Massive adapter's configuration and credential boundary using a placeholder environment-variable contract and mocked HTTP responses only, without creating an API key or making a real network request.

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
