# Strong-Leader Pullback Trading Cessation Adjudication V1

## Purpose

`strong-leader-pullback-trading-cessation-adjudication/1.0` compares bounded SEC
Item 3.01 trading-stop statements with formally reread canonical Dell EOD
observations for the first-strategy lifecycle sample.

It does not infer a first tradable date, legal delisting-effective date,
complete security-status interval, terminal payoff, or research admission.

## Inputs and fixed population

The network-disabled builder formally rereads and binds:

- the 64-case source-acceptance sample;
- the complete Form 25 candidate package;
- the 61 matched termination-reason decisions;
- the 61 matched source-party relation decisions; and
- the canonical EOD and same-session Identity evidence under the approved Dell
  data root.

The exact 61 decision sequences are registered as 45 before-open, eight
after-close, and eight unresolved timing profiles. Changed or unregistered
cases fail closed.

## Decision semantics

For each explicit timing case, the decision retains the normalized SEC clause,
offsets, source hash, source-stated stop-boundary date, expected final EOD
session, next exchange session, and three bounded formal EOD presence checks.
All EOD checks are keyed by stable `instrument_id`; ticker is not a join key.

- `matched`: the target bar is present on the expected final EOD session and
  absent on the next exchange session;
- `conflicting`: formal EOD presence disagrees with that expected boundary;
- `unsupported`: the retained SEC source does not prove a stop time, so no EOD
  timing conclusion is opened.

A conflict remains explicit even when a prior target bar proves an observed
last EOD session. Missing a target bar is not independently called a legal
delisting or a zero return.

## Authority boundary

The report counts matched, conflicting, and unsupported decisions separately.
It records zero first-tradable dates, legal delisting-effective dates,
complete first/last-tradability fields, complete suspension/delisting fields,
canonical lifecycle facts, terminal outcomes, strategy signals, performance
metrics, `/data` writes, Historical Coverage writes, research admissions,
Candidate writes, publications, deployments, and scheduler changes.

The canonical JSON report is immutable in owner-only `0700/0400` private
custody and is bound to implementation, ruleset, source reports, and exact EOD
partition fingerprints.
