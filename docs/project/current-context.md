# Authoritative Current Context

Operational state verified at: 2026-09-15T06:31:47Z

Deployment state verified at: 2026-09-15T11:53:28Z

Repository context updated at: 2026-09-15 UTC

This is the compact recovery source for a new task or device. Interpretation
belongs in [current status](current-status.md), sequencing in the
[roadmap](roadmap.md), and execution detail in the [changelog](changelog.md),
ADRs, and dated audits.

## Repository and infrastructure

| Field | Verified value |
| --- | --- |
| Workstation / user | `dell5820` / `hui` |
| Canonical repository | `/home/hui/projects/trading-intelligence-platform` |
| Branch | `main`; verify live HEAD before mutation |
| Public site | `https://whalpha.com/` |
| OCI alias | `whalpha-oci` |
| Active OCI release | `2026-09-15T115210Z-bb478169d42c` |
| Deployed source | `bb478169d42c1784f4c1ff3f05302f6dc0644f3e` |

Dell owns code, canonical data, governance, and heavy computation. OCI is the
bounded public-serving tier. A newer clean repository commit does not imply a
deployment.

Use `scripts/admin/report-current-context.sh` for a credential-free,
network-disabled reread. Run project Python through
`scripts/dev/run-project-python.sh` or repository-aware admin wrappers.

## Production

| Boundary | Verified value |
| --- | --- |
| Latest EOD / Snapshot | 2026-09-11; stale by one completed session at the 2026-09-14 review |
| Market Intelligence | `2026-09-11T205429Z-26cab64fabda`; contract 1.3 |
| Dashboard Snapshot | `2026-09-11T211340Z-26cab64fabda`; Snapshot 1.11 / Dashboard 2.8 |
| Market state | Primary 50.1578 Balanced; Secondary 50.1501 Balanced |
| Candidate display | 870 Primary / 924 Secondary; frozen Baseline V1, not Universe size |
| Languages | English default; Simplified Chinese; professional neutral Spanish |
| Access | guest and credential Sessions intentionally have identical capability |
| Failure policy | API/Snapshot failure closes without synthetic Production data |

The current release passed independent release, source, bundle, checksum,
service, protected-route, guest-flow, Candidate-route, logout, and residue
checks. Public landing content exposes the closed Factor Discovery V1 state;
the protected Lab exposes the replayed qualification report, all 12 exact
formulas, all eight Development decisions, the no-Alpha verdict, the retained
risk guard, protocol/report identities, limitations, and its locked authority
boundary. An unauthenticated Dashboard request redirects to Session entry.
Password login and final visual appearance remain manual checks.
Production Market Intelligence still consumes only 26 sessions and reports
`degraded_short_history`; canonical history is deeper.

## Canonical Dell data

| Family | Verified state |
| --- | --- |
| EOD | 1,255 contiguous XNYS sessions, 2021-09-13 through 2026-09-11; latest 9,971 rows; latest fingerprint `eec1f813851b378f47fbcd810728ed8b33b4748929ba85ff5d77e837bd12c904` |
| Identity | aligned to all EOD sessions plus one Identity-only partition; latest 10,000 instruments / 13,176 provider identities |
| Identity source time | 1,253 target sessions; 2026-08-13 and 2026-08-19 explicitly unbound |
| Membership | 3 signal-eligible plus 1,250 reconstructed research-only sessions; combined 1,253 / 1,255 |
| Corporate actions | 4,643 first-program exposures; 4,623 exact event-date assignments; 20 unassigned |
| Adjustment | 101,321 sparse split-only rows; 98,291 clear; 3,030 quarantined; neutral omitted rows and total-return coverage unproven |
| Lifecycle / terminal | 219 exact + 83 finite-interval references of 302 five-session paths; zero unbounded |
| Historical classification | complete point-in-time family absent |
| SEC fundamentals | four registered cutoff-aware queries and four strict as-operated projection sessions; engineering evidence only |
| Strict Historical Coverage | `rejected_data_blocked`; no strict research-ready manifest |
| Reconstructed research | 287 chronological sessions; 254 complete after warm-up/exclusions; `ready_for_reconstructed_development` |

Canonical inventory at this verification boundary: 21,025 files,
7,397,444,417 bytes, zero symlinks, zero publication residue; fingerprint
`b4f1dc83b5b26a6ccde3b5dffd47ac58de465fced41d129ef74c0e2282228ff7`.

Five-year price and stable-Identity depth is complete. That fact does not make
Membership, lifecycle, actions, adjustments, fundamentals, costs, or strict
Historical Coverage complete or as-operated.

## Active Universe

The provider-form Activation remains provisional and derives from analysis
session 2026-08-19.

| Universe | Members | Fingerprint |
| --- | ---: | --- |
| Primary | 1,718 CS | `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978` |
| Secondary | 1,831 = 1,718 CS + 113 ADRC | `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295` |

Activation pointer fingerprint:
`dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168`.
Provider form does not prove issuer operating structure or domicile. Future
Core/Broad activation remains deferred.

## Research state

Strong-Leader Pullback is a closed rejected historical program:

- the immutable development dataset contains 105 signal sessions, 166,313
  complete observations, and 498,939 independent 1/3/5-session label rows;
  Validation and Holdout labels remain zero;
- the fixed V1 study ended `inconclusive_evidence_floor`; and
- the only registered replacement ended `rejected_endpoint_instability`
  because its winner changed across terminal endpoint worlds.

No parameter, Validation transition, performance claim, or Candidate authority
was granted. The exact replacement replay matched report SHA-256
`070f7d8c6e29ad1e5e4c04d02ec3b19c1d0e7720c369d5ffdd991195186184b2`
and logical fingerprint
`086675c82efb4453f9bc71e88ad65fc0f64c411569313cd6ac3795ee0a6baaec`.
Detailed custody identities and source decisions remain in the dated Pullback
audits and archived contracts.

