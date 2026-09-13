# ADR 0218: Classify Unresolved Corporate-Action History Without Assignment

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0217's complete-accounting five-year corporate-action resolution shadow
contains 113,149 typed rows whose provider ticker did not resolve on the exact
event date. Those rows represent 13,931 distinct normalized provider tickers.
They cannot be repaired by a latest-ticker or nearest-session fallback, but the
1,251 Identity sessions already bound to the shadow can measure whether the
same ticker ever referred to zero, one, or multiple stable instruments.

This is useful for choosing the next evidence source. It is not sufficient to
prove that a historical candidate owned the ticker on an event date, because a
ticker can be reused, disappear between observations, or be absent on the exact
date for a real lifecycle reason. Treating a unique history-wide candidate as
an assignment would silently convert outcome evidence into point-in-time fact.

The existing helper scans this history serially and returns only candidate ID
sets. It does not retain appearance ranges or counts and is too weak to become
a reproducible planning artifact.

## Decision

Create a separate owner-only unresolved-corporate-action census with these
rules:

1. Formally reread the exact ADR 0217 resolution shadow and its bound Identity
   evidence. Select only typed rows whose resolution status is `unresolved`.
2. Scan every bound Identity Resolver and classify each distinct unresolved
   provider ticker as `zero_historical_candidates`,
   `one_historical_candidate`, or `multiple_historical_candidates`.
3. Retain, per ticker and stable candidate, the first observed session, last
   observed session, and number of observed sessions. Retain unresolved source
   row counts, exact-date failure-reason counts, and action-type counts per
   ticker.
4. Use at most eight default and 32 maximum spawned workers over deterministic
   contiguous session blocks. Each worker formally verifies every assigned
   Resolver and returns only requested-ticker aggregates and ordered artifact
   bindings. The parent verifies full session coverage and merges results
   deterministically.
5. Bind the census to the resolution-shadow physical and logical identity, all
   scanned Resolver bindings, the clean implementation revision, and a fixed
   evaluation time. Publish atomically beneath one explicitly supplied direct
   child of an owner-only Dell custody root and formally reread it.
6. Classification never changes a source row, stable ID, quarantine status,
   canonical family, Historical Coverage, research admission, Candidate,
   Production, or website state. Stable-ID assignment count is literally zero.
   The seven unrepresentable source rows remain separately counted and outside
   ticker classification.

## Consequences

- The residual population becomes measurable without weakening exact-event-
  date identity rules.
- A one-candidate ticker is a bounded investigation lead, not a resolved
  corporate action. Multiple candidates explicitly expose ticker reuse or
  identity ambiguity; zero candidates expose a source/lifecycle coverage gap.
- The measured class distribution can determine whether official/free listing
  and corporate-action evidence is sufficient or whether a paid cross-venue
  source is justified for a named residual gap.
- Process count may change runtime but must not change contract content or the
  logical fingerprint, apart from the separately recorded operational field.

## Acceptance boundary

Focused tests must prove serial/parallel equivalence, all three classes,
per-candidate appearance ranges and counts, exact source-row accounting,
tamper refusal, owner-only atomic output, clean-revision enforcement, and zero
assignment. The real census must classify all 113,149 unresolved typed rows
and leave the seven unrepresentable rows explicit, with no network request,
`/data` write, canonical action or adjustment publication, analytics,
deployment, or scheduler change.
