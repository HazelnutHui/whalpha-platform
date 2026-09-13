# Authoritative Current Context

Operational state verified at: 2026-09-13T21:52:35Z

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
  lifecycle fields remain unsupported; document content and security identity
  require separate adjudication; and
- an immutable 219-request SEC primary-document plan with 219 unique official
  URLs in 22 fixed batches; and
- the completed private SEC primary-document source package: 219 / 219
  documents, 5,430,894 retained bytes, zero retries, manifest SHA-256
  `38d7cf826769e4f3541ba5e22b4066b3f9a8779e56c770f81e7c2b5fc0833bb5`,
  and logical fingerprint
  `2bf0aa1510902415c0530d2f49630b7b03757d6780805157b03ffbad1c7d1c3e`.
  Every document passed a separate zero-network formal reread, but no content
  has been interpreted into a security-level lifecycle fact; and
- the completed document-content census: 219 / 219 parsed, report SHA-256
  `a566d966236fb046a88e662dacbcfa35ff93d57f319b86a218ef0f0ddde46869`,
  logical fingerprint
  `d22f5436aaeabeee3fe8bee8061594b42f479f25b8ad9f575fab81f3e781e77a`.
  Its bounded contexts are lexical candidates only; fact counts remain zero;
  and
- the completed structured Form 25 candidate package: 64 / 64 notices across
  62 stable-ID locators, report SHA-256
  `c634eaa46a4d143810f2e24c51d7192a48f83a590b6c8b54b353f48563b2c099`,
  and logical fingerprint
  `acdf61a7438ea494f01f47ec110db6f914fa028b40cdb214602721d09960e505`.
  The two repeated IDs remain separate and every complete field-support count
  is still zero; and
- the completed field-level Form 15 candidate package: 66 / 66 documents
  across 62 stable-ID locators, report SHA-256
  `12a8164025d0aefee9de277b79f1e94f2f371afc84fd1e8c363cb4607de4acca`,
  and logical fingerprint
  `b5a953a4e3227ed93eef73bd1c39db7bca0a9c3061611fc1e98e45fb97914e78`.
  It preserves two multi-file-number records and one certification date before
  filing without inferring effective or terminal status; and
- the completed form-aware transaction candidate package: 89 / 89 documents
  across 63 stable-ID locators, report SHA-256
  `fbaf9116fc23e00dcdeeb21075c7bdfb196b6d178b588d76fb549b27d8d790ae`,
  and logical fingerprint
  `15ecfe9c5e737aa4090ed144de822b916040390a7a513f36b09715ecf25b9d2b`.
  It separates 61 structured 8-K completion scopes, one non-Item-2.01 8-K, 24
  tender amendments, one referenced-exhibit-only 6-K, and two proxy materials;
  candidate contexts remain non-facts; and
- the completed cross-document case coverage census: all 219 candidate
  documents joined to the exact 64 stable-ID cases, with 61 structured
  transaction scopes and three explicitly exceptional profiles. Candidate
  material is present for 0 to 64 cases depending on the field, but all 512
  case/field results remain `unsupported`. Report SHA-256 is
  `77b81064c1a494275029a2c667bac7ef2cb99c83d446aa491c2be29a3fe1e09a`
  and logical fingerprint is
  `98d9c5d3da4d02316c020f0705ce1e8714a8b4086ead1a897a9e3a5511f7c1b9`;
  and
- the first point-in-time case adjudication: all 62 Form 8-K covers parsed into
  70 complete security rows, with 61 in-window common-equity document matches
  and one later IPG debt-event document rejected outside the source lifecycle
  window. Sixty-one stable-security/listing fields are now matched; the other
  451 case/field cells remain unsupported. Report SHA-256 is
  `7f868b6f1d4471cd8690d4ff4f0daf2b439f0d51808021ba5aaa30de6cb1eb94`
  and logical fingerprint is
  `e15db9ddd43efaa489fc1542ca0d42daf7e410bae91440cdf0bcccaee3507bcd`;
  and
