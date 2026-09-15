# ADR 0284: Adopt a Renewable Sequence of Bounded Factor Campaigns

## Status

Accepted

## Date

2026-09-15

## Context

Factor Discovery V1 and V2 proved that finite preregistered campaigns can
reject weak Alpha while preserving useful risk evidence. The next architecture
question is not whether research stops after two failures. It is how research
can keep generating and attacking new ideas without silently repeating old
hypotheses, expanding a parameter search after seeing outcomes, or losing the
true number of attempts.

An overall fixed lifetime campaign count would stop useful learning too early.
An unbounded outcome-aware search would make multiplicity unknowable and allow
overfitting. The durable unit therefore has to be a renewable program whose
individual campaigns remain bounded.

## Decision

1. Factor Discovery is a continuous sequence of separately versioned finite
   campaigns. The program has no predetermined final campaign count.
2. Every campaign follows the typed eight-stage cycle in
   `quant-research-discovery-cycle/1.0` and closes before another campaign may
   read Development outcomes.
3. Hypothesis novelty is checked across economic mechanism, information set,
   formula, Universe, horizon, parameter neighborhood, and related family.
   Exact duplicates stop; near-duplicates share a family and multiplicity;
   distinct questions become new trials.
4. Before any outcome access, freeze the complete trial and parameter budget,
   horizons, families, multiplicity, selection cap, and stopping rule.
5. Outcome-blind idea, data, and qualification stages remain isolated from
   labels. Only the registered Development screen and its exact replay may read
   those outcomes.
6. Close every campaign in the append-only cumulative ledger. A failed batch
   returns to new hypothesis intake; it is never retuned in place.
7. A successful batch may open a separately governed Model Construction path.
   Factor Discovery may continue independently, so one model does not end
   research or become the permanent universal model.
8. Automatically pause the affected campaign on lineage mismatch, stage
   leakage, budget breach, replay failure, or sealed-partition breach. Preserve
   all prior evidence.
9. This architecture enables a future bounded AI research factory but does not
   install an unattended scheduler, authorize new outcome access, open
   Validation/Holdout, activate a model, deploy, or trade.

## Consequences

The system can keep learning without treating “continuous” as “unlimited
search.” Failures accumulate as information, related ideas are counted
together, and each result remains reproducible. The current position is the
outcome-blind intake and deduplication stage for a not-yet-registered campaign.

## Rejected alternatives

- stop Factor Discovery after a fixed small number of campaigns;
- permit unlimited parameter or interaction generation inside one campaign;
- reset multiplicity when a failed factor receives a new name;
- select the best recent campaign without a locked model and strategy path;
- make one successful model the permanent research taxonomy; or
- let autonomous agents grant themselves outcome, Validation, Product, broker,
  or deployment authority.

