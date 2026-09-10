# Historical Research Data Foundation V1

## Purpose

This document defines the source-neutral data and retention requirements that
must be satisfied before WH Alpha builds a performance-eligible Candidate
strategy panel. It is a design boundary, not a physical dataset or acquisition
authorization.

The provider-neutral Python/Pydantic row and coverage contracts plus explicit
PyArrow schemas and temporary-root Parquet repositories are now implemented
with synthetic tests. Saved synthetic split/dividend mapping, independent
adjustment invariants, and the default-deny exact pilot planner are also
implemented. A complete canonical historical research foundation remains
absent. The completed EOD/Identity price-history acquisition supplies only two
of the six required families. Data Record Governance V1 supplies the
cross-family state vocabulary without replacing these domain contracts.

ADR 0099 implements the physical Historical Coverage layer. It stores no
duplicate facts: each family evidence manifest transitively binds the original
completion manifest and payload hashes, and the final Coverage reader refuses
to return a typed claim if any referenced byte or boundary has drifted. ADR
0100 added the formal no-write EOD/Identity adapter. ADRs 0165–0166 subsequently
published the exact EOD and point-in-time Identity family-evidence manifests
under `/data` and passed a completed-state zero-write postflight. Final
Historical Coverage across every required family remains absent.

The immediate objective is not “more bars.” It is a history that can answer,
for each signal session, which instrument existed, which Universe decision was
valid, what the market knew, how later corporate actions affect the price path,
and whether the security reached a governed terminal outcome.

## Current readiness

The 2026-08-27 and 2026-08-30 audits retained the earlier 29- and 31-session
mechanics evidence. Canonical EOD/Identity depth has since exceeded the
252-session observation minimum, but the research foundation still has:

- only a small prospective canonical signal-eligible daily Universe
  Membership series, not research-ready historical coverage;
- one canonical split-only, outcome-reconciliation Corporate Action
  publication, but no complete action-type/revision/availability or lifecycle
  dataset;
- one governed sparse split-only outcome-reconciliation ledger, but no
  complete adjustment or terminal-outcome coverage; and
- no immutable Historical Coverage publication binding all required families.

Exact current price-session depth belongs in
[current context](../project/current-context.md). The 504-session preference
for stronger Regime review remains a future depth target, not a prerequisite
that can replace the missing point-in-time families.

ADRs 0137–0145 established canonical normalized source observations for the
initial profile-bound Identity sessions, followed by append-only daily
custody. Exact current partition count and missing dates belong in
[current context](../project/current-context.md). These
historical observations remain eligible only for outcome reconciliation
because Dell observed the backfilled packages after their historical sessions.
ADR 0150 adds a directly bound daily variant that is eligible no earlier than
its actual observation time. Missing or provider-revised sources and all later
research families remain explicit, so canonical source presence does not
change readiness.

The formal state therefore remains
`NOT_READY_FOR_PERFORMANCE_EVALUATION`.

ADR 0167 adds a temporary, no-authority corroboration queue for the 547
latest-anchor inactive-lifecycle review candidates. It makes the missing
effective-date, last-tradable-session, terminal, successor/consideration, and
knowledge-time evidence executable without creating a lifecycle fact. The 271
XNAS rows have only a documented-source pilot route; the remaining 276 rows
still lack an all-exchange source selection. This planning evidence does not
change readiness.

ADR 0168 records the subsequent official-source review. A cross-venue
corporate-action/trading-status product is the preferred first inquiry and
sample route, with Nasdaq, NYSE, and Cboe evidence retained as venue-specific
benchmarks. No adapter is implemented before a real licensed sample passes the
deterministic 30-item stable-ID and semantic diagnostic. A partially useful
source may be a corroborator, but it cannot silently become the primary
lifecycle authority. This source-selection gate also does not change
readiness.

## Governing principles

- Dell is the only compute, historical-storage, and data-governance authority.
- OCI receives only separately approved serving artifacts.
- Stable `instrument_id` is the join key; ticker is effective-dated display
  identity.
