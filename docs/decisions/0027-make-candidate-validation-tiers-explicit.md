# ADR 0027: Make Candidate Validation Tiers Explicit

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0022 separates the verified-prior daily append from the serial cold
reference, but the administrator CLI previously inferred the behavior only
from whether a prior audit was supplied. That is mechanically safe yet too
implicit for automation: a daily run, periodic reference rehearsal, and
calculation or state-machine change have different evidence obligations.

Repeating the cold replay every day wastes already verified work. Conversely,
calling an incremental result a periodic or model-change validation would
weaken the reference boundary. The tiers need explicit executable rules before
the daily scheduler is designed.

## Decision

Define three Candidate validation tiers:

- `daily`: requires an immediately prior formally verified Candidate audit,
  exact prefix/version/Activation/membership bindings, a one-session append,
  independent current-session score/risk/state Oracle, restart and prefix
  gates, and the complete cumulative audit. It cannot run without
  `--prior-candidate-audit`.
- `periodic`: calculation produces a cold full-replay reference without a
  prior Candidate audit. Formal verification then compares a same-session
  verified-prior incremental audit with that cold reference across the eight
  business artifacts: source inputs, parameters, raw facts, normalization,
  score history, state history, transitions, and current risk results. The
  Oracle containers are not compared because the incremental Oracle covers the
  appended session while the cold Oracle covers every replayed session; both
  audits must independently pass their own Oracle and equivalence gates.
- `code_change`: requires the cold full-replay path without a prior Candidate
  audit. It proves deterministic calculation, all-session independent Oracle,
  append/restart/permutation/future-prefix equivalence, and completed audit
  custody. It does not by itself prove investment efficacy; model logic and
  thresholds still require chronological research and review.

The CLI accepts `--validation-tier`. Omitted calculation mode remains backward
compatible: a prior audit infers `daily`, while no prior audit infers
`code_change`. Periodic comparison is a read-only `--verify-output` operation
with an explicit `--reference-audit`. Both audits are formally reread before
their already verified artifact logical fingerprints are compared. Mismatched
dates, wrong execution modes, missing references, or any business-artifact
difference fail closed.

The daily validation ledger records `validation_tier=daily`. The CLI summary
and physical runtime metrics record the selected tier. Publication eligibility
is not granted by a summary field: publication, Snapshot, bundle, deployment,
and scheduling remain separate approval and custody boundaries.

## Consequences

- Daily automation can use the fast verified-prior path without pretending it
  performed a historical cold replay.
- A periodic job has an exact machine-checkable comparison rather than a
  manual list of fingerprints.
- Code/model changes cannot accidentally reuse a prior Candidate audit.
- Existing scripts remain compatible, but automation should always pass the
  tier explicitly.
- This phase formalizes when validation runs; deterministic multicore
  execution remains the next optimization and must match the serial path.

## Alternatives Considered

### Always run the cold reference daily

Rejected because it repeats formally verified history and delays stable EOD
availability without adding proportional daily protection.

### Compare aggregate audit fingerprints

Rejected because incremental and cold audits intentionally have different
schemas, Oracle scope, validation ledgers, and physical evidence. The correct
comparison is the complete same-session business artifact set.

### Let the scheduler infer tiers from filenames or weekdays

Rejected because validation intent and evidence requirements must be explicit
inputs, not conventions hidden in orchestration.
