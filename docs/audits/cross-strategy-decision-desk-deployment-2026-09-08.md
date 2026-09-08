# Cross-Strategy Decision Desk Deployment Audit — 2026-09-08

## Scope

This audit records the bounded product change, exact Snapshot publication,
serving-bundle construction, OCI deployment, independent remote inspection,
and final Dell reconciliation. It records no credential, Session material,
provider response body, server address, or private payload.

## Decision-useful product change

- Strategy Channels now opens with one cross-channel decision desk containing
  only the first published record from each currently available channel in the
  fixed published channel order.
- Every card retains its own channel rank, stage, within-channel score,
  extension risk, first supporting reason, and first rejection risk. The
  browser does not calculate a cross-channel score, preferred strategy,
  expected return, or trade instruction.
- Opening a card or channel row joins the exact strategy assessment to the
  same-Snapshot Candidate summary and detail using stable `instrument_id` only.
  Missing or mismatched identity fails closed. Ticker remains presentation, not
  identity.
- The combined review exposes the channel score ledger and explanation beside
  the existing market-to-entry chain, price path, descriptive levels, chase
  risk, seven-component contribution ledger, counterevidence, and invalidation.
- Quant Research Lab no longer displays the dated 31/252 aggregate as current
  readiness. Price depth is shown as length-met while Membership, corporate
  actions/adjustment, lifecycle, costs, and sealed evaluation retain their
  separate incomplete or locked states. Research remains `data_blocked`.

No Candidate formula, score, rank, strategy rule, Market Intelligence payload,
data contract, or underlying-stock/option interpretation changed.

## Verification

- Focused frontend coverage passed 13 tests, including English and Chinese
  rendering, same-Snapshot detail loading, and stable-ID mismatch refusal.
- The complete frontend regression passed 115 tests in 20 files; the
  Production build passed. Its only warning was the existing Vite chunk-size
  advisory.
- The complete API regression passed 2,209 tests. The only warnings were the
  existing Python `crypt` and Starlette/httpx deprecations.
- A real active-Snapshot compatibility audit found one unique stable-ID
  Candidate match for each of the three available channel leaders. Each bound
  detail shard exposed Entry Geometry and Candidate Visual Context.

## Snapshot and bundle

- Source revision: `14a8bec70cff37080673e679f05c8ed6eb34d95b` on clean
  Dell `main`.
- Snapshot release: `2026-09-08T160420Z-14a8bec70cff`.
- Snapshot contracts: 1.11 / Dashboard 2.8; current and expected completed
  session 2026-09-04; lag zero; review mode false.
- Snapshot pointer fingerprint:
  `056d4fd15819411c398ba9f36956d478b4fd5a19787e9d9e040b16af60f4b356`.
- Snapshot manifest SHA-256:
  `860bb1b494bae54802dc8aa4d32de94df18a20eeefda2b5ea29c5b893fbca4e9`.
- Serving bundle logical fingerprint:
  `09d3afc53612e296bde062220a51fdb2437d5136f8da6bf3eab01560ab8117ce`.
- Deployment manifest SHA-256:
  `94ca6bbd585a982a518572e4b4c856074da2a3f7973bd0c388d08288d19a1684`.
- Checksums file SHA-256:
  `a27698cd7407e793da9699ec9695b7b22e8528619c41717e74ef02567dcc8173`.

All 51 managed bundle files passed checksum validation. English and Chinese
copy was present; the stale 31/252 display and known synthetic demo markers
were absent. The manifest declares zero credential, Parquet, or raw provider
payload and preserves identical guest/credential capability.

## OCI and final state

The guarded dry-run and Apply completed. Independent inspection matched the
exact release, source revision, bundle fingerprint, manifest, and checksums.
Nginx and the localhost-only Auth Service are active and enabled. Protected
routes, a temporary guest Session, and guest/credential route-policy parity
passed. Failed system units, staging releases, and failed-release residue were
zero. Remote-state fingerprint:
`3ea4e2e58d2bf3b6f93c8b1a39907440b761a4254ed8506b82ffa965424edeb6`.

The final network-prohibited, active-source reread reported:

- canonical EOD: 304 contiguous sessions through 2026-09-04, 9,962 latest
  rows, aligned Identity;
- active Market Intelligence: `2026-09-04T112916Z-717cb82c5369`;
- active Snapshot: fresh, lag zero, no review mode;
- `/data`: 4,102 files / 2,054,208,593 bytes, fingerprint
  `b2f45c0dcee3a915aba8e7c932a747ac6698022cfb7f90b3f82b4bd828dca128`;
- symlinks and publication residue: zero; and
- research readiness: `data_blocked`, with performance claims unauthorized.

Password-based credential login and final human visual appearance remain user
checks. This deployment authorizes no model tuning, performance claim,
unattended write-capable scheduler, data acquisition, or options-return claim.
