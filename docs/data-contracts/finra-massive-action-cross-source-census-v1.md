# FINRA/Massive Action Cross-Source Census V1

## Purpose

This contract measures candidate-level action agreement between the complete
FINRA OTC Daily List range and the exact Massive split/dividend source
packages. It is a source comparison, not a stable-identity resolver or
canonical action publication.

## Contract

| Field | Value |
| --- | --- |
| Contract | `finra-massive-action-cross-source-census/1.0` |
| Evidence role | `candidate_corroboration_only` |
| Candidate key | exact effective date + FINRA old/new symbol to Massive ticker |
| Split numeric comparison | exact decimal `split_from`, `split_to` pair |
| Dividend numeric comparison | exact decimal amount; currency/basis unverified |
| Network / canonical / analytics / Product writes | zero |

The reader requires the sealed FINRA range census, rereads every underlying
FINRA package, recomputes its package chain, and requires an exact match. It
also formally rereads the two exact Massive packages. Each source binding
contains its declared range, count, and transitive manifest-chain fingerprint.

## Decision states

For each FINRA row carrying split or cash fields, the contract records:

- whether its effective date is inside the compared action range;
- whether the candidate key finds zero, one, or multiple Massive source
  occurrences;
- whether the numeric value finds zero, one, or multiple exact candidates;
- whether a unique key agrees or disagrees numerically; and
- whether numeric equality narrows an ambiguous key to one occurrence.

Provider IDs never deduplicate occurrences. A single row reached through both
old and new symbol is counted once by its source occurrence. All aggregates
are mutually reconciled by the typed model and bound by a logical fingerprint.

## Non-authority

Ticker/date agreement cannot establish stable identity. Event codes remain
opaque and no provider row is interpreted as current, cancelled, corrected,
or superseded. Cash equality cannot establish currency or gross/net/fee
semantics. The contract grants no Membership, lifecycle, terminal-return,
adjustment, research-readiness, model, Candidate, or Production authority.

The sealed output is owner-only mode `0400`, bounded to 1 MiB, refuses
overwrite, and is formally reread through the same typed contract.