- the typed transaction-event adjudication: all 61 in-window structured cases
  have one unique issuer completion date under four bounded rules. Fifty-two
  dates equal the cover report date and nine occur one to four days later.
  Report SHA-256 is
  `acf4b350e89d56bbb9ac32bfcd906cec08c66721d5d5661994ab5ed68a0fd237`
  and logical fingerprint is
  `89d4c7388aa7e47d1609fcadee3d388e9d4f342d1ff4da02b76c113528e3d510`;
  and
- the typed termination-reason adjudication: all 61 linked Item 3.01 sections
  explicitly connect merger/acquisition completion to a listing or trading
  action. All 61 reasons are matched as `merger_or_acquisition`; effective
  market-status and terminal dates remain unresolved. Report SHA-256 is
  `c3ef6f8a0e51def3419b07d7f1303105a00df9e693ec4c6cbb0a2c4c1434224d`
  and logical fingerprint is
  `dbc47b9e31bd9043259b6849f8a92816790ad2b088c23e2b87e56e60d7d49fcf`.

Exact package identities and counts are retained in:

- [Five-year SEC filer/security candidate audit](../audits/five-year-sec-filer-security-link-candidate-2026-09-13.md)
- [SEC projection-readiness audit](../audits/sec-filer-security-projection-readiness-2026-09-13.md)
- [SEC fundamental-query readiness audit](../audits/sec-fundamental-query-readiness-census-2026-09-13.md)
- [SEC fundamental-projection readiness audit](../audits/sec-fundamental-projection-readiness-census-2026-09-13.md)
- [First-strategy source sample audit](../audits/strong-leader-pullback-source-acceptance-sample-2026-09-13.md)
- [First-strategy SEC lifecycle pilot audit](../audits/strong-leader-pullback-sec-lifecycle-pilot-2026-09-13.md)
- [First-strategy SEC document plan audit](../audits/strong-leader-pullback-sec-document-plan-2026-09-13.md)
- [First-strategy SEC document source audit](../audits/strong-leader-pullback-sec-document-source-2026-09-13.md)
- [First-strategy SEC content census audit](../audits/strong-leader-pullback-sec-document-content-census-2026-09-13.md)
- [First-strategy SEC Form 25 candidate audit](../audits/strong-leader-pullback-sec-form25-candidates-2026-09-13.md)
- [First-strategy SEC Form 15 candidate audit](../audits/strong-leader-pullback-sec-form15-candidates-2026-09-13.md)
- [First-strategy SEC transaction candidate audit](../audits/strong-leader-pullback-sec-transaction-candidates-2026-09-13.md)
- [First-strategy SEC case coverage census audit](../audits/strong-leader-pullback-sec-case-coverage-census-2026-09-13.md)
- [First-strategy SEC case adjudication audit](../audits/strong-leader-pullback-sec-case-adjudication-2026-09-13.md)
- [First-strategy SEC transaction-event adjudication audit](../audits/strong-leader-pullback-sec-transaction-event-adjudication-2026-09-13.md)
- [First-strategy SEC termination-reason adjudication audit](../audits/strong-leader-pullback-sec-termination-reason-adjudication-2026-09-13.md)
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
now frozen into 22 deterministic batches and all 219 source documents are in
formally reread private custody. The completed deterministic parse census
localizes lexical evidence without promoting a fact. Form 25, Form 15, and
transaction candidate extraction is complete. The stable-ID coverage census
now measures candidate material across all 64 cases while keeping all 512
case/field results unsupported. Point-in-time inline-XBRL cover adjudication
then matched the stable security/listing field for 61 structured transaction
cases without a ticker-only join. Typed transaction completion/date work is
now complete for all 61, including nine retained cover-date differences. The
termination reason is also now matched for all 61 through bounded Item 3.01
evidence. The next internal gate is consideration and party-relation
adjudication. LNW, REVG, and SAND remain quarantined. A commercial sample
remains limited to the frozen residual fields after that review. Massive
Starter is not the sole lifecycle authority.

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
