# ADR 0252: Measure Terminal-Evidence Gaps before Versioning Research Admission

## Status

Accepted.

## Context

The Strong-Leader Pullback development-admission decision remains bound to the
2026-09-10 coverage census. That V1 contract cannot consume the later typed
lifecycle work. Repeating it unchanged would reproduce the same rejection
without measuring whether the new evidence changed the strategy-scoped gap.

The fixed strategy population contains 64 stable securities whose five-session
label windows cross their last canonical observation. Thirty fixed-cash and 12
listed-consideration cases now have daily gross reference-value evidence. The
remaining structured cases include unresolved cessation timing, CVRs, holder
elections or proration, and an unlisted unit; three exceptional source cases
never entered the 61-case structured transaction population.

Reference value is still not a canonical terminal outcome or strategy label.
The project therefore needs a result-blind bridge between the completed typed
evidence and any future version of the development census.

## Decision

Create one immutable, network-disabled terminal-gap census that:

1. Formally rereads the exact evidence-blocker census, frozen source-acceptance
   sample, terminal-payoff terms, fixed-cash evidence, original listed-
   consideration reference report, and residual reference report.
2. Retains all 64 stable IDs and requires their 1/3/5-session crossing counts
   to agree between the original blocker census and source sample.
3. Classifies each security into exactly one current evidence state. The two
   documented classes remain nominal fixed cash and gross listed consideration;
   neither is promoted to a terminal outcome.
4. Keeps every unresolved state and the three exceptional cases in the
   denominator. It reports both instrument counts and affected 1/3/5-session
   path counts.
5. Orders the next evidence work by semantic dependency: cessation timing,
   exceptional primary-source cases, CVR realization, holder election or
   proration, then unlisted-unit valuation. This is an evidence-work order,
   not a strategy ranking.
6. Writes one owner-only canonical JSON report outside `/data`, with exclusive
   atomic completion, content fingerprints, formal reread, idempotent replay,
   and conflict rejection.
7. Keeps strategy triggers, forward outcomes, performance metrics, parameters,
   canonical data, Historical Coverage, research admission, Candidate output,
   publication, deployment, scheduler changes, and network requests at zero.

## Consequences

The next lifecycle work is bounded to the measured residual population rather
than another five-year or global scan. The report can show how much of the
strategy's terminal boundary has reference evidence while preserving the
stronger requirements for lifecycle facts, label policy, adjustment
neutrality, Membership, costs, Historical Coverage, and sealed evaluation.

A new admission contract is justified only after a new outcome-blind coverage
census can actually consume admissible versions of those mandatory families.
This ADR does not authorize terminal outcomes, a backtest, or website claims.
