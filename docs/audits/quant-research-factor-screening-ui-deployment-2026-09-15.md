# Factor Screening UI Deployment Audit — 2026-09-15

## Scope

Publish the completed Factor Catalog V1 Development-screen evidence to the
trilingual public entry and protected Quant Research Lab without changing the
immutable 2026-09-11 market Snapshot, Market Intelligence publication,
Baseline Candidate calculations, research result, or authority state.

## Product projection

The deployed UI now exposes:

- `closed_no_candidate_alpha` as the outer Factor Discovery V1 state;
- zero of five candidate-Alpha factors admitted;
- one of three risk guards retained;
- all eight registered decisions with robust effect, 90% lower bound,
  Holm-adjusted p-value, and failed-gate count;
- the 106-session / 167,860-observation / 503,580-label cohort;
- the frozen horizon, bootstrap, multiplicity, and cost design;
- Development-only, reconstructed-membership, classification, Regime,
  split-neutral, and execution-calibration limits;
- exact protocol, report, SHA-256, and implementation identities; and
- explicit continuing locks on model, strategy, Validation, Holdout, Candidate,
  and trading authority.

English, Simplified Chinese, and neutral professional Spanish present the same
state. Guest and credential Sessions remain capability-identical.

## Verification

- Frontend: 22 files / 126 tests passed.
- Production TypeScript and Vite build passed.
- The checked-in public projection was programmatically reconciled field by
  field against the owner-only immutable report before commit.
- Source commit: `bb478169d42c1784f4c1ff3f05302f6dc0644f3e`
- Release: `2026-09-15T115210Z-bb478169d42c`
- Bundle contract: `oci-dashboard-serving-bundle/1.0`
- Bundle logical fingerprint:
  `38c7189a69deefe9648a68e90a51017a765e898641e12749c3cdd185b54fbf80`
- Manifest SHA-256:
  `6b5e478fa6aa5f39bf8b79f920e7c025d92eea8889b983bc74770d3275211987`
- Checksums SHA-256:
  `53706a77959bb99462bcec4901125f724734532495499f919d6f613450e27189`

Independent postflight at 2026-09-15T11:53:28Z proved the exact current
release and source, protected routes, a bounded guest Session, equal route
policy, active Nginx and localhost-only Auth Service, zero failed units, zero
unexpected private listeners, and zero staging or failed-release residue.

Password login and final visual appearance remain manual user checks because
the deployment audit did not read or use credentials.
