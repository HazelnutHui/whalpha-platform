# Authoritative Current Context

Operational state verified at: 2026-09-13T13:54:48Z

Deployment state verified at: 2026-09-11T21:23:56Z

Repository context updated at: 2026-09-13 UTC

This is the compact recovery source for a new task or device. It records the
latest verified identities, capabilities, and hard boundaries. Actual-state
interpretation belongs in [current status](current-status.md), proposed work in
the [roadmap](roadmap.md), and execution history in the
[changelog](changelog.md), dated audits, and ADRs.

## Repository and infrastructure

| Field | Verified value |
| --- | --- |
| Workstation / user | `dell5820` / `hui` |
| Source repository | `/home/hui/projects/trading-intelligence-platform` |
| Source branch | `main`; verify the live HEAD with the report |
| Working tree | clean |
| Public site | `https://whalpha.com/` |
| OCI alias | `whalpha-oci` |
| Active OCI release | `2026-09-11T211340Z-26cab64fabda` |
| Deployed source | `26cab64fabdafca710d6471cb09ac8c62ef17c2d` |

Dell is the authority for code, data, governance, and heavy computation. OCI
is limited to static serving plus the localhost authentication and public
Session boundary. Windows and a future Mac are remote entry points. A newer
clean source commit does not imply that Production has been redeployed.

Use `scripts/admin/report-current-context.sh` for a credential-free,
network-disabled reread. The shared virtual environment still points its
editable metadata at an older worktree, so operator commands must use
`scripts/dev/run-project-python.sh` or repository-aware admin wrappers rather
than bare `.venv/bin/python -m`.

## Production

| Boundary | Verified value |
| --- | --- |
| Latest EOD / Snapshot session | 2026-09-11; fresh; zero session lag |
| Market Intelligence | `2026-09-11T205429Z-26cab64fabda`; contract 1.3 |
| Dashboard Snapshot | `2026-09-11T211340Z-26cab64fabda`; Snapshot 1.11 / Dashboard 2.8 |
| Market state | Primary 50.1578 Balanced; Secondary 50.1501 Balanced |
| Candidate display | 870 Primary / 924 Secondary; Baseline V1, not Universe size |
| Languages | English default; Simplified Chinese and professional neutral Spanish |
| Access | guest and credential Sessions intentionally have identical capability |
| Failure policy | API/Snapshot failure closes without synthetic Production data |

The active site contains Quant Research Lab, Model-Driven Equity Selection,
and three supporting market tools. The Lab is the sole model authority and
default workspace. The deployed Candidate score, Entry Geometry, and technical
Strategy Channels remain transparent but unvalidated **Baseline V1**. No Lab
model is active and no Production performance claim exists.

Independent deployment postflight matched the release, source, bundle,
checksums, services, protected routes, guest flow, Candidate routes, logout,
and residue state. Password login and final visual appearance remain manual
checks. Production consumes only 26 Market Intelligence sessions, so its
analytics status is `degraded_short_history` even though canonical EOD is much
deeper.

## Canonical Dell data

| Family | Verified current state |
| --- | --- |
| EOD | 1,255 contiguous XNYS sessions, 2021-09-13 through 2026-09-11; latest 9,971 rows; latest fingerprint `eec1f813851b378f47fbcd810728ed8b33b4748929ba85ff5d77e837bd12c904` |
| Identity | all 1,255 EOD sessions plus one Identity-only 2021-09-10 partition; latest 10,000 instruments / 13,176 provider identities |
| Identity source | 1,253 target sessions; 2026-08-13 and 2026-08-19 remain explicitly unbound |
| Membership | three signal-eligible sessions / 59,892 decisions; 1,250 physically separate latest-vintage research-only sessions / 21,263,558 decisions; combined 1,253 / 1,255 sessions |
| Corporate actions | recent canonical observation 70,099 rows; canonical action is bounded split-only; complete five-year split/dividend packages and resolution work remain private evidence, not canonical completion |
| Adjustment | sparse split-only outcome reconciliation; neutral omitted rows and total-return coverage are not proven |
| Lifecycle | canonical five-year lifecycle and terminal outcomes absent |
| Classification | historical point-in-time research classification absent |
| Fundamentals | cutoff-aware SEC issuer selection and aggregate security-projection census complete for four registered queries; only four sessions have strict as-operated next-open projection evidence, while reconstructed history remains development-only |
| Historical Coverage | partial family evidence exists; final transitive publication absent |

The canonical inventory is 21,025 files / 7,397,444,417 bytes with zero
symlinks and zero publication residue. Its last full inventory fingerprint is
`b4f1dc83b5b26a6ccde3b5dffd47ac58de465fced41d129ef74c0e2282228ff7`.

The corrected EOD edition covers 1,234 fully source-bound sessions through
2026-08-12 and has published EOD/Identity family evidence. This does not make
the full 1,255-session foundation or any research cohort performance-ready.

## Universe

The active provider-form Activation remains provisional and was derived from
analysis session 2026-08-19.

| Universe | Members | Fingerprint |
| --- | ---: | --- |
| Primary | 1,718 CS | `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978` |
| Secondary | 1,831 = 1,718 CS + 113 ADRC | `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295` |

Activation pointer fingerprint:
`dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168`.
Provider security form does not prove issuer operating structure or domicile.
Future Core/Broad activation remains deferred.

## Five-year research evidence

The rolling five-year **price and identity foundation is complete**. The
five-year **performance-eligible research database is not complete** and the
formal state remains `data_blocked`.

Important private Dell evidence includes:

