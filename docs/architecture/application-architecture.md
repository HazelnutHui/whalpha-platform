# Application Architecture

## Purpose

This document defines durable application boundaries. Exact sessions,
releases, fingerprints, counts, and runtime health belong in
[current context](../project/current-context.md). Historical implementation
steps belong in ADRs, audits, and the changelog.

## System boundary

```text
Data providers
-> provider adapters
-> normalized and canonical facts
-> market analytics / quantitative research
-> immutable product publications
-> OCI static serving and Session boundary
-> browser
```

Dell is the authority for source code, credentials, ingestion, canonical data,
heavy computation, research orchestration, publication construction, and
reproducibility evidence. OCI serves bounded static artifacts and the
localhost authentication service. The browser renders typed payloads and never
holds provider, server, or broker credentials.

The current architecture is intentionally a workstation-centered modular
application, not a microservice or distributed system.

## Application components

- `apps/api`: Python contracts, canonical readers, analytics, research
  services, provider adapters, and default-disabled private APIs.
- `apps/web`: React/TypeScript/Vite product shell and visual workspaces.
- `scripts/dev`: repository-aware local development commands.
- `scripts/admin`: guarded planning, validation, publication, deployment, and
  recovery entry points.
- `/data/trading-intelligence-platform`: Dell canonical facts and immutable
  publications; never committed to Git.
- OCI release directories: checksum-bound static serving artifacts only.

The accepted stack remains FastAPI/Pydantic, Pandas/NumPy where appropriate,
Parquet/Arrow storage, React/TypeScript/Vite, and Apache ECharts. A database is
not selected because current manifests and bounded files satisfy the measured
requirements.

## Product flow

The durable decision chain is:

```text
market state
-> strength direction
-> sector/theme
-> validated stock candidate
-> trade preparation
-> entry/invalidation
-> position management
```

Market Regime & Opportunities, Sector ETF Rotation, and Market Structure &
Activity are stable context workspaces. Quant Research Lab owns model identity,
factor/model/expression lineage, evidence, lifecycle, failure, and activation
history. Stock Candidates is a downstream consumer of only the small reviewed
set of separately activated Lab expressions; there is no permanent model-count
or fixed-strategy taxonomy.

The deployed Candidate score, Entry Geometry, and technical Strategy Channels
remain transparent but unvalidated Baseline V1. They are maintained for
compatibility and correctness, not tuned as the future model architecture.

## Quantitative research flow

```text
research question and point-in-time admitted data
-> bounded Factor Discovery
-> bounded Model Construction
-> bounded Strategy Expression
-> locked factor/model/expression lineage
-> locked validation
-> single sealed holdout
-> prospective shadow / paper evidence
-> separate activation
-> Stock Candidates
-> monitoring, decay, retirement, or rollback
```

Quant Research Lab is the human-readable authority. Under ADR 0194, a future
AI Quant Research Factory may support it with specialized hypothesis, data,
implementation, statistics, cost, red-team, reproduction, and shadow-monitor
roles. Agent work remains subject to one append-only experiment registry,
finite search budgets, stage-specific data access, deterministic calculation,
and human activation authority.

Strong-Leader Pullback proved a complete rejection-capable development path but
did not produce a locked model. The factory remains deferred until one complete
factor-to-model-to-expression lineage survives locked evaluation and
prospective shadow review. Initial orchestration stays local and bounded on
Dell; no long-running agent platform, service mesh, cluster, or automatic
trading path is implied.

## Data boundaries

Provider response schemas do not enter analytics directly. The layers remain
separate:

1. source observations and transport custody;
2. normalized provider-neutral records;
3. canonical facts keyed by stable `instrument_id` and effective time;
4. derived analytics and research evidence;
5. bounded product publications; and
6. static serving artifacts.

Ticker is display metadata, not a permanent join key. Current membership,
classification, revised facts, or successor mappings may not be projected
backward. Unknown, ambiguous, malformed, and insufficient evidence remains
quarantined.

Raw EOD bars are retained under their documented semantics. Corporate actions,
adjustment ledgers, lifecycle facts, labels, and model outputs remain separate
versioned families. Price return, shareholder total return, and option return
must never be conflated.

See [Data Boundaries](data-boundaries.md),
[Historical Research Data Foundation](historical-research-data-foundation-v1.md),
and the [Data Contract index](../data-contracts/README.md).

## Provider and credential boundary

Massive is the current replaceable U.S. equity EOD/reference provider for
private research. Provider adapters run only on Dell and return canonical
contracts before analysis. Credentials remain outside Git, logs, browser
bundles, and OCI artifacts. Every live request, entitlement-dependent feature,
new source family, and canonical Apply follows its reviewed operational
boundary.

IBKR is the preferred later account/portfolio integration. Options,
fundamentals, taxonomy, estimates, news, and lifecycle sources remain separate
selections driven by explicit data requirements and acceptance tests.

## Runtime and publication boundary

The active product is a Session-protected static Snapshot deployment. Dell
constructs immutable Market Intelligence, Dashboard Snapshot, and serving
bundles. OCI validates and atomically selects an approved release; it does not
run market analytics or store canonical history.

Guest and credential Sessions intentionally receive identical product data and
capability until the policy changes. Snapshot/API failures fail closed and
never substitute synthetic Production data. Demo fixtures are development-only
and explicitly labelled.

The guarded daily chain can be run by an agent. The installed timer is read-
only; no unattended write-capable scheduler is active. Exact current runtime
state belongs in [current context](../project/current-context.md).

## Security and operational invariants

- No secret, credential, Session material, raw provider body, or private key is
  committed or served.
- Canonical data and completed revisions are immutable; corrections append a
  governed version.
- Apply, publication, deployment, rollback, scheduler mutation, and destructive
  cleanup remain distinct reviewed operations.
- OCI receives only bounded serving artifacts, never complete Parquet history.
- Research code does not default to Production writes.
- Validation and holdout custody cannot be opened by a development agent.
- Model evidence never automatically activates Candidate output or creates an
  order.

## Deferred decisions

- database introduction after measured query/concurrency need;
- unattended write-capable daily automation;
- exact active-model applicability, decay, and retirement thresholds;
- complete point-in-time taxonomy, lifecycle, corporate-action, and execution-
  cost sources;
- options-expression, fundamentals/valuation, portfolio, and IBKR layers; and
- any guest/credential capability difference.

## Non-goals

- automated trading or order execution;
- HFT;
- opaque or ungoverned ML/prediction engines;
- unbounded AI factor search;
- large microservice, Kubernetes, or distributed architectures without a
  demonstrated requirement; and
- a large event knowledge base.
