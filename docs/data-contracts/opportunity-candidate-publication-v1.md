# Opportunity Candidate Publication V1

## Status and purpose

Implemented, published, and deployed from the completed 2026-08-24 baseline-3
Candidate audit through MI 1.1, Snapshot 1.6 / Dashboard 2.3, and the bound OCI
release. Future publication sequences remain separately approved.

Contract `opportunity-candidate-publication/1.0` is a bounded,
language-neutral consumer projection of the much larger canonical Candidate
audit. It supports discretionary research priority; it is not a recommendation,
success probability, order instruction, position exit, or option return.

## Source binding

The source block freezes the Candidate audit manifest SHA-256 and logical
fingerprint; score/state/risk history fingerprints; score and state
calculation, parameter-set, and parameter fingerprints; Oracle fingerprint and
zero-mismatch result; raw-fact/permutation and append/restart/future-prefix
equivalence gates; EOD, Identity, history, Activation, current batch, and six
current risk-result fingerprints. Any false Oracle/equivalence gate or changed
typed audit record fails before a consumer payload exists.

The current session, Primary-first Universe order, memberships, EOD, Identity,
and Activation lineage must match the enclosing Market Intelligence
publication. Stable `instrument_id` is the join key; ticker remains display
metadata and may change between sessions.

## Bounded product projection

Each Universe publishes:

- full member/bar-coverage, data-quality, and candidate-stage counts;
- Conservative, Balanced, and Aggressive eligible/rejected counts and the
  fixed 25/50/100 display lists in formal risk-rank order;
- the stable-ID deduplicated union of those display lists plus any current
  Prepare, Enter, or invalidated records;
- score, confidence decomposition, seven components and raw metrics, current
  state/gates, three risk dispositions, liquidity/volatility facts, registered
  ETF price proxy, structured supporting/counterevidence, invalidation codes,
  warnings, and source record fingerprints.

The projection does not copy all 1,700+ rejected assessments, raw EOD bars,
Parquet, provider payload, credential material, audit paths, or English
`human_explanation` text. The interface localizes stable codes and never parses
colon-delimited evidence or recalculates scores and rankings.

## Snapshot consumer

Snapshot 1.6 / Dashboard 2.3 writes
`private-data/v1/opportunity-candidates.json`. The envelope binds the same
Market Intelligence publication ID, payload SHA/logical fingerprint, Candidate
analytics fingerprint, default Universe, and Primary-first Universe order.
The Snapshot manifest additionally freezes the audit, parameter, state-
parameter, per-file, and displayed-count bindings. Missing, extra, symlinked,
hash-inconsistent, cross-publication, or contract-inconsistent files fail
closed with no demo or cached fallback.
