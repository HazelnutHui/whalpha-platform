# ADR 0196: Build a Five-Year Point-in-Time Research Foundation on Dell

- Status: Accepted
- Date: 2026-09-10

## Context

WH Alpha develops short-horizon, current-market equity models whose normal
calibration window may be six to twelve months. That model window does not
remove the need for a longer population and lifecycle record. A backtest over
current survivors, current classifications, or ticker-only histories remains
biased even when the test covers only one year.

The owner has selected five years as the first complete research-history
boundary. Dell already owns the provider-neutral Parquet/manifest mechanics,
306 aligned EOD and Identity sessions, 304 normalized historical Identity
source partitions, three prospective Membership sessions, bounded split and
dividend observations, split-only canonical facts, and a sparse split
adjustment ledger. The missing work is a complete point-in-time population,
identity/lifecycle continuity, canonical action and terminal evidence,
adjustment reconciliation, point-in-time fundamentals where required, and one
transitive Historical Coverage publication.

Massive Stocks Starter is available for private Dell acquisition and is the
primary price/reference input. Its fixed lifecycle diagnostic proved that it
cannot be the sole lifecycle authority. Commercial consolidated sources may
close difficult residuals, but making one sales process the only next action
would prevent independent progress on source-neutral data construction and
free official corroboration.

## Decision

Build the first professional research foundation as a Dell-owned, rolling
five-calendar-year point-in-time history using the existing canonical
Parquet/manifest architecture. No database service, distributed platform, or
OCI computation dependency is introduced.

The declared research interval ends at the latest completed canonical XNYS
session and begins five calendar years earlier at the first XNYS session on or
after that date. A registered experiment may require an additional bounded
pre-window warm-up or post-window outcome tail; those support sessions are
declared separately and do not silently shorten the five-year evaluation
interval.

The rolling window limits the first research scope, not all retention:

- EOD, Identity, Membership, and reconstructable point-in-time inputs maintain
  at least the declared five-year interval;
- stable identity, ticker history, lifecycle, corporate actions, terminal
  outcomes, superseded revisions, manifests, experiment records, and sealed
  evidence remain append-only while source permission permits;
- rebuildable feature/panel caches may use a shorter retention policy; and
- existing older canonical evidence is not deleted merely because it falls
  outside the active research interval.

### Source composition

No provider becomes canonical by first-non-null selection. Evidence is
resolved per fact family under Source Resolution Governance V1, with conflict
or insufficient evidence quarantined.

| Source | Accepted initial role | Explicit non-role |
| --- | --- | --- |
| Massive Stocks Starter | Primary raw EOD, dated reference observations, stable FIGI inputs, inactive-candidate discovery, and split/dividend source observations | Sole lifecycle, terminal-outcome, or point-in-time fundamentals authority |
| SEC EDGAR | Official issuer filings, filing/acceptance clocks, CIK history, merger/bankruptcy/deregistration evidence, and point-in-time XBRL fundamentals | Listed-security identity or exchange-trading-status authority; CIK alone never resolves `instrument_id` |
| FINRA OTC Daily List and notices | Official OTC additions, deletions, symbol/name changes, bankruptcies, distributions, splits, and halt/status evidence | Complete major-exchange lifecycle authority |
| OpenFIGI | Public stable-identifier crosswalk and ambiguity detection | Lifecycle, membership, eligibility, or terminal fact authority |
| Alpha Vantage Listing Status | Historical active/delisted population corroboration and discrepancy detection | Unilateral stable identity, last-tradable, consideration, or terminal-return authority |
| Nasdaq Trader current Symbol Directory | Prospective daily exchange-listing corroboration from the observation date forward | Free five-year historical corporate-action evidence; Nasdaq Daily List history is a separate paid product |
| Issuer filings and official venue notices | Exception evidence for named unresolved events | A silently scraped substitute for a complete source family |

Every new source starts with an exact field/clock/permission review and a
bounded representative pilot. Official or free does not by itself mean
complete, historically point-in-time, machine-readable, retainable, or
eligible for equal-session web display. Account creation, API-key creation,
purchase, or incompatible scraping is never inferred from this decision.

### Point-in-time and completeness rules

For every historical session, the foundation separates:

1. the securities observed as listed or otherwise tradeable;
2. the securities evaluated by the frozen Universe methodology; and
3. included, excluded, and quarantined strategy eligibility decisions.

All records preserve effective, source-available, and Dell-observed/ingested
times when the source supports them. A current status, taxonomy, liquidity
measure, or successor map is never projected backward. Later-retrieved dated
evidence remains labelled with its actual evidence tier.

Every instrument that met the declared strategy scope on any session remains
in the historical population after acquisition, bankruptcy, delisting, OTC
transition, or loss of eligibility. A historical path that crosses an
unresolved identity, action, or terminal event remains in the denominator and
is quarantined; it is not dropped, assigned zero, or joined to a successor by
convenience.

Five-year completeness is family- and scope-specific. It requires formal
readback of contiguous sessions, daily Membership, stable identity, lifecycle
and terminal disposition, applicable corporate actions, the selected return
basis, bounded quarantine/missingness, and immutable transitive manifests.
Price completeness cannot relabel another family complete.

### Research use

Current-market models may train or calibrate on rolling six- or twelve-month
windows. Their method must still be replayed across the five-year foundation
through chronological development and out-of-sample folds. Longer-horizon
fundamental, macro, or options research may later require a separately
approved deeper dataset; it must disclose the five-year limitation until then.

The complete-session, outcome-blind admission rule in ADR 0195 remains in
force. This decision changes the construction program and source order, not
the completeness threshold, holdout boundary, performance authority, or model
activation process.

### Progress and stop rules

Construction proceeds by independent family so one unresolved event does not
block unrelated work. Every bounded stage must:

- start from formally reread inputs;
- publish or retain a deterministic coverage/missingness result;
- record source conflicts and the chosen disposition;
- pass focused tests and an exact post-write readback before completion;
- update current status, the roadmap, changelog, and a dated audit when real
  state changes; and
- stop optimization when its declared acceptance criterion is met.

A paid source is reconsidered only after a residual-gap census names the exact
facts that official/free sources cannot establish and measures their impact on
session admission or outcome completeness.

## Consequences

- The five-year foundation, not a single vendor purchase, becomes the data
  program authority.
- Massive remains the primary price source and a partial lifecycle input.
- LSEG, ICE, S&P, Norgate, or another commercial source may later expand one
  measured family, but none is a prerequisite for continuing all other work.
- Free-source composition can reach a strong personal professional research
  standard while preserving explicit residual uncertainty; it cannot be
  described as CRSP-equivalent without evidence.
- Starting now, prospective daily source snapshots accumulate the strongest
  `as_operated` evidence while reconstructed history remains distinctly
  labelled.
- No incomplete row, session, or family is hidden to make the database appear
  complete.

## Supersession scope

This decision supersedes ADR 0168 only where that ADR made a cross-venue paid
sample the next external dependency and placed LSEG first in the mandatory
implementation order. ADR 0168's stable-ID, semantic, permission, sample, and
conflict gates remain authoritative for any commercial lifecycle adapter.

This ADR does not itself authorize credential disclosure, account creation,
purchase, public redistribution, Production publication, deployment, model
execution, or destructive cleanup. Operational actions still require the
active task authority and their existing exact-plan safeguards.