ADR 0274 makes **Factor Discovery -> Model Construction -> Strategy
Expression** the durable architecture. ADR 0273's 12 price/volume definitions
are the first finite outcome-blind catalog, not the permanent factor universe
or a promised model. Their deterministic value, coverage, distribution,
concentration, redundancy, and exact-replay report is complete under ADR 0275.
It contains 418,756 complete 12-factor vectors across 255 eligible sessions,
18,646 explicit quarantines, 66 pair checks, and zero pairs meeting the frozen
near-duplicate rule. Report SHA-256 is
`3767c39e327e8e3959d184ae8a16d2c5be3e1425fda416093b6aeefc51485e5e`;
logical fingerprint is
`fb92e95acb146af66fb4d9e286c96852374a51884936f5d69536c4accacdab02`.

ADR 0276 froze the separate screen before outcome access: 106 complete
Development sessions, 167,860 observations, five candidate-Alpha and three
risk-guard hypotheses, role-specific 3-session labels, 1/5-session decay,
Holm control, chronological stability, cost diagnostics, and a maximum two-
Alpha/one-risk candidate set. Its logical fingerprint is
`222b14dd358f5d4e6e260c77226b11f3ac2130f8850f96abe5ae5d48a07a8a60`.

The screen and one complete exact replay are now closed at
`closed_no_candidate_alpha`. All five candidate-Alpha factors and two risk
guards failed at least one frozen gate. `rolling_maximum_drawdown_10s` alone
passed as a risk guard; it cannot support a predictive model by itself. The
503,580 labels reconcile to 503,214 observed exact, 92 terminal exact, 46
terminal interval, 156 unavailable, and 72 unexecutable rows. Report logical
fingerprint is
`5e40cd9ab11dd20a98aabdf0834dc3cfb5c5a173a94929eca73891db8f8f789a`;
SHA-256 is
`184bc3f92f97809fbc69ea13877857d78a81472d0fbd15fa48bbce0891c62704`.
No prior strategy outcome was reused, and Validation and Holdout remain
untouched. Factor Catalog V1 is closed without retuning. The next research
action is a separately registered finite Factor Discovery campaign; Model
Construction and Strategy Expression remain locked.

ADR 0277 now binds all eight consumed factor-screen trials in cumulative
machine-verifiable ledger version
`whalpha.quant-research.discovery-trial-ledger/1.0.0`; its logical fingerprint
is `502834abe5bfc171f80206138b36c8bf973c9fcc84078592b8dc92ccd5bee368`.
It records five failed candidate-Alpha trials, two failed risk guards, one
retained risk guard, and zero outcome-tested conditioner interactions. A next
campaign must append its hypotheses in a new ledger version before any new
outcome access and must disclose that its design is adaptive to consumed V1
Development evidence.

ADR 0278 registers outcome-blind Factor Catalog V2 under logical fingerprint
`6620000334a0a8bd23103341dfc1958d57c712a063dff0a39e23ffc82d51bed5`.
Its eight exact daily definitions use a 127-session maximum source window and
separate four candidate Alpha measurements, one setup conditioner, one
applicability input, and two risk guards. They bind their relationship to
consumed V1 trials and contain no outcome, factor admission, model, strategy,
Validation, Holdout, or Product authority. No real V2 factor value or forward
return has been used for selection. ADR 0279 now freezes the independent V2
outcome-blind qualification protocol at logical fingerprint
`b74214155cc148d1e0d37c530ab4fea2f385af1a81237b901eec45e1fee2eb0b`.
It uses per-stable-ID stock quarantine, complete-session SPY failure, fixed
within-group redundancy priority, and one exact replay. The first report and
replay are byte-identical at logical fingerprint
`bed79513febf21dcf585a2e953c43fb66cb02824cd509800da39af452c0380ef`
and SHA-256
`a95f2ff95ee7d2083602568c457a929d33c3636794d0e991310bd042239a1d79`.
Status is `rejected_data_or_implementation`: canonical split action and
adjustment evidence start on 2025-06-23, but the 127-session V2 source interval
starts on 2024-12-17. This closes 167,294 early benchmark-dependent paths and
leaves 266,335 / 437,402 complete vectors. No V2 factor is admitted or
registered for an outcome screen. The next action is a versioned extension
from retained five-year split evidence, not a gate or formula change.

The deployed Candidate score, Entry Geometry, and six technical Strategy
Channels remain frozen, transparent, unvalidated **Baseline V1** compatibility
behavior. They are not expected-return models and do not define the future
research taxonomy. Quant Research Lab is the sole core workspace; Model-Driven
Equity Selection is its future downstream consumer.

## Automation and standing boundaries

The installed daily wake timer is read-only. It performs no fetch, Apply,
analytics, publication, deployment, credential access, or alert delivery. No
unattended write-capable scheduler is installed; SMTP is unconfigured. The
guarded manual daily chain works end to end.

There is no standing authority for provider acquisition, `/data` mutation,
Validation or Holdout access, model activation, publication, deployment,
scheduler mutation, order execution, or destructive cleanup. A user may grant
scoped authority for a specific action. The completed website synchronization
changed presentation only; it did not change data or research authority.

## Cross-device continuity

- Windows has its own passwordless SSH key and saved Dell project.
- A future Mac must join the same Tailscale network and generate a separate SSH
  key; never copy the Windows private key.
- Add only the Mac public key to Dell, configure alias `dell5820`, save this
  canonical repository path, and run the read-only context report.
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
