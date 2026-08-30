# ADR 0090: Build Sector ETF Rotation Without a Composite Score

## Status

Accepted

## Date

2026-08-30

## Context

The decision chain needs a first-class layer between market state and Stock
Candidates. The current Dashboard shows only one-session returns for 11 sector
benchmark ETFs. Calling that display sector rotation would overstate the
evidence. The governed Market Regime input already contains the fixed ETF
basket and enough sessions for transparent 5/10/20-session comparisons, but
the project still lacks point-in-time traditional sector membership and a
reviewed Theme membership set.

## Decision

Create a source-bound `sector-etf-rotation/1.0` research product over the fixed
11 sector ETF registry and SPY. It exposes separate 5/10/20-session ETF return,
SPY return, arithmetic relative return, and within-window rank. It also exposes
the change in five-session relative return versus the immediately preceding
five sessions and the current five-session leadership run length.

Do not create a composite score. A descriptive four-quadrant posture uses only
the sign of 20-session relative return and the sign of five-session relative
acceleration: leading/improving, leading/weakening, lagging/improving, or
lagging/weakening. Exact zero is neutral. Missing inputs are never imputed and
are excluded from only the affected cross-sectional rank.

The product is explicitly an ETF price proxy. It is not sector constituent
breadth, official security classification, fund flow, alpha, causal
attribution, or a trade instruction. Theme output remains unavailable until a
curated, effective-dated membership methodology is accepted and physically
implemented.

This first slice adds the contract and deterministic calculation only. It does
not add a Snapshot file, API route, first-level navigation, publication,
deployment, or automatic daily stage.

## Consequences

- Users can compare like-for-like sector proxies on multiple independent axes
  without hiding disagreements inside one score.
- The four quadrants remain inspectable facts rather than a prediction model.
- Twenty-one sessions are enough for mechanics, but not for performance claims
  or threshold calibration; chronological validation still needs the governed
  historical foundation.
- A later product projection can combine this sector-only result with existing
  relationship evidence, while preserving separate contracts and warnings.

## Alternatives Considered

### Re-label the current one-session sector strip as rotation

Rejected because one session cannot establish persistence, acceleration, or a
multi-window leadership structure.

### Rank sectors with one weighted total

Rejected because weighting 5/10/20 windows would hide whether a sector is a
durable leader, a weakening leader, or an improving laggard.

### Add Themes from ticker names or current memberships

Rejected because heuristic labels and backward-projected memberships violate
the accepted classification and point-in-time boundaries.