- Provider observations, canonical facts, derived facts, research panels, and
  published product payloads remain separate.
- Completed revisions are immutable. Corrections append a new revision and
  preserve superseded evidence.
- Unknown, ambiguous, malformed, heuristic-only, and insufficient-evidence
  records remain quarantined.
- No current membership, ticker resolver, classification, or successor map may
  be projected backward.
- Raw OHLCV is retained as received under documented unadjusted semantics and
  is never overwritten by an adjusted series.
- A source claim, account entitlement, physical implementation, and completed
  historical coverage are four different states.

## Required data families

| Family | Grain | Authority | Required role |
| --- | --- | --- | --- |
| Canonical EOD Price Bar | instrument, session, source, revision | Implemented canonical fact | Raw OHLCV and outcome path |
| Point-in-time Identity | source observation and resolved instrument as of date | Implemented resolved snapshots; normalized source observations are canonical for the exact sessions reported by current context | Stable-ID/ticker/exchange/status evidence |
| Daily Universe Membership | universe, instrument, session, methodology | Derived canonical decision | Performance-eligible historical population |
| Corporate Action | instrument, action, source, revision | Canonical event fact | Splits, distributions, reorganizations, symbol changes, delistings |
| Instrument Lifecycle | instrument validity interval or lineage event, source, revision | Canonical identity fact | Active/inactive/delisted state, ticker history, predecessor/successor evidence |
| Adjustment Ledger | instrument, source session, basis session, method revision | Sparse split-only outcome reconciliation is canonical; complete coverage remains absent | Explicit price/share/total-return transformations |
| Historical Coverage Manifest | dataset family, bounded session/range, revision | Manifest only | Counts, fingerprints, source bounds, completeness and quarantine state |

The coverage manifest references the six families. It does not duplicate their
rows and cannot upgrade incomplete evidence to complete.

## Three-time rule

Historical records must preserve three distinct clocks:

1. **Effective time** — when the market or legal fact applies, such as an ex
   date, listing-status interval, or Universe session.
2. **Source-available time** — when the selected source says the fact became
   available, when that timestamp exists and its semantics are documented.
3. **Ingested time** — when Dell actually observed and normalized the record.

Backfill naturally has an ingested time later than its effective time. That is
not itself leakage. A historical signal feature is eligible only when the
record has defensible point-in-time semantics and its source-available cutoff
is no later than the signal cutoff. If historical availability is unknown, the
record may support later outcome reconciliation but cannot be presented as a
fact known to the signal.

Corporate actions that occur after a sealed signal may be used later to mature
or quarantine its outcome. They may not be inserted into the sealed signal.

## Daily Universe Membership requirements

Universe Membership V1 remains the logical starting point. Physical
implementation must additionally bind each completed daily partition to:

- `universe_id`, session, and methodology version;
- exact evaluated-base fingerprint and count;
- exact source Identity, security-evidence, classification, price-history, and
  override fingerprints used by the methodology;
- included, excluded, and quarantined counts;
- one explicit disposition for every instrument in the evaluated base;
- source cutoff and evaluation timestamp;
- deterministic decision fingerprint and completion status.

An omitted instrument is not equivalent to exclusion. Missing critical input
is quarantine or explicit review, not membership `false` by convenience.

Two legitimate point-in-time origins may exist:

- `as_operated`: the immutable decision actually produced for that session;
- `reconstructed_point_in_time`: a later computation using only evidence that
  was valid and knowable at that historical cutoff under a frozen methodology.

Both require exact lineage. `current_as_of_constituent_replay` remains
research-only and ineligible for performance claims.

The active provider-form Primary/Secondary Activation is provisional. A
historical reconstruction must preserve that security-form limitation and may
not retroactively claim Core/Broad issuer-structure evidence.

## Corporate-action requirements

Corporate Action V1 remains the canonical event starting point. Before a
physical implementation, its source observation must also preserve:

