# Inactive Lifecycle Completion Census Audit — 2026-09-05

## Scope

One aggregate-only Massive All Tickers census for historical anchor
`2026-07-16`, with `active=false`. The operation was bound to clean main
revision `d582c5817e44ee3dc4d9fa4ad3ece5e90d046673`, used 1,000 rows per page,
15-second serial pacing, no retry, a 20-request ceiling, and a 25,000-result
ceiling.

## Result

| Evidence | Value |
| --- | ---: |
| Status | `truncated_at_ceiling` |
| Requests / pages | 20 / 20 |
| Results | 20,000 |
| Pagination complete | no |
| `active=false` | 20,000 |
| Active conflicts / missing | 0 / 0 |
| `delisted_utc` present | 19,565 |
| `last_updated_utc` present | 20,000 |
| CIK present | 16,473 |
| Composite FIGI present | 5,001 |
| Share-class FIGI present | 4,504 |
| Duplicate ticker values | 124 |
| Logical fingerprint | `bbf205d3bc227b2b7f7541185bf71109680d0aa61af4837e47a0b37baa42ea03` |

No response body, ticker, identifier, URL, request ID, or credential was
retained or printed. `/data`, analytics, publication, deployment, and
scheduler state were unchanged.

## Interpretation

The prior six-page result understated the physical size: even 20 pages do not
reach natural pagination completion. Field presence establishes that the
source is potentially useful for retrospective delisting reconciliation, but
does not establish last tradable session, terminal reason, merger
consideration, successor identity, or when each fact was knowable.

The active 301-session source history and this inactive aggregate result are
complementary but not interchangeable. A disappearance from an active page
remains only a review candidate. The next durable step is a resumable,
streaming, owner-only source-observation package with formal reread and no
canonical Apply; it must tolerate more than 20 pages without holding every
response in memory while retaining a reviewed hard ceiling.
