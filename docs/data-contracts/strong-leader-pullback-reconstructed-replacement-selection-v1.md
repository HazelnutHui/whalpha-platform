# Strong-Leader Pullback Reconstructed Replacement Selection V1

## Purpose

`strong-leader-pullback-reconstructed-replacement-selection/1.0` registers one
coverage-corrected selection attempt after the immutable V1 development result
ended at its Regime evidence floor. It does not change V1, the canonical
method, the 24 parameter values, the source dataset, or any return metric.

The policy version is
`strong-leader-pullback-reconstructed-replacement-selection-policy/2.0.0` and
its fingerprint is
`9fa09e0b627aed2c1bb1f108eec2d73bfeb3a5407b3c0850b3605b23ef0991f9`.
The protocol logical fingerprint is
`65e2258153e6f5462a440662826a2a20594d9a889aaaa0761b71531251e07a0d`.

## Source and trial lineage

The protocol is bound to V1 report SHA-256
`c29f04b5e6da95e2256c137f23d00898b313325ac09e982a991bb823ce0f7852`
and logical fingerprint
`f0006fa38a7a729dca5b2cd34369e7c3bd2110aa17096bcd091d72875ce71f7f`.
It records one prior protocol trial and becomes the second total trial. Its
single allowed execution is adaptive development evidence, not validation.

The only design inputs taken from V1 are non-return counts and disposition
states recorded in the formal V1 review. Outcome values are excluded from the
protocol-design fingerprint.

## Eligibility and selection

All 24 combinations are evaluated and retained. A combination enters the
common eligible set only when every terminal-endpoint scenario has at least 60
numeric signals, 60 numeric controls, 20 comparable sessions, and available
inference. Any unavailable primary-family source evidence blocks the entire
selection. Unexecutable rows remain explicit no-results and are never zero-
filled.

The three endpoint scenarios independently rank the common eligible set by the
unchanged primary three-session objective: greatest session-balanced contrast
lower 90% bound, then greatest mean contrast, numeric signal count, and stable
ID. The winner must be identical in every endpoint scenario.

The common winner must also pass the frozen 25-bps cost, both chronological-
half, positive-session-ratio, and 20% concentration gates in ADR 0272. Failure
produces no lock.

## Regime, Validation, and Holdout

Regime counts and descriptive contrasts remain complete. Regime-specific
inference requires 60 signals; smaller cells are explicitly inconclusive and
do not control the overall selection.

The protocol grants no Validation access. If a lock exists, a separate review
must verify the one-run budget, source and policy fingerprints, common eligible
set, gate results, and zero authority leakage. Only then may a fixed Validation
operation be designed at family-wise alpha 0.05 over the complete 24-member
family. Holdout remains sealed, single-use, and selected-combination-only after
Validation passes.

Candidate activation, Lab performance publication, deployment, Production,
canonical `/data` writes, provider requests, and order execution are all false.

## Result and custody

The result contract is
`strong-leader-pullback-reconstructed-replacement-selection-result/1.0`. It
retains all 24 per-parameter eligibility decisions, three endpoint winner IDs,
the stable provisional winner when one exists, all six gate observations and
pass states, an exact terminal status, and a parameter lock only when every
gate passes. Its validators recompute the status, reason codes, gate
fingerprint, lock linkage, and logical fingerprint rather than trusting stored
booleans.

The only permitted private result directory is `report=20260915-v1` beneath an
owner-only `0700` custody root. The canonical JSON is immutable `0400`, bounded
to 2 MiB, atomically retained, and exactly replayable. The result records zero
network requests and zero canonical-data or Production writes. It contains no
Validation or Holdout observations and every downstream authority flag is
false, including when the development status is `locked`.

Operational procedure is defined in the
[replacement-selection runbook](../operations/strong-leader-pullback-reconstructed-replacement-selection.md).
