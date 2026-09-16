# ADR 0293: Close Campaign Three Without Alpha and Append Ledger V5

## Status

Accepted

## Date

2026-09-16

## Context

ADR 0291 registered two candidate-Alpha interactions and one risk-guard
interaction before Development outcomes. ADR 0292 then froze the remaining
evaluator and execution-custody mechanics. The exact user grant opened only one
formal Development screen and one exact replay against committed revision
`91eb383a70eb209ec9f998954586b3499ca1d4b8`.

The formal and replay reports are byte-identical. All three trials fail at
least one frozen gate. Neither candidate-Alpha interaction has a positive
primary interaction slope or stable second-half evidence. The risk guard has a
positive full-period primary slope but a negative second-half slope and
negative registered bootstrap lower bounds.

## Decision

1. Close Campaign Three at `closed_no_candidate_alpha`.
2. Reject all three registered trials at the frozen screen. Do not repair a
   formula, state definition, threshold, endpoint, block length, family, or
   gate after observing these outcomes.
3. Treat the formal report and exact replay as the exhausted execution pair for
   this protocol. No third execution is permitted.
4. Append cumulative discovery Ledger V5. It binds Ledger V4 as predecessor,
   preserves the first 14 consumed trials, records the three Campaign Three
   outcomes, and keeps the cumulative trial count at 17.
5. Record zero admitted candidate Alpha, zero newly qualified risk evidence,
   and zero model input from Campaign Three.
6. Keep Model Construction, Strategy Expression, Validation, Holdout, Stock
   Candidate activation, publication authority, options claims, broker access,
   and trading closed.
7. Return the renewable research program to outcome-blind hypothesis intake.
   Any successor campaign must disclose adaptation to all 17 consumed trials,
   deduplicate against them, freeze a finite new budget, and append another
   ledger version before reading outcomes.

## Consequences

Campaign Three contributes a reproducible negative result and evidence about
instability across chronological halves. It does not produce a model candidate
or a reason to loosen the gates. The public Lab may report the closed campaign,
exact replay, sample counts, human-readable trial logic, and failed gates, but
must not imply active Alpha, strategy performance, or Product authority.

## Rejected alternatives

- keep the risk guard because its full-period slope is positive;
- select the more favorable five-session diagnostic;
- move the market-state threshold after observing weak support;
- pool Campaign Three with prior risk evidence to construct a model without a
  surviving candidate Alpha;
- rename and rerun either rejected interaction in a successor campaign; or
- hide the failed campaign from cumulative trial accounting.
