# Canonical Split Adjustment Publication V1

Contracts:

- `canonical-split-adjustment-publication/1.0`
- `canonical-split-adjustment-apply-plan/1.0`

Methodology: `canonical-split-ratio-to-basis-v1`.

## Scope

The publication contains only canonical EOD rows whose path to one explicit
basis crosses an active split event or a quarantine event. It reuses
`AdjustmentLedgerEntryV1` rows and adds a source-bound immutable publication
manifest. It is not complete adjustment coverage, a neutral-factor map, a
total-return series, or a performance-eligible research panel.

## Source binding

The manifest binds:

- exact canonical split-action manifest path, SHA-256, and logical fingerprint;
- exact canonical EOD family-evidence path, SHA-256, logical fingerprint,
  session range, session count, and source record count;
- clean implementation revision, source cutoff, calculation time, basis, and
  methodology; and
- selected, projected, clear, quarantined, action, unresolved, and possible-
  impact counts.

The date range of both inputs must match. Source cutoff is the later of the two
publication times. Every selected EOD Parquet byte is already transitively
bound by the formal family evidence before its stable-ID/session projection is
read.

## Row rules

For source session `s`, effective event date `e`, and basis `B`, include an
event only when `s < e <= B`.

Clear factors are:

```text
split price multiplier to basis  = product(split_from) / product(split_to)
split volume multiplier to basis = product(split_to) / product(split_from)
```

The source-action-set fingerprint hashes every exact included canonical action
descriptor. A crossing conflict or unresolved possible impact changes the row
to `quarantined`, removes both factors, and fingerprints the quarantine evidence
instead. Quarantine takes precedence.

Every row has `total_return_adjustment_status=unavailable`, no total-return
multiplier, and explicit flags for sparse scope, outcome-only use, unavailable
total return, and unauthorized absent-row neutrality. The overall quality
status therefore remains pending even when its split factor is clear.

## Candidate custody

The candidate contains exactly `part-00000.parquet` and `manifest.json` in an
owner-only `0700` directory with `0400` files. The manifest binds the Parquet
physical SHA-256, bytes, and Decimal-normalized logical row fingerprint. Formal
reread validates schema, order, business-key uniqueness, counts, provenance,
statuses, flags, and date boundaries. Exact reruns are idempotent; conflicting
or tampered bytes fail closed.

## Canonical path

ADR 0178 publishes the immutable target below:

```text
market-data/adjustment-ledger/schema_version=1/
  methodology_version=canonical-split-ratio-to-basis-v1/
  basis_session=<YYYY-MM-DD>/coverage_id=<publication-fingerprint>/
```

Publication does not authorize factor one for absent rows, total return,
Historical Coverage, research performance, analytics, Snapshot, or deployment.

## Plan and Apply

The plan preserves the candidate's original derivation revision and separately
binds the clean planner revision. It fully rederives the candidate from its
exact canonical action and EOD evidence, then binds the two owner-only source
files, absent content-addressed target, whole `/data` pre-state, bytes, hashes,
and every non-authority field.

Apply rechecks the plan and derivation, takes the shared Dell data lock,
requires the exact inventory pre-state, copies both files into a deterministic
staging directory, fsyncs them, and atomically renames the complete directory.
It formally rereads canonical custody and proves the outside-target inventory
unchanged. Exact completed targets are zero-write verified recovery; partial,
symlinked, conflicting, tampered, or drifted states fail closed.
