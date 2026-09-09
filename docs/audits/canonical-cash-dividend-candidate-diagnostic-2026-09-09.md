# Canonical Cash-Dividend Candidate Diagnostic — 2026-09-09

## Result

The network-prohibited diagnostic completed on clean Dell `main` revision
`518b1cb20462890f544ef6709e0ab57477e07457`. It formally reread the exact
canonical corporate-action source publication and all 304 EOD evidence
partitions, then classified resolved cash-dividend groups without writing a
file or promoting an action.

Of 41,200 resolved stable-ID/reported-date groups, 40,454 passed only the
bounded arithmetic-candidate checks and 746 retained one or more review
reasons. Passing arithmetic does not establish the actual ex-date, source
availability, canonical Corporate Action, total-return eligibility, or a
neutral factor for omitted rows.

## Exact source binding

| Evidence | Value |
| --- | --- |
| Source-observation publication fingerprint | `7b13691e22b7e815a773ed1d575ed580bbee897eb0dbf10c41e4e0862a95b1d1` |
| Source publication SHA-256 | `648cbccaa646aa1dc04e069d1adba1ba5b4433cabfdd14d941972a9b3416fd43` |
| EOD evidence fingerprint | `923f27a8fa4e85c6d20b5c8ac0804f17dbab7437b350f02d54fea2ed5293aeb1` |
| EOD evidence SHA-256 | `ba652cb4ed21a0bfce1ce0cbd690c933cb8ae98de3f39231e282ea8f22789593` |
| Inclusive session range | 2025-06-23 through 2026-09-04; 304 sessions |
| Diagnostic logical fingerprint | `e648c4c6497c1cea8ed201617751e42781af4da578e5499d8b9060cb991bfbe1` |

## Counts

| Measure | Count |
| --- | ---: |
| Source cash-dividend rows | 68,150 |
| Exact-date stable-ID resolved rows | 41,347 |
| Unresolved rows retained outside candidates | 26,803 |
| Resolved stable-ID/reported-date groups | 41,200 |
| Bounded arithmetic candidates | 40,454 |
| Groups with at least one review reason | 746 |
| Large-distribution review groups | 31 |
| Large-distribution date-order review groups | 17 |
| Multiple same-date dividend groups | 145 |
| Same-date split/dividend groups | 13 |
| Non-USD groups | 160 |
| Groups without both adjacent EOD bars | 399 |
| Cash at or above same-basis prior close | 0 |
| Extreme cash-inclusive price-continuity reviews | 0 |

Reason counts overlap and must not be summed. The 25% large-distribution level
is a conservative review threshold, not an exchange-law assertion or an
automatic corrected date.

## VISN falsification case

The formal source reader found both rows on stable ID
`d3c6132c-c802-52ca-a172-d8c87c3266b0`.

| Reported date | Cash | Prior close / current open | Diagnostic result |
| --- | ---: | ---: | --- |
| 2026-04-28 | USD 10 | 19.53 / 9.64 | Raw ratio 0.493599590374; cash-inclusive ratio 1.005632360471; quarantined as a large distribution pending independent ex-date authority. |
| 2026-08-17 | USD 5 | 11.53 / 11.52 | Raw ratio 0.999132697311; cash-inclusive ratio 1.432784041631; quarantined for both large-distribution and date-order review. |

OCC memo 58754 independently records the USD 10 distribution with an April 28
ex-distribution date ([OCC](https://infomemo.theocc.com/infomemos?number=58754)).
For the later USD 5 distribution, the issuer states that August 17 was the
record date, August 27 the payment date, and August 28 the ex-dividend date
([issuer IR](https://vistancenetworks.gcs-web.com/news-releases/news-release-details/vistance-networks-board-approves-special-distribution-0)). Canonical EOD shows
11.63 on August 27 and a 6.80 August 28 open; adding USD 5 gives a bounded
cash-inclusive open/prior-close ratio of 1.014617368874.

The provider's USD 10 row carries a cumulative 0.27636 historical factor,
while the same-event factor from the April 27 close is 0.487967229902713774.
The provider's USD 5 row factor matches arithmetic anchored to the incorrectly
reported August 17 date, not the independently stated August 28 ex-date. Both
provider factors therefore remain audit evidence only.

## Decision boundary

- Do not publish the 40,454 arithmetic candidates as canonical dividends.
- Do not change the split-only Adjustment Ledger or fill omitted rows with one.
- Require an independent, revision-aware source or governed evidence override
  for actual ex-dates of large/special distributions.
- Keep non-USD conversion, same-date action ordering, unresolved identities,
  source availability, and point-in-time revision history as separate gates.
- Use price behavior only to falsify or prioritize review; never infer an event
  date from the price gap.

## Safety

The real diagnostic recorded zero external requests, filesystem writes,
canonical-data writes, and Adjustment Ledger writes. It changed no `/data`,
analytics, Snapshot, bundle, deployment, timer, scheduler, or Production state.
