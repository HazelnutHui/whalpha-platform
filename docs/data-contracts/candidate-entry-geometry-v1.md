# Candidate Entry Geometry V1

## Status and purpose

Implemented as an offline source calculation and canonical `/tmp` audit. The
source remains separate from Candidate leadership and is never written into
`/data`. An additive, versioned consumer is implemented in repository source
through Candidate publication 1.1, MI 1.2, Snapshot 1.7 / Dashboard 2.4, and
the frontend; whether it is active must be checked in Current Context.

Contract `candidate-entry-geometry/1.0` supplements the deployed Candidate
leadership score. It measures technical entry location and chase risk without
changing Candidate facts, state, risk eligibility, or rank. It is research
triage, not a recommendation, success probability, order instruction, stop
price, position-sizing output, or option-return model.

The first parameter set is `candidate-entry-geometry-v1-fixed-baseline-1`,
fingerprint
`e531ffdc18d334329ac906cbe89f0cc88fc2e8932412ff0b6d8ce0b732cc25a1`.

## Source and grain

Each record is keyed by:

`as_of_session + universe_id + stable instrument_id`

The calculation requires the exact 26-session formal Market Regime input panel,
one verified current `opportunity-candidate/1.1` score row, and its current
Candidate state row. The batch binds the source Candidate batch fingerprint and
history-source fingerprint. The state ledger may also contain the explicitly
missing Universe members; they are reconciled but do not create synthetic entry
records.

## Fixed facts

Available records publish:

- close, SMA10, SMA20, and simple true-range ATR14;
- three- and five-session returns;
- close-to-SMA10 and close-to-SMA20 in ATR units;
- five-session return divided by the instrument's own volatility-scaled
  expected five-session move;
- trailing consecutive up sessions, capped at five;
- current open gap, daily range, and close location;
- current volume versus prior-20 median;
- prior-five-session close high and low;
- signed breakout/pullback distance in ATR units;
- the closest SMA20 or prior-five-session-low reference at or below close, plus
  its percentage distance.

Contiguous missing history, nonpositive ATR or realized volatility, unavailable
volume facts, invalid bars, or a zero current range makes the whole geometry
unavailable. It never zero-fills partial facts.

## Extension hierarchy

The fixed parameter payload defines low, moderate, high, and extreme extension
using the maximum applicable evidence across:

- close distance above SMA20 in ATR units;
- volatility-scaled five-session move;
- consecutive up sessions combined with SMA10 distance;
- positive gap in ATR units;
- a labelled volume/range climax-risk candidate.

The climax flag is a price/volume risk proxy, not proof of exhaustion, fund
flow, or subsequent reversal.

## Technical structures and posture

- `breakout_confirmed`: strong Candidate gates, score at least 70, a close no
  more than 0.75 ATR above the prior-five-session close high, volume ratio from
  1.20 through 2.50, close location at least 0.60, and no high extension.
- `breakout_watch`: strong Candidate gates, price from 0 through 0.75 ATR below
  the prior close high, bounded volume, and no high extension.
- `pullback`: strong Candidate gates, close at or above SMA20, within 0.75 ATR
  of SMA10, 0.25 through 2.00 ATR below the prior close high, volume ratio no
  more than 1.20, close location at least 0.35, and no high extension.
- `strong_but_extended`: strong Candidate gates plus high or extreme
  extension.
- `no_viable_setup`: no bounded structure satisfies the fixed rules.

Quarantined/failed sources, invalidated Candidate state, or a Candidate score
below 50 are deprioritized. High or extreme extension routes to
`wait_for_reset`; it cannot route to `technical_review_ready`.

Every record includes a first rejection code, why-now codes, supporting facts,
counterevidence, what would make it reviewable, technical invalidation review
codes, required manual checks, and explicit semantic warnings.

## Audit boundary

The canonical audit contains exactly:

- `entry-geometry-parameter-contract.json`;
- `entry-geometry-batches.json`;
- `entry-geometry-oracle-report.json`;
- last-written `entry-geometry-audit-manifest.json`.

Files are canonical JSON, owner-read-only, hash/fingerprint bound, and held in
an owner-controlled direct child of `/tmp`. The CLI prohibits network sockets.
The manifest fixes `shadow_only=true`, `external_request_count=0`, and
`production_write_count=0`. The independent Oracle repeats raw price-location
and classification calculations without importing the production calculator
and requires zero mismatch plus input-permutation equivalence.

## Additive lane consumer

`candidate-entry-lane-consumer/1.0` with parameter set
`candidate-entry-lane-consumer-v1-fixed-baseline-1` projects the full
hard-risk-qualified population into fixed `review_now`, `watch_trigger`,
`wait_reset`, and `other_research` lanes. Each lane has a display cap of eight
and reuses Candidate issuer/industry concentration limits. It does not change
the base score, state, eligibility, or original formal rank. The publication
binds the entry audit manifest, logical fingerprint, parameter/Oracle/batch
fingerprints, and the lane-consumer parameter fingerprint.
