# ADR 0064: Separate Breakout Stage from Breakout Quality

## Status

Accepted

## Date

2026-08-28

## Context

The Momentum Breakout channel correctly routes confirmed breakouts to
`advance_to_research` and routes both near-trigger and strong-but-extended
securities to `watch_for_trigger`. The shared Watch label is operationally
safe, but it can be read as though every displayed member is a nearly completed
breakout. The real 2026-08-26 Primary population contains 10 Advance and 232
Watch records; 98 of the Watch records carry high or extreme extension and are
waiting for a reset rather than waiting for an upside trigger.

The existing Entry Geometry facts already describe the five-session trigger,
current gap, range, close location, volume, and moving-average extension. They
do not describe whether the pre-trigger range was compact or contracting,
whether the close cleared a broader twenty-session high, or how much of the
recent path came from the current session.

## Decision

Keep the frozen Strategy Preview score, status, and rank unchanged. In the
browser, render the Momentum Breakout technical setup as an explicit stage:

- `breakout_confirmed` → Triggered · review;
- `breakout_watch` → Near trigger; and
- `strong_but_extended` → Extended · reset first.

Also state explicitly that the combined Advance + Watch pool is not a list of
completed breakouts.

Advance the descriptive Continuation Facts contract to 1.1 and add six
breakout-anatomy facts:

- prior ten-session closing range divided by prior ATR14;
- prior ATR5 divided by prior ATR14;
- current close versus the prior twenty-session closing high in prior ATR14;
- current close-to-close and open-to-close moves in prior ATR14; and
- the current session's share of the last ten absolute log-return path.

All breakout denominators and reference highs end at t-1. The trigger session
therefore cannot make its own preceding base look tighter. These remain
source-bound shadow facts with an independent raw-panel Oracle. They do not
enter Strategy score, status, rank, Snapshot, or Dashboard payloads.

## Consequences

- The visible list distinguishes an actionable research trigger from a near
  trigger and from a chase-risk reset without changing the audited ranking.
- The next chronological study can evaluate base quality and pulse risk as
  separate facts rather than hiding them inside a new opaque score.
- The real 2026-08-26 audit assessed 3,543 rows with zero unavailable facts,
  zero Oracle mismatch, and exact input-permutation equivalence.
- Only 5 of the 10 Primary Advance records also closed above the prior
  twenty-session closing high, and 5 showed prior ATR5 below prior ATR14. No
  single cross-section is used to turn those observations into gates.

## Alternatives Considered

### Remove extended leaders from Watch immediately

Rejected for now because the label can be corrected without selecting a new
outcome-unvalidated status rule. A later version can split status after a
chronological policy is preregistered.

### Add the six facts directly to the Breakout score

Rejected because the repository has insufficient matured history to establish
which combinations improve one-, three-, or five-session outcomes.
