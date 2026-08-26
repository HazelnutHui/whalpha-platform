# Authoritative Current Context

Verified at: 2026-08-26 UTC

This is the authoritative compact handoff for new Codex tasks and new devices.
It records current facts and their evidence boundary. Product history remains
in the [changelog](changelog.md) and dated audits. Proposed sequencing remains
in the [roadmap](roadmap.md).

## Repository

| Field | Verified value |
| --- | --- |
| Workstation | `dell5820` |
| User | `hui` |
| Source-of-truth repository | `/home/hui/projects/trading-intelligence-platform` |
| Branch | `main` |
| Deployed bundle source commit | `895a073769adbe6ce7313cc82b4fa932a22d6cc1` |

Codex-created worktrees may be detached at the same commit. Always verify the
main repository separately before treating a worktree as the source of truth.
The repository HEAD is intentionally not frozen in this document because a
documentation or code commit legitimately advances it. The read-only report
must show the current HEAD and cleanliness separately from the immutable commit
recorded by a deployed bundle.

## Formal local state

The 2026-08-26 reconciliation used the project readers. The complete Market
Intelligence source-validation path passed before a reporting-only descriptor
field error; the corrected extraction then reread the active artifacts.

| Boundary | Active verified value |
| --- | --- |
| Canonical EOD | 27 sessions, 2026-07-17 through 2026-08-24 |
| Latest EOD | 2026-08-24, 9,942 rows |
| EOD content fingerprint | `fd9ae8083442ea45a22a2c01f69c1b5eed5d471e31fcdc163468f2220f7be63a` |
| EOD Parquet SHA-256 | `1a1a1b4b8c4474e0319788ae41f5251278ea9dd353b61c0e8e1c9dcb419f32a7` |
| Same-day Identity | 9,968 instruments / 13,131 provider identities / 9,968 resolvers |
| Identity logical fingerprint | `d68832d2c1f3ee0f9d5486eb615cc7a9aac1dc890d7339a4d57455a194277de1` |
| Activation analysis session | 2026-08-19 |
| Activation pointer fingerprint | `dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168` |
| Activation logical fingerprint | `6ea818cb3079bb77fd5fe1b8000530d2c8e2d1127fcccd40be68ac590678c7a5` |
| Primary | 1,718 CS; fingerprint `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978` |
| Secondary | 1,831 = 1,718 CS + 113 ADRC; fingerprint `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295` |
| Market Intelligence | `2026-08-24T043223Z-aee1a6ab0f67` |
| Market Intelligence payload SHA-256 | `58b48bbd14cc033435eb11c307556c9e137b70e0766e333695aba0c56c07f374` |
| Market Intelligence logical fingerprint | `35d2080f0720519960c49825df374fda2a1d1103f8874dc19238cf4c3d3a0d9e` |
| Dashboard Snapshot | `2026-08-24T045652Z-aee1a6ab0f67` |
| Contracts | Snapshot 1.5 / Dashboard 2.2 |
| Snapshot pointer fingerprint | `9d98680062a2efc274855e40e10418192aa91a68dd34e135bade942cda1899b7` |
| Data status | `stale_review`: actual 2026-08-24, expected 2026-08-25, lag one |
| `/data` inventory | 302 files / 95,250,500 bytes |
| `/data` inventory fingerprint | `a90d8c10f6dd0ae7174f8c2c7810042cd5ff3ad30689c72163b7ed42d1cdbe78` |
| `/data` symlink/staging/partial residue | zero |

Workstation listener review found no Python, Node, Vite, Uvicorn, or project
application process and no unexpected project listener. Normal SSH, DNS, and
Tailscale listeners were present.

## Analytics and presentation

- Market Regime: Primary 50.6585 Balanced; Secondary 50.9036 Balanced.
- Fixed registry: 30 ETFs and 16 relationships with 5/10/20-session windows.
- Relationship history: 336 rows over 26 sessions; confidence is low.
- English and Simplified Chinese use one language-neutral payload. English is
  the first-visit default.
- Session authentication remains active. Guest access is absent.
- Production bundles exclude synthetic Dashboard data and fail closed on API
  or Snapshot failure.

## OCI production state

The active remote release and matching local immutable bundle are
`2026-08-26T062038Z-895a073769ad`, built from deployed source commit
`895a073769adbe6ce7313cc82b4fa932a22d6cc1` and bound to the active Snapshot
and Market Intelligence publication. A later repository HEAD does not
invalidate this immutable lineage; the report exposes whether the two commits
match rather than hiding the bundle.

An authorized SSH read-only check on 2026-08-26 verified the remote `current`
symlink, clean deployment manifest fields, Nginx and Auth Service active and
enabled, and the Auth Service bound only to `127.0.0.1:8010`. Loopback HTTPS
checks verified the public data-free login, unauthenticated Dashboard redirect,
private-data and auth-status 401 responses, and external internal-verify 404.
No credential content or public endpoint was accessed. Authenticated browser
behavior remains unverified because no password was read or used.

Remote release retention is clean: only the active release and
`2026-08-19T083341Z-7ed7fdc21686` rollback remain, with no staging/partial
residue. The local report intentionally remains network-free and cannot replace
this separately authorized OCI check.

## Product guardrails

- Decision support, not automated trading, execution, or prediction.
- Conclusion first, with raw values, parameters, contributions, evidence,
  counterevidence, and market-state adjustment available for inspection.
- Never call price/volume proxies actual fund flow.
- Never call underlying-stock forward return an option return.
- Keep security form, issuer structure, listing scope, evidence, and Universe
  disposition separate and effective-dated by stable `instrument_id`.
- Quarantine unknown, ambiguous, malformed, heuristic-only, and insufficient-
  evidence records.
- Core remains the future policy goal and Broad the future secondary policy,
  but active provider-form Universes remain provisional until authoritative
  issuer evidence satisfies the documented gates.

## Explicitly not authorized by this context

This handoff does not authorize provider or SEC access, credential inspection,
EOD or Identity acquisition, scheduler changes, Activation, publication,
Snapshot creation, bundle generation, OCI deployment or rollback, guest
access, UI implementation, or a new quantitative feature.

## Cross-device continuity

- Windows already has its own dedicated passwordless SSH key and saved Dell
  remote project.
- For Mac, first join the same Tailscale network, then generate a new Mac-only
  SSH key. Never copy the Windows private key.
- Add only the Mac public key to Dell, configure the `dell5820` SSH alias, save
  `/home/hui/projects/trading-intelligence-platform` in Codex Desktop, and run
  the read-only context report before continuing work.
- Never place literal server addresses, private-key paths, or credentials in
  repository documentation.

## Recovery procedure for a new task

1. Read `AGENTS.md`, `README.md`, `docs/README.md`, this document, and
   `current-status.md`.
2. Run `scripts/admin/report-current-context.sh` from the source-of-truth
   repository.
3. Compare repository, deployed-source commit, EOD, Identity, Activation,
   Market Intelligence, Snapshot, inventory, and residue fields with this
   baseline. A newer clean repository HEAD is not itself a deployment mismatch.
4. Classify differences before making changes. Do not silently rewrite an
   active pointer, rerun acquisition, or deploy.
5. Read only the product, architecture, operation, ADR, and audit documents
   relevant to the selected single objective.
