# ADR 0243: Retain Fixed-Cash Terminal Evidence without Creating Strategy Returns

## Status

Accepted.

## Context

The bounded terminal-payoff term report identifies 30 cash-only cases with a
single deterministic amount and matched SEC/EOD cessation timing. Their last
formal EOD observations are complete, but six cases have transaction
completion and trading-stop boundary on adjacent calendar dates. Treating a
filing date, completion date, stop date, or last close as interchangeable
would introduce daily-label timing error.

The cash stated in transaction documents is also not an execution price or a
net realized return. Taxes, fees, settlement, appraisal, interest, and an
earlier strategy entry price remain separate questions.

## Decision

Create a bounded terminal-cash evidence report that accounts for the complete
61-case upstream population and admits only the 30 cases already classified as
`fixed_cash_and_timing_ready`.

For admitted cases, preserve the source-bound two-decimal gross nominal USD
amount, transaction-completion date, SEC stop boundary, observed last EOD, and
the first exchange session without a target bar. Use that first absent session
as the earliest daily terminal-value session. Do not infer an intraday event
time from adjacent calendar dates.

Retain the SEC filing acceptance timestamp as evidence availability. It is
outcome-label maturity metadata and may never become signal-time knowledge.
Keep every non-fixed, timing-conflicted, or timing-unsupported case explicitly
excluded under its prior state.

## Consequences

Thirty cases gain reproducible nominal terminal-cash evidence without
silently dropping the other 31. The six adjacent-date cases remain usable at
daily frequency because completion occurs no later than the first absent
exchange session and the last EOD boundary is independently matched.

No canonical lifecycle fact, canonical terminal outcome, strategy label,
return, performance metric, `/data` write, Historical Coverage write, research
admission, publication, deployment, or scheduler change follows from this
report. A later label policy must still bind an eligible signal, entry price,
horizon, cost scenario, and label maturity.
