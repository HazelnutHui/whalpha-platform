# ADR 0287: Pilot Stage-Isolated Multi-Agent Research Governance

## Status

Accepted

## Date

2026-09-16

## Context

Two finite Factor Discovery campaigns and 14 formal trials are closed. Their
governed sequence worked, but most research responsibilities were carried by
one controlling task. Campaign Three is the first suitable pilot for several
specialized agents because its market-state inputs are still outcome-blind and
no campaign trial has been registered.

Agent parallelism is not statistical independence. Letting several agents see
the same outcomes, revise one another's hypotheses, or vote a model into use
would enlarge an unrecorded search and violate ADR 0194 and ADR 0284.

## Decision

1. Keep one research controller as the only stage-transition authority. The
   controller owns the campaign identity, finite budget, handoff reconciliation,
   and append-only ledger proposal; it cannot override deterministic gates.
2. Separate data/evidence, hypothesis, implementation, evaluation, red-team,
   and approval/publication responsibilities. Every handoff is a typed,
   content-addressed artifact rather than an informal completion claim.
3. Permit parallel work only inside the same outcome-access class and only
   when tasks do not mutate the same artifact. Outcome-blind hypothesis,
   evidence, implementation review, and documentation work may run in
   parallel. Protocol freeze, Development evaluation, exact replay, ledger
   close, and promotion remain ordered gates.
4. Give each role only the lowest data access required by its stage. The
   currently active idea, evidence, implementation, and method-red-team roles
   cannot read outcomes. Evaluation and result-red-team access remain dormant;
   a later contract may limit them to a registered Development slice.
   Validation and Holdout remain sealed.
5. Use deterministic Dell code for calculations, fingerprints, gate decisions,
   and exact replay. Agent narratives may explain or challenge a result but
   cannot alter it.
6. Record every proposed and consumed trial in the shared deduplication and
   cumulative trial ledgers. Multiple agents proposing related hypotheses share
   the same family and multiplicity accounting.
7. Require a role-distinct independent replay and adversarial review before a
   campaign can close. Same-model or same-provider agents do not create a new
   statistical confirmation.
8. Human approval remains required for Model Construction, Validation,
   Holdout, public performance claims, Candidate activation, paper trading, or
   any later capital decision.
9. Pilot this structure on Campaign Three without creating an unattended
   scheduler, distributed service, new database, credential authority, `/data`
   write authority, deployment authority, or trading authority.
10. This decision supersedes only the pilot-timing sentence in ADR 0274 and
    the Quant Research Lab product contract for an **outcome-blind, manually
    supervised** pilot. Development evaluation remains a single deterministic
    execution boundary after a separately frozen protocol. Wider autonomous
    Factory operation remains deferred until one factor-to-model-to-expression
    lineage survives locked evaluation and prospective shadow review.

## Consequences

The research process can use parallel attention where it saves time while
preserving stage isolation and the true experiment count. The added handoff
discipline has some overhead, so the pilot deliberately uses a small role set
and existing repository artifacts. Wider concurrency is justified only after
the pilot demonstrates faster completion without lineage, replay, or stage
leakage failures.

## Rejected alternatives

- allow each agent to run an independent unrestricted backtest;
- treat majority agent opinion as model approval;
- expose Development, Validation, and Holdout to all roles;
- maintain separate hidden trial ledgers per agent; or
- build a persistent multi-agent service before one bounded pilot.
