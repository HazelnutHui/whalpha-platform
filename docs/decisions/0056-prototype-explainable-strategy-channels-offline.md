# ADR 0056: Prototype Explainable Strategy Channels Offline

## Status

Accepted

## Date

2026-08-28

## Context

The six-channel Candidate taxonomy exists, but the product still exposes one
general leadership view. Current governed inputs can describe three technical
archetypes mechanically. They cannot support value reversal, a defensible
technical reversal, or defensive rotation without substituting proxies for
missing facts. Historical readiness also remains below the 252-session floor,
so no parameter can claim outcome validation.

## Decision

Implement a Dell-only shadow preview for momentum breakout, strong-stock
pullback, and trend continuation. Each channel has its own fixed score formula,
status routing, reasons, counterevidence, invalidation, missing-evidence state,
and contiguous within-channel rank. Scores mean research priority inside one
channel only; a cross-channel total or comparison is prohibited.

Market and sector fit remain separate and explicitly unvalidated. They are not
hidden inside technical scores. Strong-stock pullback does not reuse the
general volume-participation component because orderly low-volume behavior is
already tested by Entry Geometry. Technical reversal, fundamental value
reversal, and defensive rotation emit explicit `unavailable` results until
their required evidence exists.

A bounded consumer retains full population counts but exposes at most the top
eight ranked explanations per channel. The preview is not connected to Market
Intelligence, Snapshot, frontend, Production, publication, or deployment.

## Consequences

- The user can inspect exactly why one security is ranked inside one technical
  archetype without treating the score as expected return or probability.
- Missing or quarantined inputs do not become zero or neutral scores.
- The 2026-08-26 cross-section is an implementation review only; it did not fit
  weights or thresholds.
- Chronological evaluation, product payload design, and activation review
  remain necessary before UI or Production use.
- Underlying-stock research results remain distinct from option returns.

## Implementation Evidence

The 2026-08-28 implementation now includes an independent calculation Oracle
and an atomic, immutable `/tmp` audit. On the complete 2026-08-26 Candidate and
Entry Geometry sources, both Primary and Secondary returned zero score, status,
or rank mismatches and passed input-permutation equivalence. This closes the
mechanical verification item only; the chronological-validation and activation
boundaries above remain unchanged.

## Alternatives Considered

- **Wait for full history before writing any feature code:** rejected because
  source-bound mechanics and explanations can be implemented safely without
  claiming validation.
- **Put ETF/sector alignment inside technical scores:** rejected after the real
  shadow review showed that missing driver mappings would unnecessarily make a
  large part of the Universe unavailable and would hide environment fit.
- **Classify channels in the browser:** rejected because financial logic must
  remain deterministic, source-bound, and testable on Dell.
- **Display every watch result:** rejected because hundreds of raw watch rows
  would recreate the signal-overload problem; the consumer cap is eight.
