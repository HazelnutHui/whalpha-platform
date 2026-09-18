# ADR 0313: Freeze Pagination-Aware A-share Warning Acquisition V2

## Status

Accepted

## Date

2026-09-18

## Context

ADR 0312 stopped Warning Acquisition V1 after 38 logical units because CNINFO
reported 60 announcements while the verified request page size returned only
30. A second page is not a transport retry and therefore was outside V1.
Thirty-nine V1 attempts and every raw response remain immutable.

## Decision

1. Bind V2 only to reuse package `a53…`, warning batch `853355…`, V1 plan
   `af68…`, partial census `08ac…`, its exact 39-capture set, and the already
   registered CNINFO official route-map hash.
2. Import the final successful page-1 raw capture for each of the 38 attempted
   units. Preserve the failed transport attempt and historical semantic
   checkpoints in lineage; never overwrite them or request those page-1 bytes
   again.
3. The official page-1 `total` determines `ceil(total/page_size)` pages. Page
   order is exactly `1..N`. SSE keeps page size 100 and a two-page per-unit
   ceiling; CNINFO keeps page size 30 and a four-page ceiling.
4. A later page must report the same total as page 1. Empty required pages,
   total drift, security mismatch, schema drift, challenge pages, page-limit
   overflow, and conflicting duplicates stop acquisition.
5. Primary announcements are deduplicated by document ID and deterministically
   sorted by publication time then document ID. Identical duplicates may
   collapse; conflicting document identity or a completed unique count that
   differs from the page-1 total stops the unit.
6. Page captures are append-only by request, page, and attempt. Each page may
   retry once only for transport, HTTP 429, or HTTP 5xx. Exact raw reread is
   required after every checkpoint.
7. The theoretical remaining ceiling is 1,405 page requests, but it is not
   authorized. The operational hard budget is 580 new pages and 1,160 new HTTP
   attempts. Including V1's 39 attempts, the lifetime ceiling is 1,199. This
   covers the 454 missing page-1 requests, the known missing CNINFO page 2, and
   125 bounded additional pagination pages with retry headroom.
8. Exhausting the global budget stops the run. It does not authorize another
   batch automatically.
9. Search locators remain non-adjudicative; zero results do not prove event
   absence. Lifecycle, listing, action, returns, factors, backtests, canonical
   Apply, and Product remain closed.

## Consequences

The final continuation plan fingerprint is
`74f33fed06a3fcb9996c219608a36c44bfd7feef3daa6077e7f6b6d04d6bf227`.
It imports 38 page-1 units; at plan time, only `sz.002872` had a known second
page. A tested two-page fixture proves stable total, fixed sequence, restart,
deterministic merge, and typed total/empty/duplicate blockers before live
continuation.

The bounded continuation completed all 492 units without a terminal stop. Its
census fingerprint is
`828ba7a4170d18eec1280fca3a97817148878cc8d931f0c1463a9eeac8e11fb7`:
469 new logical pages, 471 new attempts, and 510 lifetime attempts including
V1. Two retryable first attempts (one transport timeout and one HTTP 502) each
succeeded on their sole retry. The completed page distribution is 479
one-page units, 11 two-page units, and two three-page units. The census retains
4,399 deduplicated official-document locators, of which 2,454 have an observed
publication clock. Twelve SSE searches returned zero locators; those responses
remain search evidence only and do not prove event absence. Adjudication-ready
unit count remains zero.

Exact reread and an independent census rebuild matched. The immutable V2 tree
contains 943 files, 3,503,893 raw bytes, no symlinks, and only `0700`
directories and `0400` files. Its closed-tree physical fingerprint is
`c54f5ab2019b2dd5c34d4bf353b12d3a7f5be735e08caa09d0d6c550ce650df8`.

The contract is [China A-share Warning Evidence Acquisition
V2](../data-contracts/china-a-share-warning-evidence-acquisition-v2.md).
