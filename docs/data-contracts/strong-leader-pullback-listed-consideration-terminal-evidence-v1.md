# Strong-Leader Pullback Listed-Consideration Terminal Evidence V1

## Purpose

`strong-leader-pullback-listed-consideration-terminal-evidence/1.0` documents
one daily gross reference terminal value for each of the nine listed-stock
payoff cases whose consideration security passed the strict registration-
document identity gate. All 12 upstream decisions remain in the denominator;
the three unresolved identities remain explicit exclusions.

This is reference-value evidence. It is not an execution price, legal
settlement amount, canonical terminal outcome, strategy label, return, or
option result.

## Inputs and binding

The network-disabled builder formally rereads and binds:

- the 12-case listed-consideration identity adjudication;
- the 61-case common-share consideration adjudication;
- the trading-cessation adjudication;
- the normalized terminal-payoff terms; and
- only the required canonical EOD/Identity session partitions.

Every decision retains the target stable `instrument_id` and the logical
fingerprints of its identity, consideration, cessation and payoff decisions.
Ticker and company name have no join authority.

## Evidence rule and calculation

A case is valued only when its listed-consideration identity is `matched`, its
cessation boundary still passes the registered before-open or after-close
daily rule, and the assigned consideration stable ID has exactly one valid USD
canonical EOD row on the target's first absent exchange session.

The exact formula is:

`gross reference terminal value = guaranteed cash + listed ratio × unadjusted close`

Cash is recorded to two decimals, ratio to six, close to ten, and component and
total values to 16 decimals. The report retains the EOD partition's record
count, content fingerprint, Parquet hash, Identity snapshot date and
fingerprint, creation time, source, revision, currency, quality status and
flags. Adjustment uncertainty remains visible; no silent adjustment or
price substitution is allowed.

## Knowledge time and authority

The source filing acceptance time is label-maturity evidence only. The
canonical partition creation time is custody time for the reconstructed
dataset, not historical signal knowledge. Neither may enter a strategy
feature.

All canonical terminal outcomes, strategy triggers and labels, returns,
metrics, `/data` writes, Historical Coverage writes, research admissions,
Candidate writes, publications, deployments, and scheduler changes remain
zero. The immutable canonical JSON package uses owner-only `0700/0400`
custody and binds its implementation, ruleset, and all upstream reports.
