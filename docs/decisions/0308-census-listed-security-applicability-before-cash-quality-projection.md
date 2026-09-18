# ADR 0308: Census Listed-Security Applicability Before Cash-Quality Projection

## Status

Accepted; projection remains blocked

## Date

2026-09-18

## Context

ADR 0307 produced 75,391 issuer-level TTM observations. A Company Facts CIK is
a filer identity, not a listed-security identity. Applying those observations
to stable instruments additionally requires session-exact CIK linkage,
knowledge-time evidence, security form, one-issuer/many-security treatment,
listing validity, and issuer operating-structure evidence.

The retained five-year filer/security package has daily stable
`instrument_id` decisions and source-observation clocks. The retained provider
security-form snapshot is explicit but dated only 2026-08-14; it is not an
effective-dated historical classification and does not prove issuer operating
structure or domicile.

## Decision

Adopt `quant-research-sec-cash-quality-security-applicability/1.0` as an
aggregate, outcome-blind census with no projection rows.

Recover each TTM observation's signal session only through its retained source
occurrence IDs and the direct-origin selection lineage. At that exact session,
require a daily stable-instrument CIK decision, a common-security form at the
coarse Instrument Master layer, unique common-security cardinality, and source
identity evidence known no later than the session open. Ticker is descriptive
only: changes are counted under the same stable `instrument_id` and never form
a join key. One issuer with several securities and one issuer with several
common securities are counted separately.

Provider `CS` and `ADRC` observations are retained only as non-effective-dated
diagnostic form evidence. ADRs remain distinct from common shares. ETFs and
other non-common forms cannot inherit issuer TTM values. Unknown form,
effective-date gaps, listing-interval gaps, issuer-structure gaps, and missing
or late knowledge clocks fail closed. SEC filer identity never supplies any of
those missing proofs.

The plan binds the TTM and direct-lineage artifacts, all selected daily-link
partition hashes and their manifest, the provider-form snapshot, and the XNYS
calendar version. Forward/reverse census fingerprints must match. Owner-only
atomic custody retains only plan, aggregate result, and verification; it does
not persist security-level TTM rows.

## Result

All 75,391 TTM observations recovered an original signal session across 1,056
distinct sessions. One observation precedes the retained daily-link range.
57,213 observations have at least one admitted same-session CIK link; 56,542
have one common security after quarantining 577 multi-common observations and
94 observations with no common security. The linked population covers 4,740
stable instruments; 254 stable instruments use more than one ticker over the
observed TTM sessions.

No observation has identity evidence known by its signal-session open. Of the
56,542 unique-common observations, 24,098 use outcome-reconciliation-only
identity evidence and 32,444 have source evidence observed after the signal
open. Another 18,177 lack an admitted same-session CIK link. Therefore fully
applicable coverage is zero and security projection remains blocked.

The non-admitting provider snapshot matches 48,276 common-share and 171 ADR
observations; 8,095 unique-common observations lack even that snapshot match.
All 48,447 matches lack historical effective intervals. All 56,542
unique-common observations lack authoritative issuer-structure evidence and a
listing interval beyond the exact daily occurrence.

## Required evidence map

1. Accumulate or acquire stable-instrument/CIK identity observations whose
   source clocks are provably no later than each historical signal open. Do not
   relabel retrospective reconstruction as historical knowledge.
2. Add an effective-dated security-form ledger keyed by stable
   `instrument_id`, explicitly separating common shares, foreign ordinary
   shares, ADR/ADS, preferreds, funds, units, warrants, rights, and unknowns.
3. Add effective-dated listing intervals and ticker aliases under the stable
   ID. Ticker changes must not split an instrument; ticker reuse must not merge
   instruments.
4. Add authoritative issuer/security relationships and issuer operating-
   structure evidence. Provider form and SEC filer facts cannot establish
   operating-company, REIT, BDC, fund, SPAC, domicile, or incorporation state.
5. Register a policy for multi-common issuers before any shared-issuer
   sensitivity. Per-share and class-specific facts remain prohibited without
   share-class evidence.

No factor, outcome, Validation, Holdout, Candidate, canonical research,
Product, Production, or security-projection authority is granted.
