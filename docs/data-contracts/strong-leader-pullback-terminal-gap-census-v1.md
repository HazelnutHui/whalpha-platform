# Strong-Leader Pullback Terminal Gap Census V1

> Historical contract notice: ADR 0253 proved that V1's path counts used an
> Instrument Master observation boundary rather than canonical EOD presence.
> Preserve V1 for lineage only. Terminal population and impact authority now
> belongs to [V2](strong-leader-pullback-terminal-gap-census-v2.md).

## Purpose

This contract measures the exact terminal-evidence state of all stable
securities in the first strategy whose five-session label window crosses the
last canonical observation. It is an outcome-blind prioritization report, not
a lifecycle family, terminal-outcome table, strategy label, or admission.

## Inputs and binding

The report formally binds physical and logical fingerprints for:

- the strategy evidence-blocker census and its lifecycle exposure rows;
- the complete 64-security source-acceptance sample;
- the 61-case terminal-payoff term report;
- the 30-case nominal fixed-cash reference layer;
- the original nine-case listed-consideration reference layer; and
- the additive three-case residual listed-consideration reference layer.

The 64 stable IDs and their 1/3/5-session crossing counts must agree between
the blocker census and source sample. Payoff cases must be a subset of that
population. Reference evidence must be unique by stable ID and bound to the
same payoff report.

## Decision rows

Each row retains:

- stable `instrument_id` and ticker locators, with ticker granting no identity;
- structured request sequence when one exists;
- exactly one current evidence state;
- reference type, evidence count, source-available time, and quality flags;
- 1/3/5-session crossing-path counts; and
- the next required evidence gate.

The two documented reference states are nominal fixed cash and gross listed
consideration. Listed values must retain
`adjustment_factors_unverified`. Every other state has no reference value.

## Aggregates and limits

The report reconciles population, documented, remaining, state-specific, and
1/3/5-session path totals from its complete decision rows. Its priority order
is fixed by evidence dependency and cannot be inferred from strategy outcomes.

All terminal-outcome, trigger, forward-outcome, metric, parameter-selection,
canonical-write, Historical Coverage, research-admission, Candidate,
publication, deployment, scheduler, and network counts are zero. Positive
research admission requires a later versioned coverage and admission contract.

## Custody

One canonical `terminal-gap-census.json` file is written to a new direct child
of an explicit owner-only custody root. Directory mode is `0700`, file mode is
`0400`, completion is exclusive and atomic, exact replay is idempotent, and a
same-path content conflict, unexpected member, symlink, unsafe mode, or
noncanonical byte representation fails closed.
