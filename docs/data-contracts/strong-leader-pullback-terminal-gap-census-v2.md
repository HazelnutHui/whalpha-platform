# Strong-Leader Pullback Terminal Gap Census V2

## Purpose

`strong-leader-pullback-terminal-gap-census/2.0` is the authoritative
outcome-blind terminal worklist after ADR 0253 separates Instrument Master
observation dates from canonical EOD presence.

## Population and lineage

V2 binds:

- the formal terminal-boundary census;
- the immutable V1 terminal-gap census;
- the original 64-security source-acceptance sample;
- both retained inactive-lifecycle source/decision anchors;
- terminal payoff terms; and
- fixed-cash plus original and residual listed-consideration reference reports.

The original 64 stable IDs, legacy path counts, and evidence states must match
exactly. The V2 population is every stable ID with a corrected five-session
EOD-boundary crossing. Locators for additions are recovered only through the
stable-ID lifecycle evidence chain.

## Decision grain

One row is one corrected-population stable `instrument_id`. It contains:

- legacy or corrected-population origin;
- source ticker locators without fact authority;
- separate Identity and EOD observation dates;
- preserved evidence state and reference kind;
- corrected 1/3/5-session affected path counts; and
- the next required evidence gate.

New additions remain `newly_in_scope_primary_source_unadjudicated` until their
own primary-source review is complete.

## Non-authority

Reference values are not execution prices, terminal outcomes, strategy labels,
or returns. V2 contains zero triggers, forward outcomes, metrics, parameter
selection, canonical writes, Historical Coverage, research admission,
Candidate writes, publication, deployment, scheduler changes, and network
requests.

## Custody

The single canonical JSON report is owner-only mode `0400` under a real,
owner-owned mode-`0700` `census=*` directory. Creation is exclusive and atomic;
exact replay is idempotent and conflicting replay fails closed.
