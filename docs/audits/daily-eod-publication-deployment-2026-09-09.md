# Daily EOD Publication and Deployment Audit — 2026-09-09

## Scope

This audit records the guarded 2026-09-08 EOD acquisition, canonical Apply,
Dell-local analytics, Market Intelligence and Snapshot publication, persistent
Serving Bundle deployment correction, final OCI deployment, and independent
postflight. It contains no credential, provider response body, Session
material, private-key path, or server address.

## Canonical acquisition and Apply

- The first successful current-session Grouped Daily observation began at
  2026-09-09T06:58:46Z and froze its package at 06:59:18Z. It used one
  `adjusted=false` request and retained 12,534 raw provider records.
- Acquisition-package content fingerprint:
  `3da7fac4e82bec3e8aea1860b50c6bed1cba6791dfdf14c97cd9ab89f302277f`.
  Package-manifest SHA-256:
  `1fd739e8f351b90946a69f4550972c4da50c42b7e97dd5d07293a2dbe9d4d32b`.
- The exact canonical plan produced 9,964 EOD rows with zero duplicate
  business keys and zero orphan Identity references. Plan SHA-256:
  `1c5957370c7bc957489d4d70a466567b7dd99b3d9b182b33eba66ec383218a6d`.
- Canonical Apply completed `published_and_verified`. EOD and Identity now
  align at 2026-09-08. Canonical EOD contains 305 contiguous XNYS sessions
  from 2025-06-23 through 2026-09-08.
- Latest EOD content fingerprint:
  `3942c205efc681d789ee4e7c1dc8051c801a21304fa112e936be51e52b4c42ac`.
  Latest Parquet SHA-256:
  `aa2b3e43e5c07fd43cbe111267142dc493483a4eac024e08d74da4c4c7164e9f`.

The successful 06:59 UTC observation proves availability at that time for this
one Basic-account session. It does not establish the provider's earliest or
guaranteed daily release time and does not authorize blind polling.

## Dell-local analytics and publication

The persistent owner-only daily workspace executed the real 2026-09-08 chain.
Phase 1a, incremental Phase 1b, Candidate, Entry Geometry, ETF Relationships,
Market Preview, Strategy Channels, Candidate Visual Context, and MI planning
all completed successfully in about 14.6 minutes of recorded action time.
Candidate remained the largest stage at about 5.8 minutes. Snapshot planning
then completed in about 2.3 minutes and persistent bundle construction in
about 1.4 minutes. Every stage retained its normal journal reservation,
postcondition, and fail-closed boundary.

- Market Intelligence 1.3 publication:
  `2026-09-08T071528Z-d6cc4ee57917`.
- MI payload SHA-256:
  `78cc31f056f224092aeebb250a30929cae777f1731f7c4365c0758665d7d3c8e`.
- MI payload logical fingerprint:
  `a7d063cc560df7851c7ace4ca0d766dff9e3ccfb6e1be6f573d5f04792d55976`.
- Dashboard Snapshot:
  `2026-09-08T072146Z-d6cc4ee57917`; Snapshot 1.11 / Dashboard 2.8.
- Snapshot active-pointer fingerprint:
  `3bbb7286d9747b9072b2d778d7c08310438f7c0e8baf8464a799a33f78eee857`.
- Both publications are fresh, lag zero, and outside stale-review mode.

Market Regime remains confirmed Balanced while both candidate states are
Defensive: Primary 44.9243 and Secondary 45.4356. Candidate display counts are
904 and 966 respectively. Market Intelligence still uses a bounded 26-session
window and therefore correctly retains `degraded_short_history`; the wider
305-session canonical price history has not silently changed this consumer.

## Persistent deployment correction and recovery

The bounded runner successfully built the exact daily release below its
persistent session workspace. Deployment then exposed a real integration
defect: capability and custody had been updated to accept the persistent path,
but the reviewed shell entrypoint still required the legacy `/tmp` layout.

No replay or speculative retry occurred. A read-only OCI inspection proved the
prior Production release unchanged, the attempted target absent, and zero
staging or failed-release residue. The journal formally closed the reservation
as `oci_deployment_recovered_not_completed`, with one remote read and zero
remote writes.

ADR 0184 and source commit
`32321f0dadd5c8f605ee11c8188d3ed90df0814d` align the capability, custody, and
shell entrypoint on one shared validator. The full API suite passed 2,310 tests
with only two existing dependency deprecation warnings. A subsequent focused
deployment/path suite and shell syntax check passed 30 tests.

## Final Serving Bundle and OCI proof

The final UI-only bundle reused the exact active 2026-09-08 Snapshot and Market
Intelligence bytes without recomputation or `/data` writes:

- OCI release: `2026-09-09T075821Z-32321f0dadd5`;
- source revision: `32321f0dadd5c8f605ee11c8188d3ed90df0814d`;
- bundle logical fingerprint:
  `57afdf0052521e7daf631bed5995c7abc9f714a8bf962983180d49b6a4cc2979`;
- deployment-manifest SHA-256:
  `85a37e213a14f0e48a34f7c167b4ee81ebcb4872a2eda78f8b5567d6b33ced8c`;
- checksum-file SHA-256:
  `107b887382b88c71ce6d67c5369407021290751fa020db217a3f2bc77b836edb`;
- final remote-state fingerprint:
  `97edc9097ff81bb73c93b2ac5744b0cb95fe67b94f7792b486c75a6fd8b323a1`.

Direct dry-run passed, one-shot Apply completed, and independent postflight
matched the exact release, source revision, bundle fingerprint, manifest, and
checksums. Nginx and the localhost-only Auth Service are active and enabled.
Public entry, protected routes, guest Session, Dashboard, Candidate
summary/detail, Strategy Channels, Sector ETF Rotation, logout, and renewed
protection passed. Guest and credential capability remain identical. There is
no staging release, failed release, failed unit, unexpected private listener,
credential, raw-provider payload, or Parquet in the Serving Bundle. Password
login and final human visual appearance remain manual checks.

## Final Dell and authority state

- `/data`: 4,250 files / 2,236,379,948 bytes;
- inventory fingerprint:
  `fbe9e916d6b1d68fb5cf10509ad6556a2e70a3087226ea36e4b3e7280b62b640`;
- symlinks and publication residue: zero;
- research readiness: `data_blocked`;
- no historical backfill or transient computation service is active;
- the installed timer remains read-only and SMTP remains unconfigured.

This run validates acquisition through deployment with the persistent Dell
runtime workspace and records one consolidated real-session execution. It does
not authorize unattended writes, performance claims, model tuning, automated
orders, or a new data source. Historical Membership, lifecycle, complete
corporate-action/adjustment evidence, costs, availability/revision lineage,
chronological evaluation, and a sealed holdout remain incomplete.
