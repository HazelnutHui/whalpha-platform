# Authoritative Current Context

Operational state verified at: 2026-09-15T06:31:47Z

Deployment state verified at: 2026-09-14T23:44:48Z

Repository context updated at: 2026-09-15 UTC

This is the compact recovery source for a new task or device. It records only
the latest verified identities, capability boundaries, and exact evidence
needed to resume work. Interpretation belongs in [current status](current-status.md),
future sequencing in the [roadmap](roadmap.md), and execution history in the
[changelog](changelog.md), dated audits, and ADRs.

## Repository and infrastructure

| Field | Verified value |
| --- | --- |
| Workstation / user | `dell5820` / `hui` |
| Source repository | `/home/hui/projects/trading-intelligence-platform` |
| Source branch | `main`; verify the live HEAD with the context report |
| Working tree | clean at the verified report boundary |
| Public site | `https://whalpha.com/` |
| OCI alias | `whalpha-oci` |
| Active OCI release | `2026-09-14T234322Z-70438696e33c` |
| Deployed source | `70438696e33c9d7a3302a272ff13846a5f38b249` |

Dell owns code, data, governance, and heavy computation. OCI is limited to
bounded public serving and localhost authentication. A newer clean source
commit does not imply Production was redeployed.

Use `scripts/admin/report-current-context.sh` for a credential-free,
network-disabled reread. Run project Python only through
`scripts/dev/run-project-python.sh` or repository-aware admin wrappers because
the shared virtual environment retains older editable-worktree metadata.

## Production

| Boundary | Verified value |
| --- | --- |
| Latest EOD / Snapshot session | 2026-09-11; stale by one completed session at the 2026-09-14 deployment review |
| Market Intelligence | `2026-09-11T205429Z-26cab64fabda`; contract 1.3 |
| Dashboard Snapshot | `2026-09-11T211340Z-26cab64fabda`; Snapshot 1.11 / Dashboard 2.8 |
| Market state | Primary 50.1578 Balanced; Secondary 50.1501 Balanced |
| Candidate display | 870 Primary / 924 Secondary; Baseline V1, not Universe size |
| Languages | English default; Simplified Chinese and professional neutral Spanish |
| Access | guest and credential Sessions intentionally have identical capability |
| Failure policy | API/Snapshot failure closes without synthetic Production data |

Quant Research Lab is the sole core workspace and model authority.
Model-Driven Equity Selection is its future downstream consumer. The deployed
Candidate score, Entry Geometry, and technical Strategy Channels remain
transparent, unvalidated **Baseline V1**. No Lab model is active and no
Production performance claim exists.

Independent postflight matched release, source, bundle, checksums, services,
protected routes, guest flow, Candidate routes, logout, and residue state.
Password login and final visual appearance remain manual checks. Production
Market Intelligence still consumes only 26 sessions and therefore reports
`degraded_short_history`; this is a consumer-integration limit, not a price-
acquisition gap.

## Canonical Dell data

| Family | Verified current state |
| --- | --- |
| EOD | 1,255 contiguous XNYS sessions, 2021-09-13 through 2026-09-11; latest 9,971 rows; latest fingerprint `eec1f813851b378f47fbcd810728ed8b33b4748929ba85ff5d77e837bd12c904` |
| Identity | aligned to all EOD sessions plus one Identity-only 2021-09-10 partition; latest 10,000 instruments / 13,176 provider identities |
| Identity source | 1,253 target sessions; 2026-08-13 and 2026-08-19 remain explicitly unbound |
| Membership | 3 signal-eligible plus 1,250 physically separate reconstructed research-only sessions; combined 1,253 / 1,255 |
| Corporate actions | 4,643 first-strategy exposures; 4,623 exact event-date assignments and 20 unassigned; absence neutrality remains unproven |
| Adjustment | 101,321 sparse split-only rows; 98,291 clear and 3,030 quarantined; neutral omitted rows and total-return coverage are unproven |
| Lifecycle/terminal | 219 exact + 83 finite-interval references of 302 five-session paths; zero unbounded; references are not outcomes |
| Classification | complete point-in-time historical classification absent |
| Fundamentals | cutoff-aware SEC engineering exists for four registered queries; only four sessions have strict as-operated next-open projection evidence |
| Historical Coverage | final pre-research review V2 is `rejected_data_blocked`; no research-ready manifest exists |
| Method engineering | launch review V1 is `ready_for_outcome_blind_method_engineering` over 287 sessions / 437,402 paths |
| Reconstructed development labels | owner-only Dell package over 105 development sessions / 166,313 observations / 498,939 labels; validation and holdout labels remain zero |
| Reconstructed development statistics | 24 × 3 × 3 = 216 summaries; V1 is `inconclusive_evidence_floor`, no parameter lock, Validation remains closed |

