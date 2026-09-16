# ADR 0290: Freeze Campaign Three Input Qualification Before Outcomes

## Status

Accepted

## Date

2026-09-16

## Context

ADR 0289 advanced four deduplicated interaction proposals but did not prove
that their factor and Market-State inputs are sufficiently aligned, variable,
or balanced inside the exact 106-session Development cohort. Registering all
four merely to fill a budget would turn preventable input defects into outcome
trials and increase hidden multiple testing.

The existing V1 diagnostics, V2 qualification, and Market-State qualification
are outcome-blind and exactly replayed. They should be reused where they prove
the required property. Only the V2 factors need a bounded 106-session input
replay because the retained aggregate report does not expose exact per-session
Development availability.

## Decision

1. Freeze the input gates in
   `quant-research-campaign-input-qualification-protocol/1.0` before running
   the report.
2. Use only the exact 106 Development sessions from 2025-07-22 through
   2026-01-07, split chronologically into 53/53 halves.
3. Require factor coverage, minimum cross-section size, cross-sectional
   variation, source tie control, state coverage, state variation, and
   chronological-half support.
4. For candidate Alpha, require observations on both sides of the registered
   natural zero and reject excessive state-side or same-side-run
   concentration. Do not invent a hindsight threshold to rescue a proposal.
5. Do not impose the Alpha zero-side test on the continuous broad-volatility
   state used only by the risk guard; require continuous variation and
   chronological support instead.
6. Reuse the V1 outcome-blind session and pairwise evidence. Replay only the
   two required V2 factors over the exact Development intersection from the
   qualification-bound sources, and stop bar reads at the final Development
   session after the full source identity has been verified.
7. Require one formal report and one canonical-byte-identical replay under
   owner-only custody outside `/data`.
8. A ready result authorizes only screening-protocol and Ledger V4
   preparation. It does not authorize a Development outcome read.

## Consequences

A proposal may stop before consuming a formal outcome trial. Campaign Three
may proceed with fewer than four trials if the remaining qualified set still
contains at least two candidate-Alpha interactions and one risk guard. The
report remains reproducible without reprocessing the five-year database or
reading any return label.

## Rejected alternatives

- assume aggregate 287-session qualification proves exact 106-session
  alignment without replay;
- rerun the entire five-year data foundation for a 106-session input check;
- read prior outcome-bearing screen reports merely to recover factor values;
- lower input gates after learning that a proposed state is sparse; or
- use full-panel quantiles to manufacture balanced historical states.