- provider/source action identifier and source revision;
- first-observed and ingested timestamps;
- source-published/available timestamp when the source supplies one;
- separate announcement, ex, record, pay, and effective dates;
- evidence quality and ambiguity reason codes;
- predecessor, successor, related instrument, cash consideration, and exchange
  ratio only when supported;
- cancellation or correction without deleting the prior revision.

Splits, reverse splits, cash dividends, stock dividends, symbol changes,
mergers, spinoffs, and delistings are the V1 action scope. Complex tax and
cost-basis treatment remains deferred.

No action should be inferred solely from a large price move, ticker pattern,
or disappearing bar. Those observations may create review flags only.

## Instrument lifecycle and lineage requirements

Instrument Master snapshots are observations, not by themselves a complete
lifecycle ledger. The future lifecycle family must preserve:

- instrument status validity intervals;
- effective-dated ticker and primary-exchange history;
- first and last tradable session when supported;
- inactive, delisted, acquired, merged, reorganized, or unknown terminal state;
- predecessor/successor relationships with evidence grade;
- terminal cash/stock consideration facts when available;
- explicit `unresolved` state when a disappearance has no governed cause.

A symbol change normally retains one `instrument_id`. A merger, spinoff, or
new share class may require distinct stable IDs and an explicit relationship.
Ambiguous lineage never auto-merges histories.

Delisting does not delete Identity or price history. A performance outcome that
crosses an unresolved terminal event remains quarantined; it is not silently
dropped and is not assigned zero without a documented terminal-outcome rule.

## Adjustment-ledger requirements

EOD Price Bar V1 raw fields remain unchanged. The canonical sparse split-only
ledger is derived from canonical actions and binds:

- `instrument_id`;
- source session and explicit basis session;
- source-action set fingerprint;
- calculation methodology version;
- split price multiplier to basis;
- split share/volume multiplier to basis;
- price-return bridge status;
- total-return multiplier to basis when cash distributions are intentionally
  included;
- source cutoff, revision, quality status, and reason codes.

The exact multiplier direction must appear in field names and contract tests.
Price return and total return remain different series. Cash dividends do not
modify raw OHLC, and split-adjusted price must not be labelled total return.

ADR 0178 publishes only affected or quarantined EOD paths to one explicit
basis. Its split ratios, reciprocal factors, extremes, quarantine reasons, and
reverse application invariants are independently reconciled. Dividend and
complete-coverage reconciliation remain future work. A neutral factor of one
is usable only when the action-coverage manifest proves that it was derived
from complete coverage; an omitted row or a default one with
`adjustment_factors_unverified` is not evidence of no action.

## Coverage and readiness states

Each bounded history build reports one of:

- `mechanics_only`: schemas and ordering are testable but research blockers
  remain;
- `source_incomplete`: at least one required source family lacks coverage;
- `quarantined`: physical coverage exists but material ambiguity remains;
- `research_ready`: all mandatory families and evaluation gates pass for the
  declared universe, interval, methodology, and outcome basis.

`research_ready` requires all of the following:

- contiguous XNYS session inventory for the declared interval;
- same-session EOD/Identity bindings;
- completed daily membership for the evaluated universe;
- corporate-action coverage across the feature and outcome interval;
- lifecycle and terminal-status coverage;
- adjustment-ledger reconciliation for the selected return basis;
- feature warm-up and forward-horizon maturity;
- bounded quarantine and missingness statistics;
- immutable manifests and successful formal rereads.

The state applies only to its exact scope. Readiness for raw-price momentum does
not imply readiness for total return, fundamentals, options, or a different
Universe.

## Retention policy direction

