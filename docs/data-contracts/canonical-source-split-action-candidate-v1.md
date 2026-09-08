# Canonical-Source Split Action Candidate V1

Contract: `canonical-source-split-action-candidate/1.0`.

This is the owner-only, non-canonical bridge from ADR 0174 source custody to a
future canonical split-action family. It supersedes the temporary resolution-
shadow candidate as the active implementation input but does not delete or
reinterpret that historical audit evidence.

## Inputs

- one exact canonical Corporate Action Source Publication marker;
- every source partition and Identity evidence byte transitively referenced by
  that marker;
- an explicit basis session equal to the marker's bounded end date;
- one clean 40-character implementation revision; and
- a deterministic calculation timestamp no earlier than source publication.

No resolution-shadow path, provider request, current ticker fallback, nearest-
session fallback, or current-Universe filter is accepted.

## Records and gates

Resolved active split-like observations are grouped by stable `instrument_id`
and effective date. Exact Decimal ratio math remains:

```text
price multiplier  = product(split_from) / product(split_to)
volume multiplier = product(split_to) / product(split_from)
```

One-action groups are `clear_candidate`. Multiple same-date groups are
`quarantined`, including reciprocal groups whose diagnostic composed factor is
one. The factor remains visible for audit but is not ledger-admissible.

Unresolved source observations remain unassigned. A scan of the exact Identity
evidence may associate their historical ticker with one or more possible stable
IDs only to expand the quarantine set. No such association promotes the source
row or proves identity.

## Output and custody

One `candidate.json` below `/tmp` binds:

- source marker path, physical SHA-256, and logical fingerprint;
- Identity evidence path, physical SHA-256, logical fingerprint, and session
  count;
- implementation revision, date range, basis, source cutoff, and calculation
  time;
- resolved-active/quarantined source counts and clear/quarantined event-group
  counts;
- every grouped event and unresolved possible-impact stable ID; and
- explicit non-authority, coverage, point-in-time, total-return, network,
  publication, analytics, and deployment fields.

The directory is `0700`, the file is `0400`, and formal reread validates the
exact file set, order, uniqueness, counts, hashes, admission status, ratio math,
and logical fingerprint. Exact reruns are idempotent; conflicting content
fails closed.

## Interpretation boundary

The artifact is sparse event evidence, not a canonical Corporate Action,
Adjustment Ledger, neutral-factor coverage statement, Historical Coverage,
signal input, performance result, Snapshot, or website payload. It remains
`bounded_query_snapshot_only` and `outcome_reconciliation_only`. A later
inventory-bound publication decision must preserve unresolved-impact and
multiple-event quarantine.

## Recorded Dell execution

The clean-revision 2026-09-08 run on
`c46cc3f4ee883ed7ef4c850ca146b6e3807f87bb` produced 708 event groups,
including 707 clear candidates and one multiple-event quarantine, plus 43
possible-impact stable IDs. The 602,491-byte file has SHA-256
`8ef0f95dce94a041be7e5c18d69bb959ae037e52e6f22d41c2401ab92f160c83`
and logical fingerprint
`026e9087ad4ef7ec891036cbe84ee4b3bde47cb1b1349fa858fc2e090b74f132`.
Formal reread passed and canonical state remained unchanged.