Canonical inventory: 21,025 files / 7,397,444,417 bytes, zero symlinks, zero
publication residue; fingerprint
`b4f1dc83b5b26a6ccde3b5dffd47ac58de465fced41d129ef74c0e2282228ff7`.

The five-year price and stable-Identity depth is complete. The professional
performance-eligible database is not complete. Reconstructed Membership is
not `as_operated`; price depth never relabels lifecycle, action, adjustment,
fundamental, cost, or Historical Coverage evidence as ready.

## Universe

The active provider-form Activation remains provisional and was derived from
analysis session 2026-08-19.

| Universe | Members | Fingerprint |
| --- | ---: | --- |
| Primary | 1,718 CS | `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978` |
| Secondary | 1,831 = 1,718 CS + 113 ADRC | `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295` |

Activation pointer fingerprint:
`dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168`.
Provider form does not prove issuer operating structure or domicile. Future
Core/Broad activation remains deferred.

## First research program

Strong-Leader Pullback V1 is frozen as
`preregistered_data_blocked`. Its 24-combination budget, Primary/Secondary
roles, next-open entry, 1/3/5-session stock outcomes, chronological split,
purge/embargo, costs, controls, statistics, and holdout rules are registered.

Two different gates must remain visible:

- **Method engineering:** authorized for the registered method, synthetic and
  adversarial tests, private outcome-blind diagnostics, zero-row future-label
  interfaces, and Lab method/readiness presentation.
- **Strict exact/as-operated performance research:** remains rejected until all
  point-in-time Membership, lifecycle, action, adjustment, cost, and Historical
  Coverage requirements are exact.
- **Reconstructed development:** separately admitted under ADR 0268 with
  complete-session ranks, frozen mechanical adjustments, conservative terminal
  intervals, fixed costs, and sealed evaluation controls.

The launch report is in owner-only Dell custody at
`historical-evidence/strong-leader-pullback-method-engineering-launch-review/review=20260914-v1`.
Report SHA-256:
`db242897d66fb61a4f638762e5736b27b3cb788f328431a32636d02d2d9da690`;
logical fingerprint:
`1abb4ed53d4a4cb5bb6482432db254a0019168aae2712983a9d00aaa4cffef8c`.

