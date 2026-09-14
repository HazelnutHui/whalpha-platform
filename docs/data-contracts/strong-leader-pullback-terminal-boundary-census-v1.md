# Strong-Leader Pullback Terminal Boundary Census V1

## Purpose

`strong-leader-pullback-terminal-boundary-census/1.0` separates the last
canonical Instrument Master observation from the last canonical EOD presence
inside the first strategy's registered outcome window. It corrects the input
boundary for later terminal-gap measurement without calculating an outcome.

## Inputs and scope

The builder formally binds:

- the complete ADR 0221 evidence-blocker census and all 89 lifecycle rows;
- the exact rejected development-coverage census;
- all 287 reconstructed Primary Membership partitions already bound by the
  blocker census; and
- canonical EOD sessions from the first signal session through five exchange
  sessions after the last signal session.

Membership is reread to reproduce exact included signal paths. Every EOD
partition is fully validated against its manifest, content fingerprint,
physical Parquet hash, and Identity snapshot reference. Only presence of the
89 requested stable IDs is materialized.

## Decision grain

One decision is one stable `instrument_id` from the blocker lifecycle
population. It retains:

- separate first/last Instrument Master observation dates;
- the last observed EOD date inside the registered strategy window;
- the provider delisting-date candidate;
- whether EOD precedes, matches, or follows the identity observation boundary;
- original and corrected 1/3/5-session crossing counts;
- whether any count changed; and
- whether the stable ID newly enters the five-session terminal worklist.

The builder independently recalculates the legacy counts and requires them to
reproduce the blocker manifest before it accepts the corrected counts.

## Non-authority

An EOD observation is stronger evidence of price-bar presence than an
Instrument Master `as_of_date`, but it is not by itself a legal last-trading
date or a terminal-return policy. The report contains no strategy trigger,
forward return, performance metric, parameter choice, canonical write,
Historical Coverage, research admission, Candidate output, publication,
deployment, scheduler mutation, or network request.

## Physical custody

The package is one canonical JSON file under one owner-owned mode-`0700`
`census=*` directory. The file is mode `0400`. Creation is exclusive and
atomic; exact replay is idempotent and conflicting replay fails closed.
