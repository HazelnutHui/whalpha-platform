# Reconciled EOD Historical Mechanics Evidence Audit — 2026-09-12

## Boundary

Adapt the canonical ADR 0207 Reconciled EOD Edition and its exact same-session
Identity snapshots into read-only Historical Dataset Coverage Evidence
candidates. This run performed no evidence publication, Historical Coverage
publication, provider request, research evaluation, Production change, or
website deployment.

The implementation is governed by ADR 0210 and source revision
`ed56e81cd36dc7f5bf80450d65ef9bcaa58e3eba`. The caller named both:

- edition ID `reconciled-eod-v12-20210913-20260812-c798e58`; and
- interval fingerprint
  `098ff756a463c0bf142d9ce597375e3a0574db02ca641fcdcef9b6e72cb6b5e3`.

There was no latest-edition inference.

## Validation mechanics

The EOD candidate binds the edition interval completion marker and the exact
sorted set of all 1,234 session manifests and 1,234 Parquet files. The reader
formally reread every EOD row, verified the sealed interval and session
manifests, exact file sets, per-session physical hashes, record counts, source
provenance, and interval bindings.

The Identity candidate formally reread the instrument, provider-identity, and
resolver partitions for every edition session. Each canonical snapshot had to
match the same-session Identity fingerprint and provider already sealed in the
corresponding EOD session manifest.

Eight bounded Dell worker processes preserved input order and deterministic
fingerprints. The completed run took 374.70 seconds wall time, 2,898.51
seconds user CPU, and 15.53 seconds system CPU. A preceding serial measurement
was stopped without output or mutation after demonstrating sustained
single-core saturation; one accidentally duplicated owned validation process
was detected and terminated, leaving no process or filesystem residue.

## Exact result

Status: `price_identity_mechanics_only`.

EOD Price Bar candidate:

- 1 artifact / 1,234 sessions / 10,376,263 records;
- interval 2021-09-13 through 2026-08-12;
- evidence logical fingerprint
  `b65ee35bb65796dab501d4e59df132bffc566452c713bb18e8659401b632b0a5`;
- proposed evidence bytes SHA-256
  `05944964a5a1f85c0b403c5c29a2261c5ab6dee8b2a0788ab0bed94b509fde2e`;
- status `validated_not_published`.

Point-in-time Identity candidate:

- 1,234 artifacts / 1,234 sessions / 10,472,243 instrument-snapshot records;
- interval 2021-09-13 through 2026-08-12;
- evidence logical fingerprint
  `faaa73bceace816d91a5a2483714055d20c48091fe4fc8bfbcde8c27d8b647db`;
- proposed evidence bytes SHA-256
  `160a5c8184068e06a8d5432eeea687bdd8ac2a12a645791b0d973281068a18df`;
- status `validated_not_published`.

The complete report logical fingerprint is
`a143da919d89ceb89353c0e59b31f2dfaec69e387cdc4c6b6f0cedef6522a4f4`.
External requests and Production or canonical write counts were zero.

The already published legacy current-EOD and Identity family evidence remains
separate: it covers only 304 sessions from 2025-06-23 through 2026-09-04 with
logical fingerprints `923f27a8fa4e85c6d20b5c8ac0804f17dbab7437b350f02d54fea2ed5293aeb1`
and `d2225da8d4ffd2b7e83ff98b72f75647503690a2aff2c87731c00b115b65fefb`.
It was not reused or overwritten.

## Remaining blockers and next boundary

The two validated candidates do not complete the research foundation.
Daily point-in-time Membership, canonical corporate-action coverage,
instrument lifecycle/terminal outcomes, complete adjustment-ledger
reconciliation, and final Historical Coverage remain absent or incomplete.

The next bounded action is an edition-specific, no-write publication plan for
exactly these two evidence manifests. Any canonical evidence Apply remains a
separate, explicitly reviewed mutation. Final Historical Coverage and research
admission cannot proceed merely because the two candidates validate.
