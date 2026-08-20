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

Phase B1B persisted the official provider type catalog and point-in-time observations under these rules. A logical completion manifest, rather than any one component partition, defines a completed provider evidence snapshot. The resulting provider evidence establishes security form at useful coverage but does not satisfy the authoritative issuer-structure or domicile gate; production Core/Broad activation remains deferred.

Phase B2A establishes a separate SEC issuer-structure evidence boundary. SEC filer identity, filing evidence, security identity, and Universe decisions remain distinct. CIK and ticker cannot independently create canonical security identity. Official fund/BDC datasets and effective-dated filing state machines may establish exclusions; cover-page facts may establish security form only after a consistent point-in-time identity join. Missing or conflicting evidence remains quarantined. This clarification does not activate Core/Broad or authorize a live SEC request.

Phase B2B adds a bounded live-source implementation without changing activation status. Official source files are first streamed into an atomic source cache, then normalized into observation and canonical evidence datasets, and only a separate logical manifest marks the evidence snapshot completed. A source-discovery or quality failure cannot create that marker. The first authorized run stopped at the CSV discovery gate and published no evidence; Core/Broad activation remains deferred.

SEC landing-page version selection uses explicit table-row year, format, and effective/update date rather than HTML order or a hard-coded current URL. The latest candidate not later than the evidence cutoff is selected; ambiguous same-date URLs fail closed. This preserves point-in-time evidence semantics and does not alter the deferred production policy.

After SEC B2 was paused, the completed Massive evidence was used offline for two explicitly provisional shadows: provider `CS` only, and `CS` plus a separately counted `ADRC` layer. This is a reversible audit application of the existing evidence hierarchy, not a new Core/Broad decision. Security-form classification and tradability filtering are separate; the latter uses the current one-session USD 5/USD 20M Decimal gates and must be labeled provisional. Provider `CS` cannot establish domicile or issuer structure, and known reviewed contradictions remain report-only until a completed reviewed-override dataset can be read and reconciled.

The pre-activation implementation defines that missing boundary: reviewed facts are immutable stable-`instrument_id`, effective-dated shadow rows with explicit evidence provenance. They are applied after upstream tradability gates, so an `allow` decision cannot manufacture price, liquidity, or history eligibility. Publication of the boundary remains distinct from production activation.

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
