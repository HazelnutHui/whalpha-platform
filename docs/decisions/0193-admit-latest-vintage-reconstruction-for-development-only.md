# ADR 0193: Admit Latest-Vintage Reconstruction for Development Only

## Status

Accepted

## Date

2026-09-10

## Context

Strong-Leader Pullback V1 correctly refuses to treat historically backfilled
Membership as evidence that was actually observed before the modeled next
open. Only a small prospective Membership series currently meets that strict
knowledge-time test. Waiting for a full prospective development, validation,
and holdout history would prevent useful research for many months.

The retained historical Identity source interval from 2025-06-23 through
2026-08-12 contains 287 contiguous XNYS sessions before the first source gap.
The provider's dated reference query represents security status for the
requested date and avoids projecting the current constituent list backward.
However, Dell retrieved those snapshots later and did not preserve the exact
provider vintage that would have been returned on each historical session.
They therefore have revision risk and cannot be called `as_operated` or
strictly signal-time evidence.

V1 also requires both split and total-return adjustment for an experiment
whose declared label is underlying-stock price return. Adding dividends to
that label would change the estimand to shareholder total return and would
still not represent an option return.

## Decision

Add a versioned Strong-Leader Pullback development-admission policy that keeps
the frozen V1 experiment, formulas, parameter grid, statistics, and failure
record intact while creating one explicitly weaker evidence tier:
`reconstructed_point_in_time_latest_vintage`.

This tier has the following boundaries:

1. It is limited to the fixed 2025-06-23 through 2026-08-12 source interval of
   287 contiguous XNYS sessions. The 2026-08-13 and 2026-08-19 source gaps are
   not imputed, bridged, or moved inside the interval.
2. A provider snapshot must be queried for the represented session and must
   retain effective status, security form, exchange, stable-ID mapping,
   retrieval time, and exact source lineage. Current constituents, current
   classification, ticker-only joins, and undocumented historical availability
   remain prohibited.
3. The evidence is labelled latest-vintage reconstruction and
   `not_as_operated`. Historical revision/vintage bias is a required
   disclosure.
4. The first authorized use is an **outcome-blind coverage census only**. It
   may count source presence, stable-ID resolution, Membership dispositions,
   feature-path completeness, action/adjustment status, lifecycle/terminal
   status, and missing/quarantined records. It may not calculate triggers,
   returns, performance metrics, select thresholds, or select parameters.
5. After that census, a separate immutable admitted-cohort decision must set
   the exact coverage threshold and rejection rule using evidence completeness
   only, before any strategy outcome is opened. Missing instruments and
   unresolved facts remain in denominators and explicit quarantine; they are
   never silently dropped or filled.
6. If the later decision admits a cohort, this evidence tier may support the
   **development** interval only. Locked validation, sealed holdout,
   performance-grade claims, and Candidate activation require `as_operated` or
   otherwise source-time-defensible evidence under the existing next-open
   knowledge-time boundary.
7. The V2 label basis is split-adjusted **underlying-stock price return** from
   next open to the declared horizon close. Dividends remain visible event and
   risk context. They are not added to the price-return label, described as
   total return, or treated as option return.
8. A signal or outcome path crossing an unresolved split, reorganization,
   lineage, delisting, terminal event, or missing source boundary is
   quarantined. No zero return, neutral factor, successor join, or terminal
   value may be inferred by convenience.

The typed outcome-blind census contract, pure aggregator, network-disabled
reader, and owner-only `/tmp` report custody were implemented on 2026-09-10.
The fixed real census then completed and is recorded in the
[dated audit](../audits/strong-leader-pullback-development-coverage-census-2026-09-10.md).
It found zero all-required-evidence-complete paths because neutral sparse-row
adjustment evidence and lifecycle evidence remain unavailable. This decision
still grants no cohort admission, development execution, validation, holdout
access, performance claim, model activation, Candidate authority, provider
request, `/data` write, publication, deployment, or scheduler action.

## Consequences

- Development can eventually use a broad historical population without
  pretending that later-retrieved snapshots were contemporaneously observed.
- The project avoids the stronger current-constituent survivorship error while
  retaining the remaining latest-vintage revision limitation explicitly.
- Validation and holdout evidence will accumulate more slowly because their
  point-in-time standard is intentionally stronger than development.
- The coverage census can prove whether a practical admitted cohort exists
  before any return or attractive parameter result can influence its rules.
- V1 remains reproducible and may still be rejected or retained; the new
  policy does not rewrite its stricter complete-cross-section contract.

## Supersession scope

This decision narrows ADR 0151 only for a new development-only research tier.
ADR 0151 remains authoritative for signal-eligible, validation, holdout, and
Production claims. It supersedes ADR 0186 only for a future V2 development
input and price-return basis; the V1 input contract remains immutable.

## Alternatives considered

### Treat the reconstructed history as fully point-in-time

Rejected because the actual provider vintage and observation time for each
historical session were not preserved.

### Wait for 252 new prospective sessions before any research

Rejected as the only path because it is unnecessarily restrictive for
development. It remains the stronger path for validation and holdout.

### Choose a permissive coverage percentage now

Rejected because the missingness shape has not yet been measured under the
exact V2 scope. The threshold must follow an outcome-blind census and precede
all strategy outcomes.

### Require dividend total return for the stock-price timing question

Rejected because it changes the declared price-return estimand and can confuse
shareholder total return with the later options-expression problem.
