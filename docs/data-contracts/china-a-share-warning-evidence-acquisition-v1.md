# China A-share Warning Evidence Acquisition V1

## Purpose

Execute only the frozen 492-unit official warning batch with bounded network
semantics, immutable raw custody, exact reread, and fail-closed search-result
interpretation.

Versions:

- `china-ashare-warning-evidence-acquisition-plan/1.0`;
- `china-ashare-warning-evidence-acquisition-capture/1.0`; and
- `china-ashare-warning-evidence-acquisition-census/1.0`.

## Input binding

The only target inventory is reuse package `a53…` and its embedded warning
manifest `853355…`. The previously captured CNINFO official security map may
resolve required `orgId` routing only when its raw SHA-256 is already present
in the `a53…` local-evidence inventory and its original exact reader verifies
the bytes. It is not risk-warning evidence.

The plan fixes 225 SSE units and 267 CNINFO units, sequential execution, a
minimum 1,000 ms interval, and no credentials. It does not admit lifecycle,
listing-stage, or corporate-action requests.

## Attempt budget

Each logical unit has one initial attempt. A second attempt is allowed only
after transport failure, HTTP 429, or HTTP 5xx. No unit may exceed two HTTP
attempts and the batch ceiling is 984. Challenge, schema, stable-security,
official-host, or pagination semantic failures are terminal and stop the run.
Alternative-authority fallback is prohibited.

## Capture

Each capture binds plan, warning batch, request/stable subject, source
security, authority, attempt, method, public request parameters, requested and
final URLs, UTC retrieval time, HTTP status/content type, raw byte count/hash,
typed status/blocker, result count, and announcement locators. Raw bytes use
owner-only immutable custody and are reread immediately after publication.

SSE publication evidence currently exposes an official disclosure date but no
observed intraday clock; its locator sets
`publication_clock_observed=false`. CNINFO millisecond timestamps set it true.
Neither state alone provides an effective interval.

SSE results are announcement groups. Exactly one `ORG_FILE_TYPE=0` primary
announcement is retained from each group; secondary attachments do not create
additional warning-document locators.

## Status and evidence boundary

Valid statuses are parsed pending adjudication, parsed zero results,
transport blocked, HTTP blocked, challenge blocked, schema blocked, and
semantic blocked. Search captures never authorize a positive event fact.
Zero results explicitly do not prove event absence.

An announcement locator is only an input to a later official-document plan.
Adjudication readiness stays zero until exact official document bytes establish
stable-security binding, publication clock, effective interval, event kind,
warning subtype, and conflict state.

## Custody and census

Directories use `0700`; plan, capture, raw, and census files use `0400`.
Publication uses exclusive creation and same-filesystem atomic rename. Exact
reread verifies closed file sets, modes, symlink absence, schema, logical
fingerprint, raw SHA-256/size, request/attempt path binding, and plan binding.

The census reports unique completed units, total attempts, latest statuses,
locator and observed-clock counts, zero-result count, adjudication readiness,
and any typed early-stop reason. Historical censuses remain immutable.

## Authority

Acquisition does not read outcomes or returns and grants no Historical
Coverage, factor, backtest, canonical Apply, Product, deployment, or trading
authority. See [ADR
0312](../decisions/0312-stop-a-share-warning-acquisition-at-unbudgeted-cninfo-pagination.md).
