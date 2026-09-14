# Strong-Leader Pullback Fixed-Cash Terminal Evidence V1

## Purpose

`strong-leader-pullback-fixed-cash-terminal-evidence/1.0` documents the gross
nominal cash right for the bounded cases that already have one deterministic
cash term and matched cessation timing. It accounts for all 61 upstream cases
and admits exactly 30 to this evidence layer.

This is terminal-value evidence, not a canonical lifecycle fact, an execution
price, a net settlement amount, a strategy label, or a return.

## Inputs and binding

The network-disabled builder formally rereads and binds:

- the SEC common-share consideration adjudication;
- the SEC/EOD trading-cessation adjudication; and
- the terminal-payoff source-term report.

Every decision must retain the same stable `instrument_id`, sequence,
transaction-completion date, and upstream logical fingerprints. The source
population remains all 61 cases so that exclusions cannot disappear from the
denominator.

## Evidence rule

A case receives nominal fixed-cash evidence only when the upstream state is
`fixed_cash_and_timing_ready` and all of the following remain true:

- the payoff has exactly one `guaranteed_cash` term and no election;
- cessation is matched to formal stable-ID EOD presence;
- the observed last EOD equals the expected last EOD;
- the next exchange session is after the last observed EOD;
- transaction completion is no later than that first absent session; and
- before-open and after-close boundaries obey their registered daily rules.

The amount is a positive two-decimal USD string per target common share. The
first absent exchange session is the earliest daily research session on which
the nominal terminal value may be applied. This avoids inventing an unobserved
intraday effective time.

## Knowledge time and authority

The SEC filing acceptance timestamp is retained as source-availability and
label-maturity evidence. It cannot become a signal feature or be moved back to
the transaction date. Gross nominal cash excludes tax, fees, settlement
timing, interest, appraisal rights, and execution assumptions.

All canonical lifecycle facts, canonical terminal outcomes, strategy signals,
outcome labels, returns, performance metrics, `/data` writes, Historical
Coverage writes, research admissions, Candidate writes, publications,
deployments, and scheduler changes remain zero.

The canonical JSON report is immutable in owner-only `0700/0400` private
custody and binds its implementation, ruleset, and three upstream reports.
