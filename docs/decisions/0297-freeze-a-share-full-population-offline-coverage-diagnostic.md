# ADR 0297: Freeze the A-share Full-Population Offline Coverage Diagnostic

## Status

Accepted

## Date

2026-09-17

## Context

The five-year SSE/SZSE source expansion and normalization reached 109/109
partitions. That milestone proves acquisition and normalization for the frozen
5,409-target source plan; it does not prove complete China A-share market
coverage, point-in-time availability, adjusted returns, daily Universe
membership, or backtest admission. In particular, 113 targets remain
quarantined, every normalized price-limit regime is unknown, every normalized
source-availability timestamp is null, and the corporate-action and
risk-warning evidence remains incomplete.

## Decision

1. Bind the next A-share stage to the immutable population, source-completion,
   and normalized-run fingerprints already in workstation custody.
2. Evaluate exactly 13 ordered evidence families. Keep resolved and
   quarantined populations separate and disclose all blocking dependencies.
3. Treat BaoStock suspension, warning, and adjustment observations as
   reconstructed source evidence only. They cannot prove official status
   subtype, event terms, or point-in-time public availability.
4. Do not extend the six-instrument pilot price-limit evaluator to the full
   population until effective-dated IPO, main-board legacy IPO, STAR/ChiNext,
   and risk-warning rule gaps are explicitly resolved.
5. Permit offline uniqueness, calendar, lifecycle, applicability, factor-step,
   and provisional-membership diagnostics. Do not infer missing official facts
   from ticker, name, code pattern, or provider factor movement.
6. Keep Historical Coverage, adjusted returns, backtesting, Factor Discovery,
   Product publication, and canonical Apply closed.

## Consequences

The existing five-year work is converted into a finite, reviewable admission
map rather than another download cycle. Follow-up evidence work is reduced to
explicit queues: 113 identity/board cases, effective-dated warning states,
corporate-action terms, special price-limit regimes, and terminal lifecycle
boundaries. BSE remains outside the current frozen source scope.

The first implementation stage now freezes exact input bindings and bounded
per-partition/ordered aggregate contracts. It classifies provider adjustment
observations only as first, changed, or no-op evidence and scans the existing
state files in bounded batches. It does not infer corporate actions, construct
returns, materialize a full daily Universe, or change any admission decision.