The canonical outcome-blind method contract is
`strong-leader-pullback-method/1.0`; method fingerprint:
`ed3e83b1a3827d1faddea6cb0eedc0471c5e9db854d5577b7faa12e0084186ba`.
Its derived Lab record is `quant-research-lab-model-record/1.2`, remains
method-only and Candidate-ineligible, and carries no real result. It now binds
the replayed reconstructed method-engineering disclosure and code revision
`9879f2e890840487c90a89078eb31f0cbff273c0`; record fingerprint:
`4622fb2fe86cc28249f53c89003f450a9e9d19c5696cd4eb865f413140b982c8`.
The deployed Lab now presents the verified five-year research foundation,
its limitations, and the frozen evaluation controls beside the model record;
it calculates no aggregate readiness score. The V1.2 method/readiness surface
and foundation snapshot are part of the active UI-only OCI release recorded
above; the underlying 2026-09-11 Snapshot and Market Intelligence publication
were reused without mutation.
The pure mechanics contract is `candidate-strategy-research-execution/1.2`;
each mechanics batch binds the same method and experiment fingerprints and is
fixed to zero forward outcomes and zero performance authority.
The private diagnostic contract is
`strong-leader-pullback-method-diagnostics/1.1`; its pure aggregator binds the
same method, preserves explicit missing paths, and carries no outcome or
parameter-selection authority. The retained Dell report is
`historical-evidence/strong-leader-pullback-method-diagnostics/report=20260914-v2`:
417,209 of 437,402 paths are complete across 287 sessions; report SHA-256
`8bcd602c64c7a1ab403a9c97bea21c8edb1758b60d46f879cf23b4bf7c015b36`;
logical fingerprint
`c082566f283516b9a93d5658832450fb85071a3b59892cb8d922c1f37af34bd8`.
Its price and Regime values are reconstructed proxies, not canonical or as
operated. Observation contract 1.2 preserves finite extreme raw values without
changing any registered trigger threshold. An independent complete replay
returned the identical report and fingerprints with zero external, canonical,
or Production writes.

The stricter exact/as-operated pre-research report remains
`rejected_data_blocked`; it is not the separate ADR 0268 reconstructed V2
decision. Strict report SHA-256:
`0c433cd4d8f97c5e6b9df0af5cfaf4533f83160ab07d88ed7c5774dbd74d5bb1`;
logical fingerprint:
`b58a3671451ba89332b0fe437ecdea48389156ffac59bd1cc26266700c81a149`.

All detailed source packages, intermediate hashes, and case-by-case decisions
remain in the [dated audits](../audits/) and
[historical execution archive](../audits/project-execution-archive-through-2026-09-14.md).
Do not copy them back into this recovery file.

LSEG contact is owner-reported submitted, but no response, sample, quote,
entitlement, or permission decision has been reviewed. LSEG, ICE, S&P,
Norgate, or another provider remains optional future evidence work. No named
source is a prerequisite for the admitted reconstructed lane. Any future
commercial sample must still pass the frozen 20-action / 64-lifecycle
acceptance population before it changes a stronger exact/as-operated claim.

ADR 0267 and Source Acceptance Result V1 freeze provider-neutral evaluation of
that population. ADR 0268 adds a separate reconstructed-research admission that
preserves complete cross-section ranks and requires finite adversarial bounds
for every non-exact terminal reference. The formal V2 report correctly binds
287 chronological sessions, 20 warm-up sessions, 267 rankable sessions, 254
complete sessions, and 13 whole-session exclusions. Terminal references are
219 exact plus 83 finite intervals, with zero unbounded paths.

The owner-only report is
`historical-evidence/strong-leader-pullback-research-admission-v2/review=20260915-v1`;
report SHA-256
`aefaa2590d89d310a16d0ff0d0c3eb84e185611c633448b2af28c26628c4e49c`;
logical fingerprint
`6b6ea132a8efb68cf0ab21ed5911871361055692d92516a344d185415ca06a16`.
An exact zero-network replay returned `already_present`. It opens development
labels and development-only selection, but not validation, holdout,
performance claims, Candidate activation, publication, or Production.

The first immutable reconstructed development dataset is retained at
`historical-evidence/strong-leader-pullback-reconstructed-development-dataset/dataset=20260915-v1`.
It contains 105 signal sessions, 166,313 complete observations, and exactly
498,939 independent 1/3/5-session label rows: 498,580 observed exact, 90
terminal exact, 44 terminal interval, 153 unavailable-evidence, and 72
unexecutable rows. Validation and holdout labels are zero. Manifest SHA-256:
`92e9f078db840d3d8e341b4e15757429e26ff4acbdb9564aebb387aa07a5a267`;
logical fingerprint:
`91300da44caf35f838912db3d4060a6bbc98aeea23f81845194e1302e11c43c4`.
An independent full reread returned `already_present` with the same identities,
counts, owner-only modes, and zero external or canonical writes. See the
[dataset audit](../audits/strong-leader-pullback-reconstructed-development-dataset-2026-09-15.md).

