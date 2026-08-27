# Opportunity Candidate Publication V1

## Status and purpose

Implemented, published, and deployed through the completed 2026-08-26
Candidate and Entry Geometry audits, MI 1.2, Snapshot 1.7 / Dashboard 2.4, and
the bound OCI release. Repository source adds an undeployed Snapshot 1.8 /
Dashboard 2.5 delivery projection. Future publication sequences remain
separately approved.

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

## Contract 1.1 entry-location extension

`opportunity-candidate-publication/1.1` retains every 1.0 leadership fact and
formal risk rank, embeds the typed `candidate-entry-geometry/1.0` record in
each published card, and adds per-risk-mode lane selections. The card union is
expanded only as needed to serve the bounded lanes; rows must still pass the
hard Candidate risk gate, and existing concentration caps remain in force.

The fixed lane order is `review_now`, `watch_trigger`, `wait_reset`, then
`other_research`, with a display cap of eight per lane. Qualifying counts refer
to the complete hard-qualified population, not the old 25/50/100 display union.
The source freezes the entry audit, parameter, Oracle, permutation, batch, and
lane-consumer fingerprints. Explicit booleans state that leadership rank is
preserved, entry location is separate, and reference support is not a stop
price. MI 1.2 and Snapshot 1.7 / Dashboard 2.4 are the matching consumers;
older 1.0/1.1/1.6/2.3 readers remain supported without inventing entry data.

## Snapshot 1.8 summary/detail projection

Snapshot 1.8 / Dashboard 2.5 changes only static delivery. Candidate
publication 1.1 and Market Intelligence 1.2 remain the authoritative full
analytics contracts.

`opportunity-candidates-summary.json` retains source lineage, complete
Universe/stage/quality counts, risk ranks, entry lanes, and the compact fields
needed for list rendering. Every list row binds its score fingerprint,
entry-geometry fingerprint, and one deterministic stable-ID detail shard.

Detail shards retain the original typed 1.1 cards. The formal Snapshot reader
validates all descriptor/file hashes and logical fingerprints, reconstructs
the full Candidate publication, and requires exact equality with its original
logical fingerprint. The frontend performs no score or explanation
calculation; it fetches one declared shard only after the user opens a stock.
Snapshot 1.7 remains readable as a rollback contract.
