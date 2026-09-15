# Authoritative Current Context

Operational state verified at: 2026-09-15T06:31:47Z

Deployment state verified at: 2026-09-15T08:35:17Z

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
| Active OCI release | `2026-09-15T083410Z-45b1d4dfedca` |
| Deployed source | `45b1d4dfedcaffc92e2a11f21ecf208409347199` |

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
checks. Public landing content independently exposes the new Factor Discovery
direction; an unauthenticated Dashboard request redirects to Session entry.
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
or a promised model. No factor value, factor Alpha, model, strategy expression,
or three-layer Product authority exists yet.

The next research action is to implement the factor definitions and produce
zero-outcome coverage, missingness, distribution, concentration, redundancy,
and replay evidence. A separate registered screening protocol must freeze
labels, trial count, multiplicity, and stopping rules before any new outcome is
read. Model Construction and Strategy Expression remain locked until their
preceding evidence qualifies.

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
