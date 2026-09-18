# China A-share Warning Evidence Acquisition V2

V2 adds bounded official pagination without weakening V1 custody or evidence
semantics.

## Page policy

Page 1 fixes the official total and required page count. SSE uses 100 rows and
at most two pages; CNINFO uses 30 rows and at most four pages. Pages are fetched
in strict `1..N` order. Every later page must preserve total, authority,
security, interval, page size, and official-host boundaries.

Primary announcement locators deduplicate by document ID and sort by
publication time plus document ID. Total drift, an empty required page,
conflicting duplicates, completed unique-count mismatch, security/schema
drift, challenge response, or page-limit overflow is terminal.

## V1 reuse and restart

The plan imports 38 verified page-1 raw responses and all 39 prior-attempt
fingerprints. No V1 file is changed. New custody keys every capture by request
ID, page number, and attempt number. Exclusive creation, `0700` directories,
`0400` files, atomic rename, raw hash/size verification, closed sets, and exact
reread make restart append-only.

## Budget

- theoretical remaining page ceiling: 1,405, not authorized;
- operational new-page ceiling: 580;
- operational new-attempt ceiling: 1,160;
- lifetime V1+V2 attempt ceiling: 1,199;
- one retry per page only for transport, HTTP 429, or HTTP 5xx; and
- minimum interval: 1,000 ms.

Budget exhaustion is a typed stop. It does not authorize extension.

## Verified completion

Plan
`74f33fed06a3fcb9996c219608a36c44bfd7feef3daa6077e7f6b6d04d6bf227`
completed all 492 units and published census
`828ba7a4170d18eec1280fca3a97817148878cc8d931f0c1463a9eeac8e11fb7`.
The persisted result has 38 imported V1 page-1 responses, 469 new logical
pages, 471 new attempts, and 507 logical pages in total. Exact reread and an
independent census rebuild both reproduce 4,399 deduplicated locators and
2,454 observed publication clocks.

The only non-parsed first attempts were one transport timeout and one HTTP
502; each succeeded on attempt two under the frozen retry policy. No challenge,
total drift, empty required page, duplicate conflict, schema/security binding,
page ceiling, or global budget stop occurred. Twelve SSE page-1 responses had
zero results; they remain non-adjudicative search results.

## Evidence authority

Search results only produce official document locators. Even complete pages
do not establish an effective event interval or subtype, and zero results do
not prove absence. Adjudication readiness remains zero until a separately
governed official-document stage parses exact bytes. All outcome, return,
factor, backtest, Historical Coverage, canonical, Product, deployment, and
trading authority remains closed.

See [ADR 0313](../decisions/0313-freeze-pagination-aware-a-share-warning-acquisition-v2.md).
