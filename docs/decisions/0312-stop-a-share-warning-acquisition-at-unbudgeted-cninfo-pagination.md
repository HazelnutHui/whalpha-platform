# ADR 0312: Stop A-share Warning Acquisition at Unbudgeted CNINFO Pagination

## Status

Accepted

## Date

2026-09-18

## Context

ADR 0309 froze a 492-unit official risk-warning batch from reuse package
`a53db0767c5c37110bf6f5ec4aa4e1395193369cd49fe0c63c06205ce277f882`
and warning manifest
`85335587d38619cc23653e9af1e21bbb143bd0bd0abc13d1e9cd6a61c564404c`.
Each logical unit permits one initial HTTP attempt and at most one retry only
for transport, HTTP 429, or HTTP 5xx failure. Challenge, schema, and semantic
failures stop acquisition.

SSE and CNINFO preflight each succeeded on one unit. During the bounded run,
one SSE response exposed grouped files: SSE counts one announcement group
while the group can contain a primary announcement and secondary report
attachment. The original capture was immutably stopped because flattened file
count exceeded group count by one. Exact offline replay proved 43 groups and
exactly 43 `ORG_FILE_TYPE=0` primary announcements. The parser was corrected
and fixture-tested without overwriting that checkpoint or issuing a duplicate
request.

At the 38th logical unit, CNINFO returned HTTP 200 with
`totalAnnouncement=60` but only the configured first 30 rows. Fetching page 2
would be a new pagination request, not an authorized retry.

## Decision

1. Retain all 39 attempts over 38 logical units in owner-only immutable
   custody. Do not overwrite the SSE grouped-file blocker or the CNINFO
   pagination blocker.
2. Treat SSE `pageHelp.total` as announcement-group count. Within each group,
   admit exactly one `ORG_FILE_TYPE=0` primary announcement locator and ignore
   secondary attachments for the warning-document route. Missing or multiple
   primary files remain semantic blockers.
3. Stop the V1 acquisition at the CNINFO pagination boundary. Do not request a
   second page, enlarge the page size, reinterpret the second call as a retry,
   continue the remaining 454 units, or switch authority under this contract.
4. A later V2 may resume only after separately freezing pagination semantics:
   maximum pages per logical unit, total HTTP ceiling, stable ordering and
   page identity, deduplication across pages, empty/short-page termination,
   restart checkpoints, and challenge/rate-limit behavior.
5. Search locators are document-fetch candidates, not adjudication-ready event
   evidence. Even locators with observed CNINFO publication clocks lack the
   official document bytes, effective interval, event kind, and warning
   subtype required for positive adjudication. Readiness therefore remains
   zero.
6. A zero-result response, if later observed, still cannot prove that no risk-
   warning event occurred.
7. Lifecycle, listing-stage, corporate-action, return, factor, backtest,
   canonical, and Product authority remain closed.

## Consequences

The retained partial run contains 38 unique units and 39 attempts: 20 SSE
attempts and 19 CNINFO attempts. Thirty-eight attempts returned HTTP 200; one
SSE transport failure used the sole allowed retry and then succeeded. No
challenge occurred.

Stored latest status is 36 `parsed_pending_adjudication` and two immutable
`semantic_blocked` captures. Offline replay resolves the SSE grouped-file
capture to 43 primary locators, leaving only CNINFO pagination incomplete.
Stored captures contain 270 locators and 113 observed publication clocks;
including the corrected SSE offline replay yields 313 candidate locators.
None is adjudication-ready without the document stage.

The authoritative partial census is
`08ac1dfd13a33dc00fef293c5b4c2ee6f7a6750e98fc3e8aeb3ce4137a5838ca`.
The acquisition plan fingerprint is
`af68a706886a2a156be9ac2228f934113775e2f4482b011ac9598adc5b4e3d62`.

The logical interface is [China A-share Warning Evidence Acquisition
V1](../data-contracts/china-a-share-warning-evidence-acquisition-v1.md).
