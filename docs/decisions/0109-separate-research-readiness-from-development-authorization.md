# ADR 0109: Separate Research Readiness from Development Authorization

## Status

Accepted

## Date

2026-08-31

## Context

Strategy Research Readiness already stops at
`ready_for_development_review`, but the next review was undefined. Without an
explicit boundary, a future task could treat 252 complete sessions as implicit
permission to run real outcomes, select a parameter or inspect holdout data.

## Decision

Add `strategy-research-development-activation-review/1.0` as a deterministic,
review-only contract. It formally rereads the readiness assessment and binds:

- the unchanged preregistered experiment and evaluation policy;
- exact Historical Coverage/readiness fingerprints;
- one implementation revision;
- chronological execution and statistics contract versions;
- the independent inferential-Oracle version and audit fingerprint;
- the external single-use holdout-custody version and audit fingerprint; and
- zero existing real results, development activations and holdout consumptions.

Current incomplete readiness returns `blocked` and no authorization text. A
synthetically complete fixture can return
`ready_for_exact_user_authorization` and a fingerprint-bound acknowledgement,
but still sets development activation, real evaluation, parameter selection,
holdout access and performance claims to false. A future activation capability
must be a separate reviewed change and must verify the exact acknowledgement
and unchanged physical evidence before any real evaluation.

The implementation has no CLI, installed configuration, real-result reader,
writer, activation state, provider access or `/data` mutation. Pure ready-state
fixtures specify semantics but do not claim current operational readiness.

## Consequences

- Data completion can never silently start model selection.
- An old authorization cannot survive experiment, readiness, code, Oracle or
  holdout-control drift.
- Existing real work or holdout inspection blocks a second initial activation.
- The present experiment remains 31/252 `data_blocked`.

## Alternatives Considered

### Automatically enter development when readiness passes

Rejected because it merges evidence sufficiency with permission to start
selection and increases silent overfitting risk.

### Use a generic acknowledgement not bound to evidence

Rejected because it could be replayed after data, code or controls change.

### Let this review execute the first real evaluation

Rejected because review and mutation require separate custody and authority.
