# ADR 0015: Govern Security Types and Universe Eligibility

- Status: Accepted
- Date: 2026-08-15

## Context

Instrument Master V1 preserves stable identity but only distinguishes `common_stock` and `etf`. Dashboard Universe V1 consequently treated every comparable non-ETF record as an operating equity before exchange, previous-price, and previous-liquidity gates. That binary model cannot represent closed-end funds, BDCs, REIT subtypes, SPACs, preferreds, warrants, units, depositary receipts, or issuer domicile.

The 2026-08-14 read-only audit confirmed that VCX, a closed-end management investment company, passed the legacy default rule. AKAN separately demonstrates that U.S.-listed and U.S.-domiciled are different facts.

## Decision

Adopt an immutable, provider-neutral, effective-dated Security Classification V1 contract. It models security form, issuer economic structure, listing scope, classification status, evidence grade, and universe disposition independently. Effective intervals use `effective_from <= session_date < effective_to`; overlapping decisions for one stable `instrument_id` hard fail.

Evidence priority is authoritative regulatory/exchange/issuer material, explicit provider fields, verified identifier connections, then reviewed overrides. Names and ticker patterns may only produce review flags. Unknown, ambiguous, malformed, heuristic-only, and insufficient-evidence records are quarantined and cannot enter an equity candidate universe.

Phase A computes two non-production candidates:

- Core U.S. Domestic Operating Equities
- Broad U.S.-Listed Operating Equities

The product policy is now accepted: Core U.S. Domestic Operating Equities is the future default, and Broad U.S.-Listed Operating Equities is the future secondary selectable view. ETF/ETN records remain benchmark-only and are not equity-universe choices. Production activation remains deferred until authoritative evidence coverage and reconciliation gates pass.

Provider observations and canonical evidence are separate records. All normalized provider observations are retained by deterministic observation ID, including expected exclusions and unresolved records without canonical identity. Only uniquely mapped observations become canonical evidence. Canonical linkage denominators exclude expected-unjoined observations. Ticker fallback is allowed only for a unique point-in-time identity observation with an agreeing resolver; a duplicate ticker never causes an excluded observation to inherit another observation's canonical identity.

## Consequences

- Classification facts no longer change Instrument Master V1 semantics.
- U.S. listing, domicile, and incorporation remain distinct.
- ETF benchmarks remain outside equity breadth, movers, and activity-map membership.
- Manual overrides are stable-ID and effective-date keyed with authoritative evidence.
- Historical type changes append periods rather than rewriting history.
- Current production analytics remain on the legacy rule and must be disclosed as provisional until activation gates pass.

## Alternatives Considered

- Expanding the existing binary enum: rejected because it conflates identity and economic classification.
- Name/ticker inference: rejected as non-authoritative and unstable.
- Immediate production replacement: rejected because the persisted evidence cannot classify most non-ETF records reliably.
