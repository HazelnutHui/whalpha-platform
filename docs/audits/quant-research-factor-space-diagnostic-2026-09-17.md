# U.S. Factor-Space Diagnostic Audit — 2026-09-17

## Verdict

`ready_for_deduplicated_outcome_blind_intake`

The registered zero-outcome diagnostic and one independently materialized
exact replay are complete. They may govern redundancy review for the next
finite hypothesis intake. They do not admit Alpha, select a model input, open
Development outcomes, or change Candidate or Product authority.

## Bound result

| Panel | Rows | Complete cases | Registered inputs | Effective dimension | 80% / 90% / 95% components |
| --- | ---: | ---: | ---: | ---: | ---: |
| security cross-section | 167,860 | 165,430 | 20 | 9.1371 | 10 / 13 / 14 |
| Market-State time series | 106 | 106 | 10 | 4.5277 | 4 / 6 / 7 |

The stock panel remained a stable-instrument/session cross-section and the
Market-State panel remained one row per session. Session state was not copied
across stocks to inflate the sample.

The strongest stock-panel overlaps were:

- residual volatility with downside semideviation: Pearson `0.8839`;
- short-horizon relative reversal with intraday relative pressure reversal:
  Pearson `0.8448`;
- return acceleration with short-horizon reversal: Pearson `-0.7941`; and
- relative return, signed path efficiency, and distance from the prior high
  formed a separate leadership/path cluster.

The highest stock-panel VIF was `14.5671` for short-horizon relative reversal.
The highest Market-State VIF was `10.7306` for reconstructed breadth above its
20-session average. These are intake-design warnings, not automatic deletion
rules and not predictive evidence.

## Reproduction and side effects

Original and replay files are byte-identical at 115,522 bytes with SHA-256:

`2336546e1f48a35748aeb1bc5ffbc89bc69811f40f19b4bd35cb080d0c32757c`

Both runs produced logical fingerprint:

`f2042c0c5e5e020734ab58b0dfb2706a4543fdb664d2f56469e60dbb5fe8dd3f`

Both successful executions reported zero external requests, Development
outcome reads, Validation reads, Holdout reads, canonical `/data` writes, and
Production writes. Owner-only custody reread and exact byte comparison passed.

## Interpretation boundary

The 20 stock inputs are not 20 independent bets; their participation ratio is
about nine. The next intake should therefore propose hypotheses that add a
distinct mechanism or information set rather than another cosmetic transform
inside the measured reversal, path, risk, or breadth clusters. PCA components
remain diagnostics and cannot be treated as Alpha or promoted directly into a
model.

## Next gate

Register a separately finite, outcome-blind successor hypothesis intake using
the measured clusters for deduplication. Prior failed trials remain closed,
and Model Construction, Strategy Expression, Validation, Holdout, Candidate,
publication, broker, and trading authority remain locked.
