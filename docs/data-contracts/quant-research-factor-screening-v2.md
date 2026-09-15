# Quant Research Factor Screening V2

## Purpose

`quant-research-factor-screening-protocol/2.0` is the immutable before-outcomes
Development-screening contract for Factor Catalog V2. Its logical fingerprint
is `5441468ef8b392f555aac5a4e9cc8c6d50a9fb064349b6da342ccc2540dc193b`.

It binds the V2 qualification pass, frozen chronology, reconstructed
Membership, exact trial budget, labels, inference, costs, selection, and stop
rules. It authorizes no Validation, Holdout, model, strategy, Candidate,
Production, broker, or order action.

ADR 0282 fixes the implementation evidence boundary before outcomes: factor
observations must exactly replay the qualification-bound private split
extension, while the nuisance control and every future label use canonical
split evidence only. The result records all three lineages separately and
fingerprints the exact ordered observation, control, and label collections.
The reused 106-session cohort is reconstructed from the exact V1 diagnostics
bound by its screening protocol; all 118 raw Development sessions are not the
registered cohort.

## Cohort and trials

The declared Development cohort has 106 sessions from 2025-07-22 through
2026-01-07 and 167,860 Membership paths. Per-stable-ID factor defects and label
defects remain explicit exclusions; a benchmark factor defect excludes the
complete session.

Six formal trials are registered:

- four candidate Alpha measurements against 3-session next-open-to-close
  SPY-relative underlying-stock return; and
- two risk guards against exact 3-session maximum adverse excursion.

One- and five-session results are decay diagnostics. The conditioner and
Amihud applicability input consume zero standalone trials. V1's failed
20-session relative-return factor is used only as an incremental nuisance
control, not as revived Alpha or an additional V2 trial.

## Evaluation

Every session is one inference unit. The protocol uses same-session average
ranks, standalone and partial rank IC, 10,000 deterministic circular
five-session block-bootstrap replicates, chronological halves, contribution
concentration, quintile monotonicity, decay, and Holm adjustment within the
four-Alpha and two-risk families.

The admission gates and 0/10/25/50-basis-point cost diagnostics are carried
forward unchanged from the preregistered V1 protocol. Costs remain diagnostic
because a factor screen is not a portfolio or strategy expression. At most two
Alpha factors and one risk guard may proceed, with one per related group and at
least one Alpha survivor required before a Model Construction proposal.

One report and one exact replay exhaust the protocol. Outcomes remain unread at
registration. Exact rules and rationale are in [ADR 0281](../decisions/0281-freeze-factor-catalog-v2-development-screening-protocol.md).
The evidence-source boundary and Dell execution contract are in
[ADR 0282](../decisions/0282-separate-v2-factor-control-and-label-evidence-sources.md)
and the [V2 runbook](../operations/quant-research-factor-screening-v2.md).
