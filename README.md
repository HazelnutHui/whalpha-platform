# Trading Intelligence Platform

WH Alpha is a personal U.S. equity market-intelligence and quantitative
research platform. It supports discretionary decisions through the chain:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

It is not an automated trading or order-execution system. Conclusions must
remain explainable through source facts, parameters, contributions, supporting
and contrary evidence, market context, and invalidation conditions.

## Current state

The live product includes bilingual Market Regime & Opportunities, Market
Structure & Activity, Sector ETF Rotation, Stock Candidates, and an explicitly
research-only Quant Research Lab. Guest and credential Sessions intentionally
receive identical data and capabilities.

The first three are stable market-context workspaces. Quant Research Lab is
the model registry and validation authority. Its future AI Quant Research
Factory may generate hypotheses at high throughput, but every real experiment
remains deduplicated, budgeted, data-isolated, deterministic, and falsifiable.
Stock Candidates will eventually consume only one to three validated and
explicitly activated Lab models. The currently deployed Candidate score,
Entry Geometry, and technical Strategy Channels remain transparent but
unvalidated **Baseline V1**, not a direct parameter-tuning target.

Dell is the authority for code, data, and computation. OCI serves only bounded
static product artifacts and the localhost authentication boundary. The
guarded daily chain has been exercised end to end, but the installed timer is
read-only and no unattended write-capable scheduler is active.

Do not copy volatile session dates, releases, fingerprints, or current next
steps from this README. Read:

- [Authoritative current context](docs/project/current-context.md)
- [Current status](docs/project/current-status.md)
- [Roadmap](docs/project/roadmap.md)
- [Changelog](docs/project/changelog.md)

## Security and Universe governance

Classification is provider-neutral, effective-dated, and keyed by stable
`instrument_id`; ticker is display metadata rather than permanent identity.
Security form, issuer structure, listing scope, evidence quality, and Universe
disposition remain separate. Unknown, ambiguous, malformed, heuristic-only,
and insufficient-evidence records are quarantined.

The active Primary/Secondary Universes use provisional provider security-form
evidence. Provider form does not prove issuer operating structure or domicile.
Core remains the intended future default and Broad the future secondary only
after authoritative issuer-structure evidence satisfies the documented gates.

See:

- [Classification boundary](docs/architecture/classification-boundary.md)
- [Dashboard Universe activation](docs/architecture/dashboard-universe-activation.md)
- [Instrument identity resolution](docs/architecture/instrument-identity-resolution.md)
- [Data Record Governance V1](docs/data-contracts/data-record-governance-v1.md)

## Architecture

- Frontend: React, TypeScript, Vite, and Apache ECharts.
- Backend and contracts: Python 3.12, FastAPI, and Pydantic.
- Analytics: Pandas, NumPy, and exact Decimal boundaries where required.
- Canonical storage: partitioned Parquet under Dell `/data` with immutable
  manifests, content fingerprints, atomic completion, and fail-closed readers.
- Publication: immutable Market Intelligence and Dashboard Snapshot contracts,
  lazy Candidate detail shards, checksum-bound OCI serving bundles, and
  independent postflight inspection.
- Access: opaque HttpOnly Sessions; guest and credential routes share one
  capability surface until explicitly changed.

The repository prefers bounded files and explicit contracts over a new service
or database when the existing manifests already provide the required evidence.

## Data and research boundary

Canonical EOD history alone is not sufficient for a professional backtest.
Point-in-time membership, lifecycle/terminal evidence, corporate actions,
adjustment reconciliation, realistic costs, chronological splits, sealed
holdout access, and complete outcome coverage are required before performance
claims.

Candidate stock outcomes must never be described as option returns. Price and
volume proxies must never be described as actual fund flow. Research,
validation, shadow, Production, and retired states remain visibly distinct.

~~~text
registered Lab experiment -> bounded development -> locked validation
-> sealed holdout -> prospective shadow -> explicit activation
-> Stock Candidates
~~~

See:

- [Professional Quantitative Research Action Framework](docs/research/professional-quantitative-research-action-framework-v1.md)
- [Historical Research Data Foundation](docs/architecture/historical-research-data-foundation-v1.md)
- [Quant Research Lab V1](docs/product/quant-research-lab-v1.md)
- [Candidate Strategy Evaluation V1](docs/data-contracts/candidate-strategy-evaluation-v1.md)
- [ADR 0191: validated model promotion](docs/decisions/0191-promote-validated-research-models-into-stock-candidates.md)
- [ADR 0194: bounded AI-assisted research](docs/decisions/0194-govern-ai-assisted-quant-research-as-a-bounded-factory.md)

## Application entry points

- Backend: [apps/api](apps/api/README.md)
- Frontend: [apps/web](apps/web/README.md)
- Local development: [docs/development/local-development.md](docs/development/local-development.md)
- Documentation index: [docs/README.md](docs/README.md)
- ADR index: [docs/decisions/README.md](docs/decisions/README.md)

Use the repository-aware backend runner from any linked checkout:

```bash
scripts/dev/run-project-python.sh -m pytest apps/api/tests
```

Before material work, follow [AGENTS.md](AGENTS.md) and recover state through
the authoritative current-context reader. Network, credentials, canonical
Apply, publication, deployment, scheduler mutation, and destructive cleanup
remain explicit operational boundaries.

## Explicitly outside the current scope

- automated trading and order execution;
- HFT;
- ungoverned prediction engines or complex ML;
- large microservice or Kubernetes architectures;
- synthetic Production analytics;
- role-based guest restrictions before the user changes the equal-capability
  policy.
