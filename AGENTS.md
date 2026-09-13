# Trading Intelligence Platform — Agent Instructions

## Security Classification Governance

- Keep classification effective-dated and keyed by stable `instrument_id`; ticker is not a permanent key.
- Keep security form, issuer structure, listing scope, evidence, and universe disposition separate.
- Names and ticker patterns may only create review flags, never positive eligibility.
- Unknown, ambiguous, malformed, heuristic-only, and insufficient-evidence records remain quarantined.
- Unactivated Phase A/B candidates and future Core/Broad candidates must not
  feed production analytics. The explicitly activated provider-form
  Primary/Secondary Universes may feed the current Dashboard only with their
  provisional status and issuer-structure limitation preserved.
- Product policy is Core future default and Broad future secondary. The active
  provider-form Primary/Secondary Activation is provisional; production
  Core/Broad issuer-structure activation remains deferred.
- Provider security-form evidence never proves issuer operating structure or domicile; unknown evidence remains quarantined.
- SEC filer identity and filing evidence do not automatically establish listed-security identity; live SEC access requires separately authorized private User-Agent configuration.

## 1. Required Reading Order

Every new AI/Codex session must read these files before making material changes:

1. [README.md](README.md)
2. [docs/README.md](docs/README.md)
3. [docs/project/current-context.md](docs/project/current-context.md)
4. [docs/project/current-status.md](docs/project/current-status.md)
5. The product, architecture, operations, or ADR files directly related to the current task.

## 2. Project Mission

Trading Intelligence Platform is a personal, practical U.S. equity market
intelligence and professional quantitative-research platform. It helps the
user understand current market structure, develop transparent personal
models, and support discretionary research and trading decisions.

It is not an automated trading or order-execution system. Quantitative
research must remain governed, reproducible, falsifiable, and explainable; a
personal model is not permission for a black box.

The future AI Quant Research Factory is a bounded backend of Quant Research
Lab, not an ungoverned search engine. High-throughput ideas still require
deduplication, finite registered experiment budgets, stage-isolated data,
deterministic evaluation, retained failures, sealed holdout custody, and human
activation. See
[ADR 0194](docs/decisions/0194-govern-ai-assisted-quant-research-as-a-bounded-factory.md).

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
- ungoverned or opaque ML
- deep neural networks
- ungoverned prediction engines
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
- [docs/project/current-context.md](docs/project/current-context.md) must stay
  compact enough for task/device recovery; move dated execution narrative to
  audits or the changelog.
- Update current context and current status by replacing superseded facts;
  never append a completed run narrative to either file.
- [docs/project/roadmap.md](docs/project/roadmap.md) is not a commitment.
- Keep the roadmap future-facing; completed implementation detail belongs in
  the changelog, its ADR, or a dated audit.
- [docs/project/changelog.md](docs/project/changelog.md) records meaningful project-level changes.
- Avoid duplicating the same authoritative fact across many files.
- Link to the authoritative document instead.
- Keep documentation indexes curated by authority and topic; do not append a
  second chronological catalog of every ADR or audit.
- Preserve historical evidence, but label superseded direction and remove it
  from the default recovery path.

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

Do not duplicate volatile sessions, releases, fingerprints, or next-step claims
in this instruction file. Read [docs/project/current-status.md](docs/project/current-status.md)
and [docs/project/current-context.md](docs/project/current-context.md) for the
authoritative current phase and verified operational state. The roadmap remains
proposed sequencing, not authorization.
