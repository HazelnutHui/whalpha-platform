# Historical Identity Extension Family Evidence V1

## Purpose

This contract publishes one small, explicit set of existing canonical
point-in-time Identity snapshots as immutable family evidence without
duplicating EOD evidence. Its current purpose is limited to exact-event-date
corporate-action resolution support.

## Plan contract

Contract version:
`identity-extension-historical-family-evidence-publication-plan/1.0`.

The plan contains:

- an exact ordered set of one to 16 session dates;
- exactly one `point_in_time_identity` family item;
- the deterministic evidence target, expected absent-state fingerprint,
  canonical evidence bytes and SHA-256;
- source artifact, source file and record counts;
- family-set and plan logical fingerprints;
- an exact one-file inventory delta; and
- literal zero/false authority fields for network access, plan-time canonical
  writes, Historical Coverage, research development and performance claims.

For every selected session, the evidence artifact uses the canonical Identity
snapshot manifest as its completion marker. The referenced payload set is the
Instrument, provider Identity and ticker Resolver partition manifests and
Parquet files. Existing formal snapshot and historical-evidence readers must
validate all referenced bytes.

## Planning rules

- The data root is exactly `/data/trading-intelligence-platform` on Dell.
- Sessions are caller-supplied, unique, sorted and never discovered by a
  latest-session fallback.
- The target and its operation-specific staging path must be absent.
- The plan is canonical JSON in a new owner-controlled direct child of `/tmp`,
  mode `0400`.
- Planning performs zero external requests and zero `/data` writes.

## Apply and recovery rules

Apply requires the exact approved plan SHA-256, plan logical fingerprint and
family-set fingerprint. Under the shared publication lock it verifies all
source bytes and the inventory outside the planned target, publishes through
an operation-bound staging directory, atomically renames the completed target
and formally rereads it.

`verify_then_complete` is valid only when the sole target already exists and
matches exactly. It then performs zero target writes. Recovery with no
completed target is rejected so that the recovery flag cannot become an
alternate Apply authority.

## Authority limits

This object is physical source evidence only. It does not update or replace
the current/reconciled EOD evidence, final Historical Coverage, lifecycle or
membership evidence, canonical corporate actions, adjustments, research
admission, Candidate output, Production data or website state.
