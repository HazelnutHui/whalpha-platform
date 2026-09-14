# Strong-Leader Pullback Terminal-Population SEC Source Plan Audit — 2026-09-14

> Superseded execution notice: this audit records the first plan, whose
> `planned_at=10:30Z` was later found to follow its 06:36Z source acquisition.
> Preserve it only as rejected lineage. The authoritative V2 evidence is in
> the [source-custody audit](strong-leader-pullback-terminal-population-sec-source-custody-2026-09-14.md).

## Scope

ADR 0255 requires every case added by the corrected EOD terminal boundary to
receive an independent stable-ID source chain before acquisition. This run
formally cross-read terminal-gap census V2, both retained lifecycle anchors,
and the complete SEC Submissions source and payload census. It made no network
request and did not read SEC User-Agent configuration.

## Result

The single new case is stable ID
`ff8ae3f6-a3ae-5127-983b-0f94386f0055`, linked through retained lifecycle
source/decision fingerprints to CIK `0001050825`, exchange `XNYS`, and
share-class FIGI `BBG001S89FD2`. The `SCS` ticker is retained only as a locator.

The source plan contains exactly three unique accessions and URLs:

| Filing date | Form | Boundary relation |
| --- | --- | --- |
| 2025-12-10 | 25-NSE | after last EOD and before provider date candidate |
| 2025-12-11 | 8-K with Items 2.01 and 3.01 | on provider date candidate |
| 2025-12-22 | 15-12G | after provider date candidate |

The corrected last stable-ID EOD presence is 2025-12-09. Filing metadata does
not yet prove transaction completion, last tradable time, legal delisting,
consideration, terminal value, or return.

## Exact evidence

- Implementation revision:
  `7862ea039f68bdc308ac727ffddfbd0ab07e13c7`
- Planned at: `2026-09-14T10:30:00Z`
- Canonical report:
  `/home/hui/.local/state/trading-intelligence-platform/historical-source/strong-leader-pullback-terminal-population-sec-source-plan/plan=20260914-v1/terminal-population-sec-source-plan.json`
- Report bytes: `6,028`
- Report SHA-256:
  `4e43d29c25cf0b6418ac865adf0e323d9c021b99d8fe917e8813edfdd9399968`
- Logical fingerprint:
  `539d42ead648bda44bf63818dffa5c4587de65edb59195a787945a9e8ea39b4c`

Exact replay returned `already_present`. The custody and plan directories have
mode `0700`, the report has mode `0400`, and no symlink, partial, or staging
residue exists.

## Verification and next gate

Twenty linked tests passed. The complete API suite then passed 2,754 tests in
273.82 seconds; the two warnings are unchanged dependency deprecations in the
authentication and TestClient paths.

The next gate is a separate source-custody implementation that binds this plan,
enforces its exact order, host, rate, retries, response size and content hashes,
and supports safe restart. This plan authorizes no ad hoc download and no fact
or research decision.

No external request, credential read, document write, `/data` write, canonical
lifecycle mutation, terminal outcome, Historical Coverage admission, Candidate
change, publication, deployment, or scheduler mutation occurred.