The fixed V1 development-statistics run is retained at
`historical-evidence/strong-leader-pullback-reconstructed-development-statistics/report=20260915-v1`.
Its report SHA-256 is
`c29f04b5e6da95e2256c137f23d00898b313325ac09e982a991bb823ce0f7852`;
logical fingerprint is
`f0006fa38a7a729dca5b2cd34369e7c3bd2110aa17096bcd091d72875ce71f7f`.
The result is `inconclusive_evidence_floor`: 23 of 24 primary combinations
met general inference floors, but only one met the frozen reported-Regime
floor. No endpoint winner or parameter lock exists. A zero-network replay
returned `already_present`. See the
[formal statistics review](../audits/strong-leader-pullback-reconstructed-development-statistics-2026-09-15.md).

ADR 0272 registers one and only one coverage-corrected replacement selection
attempt. It retains all 24 combinations, treats sparse Regime slices as
inconclusive rather than a global selection veto, adds fixed economic and
stability gates, and records two total protocol trials. Policy fingerprint:
`9fa09e0b627aed2c1bb1f108eec2d73bfeb3a5407b3c0850b3605b23ef0991f9`.
No replacement result exists yet.

The original five-document and exact two-document supplemental SEC packages
are retained in owner-only custody. The supplement used two requests, zero
retries, and 5,064,066 bytes; manifest SHA-256
`e09a68dfaa896faecd8bd06f3ffcec62edf49997a841a1ac18752043d3bf8330`;
logical fingerprint
`2fc86e39950e93b0f93fc96a8d8bfad20e4efb4be62b3a74b87cf279ed9b0eee`.
The zero-network supplemental adjudication matched all three missing facts.
The final terminal report SHA-256 is
`5a49da2a9c148b2c237faf3b3232cd1a1de5f532c6a575645b455f3b2145bcdd`;
logical fingerprint
`37e8f7adf3433649c18961a96390be7f27ee2c0009f0d84609277ca4687c1777`.
See the [SEC source audit](../audits/strong-leader-pullback-terminal-reference-sec-source-2026-09-15.md)
and [final bounds audit](../audits/strong-leader-pullback-terminal-reference-final-review-2026-09-15.md).

## Automation and boundaries

The installed daily wake timer is active but read-only. It performs no fetch,
Apply, analytics, publication, deployment, credential access, or alert
delivery. No unattended write-capable scheduler is installed; SMTP is
unconfigured. The guarded manual chain works end to end.

No current document authorizes another live SEC acquisition, `/data` mutation,
validation or holdout access, model activation, publication, deployment,
scheduler mutation, order execution, or destructive cleanup. The admitted
development-only statistics stage is complete and inconclusive; V1 cannot be
retuned. Only the single registered replacement-selection run is next; no
Validation or later stage is open.

## Cross-device continuity

- Windows already has a dedicated passwordless SSH key and saved Dell project.
- A future Mac must join the same Tailscale network and create its own SSH key;
  never copy the Windows private key.
- Add only the Mac public key to Dell, configure alias `dell5820`, save this
  same canonical repository path, and run the read-only context report.
- Never record server addresses, private-key paths, credentials, or Session
  material in Git or chat.

## Recovery procedure

1. Read `AGENTS.md`, root `README.md`, `docs/README.md`, this file, and
   `current-status.md`.
2. Run `scripts/admin/report-current-context.sh`; use full-history validation
   only for periodic or investigative review.
3. Classify every difference before mutation. Never silently fetch, Apply,
   publish, deploy, rewrite a pointer, or clean a release.
4. Read only the contracts, ADRs, operations, and audits tied to the selected
   objective.
