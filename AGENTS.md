# Trading Intelligence Platform — Agent Instructions

## 1. Required Reading Order

Every new AI/Codex session must read these files before making material changes:

1. [README.md](README.md)
2. [docs/README.md](docs/README.md)
3. [docs/project/current-status.md](docs/project/current-status.md)
4. The product, architecture, operations, or ADR files directly related to the current task.

## 2. Project Mission

Trading Intelligence Platform is a personal, practical U.S. equity market intelligence dashboard. It helps the user understand current market structure quickly and supports discretionary research and trading decisions.

It is not an automated trading system. It is not currently a complex quantitative research platform.

## 3. Working Principles

- Work on one clearly scoped objective at a time.
- Discuss and confirm domain behavior before substantial implementation.
- Use minimal necessary complexity.
- Keep the system simple, stable, extensible, and maintainable.
- Maintain a single source of truth.
- Document material architecture decisions before implementing them.
- Verify real infrastructure and code; do not guess.
- Preserve user changes.
- Never modify unrelated systems or projects.
- Test every implementation safely.
- Update documentation when a confirmed decision or operational state changes.

## 4. Scope Boundaries

Do not independently expand this project into:

- automated trading
- order execution
- HFT
- complex ML
- deep neural networks
- prediction engines
- large microservice systems
- Kubernetes
- distributed systems
- a large Event Knowledge Base

## 5. Infrastructure Rules

- Workstation alias: `dell5820`
- Web server alias: `whalpha-oci`
- The workstation is the source of truth for code, computation, and data processing.
- OCI is the public web-serving boundary.
- Never assume sudo access.
- Never expose credentials.
- Never store secrets in Git.
- Do not include literal server IPs or key paths in repository documentation.
- Never access the unrelated second OCI instance.
- Destructive operations require exact target verification and explicit authorization.

## 6. Documentation Maintenance

- Confirmed decisions go into the relevant document.
- Material architecture decisions require an ADR.
- [docs/project/current-status.md](docs/project/current-status.md) must reflect actual current state.
- [docs/project/roadmap.md](docs/project/roadmap.md) is not a commitment.
- [docs/project/changelog.md](docs/project/changelog.md) records meaningful project-level changes.
- Avoid duplicating the same authoritative fact across many files.
- Link to the authoritative document instead.

## 7. Documentation Checkpoints

Before completing work that materially changes architecture, infrastructure, runtime behavior, data contracts, deployment, security boundaries, or project status, check whether these documents need updates:

- ADRs
- architecture documents
- operations documents
- current-status
- roadmap
- open-questions
- changelog
- README and docs index

A task that materially changes architecture, infrastructure, runtime behavior, data contracts, deployment, security boundaries, or project status is not complete until the relevant documentation has been checked and updated.

Do not create an ADR for every small code edit, formatting change, or local implementation detail. Use ADRs for material decisions that affect project direction, architecture, operations, or long-term maintenance.

## 8. Current Phase

Infrastructure, storage, application scaffold, local frontend/backend development toolchain, core EOD contracts, provider boundary, mocked Massive adapter boundary, secure Massive smoke-test transport, point-in-time Instrument Master snapshots, canonical EOD Price Bar sessions for 2026-08-12 and 2026-08-13, default-disabled private canonical EOD/Market Summary APIs, the first local React Market Dashboard V1, the private static dashboard deployment package, branded session login, and the authenticated static OCI deployment are complete and verified. Manual authenticated browser verification, public provider-backed display authorization, database/catalog services, and broader analytics modules are not implemented yet.

Current proposed activity: have the user complete authenticated browser and visual verification of the session-login Dashboard, then record production acceptance and address any visual/runtime defects found.
