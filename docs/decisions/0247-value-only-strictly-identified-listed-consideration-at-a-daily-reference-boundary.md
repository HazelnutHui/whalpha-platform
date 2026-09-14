# ADR 0247: Value Only Strictly Identified Listed Consideration at a Daily Reference Boundary

## Status

Accepted.

## Context

Nine of the 12 non-election listed-stock payoff cases now have a strict
transaction-document match and a point-in-time stable identity for the
consideration security. The other two registration documents state only a
variable-ratio formula, and the third selected filing concerns an unrelated
notes offering. Those three cases do not support a final listed-security
identity assignment.

A daily research label needs a deterministic value boundary for the nine
matched cases. The source evidence does not prove an execution price, an
intraday conversion time, tax treatment, settlement friction, or the actual
price at which received shares could have been sold.

## Decision

For an identity-matched case only, calculate one gross reference terminal
value per target common share as:

`guaranteed cash + registered share ratio × consideration-security close`

Use the formally reread canonical unadjusted close of the assigned stable
consideration security on the target security's first absent exchange session.
Require the upstream daily cessation boundary to remain matched and the EOD row
to be unique, USD-denominated, latest-revision, and `valid`. Preserve its
session-integrity hashes, point-in-time Identity binding, revision, source,
quality status, and every quality flag.

Call the result a **gross reference terminal value**, not an execution price,
legal settlement value, realized return, strategy result, or option return.
The SEC filing timestamp remains label-evidence availability and cannot become
a signal feature. Canonical partition creation time remains reconstruction
custody time and likewise cannot become signal knowledge.

Keep the three identity-unresolved cases in the denominator and excluded from
valuation. Do not infer their ratio or identity from names, tickers, later
prices, or a price-implied equation.

## Consequences

Nine cases obtain transparent, reproducible daily reference values with the
cash, ratio, price, formula, session and source bindings visible. These values
can later feed a separately governed research-outcome construction only after
the remaining mandatory evidence families and admission gate pass.

This decision creates no canonical terminal outcome, strategy label, return,
metric, `/data` or Historical Coverage write, research admission, Candidate
result, publication, deployment, or scheduler change.
