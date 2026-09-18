# ADR 0309: Reuse Local A-share Official Evidence Before Warning Acquisition

## Status

Accepted

## Date

2026-09-18

## Context

ADR 0306 froze 2,294 logical official-evidence request units from the exact
`a58e9337547438bd2260be89c4ff3004ccd2ad13f74f2ded8bf1c813dc6c72ba`
priority-plan package. Before allowing any network access, the platform needs
to determine whether existing owner-only SSE and CNINFO custody can satisfy a
unit without another request, and it needs a finite acquisition/adjudication
boundary for the first 492 risk-warning units.

Existing custody includes search captures, three second-stage SSE document
captures, and one bounded CNINFO sample. A source ticker, keyword match,
search result, or document text heuristic cannot establish the stable listed
security or the event's point-in-time effective interval.

## Decision

1. The final `a58e…` package is the only request-plan input. Local evidence is
   read only through existing exact owner-only readers and is inventoried by
   source package/capture fingerprint, official authority, raw SHA-256,
   publication clock, effective interval, structured fields, parse status,
   and stable-security binding.
2. A request is reusable only when a structured official record proves the
   same stable subject, authorized authority, observed publication clock,
   complete effective interval, raw-byte hash, and every expected field for
   the request purpose. Ticker-only matches, title/body heuristics, parsed
   zero-result searches, challenge pages, and schema-blocked captures never
   provide positive evidence.
3. Every one of the 2,294 request units receives a deterministic `reusable` or
   `network_required` decision with candidate evidence and fail-closed reason
   codes. Reuse changes neither the original request budget nor any daily
   reconstructed-Universe state.
4. Freeze the first acquisition batch at the 492 unresolved warning units.
   Route 225 Shanghai units to SSE and 267 Shenzhen units to CNINFO. This
   stage prepares the batch only; `network_execution_authorized=false`.
5. The batch permits one logical acquisition per unit. When a later operation
   is separately authorized, it may make one initial HTTP attempt and at most
   one bounded retry for transport timeout, HTTP 429, or HTTP 5xx. The ceiling
   is 984 HTTP attempts, requests are sequential, and the minimum interval is
   1,000 milliseconds. A challenge page is terminal and receives no retry.
   This transport retry does not create a second ADR-0306 request unit or an
   alternative-authority fallback.
6. Raw capture custody must retain request and batch binding, URL/final URL,
   UTC retrieval time, HTTP status, content type, byte count/hash, attempt,
   and typed blocker. A successfully captured response is only
   `captured_pending_adjudication`.
7. Positive adjudication requires a separately captured official document,
   exact stable-security binding, observed publication clock, effective
   interval, event kind, risk-warning subtype, and raw hashes. Search bytes do
   not themselves grant an event fact.
8. Persist inventory, census, batch, and manifest as canonical JSON in an
   atomic owner-only closed package. Independent replay must be byte-identical.
9. Outcome, return, Factor Discovery, Historical Coverage, backtest,
   canonical Apply, Product, deployment, and trading authority remain closed.

## Consequences

The first real offline census found 260 local capture records: 251 SSE search,
three SSE documents, and six CNINFO captures. All have raw hashes, but none has
both an observed publication clock and a complete effective interval with
stable-subject binding. Therefore zero of 2,294 units are reusable and all
2,294 remain network-required. This is a positive result for governance: no
weak local clue was silently promoted.

The next network-capable operation, if separately authorized, is exactly the
492-unit warning batch. Lifecycle (756 units) and listing stage (1,046 units)
remain outside it. Corporate-action candidates still generate zero requests.

The logical interface is [China A-share Local Official-Evidence Reuse and
Warning Batch V1](../data-contracts/china-a-share-local-official-evidence-reuse-and-warning-batch-v1.md).
