# Authoritative Current Context

Verified at: 2026-08-27 UTC

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
| Deployed bundle source commit | `1f3eb5512eb0d1ba67112395450c2783221596da` |

Codex-created worktrees may be detached at the same commit. Always verify the
main repository separately before treating a worktree as the source of truth.
The repository HEAD is intentionally not frozen in this document because a
documentation or code commit legitimately advances it. The read-only report
must show the current HEAD and cleanliness separately from the immutable commit
recorded by a deployed bundle.

## Formal local state

The 2026-08-27 reconciliation used the project readers after the separately
approved 2026-08-25 Identity/EOD publication. It reread the full local
inventory and active custody/contracts. The active Production MI/Snapshot is
still the older 2026-08-24 review release; the verified 2026-08-25 analytics
below are local `/tmp` evidence until a new publication is separately applied.

| Boundary | Active verified value |
| --- | --- |
| Canonical EOD | 28 sessions, 2026-07-17 through 2026-08-25 |
| Latest EOD | 2026-08-25, 9,954 rows |
| EOD content fingerprint | `48a2160a15d611e0fca42a8ad95128f0051e2a7fe29c9574141a1209ac7ff5ff` |
| EOD Parquet SHA-256 | `99ac16444ddc67daf0751b6843b4b2d7218fb024e33a68fd5a96dacd6339d8ad` |
| Same-day Identity | 9,974 instruments / 13,141 provider identities / 9,974 resolvers |
| Identity logical fingerprint | `2d23e6f0b5a29273d6aef5677384268c96f0fb435a7f92eb73a7863d637951f7` |
| Activation analysis session | 2026-08-19 |
| Activation pointer fingerprint | `dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168` |
| Activation logical fingerprint | `6ea818cb3079bb77fd5fe1b8000530d2c8e2d1127fcccd40be68ac590678c7a5` |
| Primary | 1,718 CS; fingerprint `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978` |
| Secondary | 1,831 = 1,718 CS + 113 ADRC; fingerprint `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295` |
| Market Intelligence | `2026-08-24T142500Z-1f3eb5512eb0`, contract 1.1 |
| Market Intelligence payload SHA-256 | `978519c1db9630ef456a1e0a2e27a35ab5cdd8786a43727ce20d24cc86d534a6` |
| Market Intelligence logical fingerprint | `9d9f04541b3d5cfc4e3282a2f2b9e3b15e43811f6d66c1459a3f7b4f7babcf5a` |
| Candidate publication | 146 Primary / 155 Secondary cards; fingerprint `fb586f32af2e7ccb00b79a5d5d72701175fa021e93ec262374a779f5b83c48a6` |
| Dashboard Snapshot | `2026-08-24T144500Z-1f3eb5512eb0` |
| Contracts | Snapshot 1.6 / Dashboard 2.3 |
| Snapshot pointer fingerprint | `223ae10170097dcfef9f9352c997a96bdc9200f75232a8f23a22db1b354bf334` |
| Active review metadata | `stale_review`: actual 2026-08-24, then-expected 2026-08-25, lag one |
| Current local freshness gate | `stale`: actual 2026-08-25, expected 2026-08-26, lag one |
| `/data` inventory | 321 files / 110,607,400 bytes |
| `/data` inventory fingerprint | `6163b94714419a9421ac8271d0d26aeccbe6e5cfcfe6e169224d40aeec63c069` |
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
- Credential and equal-capability guest entry both create the same role-free
  protected Session and load the same product payload.
- Production bundles exclude synthetic Dashboard data and fail closed on API
  or Snapshot failure.
- Production contains the Phase 5 offline candidate score/risk/state,
  independent Oracle, canonical `/tmp` audit/reread boundary, bounded
  language-neutral consumer, MI 1.1, Snapshot 1.6 / Dashboard 2.3, strict
  frontend parser, and the third first-level Stock Candidate workspace. MI 1.1,
  Snapshot 1.6 / Dashboard 2.3, and the matching OCI bundle are active.
- The current formal candidate audit is the 2026-08-24 baseline-3 directory
  `/tmp/whalpha-candidate-phase5c-baseline3-20260824.0JaMYi`, fingerprint
  `1f25a1c9060d459e372903ad116579973c709363f365f19fa66bb515774c93df`.
  It binds two calculable sessions, has zero Oracle mismatch, and passes all
  four replay-equivalence gates. This `/tmp` evidence is local development
  custody, not a Production pointer or deployment artifact.
