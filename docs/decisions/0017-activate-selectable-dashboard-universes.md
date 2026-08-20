# ADR 0017: Activate Selectable Dashboard Universes

## Status

Accepted

## Date

2026-08-20

## Context

Trailing Liquidity V1 and the Universe pre-activation review are completed for analysis session 2026-08-19. The review recommends a provider-classified CS-only primary view and an ADR-inclusive secondary view. Legacy remains a useful rollback artifact but its binary classification and one-session liquidity rule are no longer the accepted normal Dashboard policy.

## Decision

Publish a versioned Dashboard Universe Activation with two active stable IDs:

- `provider_classified_common_shares_v1`, displayed as **Common Shares**, is the sole default;
- `provider_classified_common_shares_plus_adrs_v1`, displayed as **Common Shares + ADRs**, is optional.

The activation formally references the completed trailing-liquidity and reviewed-override publications, both current/previous EOD fingerprints, the exact trailing window, and the Legacy rollback publication. Routes, snapshots, and the React selector consume the completed activation reader. Unknown selections fail closed; no route silently falls back to Legacy or demo data.

Provider type `CS` does not prove issuer domicile or operating-company structure. The primary name therefore remains **Provider-Classified Common Shares (Provisional)**. Legacy remains readable and deployable as a rollback boundary but is absent from the ordinary selector.

## Consequences

- Every Universe-dependent Dashboard module uses the same stable-ID membership and fingerprint.
- The static private snapshot contains complete payloads for both activated universes and a fixed catalog; user input never constructs a filesystem path.
- SPY, QQQ, IWM, DIA, and the eleven Sector SPDR benchmarks remain independent context rows.
- Activation does not rewrite canonical EOD, identity, trailing-liquidity, override, review, or Legacy artifacts.
- Sector taxonomy and constituent breadth remain the next separate product phase.
