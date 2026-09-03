# ADR 0124: Exclude Catalog-Known ETV Without Inferring ETF

## Status

Accepted

## Date

2026-09-03

## Context

The 300-session Historical Research Backfill stopped at 245 contiguous EOD
sessions while building the 2025-09-09 Identity plan. Its complete immutable
source package contained 11,714 observations: 68 used provider type `ETV` and
113 had no provider type. Treating both groups as malformed produced a 1.5452%
malformed ratio and correctly failed the unchanged 1% quality gate.

The formally retained Massive type catalog identifies `ETV` as “Exchange
Traded Vehicle”, with asset class `stocks` and locale `us`. The same catalog
defines `ETF` separately. Across retained historical packages, `ETV` is a
stable catalog code, while missing type remains absence of required evidence.
Neither fact establishes a specific provider-neutral security form, issuer
structure, or Universe eligibility.

## Decision

- Treat catalog-known `ETV` as a known but unsupported provider type and an
  expected exclusion from Instrument Master V1 and the active provider-form
  Primary/Secondary Universes.
- Do not infer that `ETV` means ETF, fund share, common stock, or any other
  provider-neutral `SecurityForm`; formal security evidence retains
  `SecurityForm.UNKNOWN`.
- Never create an Instrument Master row or ticker-resolver row from an `ETV`
  observation under this rule.
- Keep a missing provider type malformed and quarantined.
- Keep the 1% malformed-ratio gate and every ambiguity, collision, identity,
  custody, inventory, and formal-reread gate unchanged.
- Apply the rule prospectively when a new immutable point-in-time snapshot is
  built. Do not rewrite completed historical snapshots; any future historical
  normalization must be a separately versioned derived mapping.

## Consequences

- A stable catalog taxonomy code no longer consumes the malformed-data budget,
  while genuinely missing type evidence still does.
- The rule cannot enlarge either active Universe and cannot silently turn a
  generic exchange-traded vehicle into an ETF.
- The 2025-09-09 package can pass the unchanged quality gate because its 113
  missing-type observations alone represent 0.9647% of the 11,714 records.
- Immutable snapshots retain the policy that was active when they were
  created; provenance remains explicit rather than being overwritten.
- A future decision to model exchange-traded vehicle subtypes requires better
  evidence, a versioned contract/ruleset, and separate review.

## Alternatives Considered

- Map `ETV` to ETF or `SecurityForm.FUND_SHARE`: rejected because the provider
  catalog defines ETF separately and the generic label does not prove subtype.
- Raise the malformed threshold: rejected because it would weaken the quality
  gate for genuinely missing or malformed records.
- Leave `ETV` malformed: rejected because the retained catalog proves it is a
  recognized provider category, and doing so makes a stable taxonomy value
  indistinguishable from absent evidence.
