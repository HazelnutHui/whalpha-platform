# Massive Stocks Starter Lifecycle Capability Audit — 2026-09-10

## Result

`USEFUL_PARTIAL_SOURCE`

`REJECTED_AS_SOLE_PRIMARY_LIFECYCLE_SOURCE`

Massive Stocks Starter remains useful for EOD, point-in-time reference
observations, inactive-security discovery, splits, dividends, and limited
symbol continuity. It does not satisfy the ADR 0168 sole-primary lifecycle
gates and does not remove the need to evaluate a cross-venue lifecycle/action
source.

## Fixed diagnostic

The run reused the immutable ADR 0167 queue and the deterministic ADR 0168
selection rule. The resulting 30 instruments cover 15 non-empty
`exchange x effective-year x observation-gap` strata, with six items each for
ARCX, BATS, XASE, XNAS, and XNYS.

All 30 source observations had a Composite FIGI, Share Class FIGI, provider
ticker, `delisted_utc`, and `last_updated_utc`. Composite FIGI was the only
positive request locator. Ticker fallback was not accepted as identity
evidence.

The bounded diagnostic issued 30 serial Ticker Events requests with no retry.
Before it, four one-request controls established that the documented literal
`/vX` route worked for the public META example, `/v3` did not, and the first
inactive sample returned 404 by both Composite FIGI and ticker. No credential,
provider identifier, ticker, raw response, request ID, or pagination URL was
retained or printed.

## Observed capability

| Evidence | Result |
| --- | ---: |
| Diagnostic instruments / requests | 30 / 30 |
| Stable Composite FIGI locators present | 30 |
| HTTP 200 with events | 6 |
| HTTP 404 | 24 |
| Returned events | 9 |
| Returned event types | 9 `ticker_change` |
| Other event types | 0 |
| Returned event fields | `date`, `ticker_change`, `type` |
| Retry / raw-response retention | 0 / no |
| Result logical fingerprint | `1828b686bcb981d11f271ee06dfafdc8ecd43d128ce658c4d6693ebbeaab189a` |

| Exchange locator | Matched | HTTP 404 | Sample |
| --- | ---: | ---: | ---: |
| ARCX | 0 | 6 | 6 |
| BATS | 0 | 6 | 6 |
| XASE | 2 | 4 | 6 |
| XNAS | 4 | 2 | 6 |
| XNYS | 0 | 6 | 6 |

The public endpoint documentation and the observed payload agree that Ticker
Events currently exposes symbol changes, not a general listing-lifecycle feed.
The 404 responses are retained as unavailable/unknown, not interpreted as no
event.

Existing separate source custody remains valid: two complete inactive All
Tickers anchors, 1,949 split observations, 68,150 dividend observations, exact-
date resolution, split-only canonical facts, and the sparse split-adjustment
ledger. Those bounded facts do not change this diagnostic result.

## Mandatory-scope decision

| ADR 0168 sole-primary scope | Massive Starter result |
| --- | --- |
| Stable-security request locator | Present for all 30 diagnostic items |
| Explicit returned/not-covered disposition | Fail: 24 HTTP 404 responses do not distinguish no event from no coverage |
| Event type, effective date, status/cancellation and revisions | Fail: only dated ticker changes returned; no status, cancellation, or revision chain |
| Source-published/source-available clock | Fail: unavailable; provider `last_updated_utc` remains a current observation field, not a formal knowledge clock |
| Suspension/resumption and last-tradable evidence | Fail: unavailable as an event/status chain; `delisted_utc` remains a candidate requiring corroboration |
| Successor and cash/stock consideration applicability | Fail: unavailable |

There is no need for a percentage threshold: multiple mandatory semantic gates
are structurally absent, and stable-ID event coverage failed for 24 of 30
diagnostic items. Massive is therefore rejected as the sole-primary lifecycle
source. It remains a valuable bounded source and possible corroborator; this is
not a rejection of Massive for its current EOD, Identity, split, or dividend
roles.

## Operational boundary

The run used clean Dell source revision
`4f6b22c60b850fdae29f2a6dd5d9fa17df15807c`. It performed no canonical
`/data` write, Corporate Action or Instrument Lifecycle promotion, Historical
Coverage change, analytics, outcome access, publication, deployment, or
scheduler mutation.

The next external gate remains a production-representative LSEG DataScope
Select free-trial/sample response for the same mandatory semantics. No LSEG
contact, account, purchase, access, or adapter is authorized by this audit.