- The active MI 1.1 payload contains 146 Primary / 155 Secondary
  display-review cards; Snapshot 1.6 / Dashboard 2.3 serves the same bounded
  Candidate file of about 5.14 MB.
- Candidate Entry Geometry V1 remains a separate, immutable source calculation.
  Its original formal 2026-08-24 audit is
  `/tmp/whalpha-candidate-entry-baseline1-20260824`, fingerprint
  `6b013f948d5c6d1011cab0685f661907739b77f1cd1fbfa4307d4789a8638bee`,
  with zero independent-Oracle mismatch and input-permutation equivalence. It
  does not alter active Candidate score/state/rank. Primary Balanced top 50 contains 41
  wait-for-reset high/extreme extensions, two technical-review-ready rows, four
  breakout watches, and three no-viable-setup rows.
- A new additive consumer is implemented and locally verified but not yet
  active in Production: Candidate publication 1.1, MI 1.2, Snapshot 1.7 /
  Dashboard 2.4, and the bilingual entry-location view. It preserves formal
  leadership rank and selects fixed `review_now`, `watch_trigger`,
  `wait_reset`, and `other_research` lanes from the complete hard-risk-qualified
  population under the existing concentration caps.
- The verified 2026-08-25 Candidate audit is
  `/tmp/whalpha-candidate-phase5c-20260825.AGE0pk`, fingerprint
  `32c0647ae18e165052a4fdb5ea00a0ae7f3cec5306daecdc4360ef7de829e626`.
  The bound entry audit is
  `/tmp/whalpha-candidate-entry-20260825.LpjkWN`, fingerprint
  `3875872f719537170f17aab04b0715c86ffb67259f75adf0ee796b4a8f0c182b`.
  Both have zero Oracle mismatch, zero network/Production writes, and passed
  their formal reread; entry input-permutation equivalence is true.
- On 2026-08-25 Primary Balanced, the complete hard-qualified population is
  1,282: 52 `review_now`, 1,096 `watch_trigger`, 125 `wait_reset`, and nine
  `other_research`. Each lane has an eight-card cap; concentration rules can
  yield fewer cards. The resulting local Candidate publication 1.1 fingerprint
  is `025953284275b478d5f71f6974fd34faf197902bb9104ae513c4d525b3434df0`.
- Production contains the tested first-level workspace
  shell and user-facing `Market Regime & Opportunities` / `市场风向与机会` name.
  Market Regime & Opportunities is the first navigation item and default
  workspace; Market Structure & Activity is second.
  It centralizes Universe/language/Session controls, adds a factual first-screen
  market-structure summary, Daily Decision Brief, decision-lane relationship
  selection, prior-state markers, consolidated reliability warning, and
  collapsed 16-pair audit table.

## OCI production state

The active remote release and matching local immutable bundle are
`2026-08-26T151600Z-1f3eb5512eb0`, built from deployed source commit
`1f3eb5512eb0d1ba67112395450c2783221596da` and bound to the active Snapshot
and Market Intelligence publication. A later repository HEAD does not
invalidate this immutable lineage; the report exposes whether the two commits
match rather than hiding the bundle.

The 2026-08-26 deployment verified the remote `current` symlink, clean bundle
manifest, Nginx and Auth Service active and enabled, and the Auth Service bound
only to `127.0.0.1:8010`. Postflight checked the public data-free entry,
unauthenticated Dashboard redirect, private-data/auth-status 401 responses,
external internal-verify 404, then created a temporary guest Session and proved
it read the Dashboard and exact Snapshot 1.6 Candidate payload before logout. No
credential or cookie content was printed or retained. Password-based browser
behavior remains a manual user check.

Remote release retention contains the active release plus
`2026-08-26T103119Z-f344a589a8c9`, `2026-08-26T094339Z-f9711d5403f6`, and the
deliberate older selectable-Universe fallback
`2026-08-19T083341Z-7ed7fdc21686`, with no staging/partial residue. The local
report remains network-free and cannot replace this separately authorized OCI
check.

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
access, further UI implementation, or another quantitative feature. The
completed entry-geometry shadow described above is evidence, not continuing
authorization.

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
