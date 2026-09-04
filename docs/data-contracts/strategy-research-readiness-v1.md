# Strategy Research Readiness V1

## Purpose

`strategy-research-readiness/1.0` answers one narrow question: does exact,
source-bound historical evidence satisfy every prerequisite for a separate
review of Strong-Leader Pullback development?

It does not run a strategy, produce labels, tune parameters, estimate returns,
or authorize any operational action.

## Inputs

- the immutable `candidate-strategy-research-experiment/1.0` registration;
- canonical EOD session descriptors formally reread from Dell, including each
  session's bound point-in-time Identity date; and
- optionally, a typed `HistoricalCoverageManifestV1` supplied by the ADR 0099
  transitive formal physical reader.

The offline command intentionally has no coverage-manifest path argument. It
may accept only an exact `--coverage-id`; the reader derives its immutable path
below the canonical root and verifies all family evidence, source completion
manifests, and payload hashes before returning the typed coverage. A standalone
JSON claim cannot satisfy physical historical coverage.

## Required observations

| Requirement | Satisfied only when |
| --- | --- |
| Experiment preregistration | Exact frozen experiment is still data-blocked |
| Canonical history depth | Research-ready coverage contains at least 252 sessions |
| EOD Price Bars | Completed family covers the full manifest interval |
| Point-in-time Identity | Completed family covers the full manifest interval |
| Daily Universe Membership | Completed family covers the full manifest interval |
| Corporate Actions | Completed canonical family covers the full interval |
| Instrument Lifecycle | Completed family covers the full interval |
| Adjustment Ledger | Completed reconciled family covers the full interval |
| Feature warm-up | Manifest supports at least 20 sessions |
| Outcome horizon | Manifest supports at least five sessions |
| Matured window | At least one signal session can have complete outcomes |

`mechanics_only` means a current reader can prove some source mechanics but not
research-ready historical coverage. `blocked` means the required evidence is
absent. Neither state can be treated as satisfied.

## Result states

- `data_blocked`: one or more prerequisites are not satisfied; next action is
  `complete_historical_foundation`.
- `ready_for_development_review`: all prerequisites are satisfied; next action
  is a separate `review_development_activation`.

Both results always set `development_authorized=false`,
`performance_claims_authorized=false`, `external_request_count=0`, and
`production_write_count=0`.

ADR 0109 defines the next review-only step. A complete result may feed an exact
development-activation review, but that review still cannot activate or
execute research; it can only prepare an evidence-bound user-authorization
decision.

## Fingerprints

The result binds the experiment, evaluation policy, canonical EOD/Identity
evidence, optional Historical Coverage Manifest, ordered observations, status,
and reasons in one deterministic logical content fingerprint.

## Recorded Dell assessment

The 2026-08-30 socket-guarded read-only assessment formally reread 31 canonical
sessions through 2026-08-28. Its status is `data_blocked`; the exact result
fingerprint is
`4d3b5a1b472f710638f024443e2ad6c1dea1f4dd25920c2cd9eb1d3a51802116`.
It made zero external requests and zero Production writes.

That result is retained as dated evidence, not current state. Canonical price
history has since advanced beyond the observation minimum, but there is still
no research-ready Historical Coverage publication and the required
point-in-time families remain incomplete. See
[current context](../project/current-context.md); price-session count alone
must never be interpreted as research readiness.
