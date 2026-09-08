# Canonical Split Action Publication Audit — 2026-09-08

## Result

The ADR 0176 split-only canonical fact family was published successfully on
`dell5820` from clean main
`cccbec4850736da90e24fc5277b4c8e61bffb3ab`.

This is a provider-neutral action-fact publication, not an Adjustment Ledger,
neutral-factor coverage claim, total-return series, point-in-time signal input,
research result, Snapshot, bundle, or Production deployment.

## Inputs and derivation

- canonical source publication fingerprint:
  `7b13691e22b7e815a773ed1d575ed580bbee897eb0dbf10c41e4e0862a95b1d1`;
- canonical-source split candidate SHA-256:
  `8ef0f95dce94a041be7e5c18d69bb959ae037e52e6f22d41c2401ab92f160c83`;
- candidate logical fingerprint:
  `026e9087ad4ef7ec891036cbe84ee4b3bde47cb1b1349fa858fc2e090b74f132`;
- source date range: 2025-06-23 through 2026-09-04; and
- pre-Apply whole-data fingerprint:
  `f3117ceaab4ea25ea60c23886d171373ae15dfcee30cff6ac784af02b7e1670b`.

The formal derivation consumed all 709 resolved active split observations
exactly once and rejected any other resolved-active split key. It emitted 708
stable-ID/effective-date groups: 707 one-action groups and one two-action
quarantine. It did not assign any of the 1,240 unresolved split observations.

## Plan

- plan path:
  `/tmp/whalpha-canonical-split-action-publication-plan-20260908T233500Z.json`;
- plan SHA-256:
  `48dacad33ece6e855bf2f787086b763f6ce5cee6b0b877e419961e958ababe0c`;
- plan logical fingerprint:
  `d5b8633da94536817c1681fec192c580f154d695930017d7a5678c09ad1c0055`;
- planned target publication fingerprint:
  `76f017a1547e20b997e40cd1e61497b71c749a94e88a8632a3898fe84c106218`;
- actions logical fingerprint:
  `f2f4e54da4d79ba44be6170b386289b3cd6a8070c840a11a4ad3a86c8a79eb45`;
- Parquet SHA-256:
  `1b18f02cca55e09bc5ec907a510436f18c9cf2bb8d185f9fd421b1423a52dfd4`;
  and
- exact inventory delta: two files / 118,592 bytes.

Independent plan reread matched the source, candidate, rows, manifest, artifact
hashes, target absence, counts, and authority fields. Candidate custody was
`0700` / `0400` and the plan file was `0400`.

## Apply and recovery

The shared-lock, network-prohibited Apply reported:

- 709 rows: 707 active / two quarantined;
- 708 groups: 707 clear / one quarantined;
- 43 possible-impact stable IDs and 1,240 unresolved source actions;
- two published files / 118,592 bytes;
- zero overwritten and zero deleted files;
- outside-target fingerprint exactly equal to the pre-state; and
- post-state fingerprint
  `6d6ef7c214087130290ae151a53b7f8b7be018ffcd1cb42c9912bbcf4c843915`.

The exact same Apply was then repeated. It formally reread and reused both
files, published zero files / zero bytes, and returned `verified_existing`.

## Postflight

Current-context report 1.8 formally reread the publication and reported:

- custody state `canonical_split_only_bounded_query_snapshot`;
- `/data` 4,202 files / 2,151,599,005 bytes;
- zero symlinks and zero publication residue;
- blocker `canonical_corporate_action_coverage_incomplete`;
- absent Adjustment Ledger; and
- research status `data_blocked`, with strategy development and performance
  authority false.

Repository and Production state were otherwise unchanged. OCI still serves
release `2026-09-08T171914Z-ca2d34d50692`; no analytics, Snapshot, bundle,
deployment, or scheduler operation occurred.
