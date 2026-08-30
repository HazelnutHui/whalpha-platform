# ADR 0088: Bind Candidate Visual Context to Real Dell History

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0087 deliberately limited the first Candidate position map to current
published reference levels. A real price path and state age cannot be inferred
from those summary values. They require exact daily closes, Candidate state
history, stable instrument identity, and explicit missing-history semantics.

## Decision

Add `candidate-visual-context/1.0` as an independent, shadow-only Dell
calculation. One record is keyed by session, Universe, and stable
`instrument_id`. It binds the current Candidate score row, Entry Geometry row,
formal 26-session panel, and cumulative Candidate state ledger.

The price-path side contains exactly the latest 20 ordered canonical closes. It
is available only when every expected session exists, every close is positive,
Entry Geometry is available, and the current close agrees exactly with Entry
Geometry. Otherwise it is empty with a reason. Current SMA10/SMA20, prior-five-
session close high/low, and selected reference support are copied from the
source-bound Entry Geometry record rather than recomputed in the browser.

The state side publishes an `observed_state_age_sessions`, not an unrestricted
signal age. It walks backward through the exact retained Candidate sessions and
stops at a stage change, unavailable row, stale row, or missing row. If the same
state reaches the beginning of retained history, `left_censored=true`: the
result means at least that many observed sessions and does not claim the true
start date.

An independent validator reads the raw panel, Entry Geometry, and state rows
without importing the production visual-context calculator. The tmp-only audit
requires zero mismatch and input-permutation equivalence. The CLI prohibits
network sockets and has no `/data`, publication, Snapshot, deployment, or
scheduler authority.

## Consequences

- A future lazy Candidate detail can display a real price path and honest state
  duration without inventing browser-side history.
- The output does not affect Candidate score, state, rank, strategy channel, or
  any outcome/performance claim.
- Canonical close history retains the source panel's price/adjustment and
  corporate-action governance; it is not automatically an option-return or
  total-return series.
- Snapshot/product integration remains a separate contract and review. The
  repository-only audit is not deployed.

## Alternatives Considered

### Reconstruct history in the browser

Rejected because the current publication does not carry daily closes or full
state history.

### Call confirmation count signal age

Rejected because confirmation is capped workflow support and does not prove
when the underlying market setup first began.

### Feed visual facts into strategy scores

Rejected because this change is explanatory and has no chronological outcome
validation.
