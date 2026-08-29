# ADR 0066: Project Incremental Candidate Evidence into Publication

## Status

Accepted

## Date

2026-08-29

## Context

The verified-prior Candidate path writes audit schema 1.1 with mode-appropriate
gates: `prior_prefix_preserved`, `incremental_restart_match`, and
`future_prefix_stable`, plus an independently bound current-session Oracle.
The bounded Candidate publication was introduced before that audit mode and
still read only the cold-audit keys `append_full_replay_match` and
`restart_replay_match`.

The first real 2026-08-27 MI Plan therefore failed closed with a `KeyError`
after source custody passed but before an approval plan or any Production
write. The first correction exposed the same duplicated assumption in the MI
approval-evidence recheck, which also failed before plan creation. Requiring a
new cold full replay for every daily publication would discard the verified-
prior design and repeat already validated history. Simply setting the old
fields to true without retaining the incremental lineage would misrepresent
the evidence.

## Decision

Candidate product construction and the independent MI approval-evidence
recheck consume the same bounded planning/lineage evidence reader and the same
mode-aware projection function, not only the completion manifest. For a legacy
schema 1.0 cold audit, the existing append/full-replay, restart, and future-
prefix gates remain mandatory and the resulting payload is unchanged.

For schema 1.1, publication is eligible only when all of these hold:

- execution mode is exactly `verified_prior_incremental`;
- the canonical incremental validation ledger is physically and logically
  bound to the completion manifest;
- validation scope is
  `verified_prior_plus_current_session_oracle`;
- every reuse check and the mode-appropriate prior-prefix, incremental-restart,
  and future-prefix gate is true; and
- the exact current-session independent Oracle is present with zero mismatch.

The stable Candidate publication 1.0/1.1 source shape predates schema 1.1, so
its three legacy compatibility booleans remain physically unchanged. For an
incremental source they mean the corresponding complete chain proof, not that
the current process repeated a cold replay:

- `append_full_replay_match` projects the verified prior-prefix chain plus the
  independently checked current session;
- `restart_replay_match` projects `incremental_restart_match`; and
- `future_prefix_stable` retains its direct meaning.

The publication warnings must additionally contain
`verified_prior_incremental_validation` and
`current_session_independent_oracle_without_same_run_cold_replay`. Thus the
consumer shape remains rollback-compatible while the actual evidence mode is
explicit and inspectable. Any missing or false lineage fact fails closed.

Periodic cold-reference validation remains required by the validation-tier
policy and after any calculation, parameter, schema, source-governance, or
state-machine change. This decision does not turn a daily incremental audit
into a same-run cold replay and does not weaken those gates.

## Consequences

- Daily Candidate audits can enter publication review without rebuilding the
  already verified historical prefix.
- Existing schema 1.0 publications retain their exact logical bytes and
  fingerprints.
- New incremental publications disclose their validation mode and cold-replay
  limitation in the language-neutral payload.
- MI Plan/Apply still bind the exact Candidate audit manifest SHA/logical
  fingerprint, every artifact hash, Entry Geometry lineage, Production
  inventory, and pointer state.

## Alternatives Considered

### Require a full cold Candidate audit every day

Rejected because it makes the verified-prior daily path operationally
irrelevant and repeats hundreds of megabytes of validated history. Cold replay
remains a periodic and change-triggered reference.

### Copy the old booleans without validating the incremental ledger

Rejected because a manifest-only alias would hide the actual evidence mode and
could publish an incomplete lineage.

### Introduce an immediate Candidate/MI/Snapshot contract cascade

Deferred because the existing payload already has stable equivalence fields
and extensible warning codes. A future major contract may rename the source
fields, but it is not required to represent this mode safely.
