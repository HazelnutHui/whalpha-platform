# 2026-08-30 Sector Rotation Publication and Deployment Audit

## Scope and authority

The user authorized the complete reviewed publication chain: persistent Market
Intelligence Plan/Apply, Dashboard Snapshot Plan/Apply, serving-bundle build,
OCI preflight, deployment, and postflight. No provider acquisition, credential
read, scheduler activation, rollback, or unrelated infrastructure change was
performed.

## Formal lineage

- Canonical EOD and Identity: 2026-08-28, aligned, ordinary fresh, lag zero.
- Market Intelligence: `2026-08-28T135850Z-f483d6999a3e`, contract 1.3,
  pointer fingerprint
  `e0ba26070466254cb6dcaa8fed2b8d5637e9283f660dd70011c526abb2e58d3c`.
- Dashboard Snapshot: `2026-08-28T141747Z-83f9b629279c`, Snapshot 1.11 /
  Dashboard 2.8, pointer fingerprint
  `cd78a18de7fe102b694fbf624315b37c7648f4d0034e59c6d130e6a965ed9468`.
- Deployed source: `83f9b629279c0e7e949cf01b454ebfda60b35900`.
- Serving bundle: 52 checksummed files, logical fingerprint
  `6e2e08f1e3e9c3d06c3c069e751fce1b9ac2433837952aa2f95186f27c1721e0`.

The standard local bundle and the persistent custody bundle reread to the same
logical fingerprint. The persistent bundle uses `0700` directories and `0400`
files.

## Fail-closed corrections

The first persistent MI Apply stopped before writing because the CLI loader
retained an obsolete `/tmp`-only check after the writer and formal reader had
adopted governed persistent custody. The loader was aligned to the shared
custody validator, regression-tested, committed, and the plan was regenerated
against the new source revision before Apply.

The first OCI switch then failed its temporary-guest postflight because the
deployment validator stopped at Snapshot 1.10. Automatic rollback restored the
prior release. Review also found that the Candidate and Strategy browser
adapters stopped at 1.10. All three consumers were advanced to the exact
1.11/2.8 pair, and postflight was extended to source-bind
`sector-etf-rotation.json`. After tests and a new commit, a new Snapshot and
bundle were generated. The exact failed remote release was removed only after
its failed marker, manifest identity, and the restored current release were
verified.

## Verification

- Frontend: 106 tests passed; TypeScript/Vite Production build passed. The
  existing large-chunk performance warning remains non-blocking.
- Focused backend publication/custody tests: 27 passed.
- Focused Snapshot/deployment tests: 21 passed.
- Bundle checksum and formal readers passed.
- OCI dry-run, atomic Apply, Nginx validation, protected routes, temporary
  guest Session, Candidate, detail, Strategy, Sector Rotation, and logout
  postflight passed.
- Independent remote inspection found the target active, identical guest and
  credential route policy, zero staging/failed residue, zero failed service
  units, and no unexpected private listener. Remote state fingerprint:
  `50781e2bb39fa6ec56667c34b3455a9c9c60fcfe0c40ad323a1fb1397509bfcf`.
- Final `/data`: 694 files / 503,568,026 bytes, fingerprint
  `b32d70ae94098bf753282ff2eaa89f241bedc469995bfcd2ac97c2568ddb35ca`,
  zero symlinks and zero publication residue.

Password-based visual behavior remains a manual user check. The deployment
tool deliberately does not read or test a password; guest content and shared
route policy are the automated equal-capability evidence.
