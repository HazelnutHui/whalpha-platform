# Candidate Strategy Channel Product V1

## Status

Implemented in repository source as an additive, language-neutral, read-only
projection of the formally audited Candidate strategy-channel preview. The
product entered Production with Snapshot 1.9 / Dashboard 2.6 and remains
supported by later additive contracts. Exact active release and contract state
belong in [current context](../project/current-context.md).

## Contract

`candidate-strategy-channel-product/1.0` contains both active Universes in
stable order and all six strategy channels in fixed order. For each channel it
retains full status counts and at most eight contiguous within-channel
Advance/Watch assessments. Full deprioritized and unavailable populations stay
in the Dell audit.

Each displayed assessment preserves:

- the exact within-channel score and rank;
- why it surfaced and its first rejection risk;
- supporting evidence and counterevidence;
- what would make it researchable, invalidation, and manual checks;
- explicit market-fit availability and warnings;
- exact Candidate, Entry Geometry, strategy-batch, consumer, parameter, audit,
  and independent-Oracle lineage.

The product prohibits cross-channel score comparison and states that the fixed
baseline is not chronologically validated. Research priority is not a trade
recommendation, price/volume is not fund flow, and underlying-stock results are
not option returns. Guest and credential Sessions receive identical content.

## Delivery boundary

Snapshot 1.9 / Dashboard 2.6 adds exactly
`candidate-strategy-channels.json` beside the unchanged Snapshot 1.8 Candidate
summary and stable-ID detail shards. The browser requests the strategy file
only after the user opens Strategy Channels and performs contract, hash, source,
Universe-order, channel-order, count, rank, and decision-boundary validation.
It never recalculates financial logic.

Snapshot 1.8 and older releases remain readable and cannot silently acquire
the strategy product. The completed publication does not grant standing
publication, bundle, activation, or deployment authority.

## Validation evidence

The 2026-08-29 publication built and formally reread Snapshot 1.9 / Dashboard
2.6 from the then-active 2026-08-28 Market Intelligence publication and strategy
audit. The strategy file is 195,425 bytes, its logical fingerprint is
`d4d8ea9a1ae7ae896d0569996810e2cabbca1f02641ee9193583db0ca29dee4b`,
and it binds audit fingerprint
`2f254623c9da96f36e57c9066bba406b688dee6c884cd3351fb8f5beaa517256`.
This proves projection mechanics only, not historical performance.
