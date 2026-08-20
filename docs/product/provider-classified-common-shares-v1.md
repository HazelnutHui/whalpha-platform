# Provider-Classified Common Shares V1

This is a non-production, point-in-time shadow classification. It does not replace Dashboard Universe V1.

## Candidates

- `provider_classified_common_shares_v1`: **Provider-Classified Common Shares (Provisional)** / **供应商分类普通股（暂定）**. Only canonical Massive type `CS` is eligible.
- `provider_classified_common_shares_plus_adrs_shadow_v1`: **Provider-Classified Common Shares + ADRs (Shadow)** / **供应商分类普通股及ADR（影子比较）**. It adds canonical type `ADRC` to the first candidate; ADRC remains separately counted.

Provider type is security-form evidence only. `CS` does not establish U.S. domicile, operating-company status, or absence of REIT, BDC, SPAC, closed-end-fund, or provider-classification exceptions. Neither candidate is Core U.S. Domestic Operating Equities, a Russell-like universe, or a complete U.S. equity market.

## Classification

Membership begins from the completed 2026-08-14 canonical provider evidence keyed by stable `instrument_id`. Exactly one evidence record must exist, its type must be present in the completed provider catalog, its date cannot be later than the analysis date, and its instrument must exist in the completed Instrument Master. Ticker-only joins and inference from name, CIK, FIGI, description, or the old binary `InstrumentType` are prohibited.

Missing, new/unknown, multiple, conflicting, future-dated, malformed, ambiguous, collision, orphan, or formally contradicted evidence is quarantined. Explicit types other than `CS`/`ADRC` are deterministic exclusions. A completed 2026-08-19 pre-activation review now publishes a versioned stable-ID override overlay: VCX has an authoritative exclusion and AKAN an authoritative allow. Neither changes trailing-qualified membership because VCX already fails liquidity and AKAN already fails price; `allow` cannot bypass those gates. Other unresolved edge records remain unchanged.

## Tradability Layer

Security-form classification is applied before, and independently from, this sequential analysis filter:

1. current and previous completed canonical bars exist;
2. current primary exchange is one of `XNYS`, `XNAS`, `ARCX`, or `BATS`;
3. previous close is at least USD 5;
4. exact Decimal previous close × previous volume is at least USD 20 million.

This is `one_session_liquidity_provisional`, not trailing liquidity. A future production review needs a point-in-time multi-session liquidity rule and issuer-structure evidence.

## Activation Boundary

The implementation is a provider-neutral frozen offline audit service. It writes no production dataset, changes no API or frontend response, and cannot activate Core/Broad or Dashboard membership. See the [2026-08-14 shadow audit](../audits/provider-classified-common-shares-2026-08-14.md).