- 1,250 physically separate reconstructed latest-vintage Membership sessions;
  together with three signal-eligible sessions, the formal five-year census
  covers 1,253 / 1,255 sessions and 21,323,450 decisions. ADR 0227 recovered
  the 37 collision-derived join-gate gaps under a separate V4 research method;
  only the two unavailable source sessions remain missing;
- a complete 1,255-session SEC filer/security link candidate with 10,681,604
  decisions; all issuer projection was initially disabled;
- ADR 0224's conservative issuer-fact projection class, covering 6,122,451
  admitted single-common-stock row-sessions structurally. The complete
  cutoff-aware census admits only 17,879 rows across four sessions at the
  strict as-operated next-open tier; 6,104,572 reconstructed rows across 1,249
  sessions remain development-only;
- 41,619,407 normalized SEC fact occurrences, a complete semantic census, and
  four exact issuer-level source queries. The complete 24,489,804-evaluation
  projection census measures reconstructed selection coverage of 84.97%
  Assets, 81.52% equity, 73.01% annual net income, and 61.98% annual operating
  income without retaining issuer values or opening outcomes;
- a complete five-year corporate-action source package and private resolution
  diagnostics, still without canonical lifecycle, terminal-return, neutral-row,
  or total-return authority; and
- the exact first-strategy source acceptance population: 20 unresolved action
  relations across four IDs plus 64 lifecycle-crossing IDs; and
- a formally bound SEC metadata pilot over all 64 lifecycle cases, retaining
  2,144 official filing locators. All cases have one of 219 candidates on or
  after their last canonical observation, but all eight complete security-
  lifecycle fields remain unsupported until document content and security
  identity are proven; and
- an immutable 219-request SEC primary-document plan with 219 unique official
  URLs in 22 fixed batches. It is a no-request artifact; source-content custody
  and field interpretation remain pending.

Exact package identities and counts are retained in:

- [Five-year SEC filer/security candidate audit](../audits/five-year-sec-filer-security-link-candidate-2026-09-13.md)
- [SEC projection-readiness audit](../audits/sec-filer-security-projection-readiness-2026-09-13.md)
- [SEC fundamental-query readiness audit](../audits/sec-fundamental-query-readiness-census-2026-09-13.md)
- [SEC fundamental-projection readiness audit](../audits/sec-fundamental-projection-readiness-census-2026-09-13.md)
- [First-strategy source sample audit](../audits/strong-leader-pullback-source-acceptance-sample-2026-09-13.md)
- [First-strategy SEC lifecycle pilot audit](../audits/strong-leader-pullback-sec-lifecycle-pilot-2026-09-13.md)
- [First-strategy SEC document plan audit](../audits/strong-leader-pullback-sec-document-plan-2026-09-13.md)
- [Five-year research baseline](../audits/five-year-research-foundation-baseline-2026-09-10.md)
- [Five-year research Membership continuation](../audits/five-year-research-membership-continuation-2026-09-13.md)
- [Five-year research Membership collision recovery](../audits/five-year-research-membership-collision-recovery-2026-09-13.md)

## Research and product authority

The durable product chain is:

```text
market state -> strength direction -> sector/theme -> validated stock candidate
-> trade preparation -> entry/invalidation -> position management
```

Quant Research Lab owns model identity, methods, evidence, validation, failure,
and lifecycle. Stock Candidates will consume only one to three separately
validated and explicitly activated models. Strong-Leader Pullback V1 remains
`preregistered_data_blocked`; it has fixture-tested mechanics, zero real
out-of-sample observations, and no Candidate authority.

The first SEC issuer-query registry, cutoff-aware selector, source-readiness
census, and aggregate security-projection census are finished. The engineering
path is reproducible, but the historical data gate is rejected: only four
sessions have strict projection evidence. Do not build a broad fact-by-session
panel or a security feature. Reopen this lane only for newly admitted
historical source-time evidence or a separately registered strategy need.

The first source-specific lifecycle pilot is now bound to the immutable
20-action / 64-lifecycle sample. SEC metadata narrowed the 64 lifecycle cases
to 2,144 document candidates, including 219 on or after the last canonical
observation, without promoting a single terminal fact. Those 219 documents are
now frozen into 22 deterministic no-request batches. The next internal gate is
resumable SEC source-content custody; a commercial sample remains limited to
the exact fields still unsupported after document review. Massive Starter is
not the sole lifecycle authority.

Only after admissible Membership, lifecycle/terminal outcomes, action/adjustment
semantics, exact Historical Coverage, costs, and sealed evaluation custody are
admitted may the first real chronological study begin. See the
[roadmap](roadmap.md).

## Automation and boundaries

The installed daily wake timer is active but read-only. It performs no fetch,
Apply, analytics, publication, deployment, alert delivery, or credential
access. No unattended write-capable scheduler is installed; SMTP is
unconfigured. The guarded manual daily chain works end to end. Its latest
measured offline portion took about 17.1 minutes; Candidate was the main
hotspot at about 7.0 minutes and one CPU core. The rejected segmented path must
not be reopened without a new measured budget breach and a design addressing
both known gaps.

No current document authorizes provider access, credential use, `/data`
mutation, research outcome opening, model activation, publication, deployment,
scheduler mutation, order execution, or destructive cleanup.

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
2. Run `scripts/admin/report-current-context.sh`; use full history validation
   only for periodic or investigative review.
3. Compare repository, EOD, Identity, Activation, MI, Snapshot, inventory, and
   residue with this baseline.
4. Classify differences before mutation. Never silently fetch, Apply, publish,
   deploy, rewrite a pointer, or clean a release.
5. Read only the contracts, ADRs, operations, and audits tied to the selected
   objective.