| Data class | Initial retention direction | Reason |
| --- | --- | --- |
| Canonical EOD, Identity, Membership | No automatic expiry while source permission remains valid; 504-session initial operating target | Reproducible point-in-time research |
| Corporate actions and lifecycle | Append-only while source permission remains valid | Sparse events affect all later interpretation |
| Adjustment revisions and manifests | No automatic expiry while their source facts may lawfully be retained | Reproduce prior labels and methodology |
| Sealed signals and matured outcomes | No automatic expiry after implementation | Preserve genuine out-of-sample evidence |
| Rebuildable panel caches | At least 90 days; content-addressed and safely disposable only by a future policy | Runtime efficiency, not canonical evidence |
| Staging and partial acquisition files | Operation-bounded; cleanup only after formal terminal classification | Avoid ambiguous partial state |
| Raw provider response bodies | Do not retain by default | Licensing, sensitive content, and unnecessary duplication; revisit explicitly |

This direction creates no deletion job. Source-specific termination or deletion
obligations override the no-expiry direction. A future retention change must
account for provider terms, account termination, backup, recovery, and
evaluation reproducibility through a separately reviewed deletion procedure.

## History depth

- ADR 0196 sets a rolling five-calendar-year point-in-time history as the
  first complete research-foundation target. It is the active construction
  scope, while six- or twelve-month windows remain model calibration choices.
- 252 contiguous completed sessions is the minimum acquisition floor in the
  current evaluation policy.
- 504 sessions is the preferred first target for Regime-stratified review.
- A raw session count is not the number of mature signal observations. The
  feature warm-up and maximum five-session outcome horizon reduce usable dates.
- A future formula with a longer lookback raises the required acquisition
  range; it cannot silently consume the evaluation interval as warm-up.
- The original 29-session sequence was mechanics-only. Canonical EOD/Identity
  now exceeds the 252-session floor, but the full research foundation remains
  blocked by the other required families and Coverage publication.
- Stable identity, lifecycle, corporate actions, terminal outcomes,
  superseded revisions, and research evidence remain append-only while source
  permission permits; the rolling window is not a deletion instruction.

## Physical storage direction

V1 remains Parquet-first under the approved Dell data root, with one explicit
schema-version directory, bounded partitions, deterministic ordering,
content fingerprints, physical file hashes, manifests, and atomic completion.
EOD/Identity paths and their family-evidence manifests are canonical. A small
prospective set of signal-eligible Membership partitions is canonical and
governed by its physical-first, marker-last publication boundary. ADR 0176
adds a sparse canonical split-only action publication, and ADR 0178 adds sparse
affected-path split adjustments, without claiming full Corporate Action or
Adjustment coverage. Lifecycle and final Historical Coverage remain absent;
no missing family has been populated as complete merely because partial
canonical evidence exists under `/data`.

The design should prefer:

- session partitions for daily observations and membership;
- bounded year or event-date partitions for sparse corporate actions;
- effective-date/as-of partitions for lifecycle observations;
- immutable methodology/revision partitions for derived adjustments;
- content-addressed reuse inside one build;
- compaction only through a separately reviewed immutable replacement.

No database, catalog service, distributed system, or OCI compute dependency is
required for this scale.

## Acquisition gates

Before any historical provider request or `/data` write, review and freeze:

1. exact provider endpoints and current plan entitlement;
2. lawful private-use and retention boundary;
3. requested dates, pages, calls, pacing, retry, and resume behavior;
4. expected rows/bytes and Dell staging/canonical paths;
5. raw-response retention decision;
6. mapping and quality gates;
7. idempotency, conflict, recovery, and rollback behavior;
8. pilot size and explicit authorization.

The completed EOD/Identity acquisition followed a small representative Pilot.
Any first acquisition for a new missing family or provider must likewise begin
with its own bounded representative Pilot rather than a bulk run.

## Deferred work

- Exact provider selection and live entitlement verification
- Corporate-action and lifecycle adapters
- Canonical adjustment coverage beyond the ADR 0177 sparse affected-path split
  candidate, including neutral-row proof and dividend total return
- Historical membership builder
- Canonical membership, action, lifecycle, adjustment, cost, and evaluation
  acquisition/build orchestration
- Backup and deletion policy
- Formula selection, signal generation, and performance evaluation
