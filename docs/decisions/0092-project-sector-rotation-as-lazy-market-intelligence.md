# ADR 0092: Project Sector Rotation as Lazy Market Intelligence

## Status

Accepted

## Date

2026-08-30

## Context

Sector ETF Rotation is the next link between Market Regime and Stock
Candidates. Its V1 result is a small, language-neutral market-intelligence
product with one market-wide answer, not a Primary/Secondary Universe result.
It must preserve the score-free 5/10/20-session facts and cannot imply
constituent breadth, fund flow, causality, or governed Theme membership.

The current Market Intelligence publication is the authoritative semantic
source for Dashboard analytics. The static Snapshot already supports lazy
Candidate detail files, while the first workspace must remain fast.

## Decision

Add Sector ETF Rotation through one additive contract chain:

1. The normal Phase 1a calculation process computes and audits rotation from
   the already loaded formal panel. It must not rescan canonical history.
2. Market Intelligence 1.3 binds the formally reread rotation audit and embeds
   exactly one `SectorEtfRotationSnapshotV1`. It does not duplicate the product
   by Universe.
3. Dashboard Snapshot 1.11 / Dashboard 2.8 projects that product to a dedicated
   `sector-etf-rotation.json` file with complete publication, audit, parameter,
   source, and product fingerprints.
4. The browser fetches this file only when the Sector Rotation workspace is
   opened. Failure is closed and does not substitute demo data.
5. The workspace presents relative-return windows, acceleration, leadership
   duration, and the four descriptive quadrants. It has no total score or trade
   verdict. Exact methods and fingerprints remain available but secondary.
6. Theme Rotation is shown as unavailable until governed effective-dated
   membership exists; no hand-maintained Theme list enters Production.

The intended first-level order is Market Regime, Sector Rotation, Market
Dashboard, then Stock Candidates. This follows the decision chain from market
state to direction and sector leadership before individual names. Guest and
credential Sessions receive the same file, page, and functionality.

No publication Apply, Snapshot activation, bundle, or deployment is authorized
by accepting this ADR.

## Consequences

- The initial page does not download the rotation payload.
- The market-wide product has one source of truth and cannot drift between
  Universes.
- Contract versions advance explicitly and older active releases remain
  readable.
- Production integration is gated on atomic daily audit production and strict
  reread validation.
- A later governed Industry or Theme dataset can add separate products without
  redefining Sector ETF V1.

## Alternatives Considered

### Put rotation directly in the existing Regime payload

Rejected because it couples a distinct product to the first-page payload and
encourages treating ETF rotation as a Regime subscore.

### Create a separate active publication and pointer

Rejected because it adds another approval, activation, and rollback system for
a small product that belongs to the existing Market Intelligence release.

### Duplicate rotation for Primary and Secondary Universes

Rejected because the fixed sector ETFs and SPY benchmark are identical for both
Universes; duplication would imply a distinction the calculation does not make.

### Ship a static Theme list now

Rejected because it would lack effective-dated, governed membership and create
look-ahead and classification drift risk.
