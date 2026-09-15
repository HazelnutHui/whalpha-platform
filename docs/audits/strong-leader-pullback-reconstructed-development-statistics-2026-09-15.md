# Strong-Leader Pullback Reconstructed Development Statistics Review

Reviewed: 2026-09-15 UTC

## Verdict

The fixed Strong-Leader Pullback V1 reconstructed-development comparison is
complete and reproducible, but **inconclusive**. No parameter combination was
locked and Validation remains closed.

This is the registered failure-preserving outcome, not a runtime failure. The
review does not lower a gate, inspect Validation or Holdout, or convert the
private event study into a public performance claim.

## Exact bindings

- statistics implementation revision:
  `0d2b4641d105d652c3bff56a96b1c04b538c43ea`;
- source development manifest SHA-256:
  `92e9f078db840d3d8e341b4e15757429e26ff4acbdb9564aebb387aa07a5a267`;
- source development logical fingerprint:
  `91300da44caf35f838912db3d4060a6bbc98aeea23f81845194e1302e11c43c4`;
- report SHA-256:
  `c29f04b5e6da95e2256c137f23d00898b313325ac09e982a991bb823ce0f7852`;
- report logical fingerprint:
  `f0006fa38a7a729dca5b2cd34369e7c3bd2110aa17096bcd091d72875ce71f7f`;
- statistics policy fingerprint:
  `a420675be6c7eb580bc95906f4ef0588eccee0d9640047a57d459423e5708f37`;
  and
- private owner-only report:
  `historical-evidence/strong-leader-pullback-reconstructed-development-statistics/report=20260915-v1`.

The source covers 105 development signal sessions from 2025-07-23 through
2026-01-07, 166,313 observations, and 498,939 independent 1/3/5-session label
rows. The report contains the exact registered matrix of 24 parameter
combinations, three horizons, and three terminal-endpoint scenarios: 216
summaries in total.

## Gate result

The retained selection status is `inconclusive_evidence_floor`. Every endpoint
winner is null, the selected parameter ID is null, and no parameter-lock
object exists.

For the primary three-session `contrast_adverse` view:

- 23 of 24 combinations met the signal, control, and comparable-session
  inference floors;
- only one of 24 met the frozen reported-Regime observation floor;
- signal counts ranged from 46 to 1,513, control counts from 12,224 to 25,982,
  and paired-session counts from 35 to 105;
- 19 combinations produced between one and 47 Defensive signal observations,
  below the registered floor of 60;
- primary-family signal and control unavailable-evidence counts were zero;
- primary-family signal unexecutable counts were zero; and
- one no-next-open control disposition appeared in each parameter family and
  remained an explicit no-result rather than an imputed return.

The formal gate review used coverage, disposition, and selection-state fields.
It did not use development return values to redesign V1. The private report
retains the complete registered event-study metrics for evidence and later
failure analysis.

## Reproduction and custody

The complete backend suite passed 2,898 tests before the real run. The first
run atomically published the report under owner-only `0700/0400` custody. A
second zero-network run with the same source, revision, and creation time
recomputed the same report, returned `already_present`, and matched both
fingerprints. No staging residue remained.

Both runs reported zero network requests, zero canonical-data writes, and zero
Production writes. Validation and Holdout data were not accessed. Candidate
activation, publication, deployment, performance claims, and order execution
remain unauthorized.

## Decision and next action

Strong-Leader Pullback V1 stops at `development_inconclusive_no_parameter_lock`.
Its parameter grid, floors, and result must not be edited or rerun as a new V1
to manufacture a pass.

A replacement preregistered experiment may be designed from this explicit
coverage failure while preserving the untouched Validation and Holdout
partitions. It must receive a new version and fingerprint, a bounded trial
budget, and a before-results analysis plan. No replacement design is
authorized merely by this review.
