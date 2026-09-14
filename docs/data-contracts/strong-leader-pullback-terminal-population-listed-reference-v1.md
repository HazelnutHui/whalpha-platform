# Strong-Leader Pullback Terminal-Population Listed Reference V1

## Purpose

`strong-leader-pullback-terminal-population-listed-reference/1.0` strictly
binds HNI common stock and calculates the cash, mixed, and stock SCS daily
reference alternatives on 2025-12-10.

## Evidence gate

The report formally binds the payoff policy, core adjudication, cessation
decision, official SEC Submissions package, same-session Instrument Master,
and canonical EOD partition. Assignment requires agreement on source issuer
and security form, SEC CIK/ticker/exchange, and canonical stable ID, exchange,
currency, FIGI lineage, type, and quality. Ticker and name are never sufficient
alone.

The canonical HNI close is formatted to ten decimal places. Each alternative
uses exact Decimal arithmetic:

`gross reference = cash amount + HNI share ratio × HNI close`

The mixed no-valid-election alternative is primary; all three values and their
range remain visible.

## Non-authority

The values are gross daily references, not holder-specific elections,
execution prices, net settlements, terminal outcomes, strategy labels,
returns, or performance. Automatic-adjustment details and proration remain
unresolved. Source and custody times cannot enter features. The owner-only
`0700/0400` package is immutable and exact replay is idempotent; network,
`/data`, Historical Coverage, admission, Candidate, publication, deployment,
and scheduler writes are all zero.
